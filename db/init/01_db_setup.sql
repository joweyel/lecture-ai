CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE "source_type" AS ENUM (
  'slides',
  'lecture_transcript',
  'exercise_sheet',
  'textbook',
  'lecture_notes',
  'paper',
  'article',
  'other'
);

CREATE TYPE "ingestion_status" AS ENUM (
  'pending',
  'extracting',
  'transforming',
  'embedding',
  'done',
  'failed'
);

CREATE TYPE "term_season" AS ENUM ('winter', 'summer');

CREATE TYPE "material_role" AS ENUM ('primary', 'supplementary');

CREATE TYPE "lang" AS ENUM ('de', 'en');

CREATE TABLE
  "users" (
    "id" UUID PRIMARY KEY DEFAULT (gen_random_uuid ()),
    "email" varchar(100) UNIQUE NOT NULL,
    "hashed_password" varchar(1024) NOT NULL,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "is_superuser" BOOLEAN NOT NULL DEFAULT false,
    "is_verified" BOOLEAN NOT NULL DEFAULT false,
    "created_at" timestamptz NOT NULL DEFAULT (now ())
  );

CREATE TABLE
  "documents" (
    "id" UUID PRIMARY KEY DEFAULT (gen_random_uuid ()),
    "user_id" UUID NOT NULL,
    "title" TEXT NOT NULL,
    "origin" TEXT,
    "source_type" source_type NOT NULL,
    "author" TEXT,
    "created_date" DATE,
    "file_path" TEXT NOT NULL,
    "content_hash" TEXT NOT NULL,
    "status" ingestion_status NOT NULL DEFAULT 'pending',
    "error" TEXT,
    "ingested_at" timestamptz,
    "created_at" timestamptz NOT NULL DEFAULT (now ())
  );

CREATE TABLE
  "universities" (
    "id" UUID PRIMARY KEY DEFAULT (gen_random_uuid ()),
    "name" TEXT UNIQUE NOT NULL
  );

CREATE TABLE
  "courses" (
    "id" UUID PRIMARY KEY DEFAULT (gen_random_uuid ()),
    "user_id" UUID NOT NULL,
    "university_id" UUID,
    "name" TEXT NOT NULL,
    "code" TEXT
  );

CREATE TABLE
  "lecture_editions" (
    "id" UUID PRIMARY KEY DEFAULT (gen_random_uuid ()),
    "course_id" UUID NOT NULL,
    "year" INTEGER NOT NULL,
    "season" term_season NOT NULL,
    "lecturer" TEXT,
    "created_at" timestamptz NOT NULL DEFAULT (now ())
  );

CREATE TABLE
  "lecture_documents" (
    "edition_id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "role" material_role NOT NULL,
    "week" INTEGER,
    PRIMARY KEY ("edition_id", "document_id")
  );

CREATE TABLE
  "chunks" (
    "id" UUID PRIMARY KEY DEFAULT (gen_random_uuid ()),
    "document_id" UUID NOT NULL,
    "chunk_index" INTEGER NOT NULL,
    "content" TEXT NOT NULL,
    "embedding" vector (1024),
    "created_at" timestamptz NOT NULL DEFAULT (now ()),
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "embedding_model" TEXT,
    "token_count" INTEGER,
    "language" lang
  );

CREATE UNIQUE INDEX "documents_user_content_hash_idx" ON "documents" ("user_id", "content_hash");

CREATE INDEX ON "documents" ("source_type");

CREATE INDEX ON "documents" ("status");

CREATE UNIQUE INDEX "courses_user_id_university_id_name_idx" ON "courses" ("user_id", "university_id", "name");

CREATE UNIQUE INDEX "lecture_editions_course_year_season_idx" ON "lecture_editions" ("course_id", "year", "season");

CREATE INDEX "lecture_documents_document_idx" ON "lecture_documents" ("document_id");

CREATE INDEX "chunks_document_idx" ON "chunks" ("document_id");

CREATE UNIQUE INDEX "chunks_document_chunk_index_idx" ON "chunks" ("document_id", "chunk_index");

COMMENT ON COLUMN "documents"."content_hash" IS 'Avoids reinserting identical documents';

COMMENT ON COLUMN "documents"."error" IS 'last failure reason';

COMMENT ON COLUMN "universities"."name" IS 'Name of the university';

COMMENT ON COLUMN "courses"."code" IS 'Course code of the university lecture';

COMMENT ON COLUMN "lecture_editions"."year" IS 'winter term: starting year (2019 = WS 2019/20)';

COMMENT ON COLUMN "chunks"."chunk_index" IS 'Order within the document';

COMMENT ON COLUMN "chunks"."embedding" IS 'bge-m3 dense embedding; NULL until embedded';

COMMENT ON COLUMN "chunks"."metadata" IS 'free-form extras: section, slide number, extractor info';

ALTER TABLE "documents" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "courses" ADD FOREIGN KEY ("university_id") REFERENCES "universities" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "courses" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "lecture_editions" ADD FOREIGN KEY ("course_id") REFERENCES "courses" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "lecture_documents" ADD FOREIGN KEY ("edition_id") REFERENCES "lecture_editions" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "lecture_documents" ADD FOREIGN KEY ("document_id") REFERENCES "documents" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "chunks" ADD FOREIGN KEY ("document_id") REFERENCES "documents" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;