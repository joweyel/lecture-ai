-- Sample lecture material for development and demos.
-- Depends on dev_user.sql: every row is owned by the development user.
-- Fixed UUIDs so the data survives re-runs and can be referenced by hand.
-- Idempotent: safe to run as often as you like.
--
--   docker compose exec -T db bash -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < db/seed/sample_data.sql
--
-- Chunks are seeded without embeddings on purpose: the ingestion pipeline
-- fills those in, and the chunks_embedding_model_equal constraint requires
-- embedding and embedding_model to be set together.

BEGIN;

-- ── Universities ────────────────────────────────────────────────────────────

INSERT INTO universities (id, name)
VALUES
    ('10000000-0000-0000-0000-000000000001', 'Technische Universität Berlin'),
    ('10000000-0000-0000-0000-000000000002', 'University of Edinburgh')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- ── Courses ─────────────────────────────────────────────────────────────────

INSERT INTO courses (id, user_id, university_id, name, code)
VALUES
    (
        '20000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000001',
        '10000000-0000-0000-0000-000000000001',
        'Datenbanksysteme',
        'DBS-101'
    ),
    (
        '20000000-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000001',
        '10000000-0000-0000-0000-000000000002',
        'Machine Learning for Developers',
        'INFR-11020'
    )
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    code = EXCLUDED.code;

-- ── Lecture editions ────────────────────────────────────────────────────────

INSERT INTO lecture_editions (id, course_id, year, season, lecturer)
VALUES
    (
        '30000000-0000-0000-0000-000000000001',
        '20000000-0000-0000-0000-000000000001',
        2025,
        'winter',
        'Prof. Dr. A. Schneider'
    ),
    (
        '30000000-0000-0000-0000-000000000002',
        '20000000-0000-0000-0000-000000000002',
        2026,
        'summer',
        'Dr. M. Okoro'
    )
ON CONFLICT (id) DO UPDATE SET lecturer = EXCLUDED.lecturer;

-- ── Documents ───────────────────────────────────────────────────────────────
-- Mixed source types and ingestion states so the status filters have something
-- to show. file_path points at files that do not exist yet; nothing reads them
-- until the upload endpoint is built.

INSERT INTO documents (
    id, user_id, title, origin, source_type, author,
    created_date, file_path, content_hash, status, error, ingested_at
)
VALUES
    (
        '40000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000001',
        'Relationale Algebra, Woche 3',
        'TU Berlin ISIS',
        'slides',
        'Prof. Dr. A. Schneider',
        DATE '2025-10-20',
        '/data/documents/dbs-w03-relationale-algebra.pdf',
        'seed-hash-dbs-w03',
        'done',
        NULL,
        TIMESTAMPTZ '2025-10-21 09:14:00+02'
    ),
    (
        '40000000-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000001',
        'Normalformen und Schlüssel, Woche 4',
        'TU Berlin ISIS',
        'slides',
        'Prof. Dr. A. Schneider',
        DATE '2025-10-27',
        '/data/documents/dbs-w04-normalformen.pdf',
        'seed-hash-dbs-w04',
        'done',
        NULL,
        TIMESTAMPTZ '2025-10-28 10:02:00+01'
    ),
    (
        '40000000-0000-0000-0000-000000000003',
        '00000000-0000-0000-0000-000000000001',
        'Übungsblatt 2: Anfrageoptimierung',
        'TU Berlin ISIS',
        'exercise_sheet',
        NULL,
        DATE '2025-11-03',
        '/data/documents/dbs-uebung-02.pdf',
        'seed-hash-dbs-ex02',
        'pending',
        NULL,
        NULL
    ),
    (
        '40000000-0000-0000-0000-000000000004',
        '00000000-0000-0000-0000-000000000001',
        'Gradient Descent and Backpropagation',
        'Course website',
        'slides',
        'Dr. M. Okoro',
        DATE '2026-04-14',
        '/data/documents/ml-l05-gradient-descent.pdf',
        'seed-hash-ml-l05',
        'done',
        NULL,
        TIMESTAMPTZ '2026-04-15 16:40:00+01'
    ),
    (
        '40000000-0000-0000-0000-000000000005',
        '00000000-0000-0000-0000-000000000001',
        'Lecture 5 transcript',
        'Automatic transcription',
        'lecture_transcript',
        NULL,
        DATE '2026-04-14',
        '/data/documents/ml-l05-transcript.txt',
        'seed-hash-ml-l05-tr',
        'failed',
        'Audio track too quiet to transcribe past 00:42:11',
        NULL
    ),
    (
        '40000000-0000-0000-0000-000000000006',
        '00000000-0000-0000-0000-000000000001',
        'Notes on vector search',
        NULL,
        'lecture_notes',
        'Johannes Weyel',
        DATE '2026-05-02',
        '/data/documents/personal-vector-search-notes.md',
        'seed-hash-notes-vec',
        'done',
        NULL,
        TIMESTAMPTZ '2026-05-02 21:05:00+02'
    )
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    status = EXCLUDED.status,
    error = EXCLUDED.error;

