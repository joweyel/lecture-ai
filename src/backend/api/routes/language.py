from fastapi import APIRouter

from ingestion.language import detect_language as detect_language_fn
from schemas.language import LanguageDetectRequest, LanguageDetectResponse

router = APIRouter(prefix="/language", tags=["language"])


@router.post("/detect", response_model=LanguageDetectResponse)
def detect_language(text: LanguageDetectRequest):
    """Detect the language of the given text.

    Parameters
    ----------
    text : LanguageDetectRequest
        The text to detect the language of.

    Returns
    -------
    LanguageDetectResponse
        The detected language.
    """
    return LanguageDetectResponse(language=detect_language_fn(text.text))
