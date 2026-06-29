#!/usr/bin/env python3
"""Load pNEUMA CSV files into the warehouse raw schema (ELT load step)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

# Allow imports when executed from repo root or /opt/airflow/scripts
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pneuma_parser import FileMetadata, iter_vehicle_rows, parse_filename  # noqa: E402

ENV_TO_DATABASE = {
    "dev": "traffic_dev",
    "staging": "traffic_staging",
    "prod": "traffic_prod",
}

BATCH_SIZE = 5_000


def warehouse_database(deploy_env: str) -> str:
    database = ENV_TO_DATABASE.get(deploy_env)
    if database is None:
        raise ValueError(f"Unknown DEPLOY_ENV '{deploy_env}'. Use dev, staging, or prod.")
    return database


def connect(deploy_env: str):
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=warehouse_database(deploy_env),
    )


def ensure_tables(connection) -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS raw.vehicle_tracks (
        track_id INTEGER NOT NULL,
        vehicle_type VARCHAR(50),
        traveled_distance DOUBLE PRECISION,
        avg_speed DOUBLE PRECISION,
        source_file VARCHAR(255) NOT NULL,
        capture_date DATE,
        area_code VARCHAR(20),
        time_window_start VARCHAR(10),
        time_window_end VARCHAR(10),
        loaded_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (track_id, source_file)
    );

    CREATE TABLE IF NOT EXISTS raw.trajectory_points (
        track_id INTEGER NOT NULL,
        source_file VARCHAR(255) NOT NULL,
        point_index INTEGER NOT NULL,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        speed DOUBLE PRECISION,
        lon_acceleration DOUBLE PRECISION,
        lat_acceleration DOUBLE PRECISION,
        recorded_at DOUBLE PRECISION,
        PRIMARY KEY (track_id, source_file, point_index)
    );

    CREATE INDEX IF NOT EXISTS idx_trajectory_points_source
        ON raw.trajectory_points (source_file);
    """
    with connection.cursor() as cursor:
        cursor.execute(ddl)
    connection.commit()


def delete_existing_source(connection, metadata: FileMetadata) -> None:
    """Idempotent reload: remove prior rows for the same source file."""
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM raw.trajectory_points WHERE source_file = %s",
            (metadata.source_file,),
        )
        cursor.execute(
            "DELETE FROM raw.vehicle_tracks WHERE source_file = %s",
            (metadata.source_file,),
        )
    connection.commit()


def load_csv(path: Path, deploy_env: str) -> dict[str, int]:
    metadata = parse_filename(path)
    track_count = 0
    point_count = 0

    with connect(deploy_env) as connection:
        ensure_tables(connection)
        delete_existing_source(connection, metadata)

        track_buffer: list[tuple] = []
        point_buffer: list[tuple] = []

        with connection.cursor() as cursor:
            for track, points in iter_vehicle_rows(path):
                track_buffer.append(
                    (
                        track.track_id,
                        track.vehicle_type,
                        track.traveled_distance,
                        track.avg_speed,
                        metadata.source_file,
                        metadata.capture_date,
                        metadata.area_code,
                        metadata.time_start,
                        metadata.time_end,
                    )
                )
                track_count += 1

                for point in points:
                    point_buffer.append(
                        (
                            point.track_id,
                            metadata.source_file,
                            point.point_index,
                            point.latitude,
                            point.longitude,
                            point.speed,
                            point.lon_acceleration,
                            point.lat_acceleration,
                            point.recorded_at,
                        )
                    )
                    point_count += 1

                    if len(point_buffer) >= BATCH_SIZE:
                        _flush_points(cursor, point_buffer)
                        point_buffer.clear()

                if len(track_buffer) >= 500:
                    _flush_tracks(cursor, track_buffer)
                    track_buffer.clear()

            if track_buffer:
                _flush_tracks(cursor, track_buffer)
            if point_buffer:
                _flush_points(cursor, point_buffer)

        connection.commit()

    return {
        "tracks": track_count,
        "points": point_count,
        "source_file": metadata.source_file,
        "database": warehouse_database(deploy_env),
    }


def _flush_tracks(cursor, rows: list[tuple]) -> None:
    execute_values(
        cursor,
        """
        INSERT INTO raw.vehicle_tracks (
            track_id, vehicle_type, traveled_distance, avg_speed,
            source_file, capture_date, area_code, time_window_start, time_window_end
        ) VALUES %s
        ON CONFLICT (track_id, source_file) DO UPDATE SET
            vehicle_type = EXCLUDED.vehicle_type,
            traveled_distance = EXCLUDED.traveled_distance,
            avg_speed = EXCLUDED.avg_speed,
            capture_date = EXCLUDED.capture_date,
            area_code = EXCLUDED.area_code,
            time_window_start = EXCLUDED.time_window_start,
            time_window_end = EXCLUDED.time_window_end,
            loaded_at = NOW()
        """,
        rows,
    )


def _flush_points(cursor, rows: list[tuple]) -> None:
    execute_values(
        cursor,
        """
        INSERT INTO raw.trajectory_points (
            track_id, source_file, point_index, latitude, longitude,
            speed, lon_acceleration, lat_acceleration, recorded_at
        ) VALUES %s
        ON CONFLICT (track_id, source_file, point_index) DO UPDATE SET
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            speed = EXCLUDED.speed,
            lon_acceleration = EXCLUDED.lon_acceleration,
            lat_acceleration = EXCLUDED.lat_acceleration,
            recorded_at = EXCLUDED.recorded_at
        """,
        rows,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load pNEUMA CSV into raw schema")
    parser.add_argument("csv_path", type=Path, help="Path to pNEUMA CSV file")
    parser.add_argument(
        "--env",
        default=os.environ.get("DEPLOY_ENV", "dev"),
        choices=sorted(ENV_TO_DATABASE),
        help="Target warehouse environment",
    )
    args = parser.parse_args()

    if not args.csv_path.exists():
        raise SystemExit(f"File not found: {args.csv_path}")

    stats = load_csv(args.csv_path, args.env)
    print(
        f"Loaded {stats['tracks']} tracks and {stats['points']} points "
        f"from {stats['source_file']} into {stats['database']}"
    )


if __name__ == "__main__":
    main()
