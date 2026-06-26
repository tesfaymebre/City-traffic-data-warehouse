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

We separate **dev**, **staging**, and **prod** via:

- Docker Compose profiles / env files
- dbt targets in `profiles.yml`
- Airflow Variables and Connections per environment

## Local setup

> Docker Compose and service wiring are added in the next milestone.

1. Copy `.env.example` to `.env` and update credentials.
2. Place pNEUMA CSV files in `data/raw/`.
3. Follow `docs/` as each component is introduced.

## Development

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
