import enum


class SourceType(enum.StrEnum):
    SLIDES = "slides"
    LECTURE_TRANSCRIPT = "lecture_transcript"
    EXERCISE_SHEET = "exercise_sheet"
    TEXTBOOK = "textbook"
    LECTURE_NOTES = "lecture_notes"
    PAPER = "paper"
    ARTICLE = "article"
    OTHER = "other"


class IngestionStatus(enum.StrEnum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    TRANSFORMING = "transforming"
    EMBEDDING = "embedding"
    DONE = "done"
    FAILED = "failed"


class TermSeason(enum.StrEnum):
    WINTER = "winter"
    SUMMER = "summer"


class MaterialRole(enum.StrEnum):
    PRIMARY = "primary"
    SUPPLEMENTARY = "supplementary"


class Lang(enum.StrEnum):
    DE = "de"
    EN = "en"


def enum_values(enum_class: type[enum.StrEnum]) -> list[str]:
    # This function is used to get the values of an enum class
    return [member.value for member in enum_class]
