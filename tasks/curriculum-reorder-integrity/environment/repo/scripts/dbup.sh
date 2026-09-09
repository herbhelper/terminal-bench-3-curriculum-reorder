#!/bin/bash
# Start the local Postgres cluster and make sure the curriculum database exists.
# Safe to run repeatedly.
set -e

pg_ctlcluster 16 main start 2>/dev/null || true

for _ in $(seq 1 30); do
    su postgres -c "psql -tAc 'SELECT 1'" >/dev/null 2>&1 && break
    sleep 1
done

su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='curriculum'\"" | grep -q 1 || \
    su postgres -c "psql -qc \"CREATE ROLE curriculum LOGIN PASSWORD 'curriculum' SUPERUSER\""

su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='curriculum'\"" | grep -q 1 || \
    su postgres -c "createdb -O curriculum curriculum"

echo "postgres ready"
