#!/usr/bin/env python3
"""Validate YAML syntax for all project *.yml / *.yaml files (mirrors CI)."""

from __future__ import annotations

import pathlib
import sys

import yaml

SKIP_PARTS = {".git", "dbt_packages", "target"}


def validate_yaml_files() -> list[str]:
    errors: list[str] = []
    root = pathlib.Path(".")

    for pattern in ("*.yml", "*.yaml"):
        for path in root.rglob(pattern):
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"{path}: {exc}")

    return errors


def main() -> None:
    errors = validate_yaml_files()
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("All YAML files are valid.")


if __name__ == "__main__":
    main()
