# Seed data

SQL that puts convenience data into the database. Separate from `db/init/`, which holds the schema and is mounted into the Postgres container to run automatically on an empty volume. Nothing here runs by itself. You run it when you want it.

Running a script twice is harmless. The second run changes nothing.

Run every command from the **repository root**. The input redirect uses a relative path.

## `dev_user.sql`

The development owner, used while authentication is deferred. Fixed UUID, so `DEV_USER_ID` in `.env` stays valid even after `docker compose down -v` wipes the database.

### Run it

```bash
docker compose exec -T db bash -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < db/seed/dev_user.sql
```

Expected output: `INSERT 0 1`.

### Verify

```bash
docker compose exec db bash -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT id, email FROM users;"'
```

Expected:

| **`id`**                             | **`email`**          |
| ------------------------------------ | -------------------- |
| 00000000-0000-0000-0000-000000000001 | <dev@lecture-ai.org> |

That id belongs in `.env`:

```dotenv
DEV_USER_ID=00000000-0000-0000-0000-000000000001
```

### When to re-run

- After `docker compose down -v`, which deletes the volume and with it the row
- After editing the script, e.g. changing the email

`ON CONFLICT (id) DO UPDATE` means a re-run corrects the existing row instead of failing. With `DO NOTHING` it would silently keep the old values.

### Notes

- `-T` disables TTY allocation, which is what allows `< file` to be piped in.
- The environment variables are expanded **inside** the container, so no credentials appear in your shell history.
- Delete `dev_user.sql` and the `DEV_USER_ID` setting once real authentication exists.
