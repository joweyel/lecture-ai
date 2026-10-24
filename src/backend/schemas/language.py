from pydantic import BaseModel, Field

from models.enums import Lang


class LanguageDetectRequest(BaseModel):
    """Text to detect the language of."""

    text: str = Field(min_length=1, description="Text to detect the language of.")


class LanguageDetectResponse(BaseModel):
    """Response containing the detected language."""

    language: Lang | None = Field(description="Detected language. Either 'en' or 'de'.")
