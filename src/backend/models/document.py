from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.enums import IngestionStatus, SourceType, enum_values


class Documents(Base):
    __tablename__ = "documents"
    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[SourceType] = mapped_column(
        ENUM(
            SourceType,
            name="source_type",
            create_type=False,  # enum type already in postrgres
            values_callable=enum_values,
        )
    )
    author: Mapped[str | None] = mapped_column(Text)
    created_date: Mapped[date | None] = mapped_column(Date)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IngestionStatus] = mapped_column(
        ENUM(
            IngestionStatus,
            name="ingestion_status",
            create_type=False,
            values_callable=enum_values,
        ),
        default=IngestionStatus.PENDING,
    )
    error: Mapped[str | None] = mapped_column(Text)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Document {self.title!r} {self.source_type.value}>"
