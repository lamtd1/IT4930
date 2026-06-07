"""
BM25 Retriever implementation using rank-bm25.

Supports:
- Building and persisting a BM25Okapi index
- Loading an existing index from disk
- Returning ranked RetrievalResult objects
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

from src.retrieval.base import BaseRetriever
from src.schemas.retrieval import RetrievalResult
from src.utils.text_utils import build_corpus_text, tokenize_for_bm25

logger = logging.getLogger(__name__)


class BM25Retriever(BaseRetriever):
    """
    Retriever backed by BM25Okapi (Okapi BM25 probabilistic model).

    Args:
        bm25:      Fitted ``BM25Okapi`` instance.
        isbn_list: Ordered list of ISBN-13 strings aligned with BM25 corpus.
        title_map: Mapping from ISBN-13 to book title.
    """

    def __init__(
        self,
        bm25: BM25Okapi,
        isbn_list: list[str],
        title_map: dict[str, str],
    ) -> None:
        self._bm25 = bm25
        self._isbn_list = isbn_list
        self._title_map = title_map

    @property
    def name(self) -> str:
        return "bm25"

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------
    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        index_path: Path,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> "BM25Retriever":
        """
        Build a BM25 index over the corpus and persist it to disk.

        Args:
            df:         DataFrame with ``isbn13``, ``title``, ``description``,
                        and optionally ``categories`` columns.
            index_path: Destination pickle path for the BM25 index.
            k1:         BM25 k1 hyperparameter (term frequency saturation).
            b:          BM25 b hyperparameter (document length normalisation).

        Returns:
            A ready-to-use ``BM25Retriever`` instance.
        """
        logger.info("Building BM25 index: %d documents, k1=%.2f, b=%.2f", len(df), k1, b)

        tokenized_corpus: list[list[str]] = []
        for _, row in df.iterrows():
            text = build_corpus_text(
                title=str(row.get("title", "")),
                description=str(row.get("description", "")),
                categories=str(row.get("categories", "")),
            )
            tokenized_corpus.append(tokenize_for_bm25(text))

        bm25 = BM25Okapi(tokenized_corpus, k1=k1, b=b)

        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, "wb") as fh:
            pickle.dump(bm25, fh)

        logger.info("BM25 index saved to %s", index_path)

        isbn_list = df["isbn13"].astype(str).tolist()
        title_map = dict(zip(df["isbn13"].astype(str), df["title"].astype(str)))

        return cls(bm25, isbn_list, title_map)

    @classmethod
    def load(
        cls,
        index_path: Path,
        df: pd.DataFrame,
    ) -> "BM25Retriever":
        """
        Load a pre-built BM25 index from disk.

        Args:
            index_path: Path to the pickled BM25 index.
            df:         DataFrame (used to reconstruct isbn/title maps).

        Returns:
            A ready-to-use ``BM25Retriever`` instance.
        """
        logger.info("Loading BM25 index from %s", index_path)
        with open(index_path, "rb") as fh:
            bm25: BM25Okapi = pickle.load(fh)

        isbn_list = df["isbn13"].astype(str).tolist()
        title_map = dict(zip(df["isbn13"].astype(str), df["title"].astype(str)))

        logger.info("BM25 index loaded: %d documents in corpus", len(isbn_list))
        return cls(bm25, isbn_list, title_map)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Retrieve top-k documents using BM25 relevance scoring.

        Args:
            query:  Natural-language search query.
            top_k:  Number of results to return.

        Returns:
            Ranked list of ``RetrievalResult`` (highest BM25 score first).
        """
        tokenized_query = tokenize_for_bm25(query)
        scores: np.ndarray = self._bm25.get_scores(tokenized_query)

        top_indices = np.argsort(scores)[::-1]
        results: list[RetrievalResult] = []

        rank = 1
        for idx in top_indices:
            if idx >= len(self._isbn_list):
                continue
            isbn = self._isbn_list[idx]
            results.append(
                RetrievalResult(
                    isbn13=isbn,
                    title=self._title_map.get(isbn, ""),
                    score=float(scores[idx]),
                    rank=rank,
                )
            )
            rank += 1
            if rank > top_k:
                break

        return results
