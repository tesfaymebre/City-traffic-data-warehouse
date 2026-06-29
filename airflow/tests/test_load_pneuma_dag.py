"""Airflow DAG structure smoke tests (no apache-airflow import required locally)."""

from pathlib import Path


def test_load_pneuma_dag_structure():
    dag_file = Path(__file__).resolve().parents[1] / "dags" / "load_pneuma_dag.py"
    content = dag_file.read_text(encoding="utf-8")

    assert dag_file.exists()
    assert 'dag_id="load_pneuma_raw"' in content
    for task_id in (
        "inventory_raw_files",
        "discover_csv_files",
        "load_all_csv_files",
        "validate_load_counts",
    ):
        assert f'task_id="{task_id}"' in content

    assert "inventory_raw_files >> discover_csv_files_task" in content
    assert "trigger_dbt_transform" in content
    assert "PostgresHook" in content
    assert "deploy_env" in content