-- ── Edition membership ──────────────────────────────────────────────────────
-- Document 6 is deliberately left out: loose material with no course, which is
-- the case the documents/users relationship exists to support.

INSERT INTO lecture_documents (edition_id, document_id, role, week)
VALUES
    ('30000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001', 'primary', 3),
    ('30000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000002', 'primary', 4),
    ('30000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000003', 'supplementary', 4),
    ('30000000-0000-0000-0000-000000000002', '40000000-0000-0000-0000-000000000004', 'primary', 5),
    ('30000000-0000-0000-0000-000000000002', '40000000-0000-0000-0000-000000000005', 'supplementary', 5)
ON CONFLICT (edition_id, document_id) DO UPDATE SET
    role = EXCLUDED.role,
    week = EXCLUDED.week;

-- ── Chunks ──────────────────────────────────────────────────────────────────
-- Both languages, so the tsv generated column exercises the german and the
-- english text search configuration. embedding stays NULL until ingestion runs.

INSERT INTO chunks (id, document_id, chunk_index, content, metadata, token_count, language)
VALUES
    (
        '50000000-0000-0000-0000-000000000001',
        '40000000-0000-0000-0000-000000000001',
        0,
        'Die relationale Algebra beschreibt Operationen auf Relationen. '
        'Die wichtigsten Operatoren sind Selektion, Projektion, Vereinigung, '
        'Differenz und das kartesische Produkt.',
        '{"slide": 4, "section": "Grundlagen"}',
        34,
        'de'
    ),
    (
        '50000000-0000-0000-0000-000000000002',
        '40000000-0000-0000-0000-000000000001',
        1,
        'Ein Verbund lässt sich aus kartesischem Produkt und Selektion '
        'zusammensetzen. Datenbanken optimieren diesen Fall, weil das '
        'Zwischenergebnis des Produkts sehr groß werden kann.',
        '{"slide": 9, "section": "Verbundoperationen"}',
        38,
        'de'
    ),
    (
        '50000000-0000-0000-0000-000000000003',
        '40000000-0000-0000-0000-000000000002',
        0,
        'Eine Relation ist in dritter Normalform, wenn sie in zweiter '
        'Normalform ist und kein Nichtschlüsselattribut transitiv vom '
        'Primärschlüssel abhängt.',
        '{"slide": 12, "section": "Normalformen"}',
        31,
        'de'
    ),
    (
        '50000000-0000-0000-0000-000000000004',
        '40000000-0000-0000-0000-000000000004',
        0,
        'Gradient descent updates each parameter by stepping against the '
        'gradient of the loss. The learning rate controls how far each step '
        'moves, and choosing it badly is the most common cause of a model '
        'that will not converge.',
        '{"slide": 7, "section": "Optimisation"}',
        45,
        'en'
    ),
    (
        '50000000-0000-0000-0000-000000000005',
        '40000000-0000-0000-0000-000000000004',
        1,
        'Backpropagation applies the chain rule backwards through the network, '
        'reusing the intermediate results computed during the forward pass '
        'instead of recomputing them for every parameter.',
        '{"slide": 11, "section": "Optimisation"}',
        36,
        'en'
    ),
    (
        '50000000-0000-0000-0000-000000000006',
        '40000000-0000-0000-0000-000000000006',
        0,
        'Dense retrieval finds passages whose meaning is close to the query, '
        'while keyword search matches the exact terms a reader typed. Hybrid '
        'search runs both and merges the two ranked lists.',
        '{"section": "Retrieval"}',
        40,
        'en'
    ),
    (
        '50000000-0000-0000-0000-000000000007',
        '40000000-0000-0000-0000-000000000006',
        1,
        'Reciprocal rank fusion combines result lists by position rather than '
        'by score, which avoids having to make cosine distance and a lexical '
        'rank comparable to one another.',
        '{"section": "Retrieval"}',
        37,
        'en'
    )
ON CONFLICT (id) DO UPDATE SET
    content = EXCLUDED.content,
    metadata = EXCLUDED.metadata,
    token_count = EXCLUDED.token_count,
    language = EXCLUDED.language;

COMMIT;
