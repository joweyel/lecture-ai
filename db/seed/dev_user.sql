-- Development owner, used while authentication is deferred.
-- Fixed UUID so DEV_USER_ID in .env stays valid across `docker compose down -v`.
-- Idempotent: safe to run as often as you like.
--
--   docker compose exec -T db bash -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < db/seed/dev_user.sql
--
-- Delete this file once real authentication exists.

INSERT INTO users (id, email, hashed_password)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'dev@lecture-ai.org',
    'placeholder-not-a-hash'
)
ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;
