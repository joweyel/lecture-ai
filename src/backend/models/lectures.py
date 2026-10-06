from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.enums import MaterialRole, TermSeason, enum_values

# TODO: Adding Indexes for better documntation later


class Universities(Base):
    __tablename__ = "universities"
    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    def __repr__(self):
        return f"<University {self.name!r}>"


class Courses(Base):
    __tablename__ = "courses"
    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    university_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("universities.id"),
    )  # Course can also be independent of university
    name: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str | None] = mapped_column(Text)

    def __repr__(self):
        return f"<Course {self.name!r}, {self.code!r}>"


class LectureEditions(Base):
    __tablename__ = "lecture_editions"
    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    course_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[TermSeason] = mapped_column(
        ENUM(
            TermSeason,
            name="term_season",
            create_type=False,
            values_callable=enum_values,
        )
    )
    lecturer: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LectureDocuments(Base):
    __tablename__ = "lecture_documents"
    __table_args__ = (PrimaryKeyConstraint("edition_id", "document_id"),)

    edition_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("lecture_editions.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MaterialRole] = mapped_column(
        ENUM(
            MaterialRole,
            name="material_role",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    week: Mapped[int | None] = mapped_column(Integer)

    def __repr__(self):
        return f"<LectureDocument {self.role!r}, {self.week!r}>"
