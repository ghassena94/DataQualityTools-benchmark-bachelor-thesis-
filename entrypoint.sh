#!/bin/bash
# Wait for the PostgreSQL container (defined in docker-compose.yml as "db")
# to accept connections before starting the application.
# PostgreSQL is NOT started here — it runs as a separate container.

set -euo pipefail

PGHOST="${PGHOST:-db}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-reinuser}"
export PGPASSWORD="${PGPASSWORD:-abcd1234}"
PGDATABASE="${PGDATABASE:-rein}"

echo "Waiting for PostgreSQL at ${PGHOST}:${PGPORT}..."
until pg_isready -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -q; do
    echo "  PostgreSQL not ready yet — retrying in 2s..."
    sleep 2
done
echo "PostgreSQL is ready."

exec "$@"
