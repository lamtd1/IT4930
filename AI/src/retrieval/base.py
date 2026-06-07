"""
Abstract base class for all retriever implementations.

Every retriever in this benchmark exposes the same ``search`` interface
so the evaluator and hybrid fusion layer are completely retriever-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.schemas.retrieval import RetrievalResult


class BaseRetriever(ABC):
    """
    Abstract retriever interface.

    Subclasses must implement:
    - ``search(query, top_k) -> list[RetrievalResult]``
    - ``name`` property returning a human-readable identifier

    Optionally override:
    - ``build(...)`` – index construction
    - ``load(...)`` – index loading from disk
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name used in evaluation reports."""
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Retrieve the top-k most relevant documents for ``query``.

        Args:
            query:  Natural-language search query string.
            top_k:  Maximum number of results to return.

        Returns:
            Ranked list of ``RetrievalResult`` objects (most relevant first).
            May return fewer than ``top_k`` if the corpus is smaller.
        """
        ...
