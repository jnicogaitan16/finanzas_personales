#!/bin/sh
set -e
# Solo corre la primera vez que se crea el volumen de ESTE Postgres (puerto host 5433).
# No toca el Postgres de kamecol (puerto 5432).
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
SELECT 'CREATE DATABASE finanzas'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'finanzas')\gexec
GRANT ALL PRIVILEGES ON DATABASE finanzas TO "$POSTGRES_USER";
EOSQL
