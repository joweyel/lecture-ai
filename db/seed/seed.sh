#!/usr/bin/env bash
set -e  # Stops the script if any command fails

# Seed the database
docker compose exec -T db bash -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < db/seed/dev_user.sql
if [ -f "db/seed/sample_data.sql" ]; then
    docker compose exec -T db bash -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < db/seed/sample_data.sql
fi
