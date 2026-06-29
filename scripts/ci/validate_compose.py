#!/usr/bin/env python3
"""Validate docker-compose.yml structure (mirrors CI)."""

from __future__ import annotations

import pathlib
import sys

import yaml

REQUIRED_SERVICES = {"postgres", "airflow-webserver", "airflow-scheduler", "redash-server"}
COMPOSE_PATH = pathlib.Path("docker/docker-compose.yml")


def main() -> None:
    if not COMPOSE_PATH.exists():
        print(f"Missing compose file: {COMPOSE_PATH}")
        sys.exit(1)

    data = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    if "services" not in data:
        print("docker-compose.yml must define services")
        sys.exit(1)

    missing = REQUIRED_SERVICES - set(data["services"])
    if missing:
        print(f"Missing services: {missing}")
        sys.exit(1)

    print("docker-compose.yml structure is valid.")


if __name__ == "__main__":
    main()
