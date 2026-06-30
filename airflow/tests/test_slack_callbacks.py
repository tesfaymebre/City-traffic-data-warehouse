"""Slack alerting callback tests."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PLUGINS_DIR = Path(__file__).resolve().parents[1] / "plugins"
sys.path.insert(0, str(PLUGINS_DIR))

from slack_callbacks import _build_slack_payload, task_failure_slack_alert  # noqa: E402


def _sample_context(exception: Exception | None = ValueError("load failed")) -> dict:
    ti = MagicMock()
    ti.dag_id = "load_pneuma_raw"
    ti.task_id = "validate_load_counts"
    ti.log_url = "http://localhost:8080/log"
    return {
        "task_instance": ti,
        "exception": exception,
        "logical_date": None,
        "run_id": "manual__2024-01-01",
    }


def test_build_slack_payload_includes_dag_and_task():
    payload = _build_slack_payload(_sample_context())
    text = json.dumps(payload)
    assert "load_pneuma_raw" in text
    assert "validate_load_counts" in text
    assert "load failed" in text


def test_task_failure_slack_alert_noop_without_webhook():
    with patch.dict("os.environ", {}, clear=True):
        task_failure_slack_alert(_sample_context())  # should not raise


def test_task_failure_slack_alert_posts_to_webhook():
    context = _sample_context()
    with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.status = 200
            task_failure_slack_alert(context)
            mock_urlopen.assert_called_once()
            request = mock_urlopen.call_args[0][0]
            assert request.full_url == "https://hooks.slack.com/test"
            body = json.loads(request.data.decode())
            assert "load_pneuma_raw" in body["text"]


def test_dags_wire_slack_failure_callback():
    for dag_file in ("load_pneuma_dag.py", "transform_pneuma_dbt_dag.py"):
        content = (Path(__file__).resolve().parents[1] / "dags" / dag_file).read_text()
        assert "from slack_callbacks import task_failure_slack_alert" in content
        assert '"on_failure_callback": task_failure_slack_alert' in content
