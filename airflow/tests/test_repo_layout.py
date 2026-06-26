"""Smoke tests for repository scaffolding."""


def test_repo_layout_exists():
    """Ensure core project directories are present."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    expected = ["airflow/dags", "dbt/models", "docker", "scripts", "data/raw"]
    for relative in expected:
        assert (root / relative).exists(), f"Missing directory: {relative}"
