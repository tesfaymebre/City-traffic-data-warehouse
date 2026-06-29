"""Tests for pNEUMA CSV parsing."""

from pathlib import Path

from scripts.pneuma_parser import iter_vehicle_rows, parse_filename

DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
    / "20181024_d1_0830_0900.csv"
)


def test_parse_filename_extracts_metadata():
    metadata = parse_filename(Path("20181024_d1_0830_0900.csv"))
    assert metadata.capture_date == "2018-10-24"
    assert metadata.area_code == "d1"
    assert metadata.time_start == "0830"
    assert metadata.time_end == "0900"


def test_iter_vehicle_rows_reads_first_track():
    if not DATA_FILE.exists():
        return

    track, points = next(iter(iter_vehicle_rows(DATA_FILE)))
    assert track.track_id == 1
    assert track.vehicle_type == "Car"
    assert len(points) > 100
    assert points[0].latitude > 37.0
    assert points[0].recorded_at == 0.0
