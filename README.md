# City Traffic Data Warehouse

A fully dockerized **ELT** data platform for city traffic trajectory data (pNEUMA dataset).

## Stack

| Layer | Tool | Role |
|-------|------|------|
| Warehouse | PostgreSQL | Store raw + transformed data |
| Orchestration | Apache Airflow | Schedule loads and dbt runs |
| Transform | dbt | SQL-based analytics engineering |
| BI | Redash | Dashboards and ad-hoc queries |

## Repository layout

```
├── airflow/          # DAGs, plugins, and pipeline tests
├── dbt/              # dbt models, macros, seeds, and tests
├── docker/           # docker-compose and service configs
├── scripts/          # Helper scripts (load, seed, deploy)
├── data/raw/         # Local raw CSV files (not committed)
└── docs/             # Architecture notes and write-ups
```

## Environments

We separate **dev**, **staging**, and **prod** using:

| Layer | Mechanism |
|-------|-----------|
| PostgreSQL | Separate databases: `traffic_dev`, `traffic_staging`, `traffic_prod` |
| dbt | Targets in `dbt/profiles.yml` mapped to each database |
| Airflow | `DEPLOY_ENV` variable selects which environment DAGs write to |
| Schemas | `raw` → `staging` → `marts` inside each database |

Switch environments locally:

```bash
# In .env
DEPLOY_ENV=staging   # or prod
make down && make up
```

## Local setup (Docker)

**Prerequisites:** Docker Desktop, Make

```bash
# 1. Bootstrap secrets into .env
make env

# 2. Start the full stack (first run builds images — ~5-10 min)
make up

# 3. Open UIs
# Airflow:  http://localhost:8080  (admin / admin)
# Redash:   http://localhost:5000  (create account on first visit)
# dbt docs: http://localhost:8081  (after `make dbt-docs`)
# Postgres: localhost:15432  (host port; containers still use postgres:5432 internally)
```

Useful commands:

```bash
make ps          # container status
make logs        # tail all logs
make dbt-debug   # verify dbt → Postgres connection
make dbt-run     # build staging + mart models
make dbt-test    # run data quality tests
make dbt-docs    # generate docs at http://localhost:8081
make down        # stop services
make reset       # stop + delete volumes (wipes all data)
```

### Redash dashboard (Task 4)

After loading and transforming data:

```bash
# 1. Open Redash and create your account (first visit only)
make redash-ui   # http://localhost:5000

# 2. Copy your API key to .env
#    User Settings → API Key → REDASH_API_KEY=...

# 3. Bootstrap data source, queries, and dashboard from redash/
make redash-bootstrap
```

Version-controlled assets live in `redash/`:

| Path | Purpose |
|------|---------|
| `redash/queries/*.sql` | Dashboard SQL (queries `marts` schema) |
| `redash/dashboard.yml` | Widget layout and visualization types |
| `scripts/redash/bootstrap_redash.py` | Pushes assets to Redash via REST API |

The **City Traffic Overview** dashboard includes KPI counters, vehicle mix charts, speed charts, and a detail table sourced from `mart_traffic_by_vehicle_type` and related marts.

### Slack alerting (optional)

Get notified in Slack when a DAG task fails (after retries are exhausted):

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Choose your workspace and app name (e.g. `Traffic Warehouse Alerts`)
3. **Incoming Webhooks** → toggle **On** → **Add New Webhook to Workspace**
4. Pick a channel (e.g. `#data-alerts`) → **Allow**
5. Copy the webhook URL into `.env`:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../...
   ```
6. Restart Airflow so it picks up the new env var:
   ```bash
   make down && make up
   ```

Both `load_pneuma_raw` and `transform_pneuma_dbt` use `on_failure_callback` to post DAG name, task, error, and a log link. If `SLACK_WEBHOOK_URL` is empty, alerting is silently disabled.

**Important:** Alerts fire only after **all retries are exhausted** (default: 1 retry, 5-minute delay). A failed task shows `up_for_retry` in the UI first; expect the Slack message ~5 minutes later.

Quick webhook test (no DAG failure needed):

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec airflow-scheduler \
  python -c "import json, os, urllib.request; urllib.request.urlopen(urllib.request.Request(os.environ['SLACK_WEBHOOK_URL'], data=json.dumps({'text':'Slack test OK'}).encode(), method='POST', headers={'Content-Type':'application/json'}))"
```

Place pNEUMA CSV files in `data/raw/` before running load DAGs (Task 1).

## Write-up (Task 5)

See [docs/approach-and-decisions.md](docs/approach-and-decisions.md) for the short article on architecture choices, ELT rationale, and lessons learned.

## Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check airflow scripts
pytest airflow/tests -q
```

## Data source

[pNEUMA open traffic dataset](https://open-traffic.epfl.ch/index.php/downloads/#1599047632450-ebe509c8-1330) — naturalistic vehicle trajectories collected by drone swarm over Athens.

## License

Educational project — 10 Academy Cohort A, Week 2.
