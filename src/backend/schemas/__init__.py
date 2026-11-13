from .base import ReadBase
from .chunk import ChunkRead
from .document import (
    DocumentCreate,
    DocumentRead,
    DocumentStatus,
    DocumentUpdate,
)
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
    "ChunkRead",
    "CourseCreate",
    "CourseRead",
    "CourseUpdate",
    "DocumentCreate",
    "DocumentRead",
    "DocumentStatus",
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
