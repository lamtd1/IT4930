"""
Text utility functions for the book retrieval benchmark.

All functions are pure (no side effects) and fully type-hinted so they
can be tested in isolation without any external dependencies.
"""

from __future__ import annotations

import re
import unicodedata


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
_WHITESPACE_PATTERN = re.compile(r"\s+")

# BGE models expect this prefix for query encoding (not for corpus documents)
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def clean_text(text: str) -> str:
    """
    Normalise raw book description text for indexing and retrieval.

    Steps applied in order:
    1. Strip HTML tags
    2. Remove URLs
    3. Normalise unicode to NFKD then encode as ASCII (drops accents)
    4. Collapse whitespace and strip leading/trailing spaces

    Args:
        text: Raw string (may contain HTML, URLs, unicode characters).

    Returns:
        Cleaned plain-text string.  Returns empty string for non-string inputs.
    """
    if not isinstance(text, str):
        return ""

    # Remove HTML tags
    text = _HTML_TAG_PATTERN.sub(" ", text)

    # Remove URLs
    text = _URL_PATTERN.sub(" ", text)

    # Normalise unicode (NFKD decomposes characters, then encode strips non-ASCII)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Collapse whitespace
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()

    return text


def build_corpus_text(
    title: str,
    description: str,
    categories: str = "",
) -> str:
    """
    Build a single concatenated text field used for TF-IDF and BM25 indexing.

    The title is repeated twice to give it additional weight in sparse models
    without requiring custom IDF modifications.

    Args:
        title:       Book title.
        description: Book description / synopsis (should already be cleaned).
        categories:  Comma-separated genre/category tags (optional).

    Returns:
        Concatenated corpus string ready for vectorisation.
    """
    parts: list[str] = []

    if title:
        clean_title = clean_text(title)
        parts.append(clean_title)
        parts.append(clean_title)  # repeat for weighting

    if description:
        parts.append(clean_text(description))

    if categories:
        parts.append(clean_text(categories))

    return " ".join(filter(None, parts))


def apply_bge_query_prefix(query: str) -> str:
    """
    Prepend the BGE instruction prefix to a query string.

    BGE bi-encoder models are trained with this prefix on query inputs
    (but NOT on corpus documents) for asymmetric retrieval tasks.

    Args:
        query: Raw user query string.

    Returns:
        Query with BGE instruction prefix prepended.
    """
    return f"{BGE_QUERY_PREFIX}{query}"


def tokenize_for_bm25(text: str) -> list[str]:
    """
    Simple whitespace tokeniser used for BM25 indexing and querying.

    Lowercases the text before splitting to ensure consistent tokenisation.

    Args:
        text: Input text string.

    Returns:
        List of lowercase tokens.
    """
    return text.lower().split()
