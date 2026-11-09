from lingua import Language, LanguageDetectorBuilder

from models.enums import Lang

LANGUAGES: list[Language] = [Language.ENGLISH, Language.GERMAN]
detector = LanguageDetectorBuilder.from_languages(*LANGUAGES).build()


def detect_language(text: str) -> Lang | None:
    """
    Detect the language of the given text.

    Parameters
    ----------
    text: str
        The text to detect the language of.

    Returns
    -------
    Lang | None
        The detected language or None if the language could not be detected.
    """
    language = detector.detect_language_of(text)
    if language is None:
        return None
    return Lang(language.iso_code_639_1.name.lower())  # 'en'


if __name__ == "__main__":
    print(detect_language("Hello, world!"))
    print(detect_language("Hallo, Welt!"))

    # From: https://github.com/pemistahl/lingua-py#detection-of-multiple-languages
    text_en: str = """
    In the example above, a list is returned containing those languages which the
    calling instance of LanguageDetector has been built from, sorted by their
    confidence value in descending order. Each value is a probability between
    0.0 and 1.0. The probabilities of all languages will sum to 1.0. If the
    language is unambiguously identified by the rule engine, the value 1.0 will
    always be returned for this language. The other languages will receive a
    value of 0.0.
    """
    print(detect_language(text_en))
    assert detect_language(text_en) == Lang.EN.lower()

    # From: https://de.wikipedia.org/wiki/Technische_Universit%C3%A4t_Darmstadt
    text_de: str = """
    Die Technische Universität Darmstadt ist eine 1877 in Darmstadt gegründete
    technische Universität. Sie ist seit 2004 die erste vollständig autonome
    Universität der Bundesrepublik Deutschland. Das heißt, sie legt alleine ihre
    Forschungsschwerpunkte fest und beruft ihre Professoren.[7] Mit rund 25.000
    Studenten und 5000 Beschäftigten, davon etwa 350 Professoren, zählt sie zu
    den mittelgroßen Universitäten in Deutschland und gehört dem Universitätsverbund
    der TU9 an.
    """
    print(detect_language(text_de))
    assert detect_language(text_de) == Lang.DE.lower()
