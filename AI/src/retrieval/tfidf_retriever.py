"""
TF-IDF Retriever implementation using scikit-learn.

Supports:
- Building and persisting a TfidfVectorizer and its sparse matrix
- Loading an existing model from disk
- Cosine similarity search returning ranked RetrievalResult objects
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.retrieval.base import BaseRetriever
from src.schemas.retrieval import RetrievalResult
from src.utils.text_utils import build_corpus_text

logger = logging.getLogger(__name__)


class TFIDFRetriever(BaseRetriever):
    """
    Retriever backed by a TF-IDF sparse vector space model.

    Args:
        vectorizer:   Fitted ``TfidfVectorizer`` instance.
        tfidf_matrix: Sparse document-term matrix (n_docs × n_features).
        isbn_list:    Ordered list of ISBN-13 strings aligned with matrix rows.
        title_map:    Mapping from ISBN-13 to book title (for result objects).
    """

    def __init__(
        self,
        vectorizer: TfidfVectorizer,
        tfidf_matrix: sp.spmatrix,
        isbn_list: list[str],
        title_map: dict[str, str],
    ) -> None:
        self._vectorizer = vectorizer
        self._tfidf_matrix = tfidf_matrix
        self._isbn_list = isbn_list
        self._title_map = title_map

    @property
    def name(self) -> str:
        return "tfidf"

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------
    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        model_path: Path,
        matrix_path: Path,
        max_features: int = 15000,
        min_df: int = 2,
    ) -> "TFIDFRetriever":
        """
        Fit a TfidfVectorizer on the corpus and persist artefacts to disk.

        Args:
            df:           DataFrame with columns ``isbn13``, ``title``, ``description``,
                          and optionally ``categories``.
            model_path:   Destination pickle path for the fitted vectorizer.
            matrix_path:  Destination ``.npz`` path for the sparse matrix.
            max_features: Vocabulary size cap.
            min_df:       Minimum document frequency for a term to be included.

        Returns:
            A ready-to-use ``TFIDFRetriever`` instance.
        """
        logger.info(
            "Building TF-IDF index: %d documents, max_features=%d, min_df=%d",
            len(df),
            max_features,
            min_df,
        )

        corpus = df.apply(
            lambda row: build_corpus_text(
                title=str(row.get("title", "")),
                description=str(row.get("description", "")),
                categories=str(row.get("categories", "")),
            ),
            axis=1,
        ).tolist()

        vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=min_df,
            stop_words="english",
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # Persist artefacts
        model_path.parent.mkdir(parents=True, exist_ok=True)
        matrix_path.parent.mkdir(parents=True, exist_ok=True)

        with open(model_path, "wb") as fh:
            pickle.dump(vectorizer, fh)
        sp.save_npz(str(matrix_path), tfidf_matrix)

        logger.info(
            "TF-IDF index saved: vectorizer → %s, matrix → %s",
            model_path,
            matrix_path,
        )

        isbn_list = df["isbn13"].astype(str).tolist()
        title_map = dict(zip(df["isbn13"].astype(str), df["title"].astype(str)))

        return cls(vectorizer, tfidf_matrix, isbn_list, title_map)

    @classmethod
    def load(
        cls,
        model_path: Path,
        matrix_path: Path,
        df: pd.DataFrame,
    ) -> "TFIDFRetriever":
        """
        Load a pre-built TF-IDF model from disk.

        Args:
            model_path:  Path to the pickled vectorizer.
            matrix_path: Path to the ``.npz`` sparse matrix.
            df:          DataFrame (used to reconstruct isbn/title maps).

        Returns:
            A ready-to-use ``TFIDFRetriever`` instance.
        """
        logger.info("Loading TF-IDF model from %s", model_path)
        with open(model_path, "rb") as fh:
            vectorizer: TfidfVectorizer = pickle.load(fh)

        tfidf_matrix = sp.load_npz(str(matrix_path))
        isbn_list = df["isbn13"].astype(str).tolist()
        title_map = dict(zip(df["isbn13"].astype(str), df["title"].astype(str)))

        logger.info(
            "TF-IDF model loaded: %d documents, %d features",
            tfidf_matrix.shape[0],
            tfidf_matrix.shape[1],
        )
        return cls(vectorizer, tfidf_matrix, isbn_list, title_map)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Retrieve top-k documents using cosine similarity in TF-IDF space.

        Args:
            query:  Natural-language search query.
            top_k:  Number of results to return.

        Returns:
            Ranked list of ``RetrievalResult`` (highest cosine similarity first).
        """
        query_vec = self._vectorizer.transform([query])
        scores: np.ndarray = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

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
