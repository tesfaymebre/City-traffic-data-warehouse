COMPOSE_FILE := docker/docker-compose.yml
COMPOSE := docker compose --env-file .env -f $(COMPOSE_FILE)

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
PYTEST := $(VENV)/bin/pytest

.PHONY: help env up down logs ps reset airflow-ui redash-ui redash-bootstrap dbt-debug load-sample trigger-load dbt-deps dbt-run dbt-build dbt-test dbt-source-freshness dbt-docs trigger-transform ci ci-install ci-lint ci-yaml ci-compose ci-test

help:
	@echo "Targets:"
	@echo "  make ci               Run all CI checks locally (lint, yaml, compose, tests)"
	@echo "  make ci-lint          Ruff lint (airflow, scripts)"
	@echo "  make ci-yaml          Validate YAML files"
	@echo "  make ci-compose       Validate docker-compose structure"
	@echo "  make ci-test          Run pytest (airflow/tests)"
	@echo "  make env              Create .env from .env.example (with secrets)"
	@echo "  make up               Start the full stack"
	@echo "  make down             Stop the stack"
	@echo "  make logs             Tail service logs"
	@echo "  make ps               Show running containers"
	@echo "  make reset            Stop stack and delete volumes (destructive)"
	@echo "  make dbt-debug        Test dbt connection inside Airflow container"
	@echo "  make dbt-deps         Install dbt package dependencies"
	@echo "  make dbt-run          Run dbt models (dev target)"
	@echo "  make dbt-build        Run dbt build (models + tests, circuit breaker)"
	@echo "  make dbt-test         Run dbt tests only"
	@echo "  make dbt-source-freshness  Check raw source freshness"
	@echo "  make dbt-docs         Generate and serve dbt docs at :8081"
	@echo "  make load-sample      Load sample CSV into dev warehouse (CLI)"
	@echo "  make trigger-load     Trigger load_pneuma_raw DAG in Airflow"
	@echo "  make trigger-transform Trigger transform_pneuma_dbt DAG in Airflow"
	@echo "  make redash-ui         Open Redash UI URL"
	@echo "  make redash-bootstrap  Create Redash data source, queries, and dashboard"

env:
	@bash scripts/bootstrap_env.sh

# ---------------------------------------------------------------------------
# Local CI (mirrors .github/workflows/ci.yml)
# ---------------------------------------------------------------------------
ci-install:
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@$(PIP) install -q -r requirements-dev.txt

ci-lint: ci-install
	@echo "==> ruff check airflow scripts"
	@$(RUFF) check airflow scripts

ci-yaml: ci-install
	@echo "==> validate YAML files"
	@$(PYTHON) scripts/ci/validate_yaml.py

ci-compose: ci-install
	@echo "==> validate docker-compose.yml"
	@$(PYTHON) scripts/ci/validate_compose.py

ci-test: ci-install
	@echo "==> pytest airflow/tests"
	@$(PYTEST) airflow/tests -q

ci: ci-lint ci-yaml ci-compose ci-test
	@echo "All CI checks passed."

up: env
	@mkdir -p airflow/logs
	$(COMPOSE) up -d --build airflow-init redash-init
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

ps:
	$(COMPOSE) ps

reset:
	$(COMPOSE) down -v

airflow-ui:
	@echo "Airflow UI: http://localhost:8080"

redash-ui:
	@echo "Redash UI: http://localhost:$${REDASH_PORT:-5000}"

redash-bootstrap:
	@$(PYTHON) scripts/redash/bootstrap_redash.py

dbt-debug:
	$(COMPOSE) run --rm --entrypoint dbt airflow-scheduler debug --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt

dbt-deps:
	$(COMPOSE) run --rm --entrypoint dbt airflow-scheduler deps --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt

dbt-run:
	$(COMPOSE) run --rm --entrypoint dbt airflow-scheduler run --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt --target dev

dbt-build:
	$(COMPOSE) run --rm --entrypoint dbt airflow-scheduler build --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt --target dev

dbt-test:
	$(COMPOSE) run --rm --entrypoint dbt airflow-scheduler test --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt --target dev

dbt-source-freshness:
	$(COMPOSE) run --rm --entrypoint dbt airflow-scheduler source freshness --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt --target dev

dbt-docs:
	$(COMPOSE) run --rm --entrypoint dbt airflow-scheduler docs generate --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt --target dev
	$(COMPOSE) up -d dbt-docs
	@echo "dbt docs: http://localhost:$${DBT_DOCS_PORT:-8081}"

load-sample:
	$(COMPOSE) run --rm --entrypoint python airflow-scheduler \
		/opt/airflow/scripts/load_pneuma.py \
		/opt/airflow/data/raw/20181024_d1_0830_0900.csv --env dev

trigger-load:
	$(COMPOSE) exec airflow-scheduler airflow dags unpause load_pneuma_raw
	$(COMPOSE) exec airflow-scheduler airflow dags trigger load_pneuma_raw

trigger-transform:
	$(COMPOSE) exec airflow-scheduler airflow dags unpause transform_pneuma_dbt
	$(COMPOSE) exec airflow-scheduler airflow dags trigger transform_pneuma_dbt
