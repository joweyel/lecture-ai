from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.enums import MaterialRole, TermSeason
from schemas.base import ReadBase

########################################################
##                  Universities                      ##
########################################################


class UniversityCreate(BaseModel):
    """Fields a user may send when registering a university."""

    name: str = Field(min_length=1, description="Name of the university")


class UniversityRead(BaseModel):
    """What the API returns, including the server-owned fields."""

    model_config = ConfigDict(
        from_attributes=True,
    )
    id: UUID = Field(description="Unique identifier for the university")
    name: str = Field(description="Name of the university")


class UniversityUpdate(BaseModel):
    """Fields a user may change. All optional; PATCH sends only what changes."""

    name: str | None = Field(None, min_length=1, description="Name of the university")


########################################################
##                     Courses                        ##
########################################################


class CourseCreate(BaseModel):
    """Fields a user may send when registering a course."""

    name: str = Field(min_length=1, description="Name of the course")
    code: str | None = Field(None, min_length=1, description="Code at the university")
    university_id: UUID | None = Field(
        None, description="University this course belongs to"
    )


class CourseUpdate(BaseModel):
    """Fields a user may change. All optional; PATCH sends only what changes."""

    name: str | None = Field(None, min_length=1, description="Name of the course")
    code: str | None = Field(None, min_length=1, description="Code at the university")
    university_id: UUID | None = Field(
        None, description="University this course belongs to"
    )


class CourseRead(ReadBase):
    """What the API returns, including the server-owned fields."""

    id: UUID = Field(description="Unique identifier for the course")
    name: str = Field(description="Name of the course")
    code: str | None = Field(None, description="Code at the university")
    university_id: UUID | None = Field(
        None, description="University this course belongs to"
    )


########################################################
##                LectureEditions                     ##
########################################################


class LectureEditionsCreate(BaseModel):
    """Fields a user may send when registering a lecture edition.

    course_id comes from the path: POST /courses/{course_id}/editions
    """

    year: int = Field(ge=1900, le=2100, description="Year of the lecture edition")
    season: TermSeason = Field(description="Season of the lecture edition")
    lecturer: str | None = Field(None, description="Lecturer of the lecture edition")


class LectureEditionsUpdate(BaseModel):
    """Fields a user may change. All optional; PATCH sends only what changes."""

    year: int | None = Field(
        None, ge=1900, le=2100, description="Year of the lecture edition"
    )
    season: TermSeason | None = Field(None, description="Season of the lecture edition")
    lecturer: str | None = Field(None, description="Lecturer of the lecture edition")


class LectureEditionsRead(ReadBase):
    """What the API returns, including the server-owned fields."""

    id: UUID = Field(description="Unique identifier for the lecture edition")
    course_id: UUID = Field(description="Course this lecture edition belongs to")
    year: int = Field(description="Year of the lecture edition")
    season: TermSeason = Field(description="Season of the lecture edition")
    lecturer: str | None = Field(None, description="Lecturer of the lecture edition")
    created_at: datetime = Field(
        description="Date and time the lecture edition was created"
    )


########################################################
##                LectureDocuments                    ##
########################################################


class LectureDocumentsCreate(BaseModel):
    """Fields a user may send when registering a lecture document."""

    edition_id: UUID = Field(description="Edition this lecture document belongs to")
    document_id: UUID = Field(description="Document this lecture document belongs to")
    role: MaterialRole = Field(description="Role of the lecture document")
    week: int | None = Field(None, ge=1, description="Week of the lecture document")


class LectureDocumentsUpdate(BaseModel):
    """Fields a user may change. All optional; PATCH sends only what changes."""

    role: MaterialRole | None = Field(None, description="Role of the lecture document")
    week: int | None = Field(None, ge=1, description="Week within the edition")


class LectureDocumentsRead(ReadBase):
    """What the API returns, including the server-owned fields."""

    edition_id: UUID = Field(description="Edition this lecture document belongs to")
    document_id: UUID = Field(description="Document this lecture document belongs to")
    role: MaterialRole = Field(description="Role of the lecture document")
    week: int | None = Field(None, description="Week of the lecture document")
