"""
Airflow DAG: load pNEUMA trajectory CSVs into the warehouse raw schema.

Environment separation (dev / staging / prod):
  - Airflow Variable `deploy_env` selects the target warehouse database.
  - Postgres connections: postgres_dev, postgres_staging, postgres_prod.
  - Falls back to container env DEPLOY_ENV when the Variable is unset.

Task flow:
  inventory_raw_files -> discover_csv_files -> load_all_csv_files -> validate_load_counts
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

DEFAULT_DEPLOY_ENV = os.environ.get("DEPLOY_ENV", "dev")
RAW_DATA_DIR = os.environ.get("PNEUMA_DATA_DIR", "/opt/airflow/data/raw")
SCRIPTS_DIR = os.environ.get("LOAD_SCRIPTS_DIR", "/opt/airflow/scripts")

default_args = {
    "owner": "traffic-data-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def get_deploy_env() -> str:
    """Resolve target environment from Airflow Variable or container env."""
    return Variable.get("deploy_env", default_var=DEFAULT_DEPLOY_ENV)


def get_postgres_conn_id(deploy_env: str | None = None) -> str:
    env_name = deploy_env or get_deploy_env()
    return f"postgres_{env_name}"


def discover_csv_files(**context) -> list[str]:
    """Return absolute paths to pNEUMA CSV files in the raw data directory."""
    pattern = str(Path(RAW_DATA_DIR) / "*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {RAW_DATA_DIR}. "
            "Place pNEUMA files under data/raw/ before triggering this DAG."
        )
    context["ti"].xcom_push(key="csv_files", value=files)
    return files


def load_all_csv_files(**context) -> list[dict]:
    """Load every discovered CSV into the environment selected by deploy_env."""
    ti = context["ti"]
    csv_files = ti.xcom_pull(task_ids="discover_csv_files", key="csv_files") or []
    deploy_env = get_deploy_env()
    results: list[dict] = []

    for csv_path in csv_files:
        command = [
            sys.executable,
            f"{SCRIPTS_DIR}/load_pneuma.py",
            csv_path,
            "--env",
            deploy_env,
        ]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        results.append(
            {
                "csv_path": csv_path,
                "stdout": completed.stdout.strip(),
                "env": deploy_env,
            }
        )

    ti.xcom_push(key="load_results", value=results)
    return results


def validate_load_counts(**context) -> None:
    """Sanity-check that raw tables contain rows for each loaded source file."""
    deploy_env = get_deploy_env()
    conn_id = get_postgres_conn_id(deploy_env)
    ti = context["ti"]
    csv_files = ti.xcom_pull(task_ids="discover_csv_files", key="csv_files") or []

    hook = PostgresHook(postgres_conn_id=conn_id)
    for csv_path in csv_files:
        source_file = Path(csv_path).name
        track_count = hook.get_first(
            "SELECT COUNT(*) FROM raw.vehicle_tracks WHERE source_file = %s",
            parameters=(source_file,),
        )[0]
        point_count = hook.get_first(
            "SELECT COUNT(*) FROM raw.trajectory_points WHERE source_file = %s",
            parameters=(source_file,),
        )[0]
        if track_count == 0 or point_count == 0:
            raise ValueError(
                f"Validation failed for {source_file} in {deploy_env}: "
                f"tracks={track_count}, points={point_count}"
            )


with DAG(
    dag_id="load_pneuma_raw",
    description="Load pNEUMA drone trajectory CSVs into raw warehouse tables",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["pneuma", "raw", "elt"],
    doc_md=__doc__,
) as dag:
    inventory_raw_files = BashOperator(
        task_id="inventory_raw_files",
        bash_command=f"""
        echo "Deploy env: {{{{ var.value.get('deploy_env', '{DEFAULT_DEPLOY_ENV}') }}}}"
        echo "Raw data directory: {RAW_DATA_DIR}"
        ls -lh {RAW_DATA_DIR}/*.csv 2>/dev/null || echo "No CSV files yet"
        """,
    )

    discover_csv_files_task = PythonOperator(
        task_id="discover_csv_files",
        python_callable=discover_csv_files,
    )

    load_all_csv_files_task = PythonOperator(
        task_id="load_all_csv_files",
        python_callable=load_all_csv_files,
    )

    validate_load = PythonOperator(
        task_id="validate_load_counts",
        python_callable=validate_load_counts,
    )

    trigger_dbt_transform = TriggerDagRunOperator(
        task_id="trigger_dbt_transform",
        trigger_dag_id="transform_pneuma_dbt",
        wait_for_completion=False,
    )

    (
        inventory_raw_files
        >> discover_csv_files_task
        >> load_all_csv_files_task
        >> validate_load
        >> trigger_dbt_transform
    )
