COMPOSE_FILE := docker/docker-compose.yml
COMPOSE := docker compose --env-file .env -f $(COMPOSE_FILE)

.PHONY: help env up down logs ps reset airflow-ui redash-ui dbt-debug load-sample trigger-load

help:
	@echo "Targets:"
	@echo "  make env          Create .env from .env.example (with secrets)"
	@echo "  make up           Start the full stack"
	@echo "  make down         Stop the stack"
	@echo "  make logs         Tail service logs"
	@echo "  make ps           Show running containers"
	@echo "  make reset        Stop stack and delete volumes (destructive)"
	@echo "  make dbt-debug    Test dbt connection inside Airflow container"
	@echo "  make load-sample  Load sample CSV into dev warehouse (CLI)"
	@echo "  make trigger-load Trigger load_pneuma_raw DAG in Airflow"

env:
	@bash scripts/bootstrap_env.sh

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
	@echo "Redash UI: http://localhost:5000"

dbt-debug:
	$(COMPOSE) run --rm --entrypoint dbt airflow-scheduler debug --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt

load-sample:
	$(COMPOSE) run --rm --entrypoint python airflow-scheduler \
		/opt/airflow/scripts/load_pneuma.py \
		/opt/airflow/data/raw/20181024_d1_0830_0900.csv --env dev

trigger-load:
	$(COMPOSE) exec airflow-scheduler airflow dags unpause load_pneuma_raw
	$(COMPOSE) exec airflow-scheduler airflow dags trigger load_pneuma_raw
