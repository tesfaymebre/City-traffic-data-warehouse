-- Runs once on first Postgres container start.
-- Creates isolated databases for DWH environments + Airflow + Redash metadata.

CREATE DATABASE traffic_dev;
CREATE DATABASE traffic_staging;
CREATE DATABASE traffic_prod;
CREATE DATABASE airflow;
CREATE DATABASE redash;

-- Raw landing zone schema in each warehouse database.
\connect traffic_dev
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

\connect traffic_staging
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

\connect traffic_prod
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;
