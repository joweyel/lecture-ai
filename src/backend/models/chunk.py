from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.enums import Lang, enum_values

type MetaDataDict = dict[str, Any]


class Chunks(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        CheckConstraint(
            "chunk_index >= 0",
            name="chunks_chunk_index_nonnegative",
        ),
        CheckConstraint(
            "token_count IS NULL OR token_count > 0",
            name="chunks_token_count_positive",
        ),
        CheckConstraint(
            "(embedding_model IS NULL) = (embedding IS NULL)",
            name="chunks_embedding_model_equal",
        ),
        Index("chunks_document_idx", "document_id"),
        Index(
            "chunks_document_chunk_index_idx",
            "document_id",
            "chunk_index",
            unique=True,
        ),
        Index("chunks_tsv_idx", "tsv", postgresql_using="gin"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR(1024))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    meta_data: Mapped[MetaDataDict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    embedding_model: Mapped[str | None] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[Lang | None] = mapped_column(
        ENUM(
            Lang,
            name="lang",
            create_type=False,
            values_callable=enum_values,
        ),
    )
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector(CASE language WHEN 'de' THEN 'german'::regconfig WHEN 'en' THEN 'english'::regconfig ELSE 'english'::regconfig END, content)",
            persisted=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Chunk {self.id} "
            f"document_id={self.document_id} "
            f"chunk_index={self.chunk_index} "
            f"content={self.content[:10]}...>"
        )
