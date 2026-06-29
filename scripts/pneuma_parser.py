"""Parse pNEUMA wide-format trajectory CSV files."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# Filename example: 20181024_d1_0830_0900.csv
FILENAME_PATTERN = re.compile(
    r"^(?P<date>\d{8})_(?P<area>[a-zA-Z0-9]+)_(?P<time_start>\d{4})_(?P<time_end>\d{4})\.csv$"
)

STATIC_FIELD_COUNT = 4
POINT_FIELD_COUNT = 6


@dataclass(frozen=True)
class FileMetadata:
    source_file: str
    capture_date: str | None
    area_code: str | None
    time_start: str | None
    time_end: str | None


@dataclass(frozen=True)
class VehicleTrack:
    track_id: int
    vehicle_type: str
    traveled_distance: float
    avg_speed: float


@dataclass(frozen=True)
class TrajectoryPoint:
    track_id: int
    point_index: int
    latitude: float
    longitude: float
    speed: float
    lon_acceleration: float
    lat_acceleration: float
    recorded_at: float


def parse_filename(path: Path) -> FileMetadata:
    """Extract area/date/time metadata encoded in the pNEUMA filename."""
    match = FILENAME_PATTERN.match(path.name)
    if not match:
        return FileMetadata(
            source_file=path.name,
            capture_date=None,
            area_code=None,
            time_start=None,
            time_end=None,
        )

    groups = match.groupdict()
    raw_date = groups["date"]
    formatted_date = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    return FileMetadata(
        source_file=path.name,
        capture_date=formatted_date,
        area_code=groups["area"],
        time_start=groups["time_start"],
        time_end=groups["time_end"],
    )


def _strip(value: str) -> str:
    return value.strip()


def _to_float(value: str) -> float:
    return float(_strip(value))


def _to_int(value: str) -> int:
    return int(_strip(value))


def iter_vehicle_rows(path: Path) -> Iterator[tuple[VehicleTrack, list[TrajectoryPoint]]]:
    """
    Yield each vehicle track and its trajectory points from a wide pNEUMA CSV row.

    Row layout:
      track_id, type, traveled_d, avg_speed,
      then repeating (lat, lon, speed, lon_acc, lat_acc, time) for each sample.
    """
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter=";")
        next(reader)  # header describes one point template only

        for row in reader:
            if len(row) < STATIC_FIELD_COUNT + POINT_FIELD_COUNT:
                continue

            track = VehicleTrack(
                track_id=_to_int(row[0]),
                vehicle_type=_strip(row[1]),
                traveled_distance=_to_float(row[2]),
                avg_speed=_to_float(row[3]),
            )

            points: list[TrajectoryPoint] = []
            point_index = 0
            for offset in range(STATIC_FIELD_COUNT, len(row), POINT_FIELD_COUNT):
                chunk = row[offset : offset + POINT_FIELD_COUNT]
                if len(chunk) < POINT_FIELD_COUNT:
                    break

                points.append(
                    TrajectoryPoint(
                        track_id=track.track_id,
                        point_index=point_index,
                        latitude=_to_float(chunk[0]),
                        longitude=_to_float(chunk[1]),
                        speed=_to_float(chunk[2]),
                        lon_acceleration=_to_float(chunk[3]),
                        lat_acceleration=_to_float(chunk[4]),
                        recorded_at=_to_float(chunk[5]),
                    )
                )
                point_index += 1

            yield track, points
