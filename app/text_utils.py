import re
import unicodedata

STOPWORDS = {
    "les", "des", "une", "aux", "pour", "dans", "avec", "sur", "par", "est",
    "sont", "que", "qui", "pas", "plus", "son", "ses", "leur", "leurs", "cette",
    "ces", "ainsi", "vers", "chez", "entre", "sans", "sous", "tout", "tous",
    "faire", "afin", "the", "and",
    # trop génériques pour distinguer un département
    "service", "departement",
}


def normalize(text: str | None) -> str:
    """Minuscules, sans accents, apostrophes conservées."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _stem(token: str) -> str:
    # Singularisation grossière (suffisant pour un v1 à base de règles)
    if len(token) > 4 and token.endswith(("s", "x")):
        return token[:-1]
    return token


def tokenize(text: str | None) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", normalize(text))
    return {_stem(t) for t in tokens if len(t) >= 3 and t not in STOPWORDS}
