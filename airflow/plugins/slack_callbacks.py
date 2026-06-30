"""
Slack failure alerts for Airflow DAGs.

Set SLACK_WEBHOOK_URL in .env to enable. When unset, callbacks are no-ops so
local development works without Slack configured.

Create a webhook (free Slack workspace):
  1. https://api.slack.com/apps → Create New App → From scratch
  2. Incoming Webhooks → Activate → Add New Webhook to Workspace
  3. Copy the URL into .env as SLACK_WEBHOOK_URL
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


def _format_execution_time(context: dict[str, Any]) -> str:
    logical_date = context.get("logical_date") or context.get("execution_date")
    if logical_date is None:
        return "unknown"
    return logical_date.isoformat()


def _build_slack_payload(context: dict[str, Any]) -> dict[str, Any]:
    ti = context["task_instance"]
    dag_id = ti.dag_id
    task_id = ti.task_id
    deploy_env = os.environ.get("DEPLOY_ENV", "dev")
    exception = context.get("exception")
    log_url = ti.log_url
    run_id = context.get("run_id", "unknown")

    error_text = str(exception) if exception else "No exception message available"
    if len(error_text) > 500:
        error_text = f"{error_text[:497]}..."

    header = f":red_circle: Airflow task failed ({deploy_env})"
    fields = [
        f"*DAG:* `{dag_id}`",
        f"*Task:* `{task_id}`",
        f"*Run:* `{run_id}`",
        f"*Logical date:* `{_format_execution_time(context)}`",
        f"*Error:* ```{error_text}```",
    ]
    if log_url:
        fields.append(f"*Logs:* <{log_url}|View in Airflow>")

    return {
        "text": f"{header} — {dag_id}.{task_id}",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": header}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(fields)}},
        ],
    }


def task_failure_slack_alert(context: dict[str, Any]) -> None:
    """Airflow on_failure_callback — posts a Slack message when SLACK_WEBHOOK_URL is set."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.info("SLACK_WEBHOOK_URL not set — skipping Slack alert")
        return

    payload = _build_slack_payload(context)
    ti = context["task_instance"]
    logger.info("Sending Slack alert for %s.%s", ti.dag_id, ti.task_id)
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                body = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Slack webhook returned {response.status}: {body}")
            logger.info("Slack alert sent for %s.%s", ti.dag_id, ti.task_id)
    except urllib.error.URLError as exc:
        # Never fail the DAG further because alerting itself broke.
        logger.warning("Slack alert failed: %s", exc)
