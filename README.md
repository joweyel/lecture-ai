# Learning Material Assistant

Ingests lecture material and answers questions about it with citations that
point back at the slide or page.

## See it work

Everything runs in Docker. Commands are run from the repository root.

```bash
./start_docker.sh gpu          # or cpu, without an nvidia gpu
db/seed/seed.sh                # dev user and sample rows
# Upload "simulated" until endpoint done
cp ~/Documents/MVP-Lectures/books/3A979-8-8688-2946-8.pdf data/documents/
```

Register the file in the SQL console on <http://localhost:8501>.
`data/documents/` is mounted into the backend at `/data/documents`, and
`file_path` holds the bare file name:

```sql
INSERT INTO documents (user_id, title, source_type, file_path, content_hash)
VALUES (
    '00000000-0000-0000-0000-000000000001',   -- the dev user from db/seed
    'LangChain book',
    'textbook',
    '3A979-8-8688-2946-8.pdf',
    'demo-1'
)
RETURNING id;
```

Run the pipeline with the id it printed. It extracts with docling, chunks,
detects the language and embeds:

```bash
docker compose exec backend python -m ingestion.ingest -d <document-uuid>
```

That book is 744 pages. On a gpu it extracts in 33 s and ends at 917 chunks
and 191356 tokens, embedded in four batches, about 40 s in total.

Then look at what landed, again in the SQL console:

```sql
SELECT
    doc.title,
    doc.status,
    doc.language,
    count(cnk.*) AS chunks,
    round(avg(c.token_count)) AS avg_tokens
FROM
    documents doc
LEFT JOIN chunks cnk
    ON cnk.document_id = doc.id
GROUP BY
    doc.id,
    doc.title,
    doc.status,
    doc.language;

SELECT
    chunk_index,
    meta_data->'pages' AS pages,
    left(content, 60) AS start
FROM
    chunks
ORDER BY
    chunk_index
LIMIT 5;
```

Swagger is on <http://localhost:5000/docs>.

## Where things are

| Path               | What it holds                                     |
| ------------------ | ------------------------------------------------- |
| `src/backend/`     | FastAPI, SQLAlchemy 2.0 async, the ingestion code |
| `src/frontend-st/` | Streamlit, currently a SQL console                |
| `db/init/`         | the schema, applied when the volume is created    |
| `db/seed/`         | dev user and sample rows                          |
| `docs/`            | the API contract                                  |

## Before committing

Linting and formatting run as a git hook. Once per machine:

```bash
uv tool install pre-commit
pre-commit install            # once per clone, writes .git/hooks/pre-commit
```

The hooks are `ruff check` and `ruff format --check`, which reject a commit
instead of rewriting your code, plus merge conflict markers, yaml and toml
syntax, large files, private keys, trailing whitespace and the final newline.
They live in `.pre-commit-config.yaml` and run in their own environments, so
neither the backend venv nor `pyproject.toml` is involved.

```bash
pre-commit run --all-files    # check the whole repo without committing
pre-commit autoupdate         # pin the hooks to their current releases
```
