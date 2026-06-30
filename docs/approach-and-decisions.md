# Building a City Traffic Data Warehouse: Approach and Key Decisions

**Author:** Tesfamichael Asfaw  
**Project:** 10 Academy Cohort A — Week 2 Challenge  
**Dataset:** [pNEUMA](https://open-traffic.epfl.ch/) vehicle trajectories over Athens, Greece

---

## The problem

Urban planners and traffic engineers need reliable answers to simple questions: *How many cars passed through downtown? What speeds do buses average? Where is congestion worst?*

The pNEUMA dataset provides drone-captured GPS trajectories for thousands of vehicles. Raw files are wide, repetitive CSVs — one row per vehicle with hundreds of embedded coordinate columns. The challenge was to turn that into a queryable warehouse, trustworthy analytics models, and a live dashboard — all reproducible on a laptop via Docker.

---

## High-level approach: ELT, not ETL

We chose **ELT** (Extract → Load → Transform):

1. **Extract** pNEUMA CSV files from disk  
2. **Load** them into PostgreSQL `raw` tables with minimal change  
3. **Transform** inside the warehouse using dbt SQL models  

Transformations run *after* data lands in Postgres, not in a separate ETL tool. That keeps the raw layer as a durable audit trail and lets analysts re-run transforms without re-ingesting files.

```
CSV files → Airflow load DAG → raw schema → dbt (staging → marts) → Redash dashboard
```

---

## Architecture decisions

### 1. Dockerized monorepo

Everything runs in one `docker-compose` stack: PostgreSQL, Airflow, Redash, and an nginx container for dbt docs. A single `make up` gives every teammate the same environment.

**Why:** Eliminates "works on my machine" drift. CI validates the same compose file, YAML, and DAG structure on every push.

### 2. Environment separation without infrastructure sprawl

Instead of three separate Postgres servers, we use **one instance with three databases**:

| Database | Purpose |
|----------|---------|
| `traffic_dev` | Local experimentation |
| `traffic_staging` | Pre-production validation |
| `traffic_prod` | Production tables |

Each database has identical schemas: `raw` → `staging` → `marts`. Airflow reads a `deploy_env` variable to pick the right Postgres connection and dbt target. Switching environments is a one-line `.env` change.

**Why:** Matches how many real teams start — logical isolation before physical isolation. Cheap locally, easy to promote to separate RDS instances later.

### 3. Parsing the wide pNEUMA format in Python, not SQL

Each CSV row contains static vehicle metadata plus repeating groups of six fields (latitude, longitude, speed, accelerations, timestamp). We parse this in `scripts/pneuma_parser.py` and load two normalized tables:

- `raw.vehicle_tracks` — one row per vehicle trip  
- `raw.trajectory_points` — one row per GPS sample  

**Why:** SQL is poor at unpivoting variable-width rows from a file format the database never sees again. Python handles the structure once; Postgres stores clean relational data.

### 4. Composite key: `(track_id, source_file)`

`track_id` repeats across different CSV files. A vehicle with `track_id = 1` in `20181024_d1_0830_0900.csv` is unrelated to `track_id = 1` in another file.

Every downstream model keys on **both** columns. This was one of the most important modeling decisions — without it, joins silently merge unrelated trips.

### 5. dbt layering: staging views, mart tables

| Layer | Materialization | Role |
|-------|-----------------|------|
| `stg_vehicle_tracks` | view | Clean types, filter nulls |
| `stg_trajectory_points` | view | Drop impossible coordinates |
| `fct_trajectory_points` | table | Point-level fact with vehicle metadata |
| `mart_vehicle_trip_summary` | table | One row per trip with aggregates |
| `mart_traffic_by_vehicle_type` | table | BI-ready rollups for Redash |

Staging stays lightweight (views). Marts are materialized tables because Redash queries scan them repeatedly.

**Custom macros:**

- `generate_schema_name` — forces models into exact `staging` and `marts` schemas (dbt's default would prefix with `public_`)  
- `format_time_window` — turns filename tokens like `0830_0900` into readable `08:30–09:00` labels  

### 6. Orchestration: two Airflow DAGs, one pipeline

| DAG | Responsibility |
|-----|----------------|
| `load_pneuma_raw` | Discover CSVs → load → validate counts → trigger transform |
| `transform_pneuma_dbt` | dbt deps → source freshness → **dbt build** → docs |

Load and transform are separate DAGs so a failed dbt run does not block re-loading a corrected file, and vice versa. `TriggerDagRunOperator` chains them after a successful load.

**Metadata management:** `deploy_env` lives in both an environment variable and an Airflow Variable, so DAGs and standalone scripts agree on the target without hard-coding connection strings.

### 7. Hard circuit breaker with `dbt build`

Early versions ran `dbt run` then `dbt test`. If a mart test failed, bad data was already written.

We switched to **`dbt build`**, which runs models and tests in dependency order. If a staging test fails, mart tables are **skipped** — they keep their last good version.

Combined with **source freshness** checks on `raw.vehicle_tracks.loaded_at`, stale or broken upstream data is caught before any mart refresh.

### 8. Data quality with `dbt_expectations`

We evaluated Great Expectations, re-data, and `dbt_expectations`. We chose **`dbt_expectations`** because:

- Tests live next to model definitions in YAML  
- They run inside the existing `dbt test` / `dbt build` flow  
- No extra service to deploy  

Rules cover Athens bounding boxes for GPS coordinates, valid vehicle types, speed ranges, row counts, and a custom singular test for trip-level speed consistency (`avg_speed` vs mean of point speeds).

### 9. Redash: version-controlled queries + API bootstrap

Manual dashboard setup does not survive redeploys. We store SQL in `redash/queries/` and a layout in `redash/dashboard.yml`. `make redash-bootstrap` pushes everything to Redash via its REST API — data source, queries, visualizations, and the **City Traffic Overview** dashboard.

**Why:** Matches the challenge's recommendation for query version control. Dashboards become reproducible infrastructure, not click-ops.

### 10. Slack alerts on DAG failure

Both Airflow DAGs register an `on_failure_callback` that posts to a Slack Incoming Webhook when `SLACK_WEBHOOK_URL` is set. The message includes the DAG, task, environment, error snippet, and a link to task logs. If the webhook is unset, the callback is a no-op — local dev works without Slack.

**Why Slack over email:** No SMTP setup in Docker; free workspaces support Incoming Webhooks; common pattern on data teams.

---

## What we deliberately deferred

| Item | Reason |
|------|--------|
| Auto-generating Airflow DAGs from dbt metadata | Powerful pattern (see [Astronomer guide](https://www.astronomer.io/blog/airflow-dbt-2/)), but overkill for five models |
| Read-only Postgres role for Redash | Good security practice; `traffic_admin` is acceptable for local dev |
| Great Expectations | Strong tool, but adds a separate checkpoint store beyond what dbt already provides |

These are natural next steps when moving from a challenge repo to a production deployment.

---

## End-to-end flow (one sentence)

A scheduler drops CSVs into `data/raw/`, Airflow loads them into Postgres, dbt builds tested mart tables, and Redash visualizes traffic mix and speed — with every layer separated by environment and guarded by automated quality checks.

---

## References

- [pNEUMA dataset](https://open-traffic.epfl.ch/)  
- [dbt documentation](https://docs.getdbt.com/)  
- [dbt_expectations package](https://github.com/metaplane/dbt_expectations)  
- [Apache Airflow](https://airflow.apache.org/)  
- [Redash](https://redash.io/)  
- [Astronomer: Running dbt in Airflow](https://www.astronomer.io/blog/airflow-dbt-2/)
