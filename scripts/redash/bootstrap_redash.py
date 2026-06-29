#!/usr/bin/env python3
"""
Bootstrap Redash data source, queries, and dashboard from version-controlled assets.

Prerequisites:
  1. Stack running (`make up`)
  2. Redash account created at http://localhost:5000
  3. API key copied to REDASH_API_KEY in .env (User Settings → API Key)

Usage:
  python scripts/redash/bootstrap_redash.py
  make redash-bootstrap
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]
REDASH_DIR = ROOT_DIR / "redash"
CONFIG_PATH = REDASH_DIR / "dashboard.yml"
QUERIES_DIR = REDASH_DIR / "queries"


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE pairs from .env into os.environ if not already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


class RedashClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict | list:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Key {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Redash API {method} {path} failed ({exc.code}): {detail}") from exc

    def list_data_sources(self) -> list[dict]:
        return self._request("GET", "/api/data_sources")

    def create_data_source(self, name: str, pg_options: dict) -> dict:
        return self._request(
            "POST",
            "/api/data_sources",
            {"name": name, "type": "pg", "options": pg_options},
        )

    def test_data_source(self, data_source_id: int) -> dict:
        return self._request("POST", f"/api/data_sources/{data_source_id}/test")

    def _as_result_list(self, result: dict | list) -> list[dict]:
        """Normalize Redash list endpoints that may return a paginated envelope."""
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        raise RuntimeError(f"Unexpected Redash list response: {type(result)}")

    def list_queries(self) -> list[dict]:
        result = self._request("GET", "/api/queries?page_size=250")
        return self._as_result_list(result)

    def create_query(self, name: str, query: str, data_source_id: int) -> dict:
        return self._request(
            "POST",
            "/api/queries",
            {
                "name": name,
                "query": query,
                "data_source_id": data_source_id,
                "options": {"apply_auto_limit": True},
            },
        )

    def get_query(self, query_id: int) -> dict:
        return self._request("GET", f"/api/queries/{query_id}")

    def get_dashboard(self, dashboard_id: int) -> dict:
        return self._request("GET", f"/api/dashboards/{dashboard_id}")

    def create_visualization(self, query_id: int, spec: dict) -> dict:
        return self._request("POST", "/api/visualizations", spec | {"query_id": query_id})

    def list_dashboards(self) -> list[dict]:
        result = self._request("GET", "/api/dashboards?page_size=250")
        return self._as_result_list(result)

    def create_dashboard(self, name: str, tags: list[str]) -> dict:
        return self._request("POST", "/api/dashboards", {"name": name, "tags": tags})

    def create_widget(self, dashboard_id: int, visualization_id: int, position: dict) -> dict:
        return self._request(
            "POST",
            "/api/widgets",
            {
                "dashboard_id": dashboard_id,
                "visualization_id": visualization_id,
                "text": "",
                "width": 1,
                "options": {
                    "parameterMappings": {},
                    "isHidden": False,
                    "position": {
                        "autoHeight": False,
                        "sizeX": position["size_x"],
                        "sizeY": position["size_y"],
                        "minSizeX": 1,
                        "maxSizeX": 12,
                        "minSizeY": 1,
                        "maxSizeY": 1000,
                        "col": position["col"],
                        "row": position["row"],
                    },
                },
            },
        )


def ensure_data_source(client: RedashClient, config: dict) -> int:
    ds_config = config["data_source"]
    name = ds_config["name"]

    for source in client.list_data_sources():
        if source["name"] == name:
            print(f"Data source already exists: {name} (id={source['id']})")
            return source["id"]

    pg_options = {
        "host": os.environ.get("REDASH_DATASOURCE_HOST", "postgres"),
        "port": int(os.environ.get("REDASH_DATASOURCE_PORT", "5432")),
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "dbname": os.environ.get("REDASH_DATASOURCE_DB", "traffic_dev"),
        "sslmode": "prefer",
    }
    created = client.create_data_source(name, pg_options)
    source_id = created["id"]
    print(f"Created data source: {name} (id={source_id})")

    test_result = client.test_data_source(source_id)
    if test_result.get("message") != "success":
        raise RuntimeError(f"Data source connection test failed: {test_result}")
    print("Data source connection test: success")
    return source_id


def find_query_by_name(queries: list[dict], name: str) -> dict | None:
    return next((q for q in queries if q["name"] == name), None)


def build_visualization_spec(query_spec: dict, query_id: int) -> dict:
    viz_type = query_spec["visualization"]
    name = query_spec["name"]

    if viz_type == "counter":
        return {
            "type": "COUNTER",
            "name": name,
            "options": {
                "counterLabel": name,
                "counterColName": "total_vehicles",
                "rowNumber": 1,
                "targetRowNumber": 1,
            },
            "query_id": query_id,
        }

    if viz_type == "chart":
        x_col = query_spec["x_column"]
        y_cols = query_spec["y_columns"]
        column_mapping = {x_col: "x"}
        for col in y_cols:
            column_mapping[col] = "y"
        return {
            "type": "CHART",
            "name": name,
            "options": {
                "globalSeriesType": query_spec.get("chart_type", "column"),
                "columnMapping": column_mapping,
                "seriesOptions": {},
                "xAxis": {"type": "category", "labels": {"enabled": True}},
                "yAxis": [{"type": "linear"}],
                "legend": {"enabled": False},
            },
            "query_id": query_id,
        }

    return {"type": "TABLE", "name": name, "options": {}, "query_id": query_id}


def counter_column_for_query(file_name: str) -> str:
    mapping = {
        "01_total_vehicles.sql": "total_vehicles",
        "02_total_gps_points.sql": "total_gps_points",
    }
    return mapping.get(file_name, "value")


def ensure_queries_and_visualizations(
    client: RedashClient,
    data_source_id: int,
    config: dict,
) -> dict[str, int]:
    """Return mapping of query name -> visualization id for dashboard widgets."""
    existing = client.list_queries()
    viz_by_query_name: dict[str, int] = {}

    for query_spec in config["queries"]:
        name = query_spec["name"]
        sql_path = QUERIES_DIR / query_spec["file"]
        sql = sql_path.read_text(encoding="utf-8").strip()

        query = find_query_by_name(existing, name)
        if query is None:
            query = client.create_query(name, sql, data_source_id)
            print(f"Created query: {name} (id={query['id']})")
        else:
            query = client.get_query(query["id"])
            print(f"Query already exists: {name} (id={query['id']})")

        query_id = query["id"]
        viz_spec = build_visualization_spec(query_spec, query_id)

        if viz_spec["type"] == "COUNTER":
            viz_spec["options"]["counterColName"] = counter_column_for_query(query_spec["file"])

        target_viz = next(
            (v for v in query.get("visualizations", []) if v["type"] == viz_spec["type"]),
            None,
        )
        if target_viz is None:
            created_viz = client.create_visualization(query_id, viz_spec)
            viz_id = created_viz["id"]
            print(f"  Created {viz_spec['type']} visualization (id={viz_id})")
        else:
            viz_id = target_viz["id"]
            print(f"  Using existing {viz_spec['type']} visualization (id={viz_id})")

        viz_by_query_name[name] = viz_id

    return viz_by_query_name


def ensure_dashboard(
    client: RedashClient,
    config: dict,
    viz_by_query_name: dict[str, int],
) -> int:
    dashboard_config = config["dashboard"]
    name = dashboard_config["name"]
    tags = dashboard_config.get("tags", [])

    dashboards = client.list_dashboards()
    dashboard = next((d for d in dashboards if d["name"] == name), None)
    if dashboard is None:
        dashboard = client.create_dashboard(name, tags)
        print(f"Created dashboard: {name} (id={dashboard['id']})")
    else:
        print(f"Dashboard already exists: {name} (id={dashboard['id']})")

    dashboard_id = dashboard["id"]
    full_dashboard = client.get_dashboard(dashboard_id)
    existing_viz_ids = {
        widget["visualization"]["id"]
        for widget in full_dashboard.get("widgets", [])
        if widget.get("visualization")
    }

    for query_spec in config["queries"]:
        if "widget" not in query_spec:
            continue
        viz_id = viz_by_query_name[query_spec["name"]]
        if viz_id in existing_viz_ids:
            print(f"  Widget already on dashboard: {query_spec['name']}")
            continue
        client.create_widget(dashboard_id, viz_id, query_spec["widget"])
        print(f"  Added widget for: {query_spec['name']}")

    return dashboard_id


def main() -> int:
    load_dotenv(ROOT_DIR / ".env")

    api_key = os.environ.get("REDASH_API_KEY")
    if not api_key:
        print(
            "ERROR: REDASH_API_KEY is not set.\n"
            "1. Open http://localhost:5000 and create your account\n"
            "2. Go to User Settings → API Key\n"
            "3. Add REDASH_API_KEY=<your-key> to .env\n"
            "4. Re-run: make redash-bootstrap",
            file=sys.stderr,
        )
        return 1

    for var in ("POSTGRES_USER", "POSTGRES_PASSWORD"):
        if not os.environ.get(var):
            print(f"ERROR: {var} is not set in .env", file=sys.stderr)
            return 1

    base_url = os.environ.get("REDASH_URL", "http://localhost:5000")
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    client = RedashClient(base_url, api_key)
    print(f"Connecting to Redash at {base_url}")

    data_source_id = ensure_data_source(client, config)
    viz_by_query_name = ensure_queries_and_visualizations(client, data_source_id, config)
    dashboard_id = ensure_dashboard(client, config, viz_by_query_name)

    print(f"\nDone. Open dashboard: {base_url}/dashboards/{dashboard_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
