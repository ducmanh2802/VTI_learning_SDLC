#!/bin/sh
set -eu
: "${CORE_DB_PASSWORD:?CORE_DB_PASSWORD is required}"
: "${ANALYTICS_DB_PASSWORD:?ANALYTICS_DB_PASSWORD is required}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v core_pw="$CORE_DB_PASSWORD" -v analytics_pw="$ANALYTICS_DB_PASSWORD" <<'SQL'
SELECT 'CREATE ROLE core_rw NOLOGIN' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'core_rw')\gexec
SELECT 'CREATE ROLE analytics_rw NOLOGIN' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'analytics_rw')\gexec
SELECT format('CREATE ROLE core_svc LOGIN PASSWORD %L IN ROLE core_rw', :'core_pw')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'core_svc')\gexec
SELECT format('CREATE ROLE analytics_svc LOGIN PASSWORD %L IN ROLE analytics_rw', :'analytics_pw')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'analytics_svc')\gexec
ALTER ROLE core_svc SET search_path = core, paper, strategy, market;
ALTER ROLE analytics_svc SET search_path = market, ai, research, strategy;
SQL
