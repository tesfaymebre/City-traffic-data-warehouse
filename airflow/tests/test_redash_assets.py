"""Redash dashboard asset smoke tests."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REDASH_DIR = ROOT / "redash"
QUERIES_DIR = REDASH_DIR / "queries"
CONFIG_PATH = REDASH_DIR / "dashboard.yml"


def test_redash_query_files_exist_and_reference_marts():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    for query_spec in config["queries"]:
        sql_path = QUERIES_DIR / query_spec["file"]
        assert sql_path.exists(), f"Missing query file: {query_spec['file']}"
        sql = sql_path.read_text(encoding="utf-8")
        assert "marts." in sql, f"{query_spec['file']} should query marts schema"


def test_redash_dashboard_config_structure():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert config["dashboard"]["name"] == "City Traffic Overview"
    assert config["data_source"]["type"] == "pg"
    assert len(config["queries"]) >= 5
    widget_queries = [q for q in config["queries"] if "widget" in q]
    assert len(widget_queries) >= 4


def test_redash_bootstrap_script_exists():
    bootstrap = ROOT / "scripts" / "redash" / "bootstrap_redash.py"
    content = bootstrap.read_text(encoding="utf-8")
    assert bootstrap.exists()
    assert "RedashClient" in content
    assert "REDASH_API_KEY" in content
