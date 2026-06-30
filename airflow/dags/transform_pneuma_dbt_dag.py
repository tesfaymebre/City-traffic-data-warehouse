"""
Airflow DAG: run dbt transformations after raw pNEUMA data is loaded.

Circuit-breaker pattern (dbt build):
  source freshness -> dbt build -> dbt docs generate

dbt build runs models and tests in dependency order. If a staging test fails,
downstream mart models are NOT rebuilt — hard circuit breaker for prod tables.

Environment:
  Uses Airflow Variable `deploy_env` (dev / staging / prod) passed to dbt --target.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from slack_callbacks import task_failure_slack_alert

DEFAULT_DEPLOY_ENV = os.environ.get("DEPLOY_ENV", "dev")
DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt")
DBT_PROFILES_DIR = os.environ.get("DBT_PROFILES_DIR", "/opt/airflow/dbt")

default_args = {
    "owner": "traffic-data-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "on_failure_callback": task_failure_slack_alert,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def dbt_cmd(subcommand: str) -> str:
    """Build a dbt CLI command with the active deploy target."""
    return f"""
    set -euo pipefail
    DEPLOY_TARGET="{{{{ var.value.get('deploy_env', '{DEFAULT_DEPLOY_ENV}') }}}}"
    echo "Running dbt {subcommand} against target: ${{DEPLOY_TARGET}}"
    dbt {subcommand} \
      --project-dir {DBT_PROJECT_DIR} \
      --profiles-dir {DBT_PROFILES_DIR} \
      --target "${{DEPLOY_TARGET}}"
    """


with DAG(
    dag_id="transform_pneuma_dbt",
    description="dbt staging and mart models for pNEUMA traffic data",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["pneuma", "dbt", "transform", "elt", "data_quality"],
    doc_md=__doc__,
) as dag:
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=dbt_cmd("deps"),
    )

    dbt_source_freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command=dbt_cmd("source freshness"),
    )

    # build = run models + tests in DAG order (circuit breaker)
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=dbt_cmd("build"),
    )

    dbt_docs_generate = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=dbt_cmd("docs generate"),
    )

    dbt_deps >> dbt_source_freshness >> dbt_build >> dbt_docs_generate
