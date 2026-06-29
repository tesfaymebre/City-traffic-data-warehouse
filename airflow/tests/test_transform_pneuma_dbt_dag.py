"""dbt transform DAG structure smoke tests."""

from pathlib import Path


def test_transform_pneuma_dbt_dag_structure():
    dag_file = Path(__file__).resolve().parents[1] / "dags" / "transform_pneuma_dbt_dag.py"
    content = dag_file.read_text(encoding="utf-8")

    assert dag_file.exists()
    assert 'dag_id="transform_pneuma_dbt"' in content
    for task_id in (
        "dbt_deps",
        "dbt_source_freshness",
        "dbt_build",
        "dbt_docs_generate",
    ):
        assert f'task_id="{task_id}"' in content
    assert "dbt_source_freshness >> dbt_build >> dbt_docs_generate" in content
