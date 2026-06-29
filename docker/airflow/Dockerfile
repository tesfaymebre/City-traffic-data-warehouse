# Extend the official Airflow image with dbt + Postgres provider for ELT pipelines.
FROM apache/airflow:2.8.4-python3.11

USER airflow

RUN pip install --no-cache-dir \
    "apache-airflow-providers-postgres==5.10.0" \
    "dbt-postgres==1.7.14" \
    "psycopg2-binary==2.9.9"
