from .base import ReadBase
from .document import DocumentCreate, DocumentRead, DocumentUpdate
from .lectures import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    LectureDocumentsCreate,
    LectureDocumentsRead,
    LectureDocumentsUpdate,
    LectureEditionsCreate,
    LectureEditionsRead,
    LectureEditionsUpdate,
    UniversityCreate,
    UniversityRead,
    UniversityUpdate,
)

__all__ = [
    "CourseCreate",
    "CourseRead",
    "CourseUpdate",
    "DocumentCreate",
    "DocumentRead",
    "DocumentUpdate",
    "LectureDocumentsCreate",
    "LectureDocumentsRead",
    "LectureDocumentsUpdate",
    "LectureEditionsCreate",
    "LectureEditionsRead",
    "LectureEditionsUpdate",
    "ReadBase",
    "UniversityCreate",
    "UniversityRead",
    "UniversityUpdate",
]
