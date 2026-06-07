"""
Unit tests for TF-IDF and BM25 retrievers.

TF-IDF and BM25 tests use build() on a small in-memory sample DataFrame
so no external services (ChromaDB, OpenAI) are required.

Dense and Reranking retriever tests use mocks to avoid requiring GPU/network.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.tfidf_retriever import TFIDFRetriever
from src.schemas.retrieval import RetrievalResult


# ---------------------------------------------------------------------------
# TF-IDF Retriever
# ---------------------------------------------------------------------------

class TestTFIDFRetriever:
    def test_build_creates_files(self, tmp_path: Path, sample_df: pd.DataFrame):
        model_path = tmp_path / "tfidf.pkl"
        matrix_path = tmp_path / "tfidf_matrix.npz"

        retriever = TFIDFRetriever.build(
            df=sample_df,
            model_path=model_path,
            matrix_path=matrix_path,
            max_features=500,
            min_df=1,
        )

        assert model_path.exists(), "Vectorizer pickle should be saved"
        assert matrix_path.exists(), "Matrix .npz should be saved"
        assert retriever is not None

    def test_search_returns_results(self, tmp_path: Path, sample_df: pd.DataFrame):
        model_path = tmp_path / "tfidf.pkl"
        matrix_path = tmp_path / "tfidf_matrix.npz"

        retriever = TFIDFRetriever.build(
            df=sample_df,
            model_path=model_path,
            matrix_path=matrix_path,
            max_features=500,
            min_df=1,
        )
        results = retriever.search("alien invasion science fiction", top_k=3)
        assert len(results) <= 3
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_search_returns_relevant_book(self, tmp_path: Path, sample_df: pd.DataFrame):
        model_path = tmp_path / "tfidf.pkl"
        matrix_path = tmp_path / "tfidf_matrix.npz"

        retriever = TFIDFRetriever.build(
            df=sample_df,
            model_path=model_path,
            matrix_path=matrix_path,
            max_features=500,
            min_df=1,
        )
        # The sci-fi query should bring up the sci-fi book
        results = retriever.search("alien invasion", top_k=4)
        isbns = [r.isbn13 for r in results]
        assert "9780000000001" in isbns or "9780000000004" in isbns

    def test_load_roundtrip(self, tmp_path: Path, sample_df: pd.DataFrame):
        model_path = tmp_path / "tfidf.pkl"
        matrix_path = tmp_path / "tfidf_matrix.npz"

        TFIDFRetriever.build(
            df=sample_df,
            model_path=model_path,
            matrix_path=matrix_path,
            max_features=500,
            min_df=1,
        )
        loaded = TFIDFRetriever.load(
            model_path=model_path,
            matrix_path=matrix_path,
            df=sample_df,
        )
        results = loaded.search("wizard magic fantasy", top_k=2)
        assert len(results) >= 1

    def test_results_are_sorted_by_score(self, tmp_path: Path, sample_df: pd.DataFrame):
        model_path = tmp_path / "tfidf.pkl"
        matrix_path = tmp_path / "tfidf_matrix.npz"

        retriever = TFIDFRetriever.build(
            df=sample_df,
            model_path=model_path,
            matrix_path=matrix_path,
            max_features=500,
            min_df=1,
        )
        results = retriever.search("thinking fast slow psychology", top_k=4)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True), "Results must be sorted descending by score"

    def test_ranks_are_sequential(self, tmp_path: Path, sample_df: pd.DataFrame):
        model_path = tmp_path / "tfidf.pkl"
        matrix_path = tmp_path / "tfidf_matrix.npz"

        retriever = TFIDFRetriever.build(
            df=sample_df,
            model_path=model_path,
            matrix_path=matrix_path,
            max_features=500,
            min_df=1,
        )
        results = retriever.search("test query", top_k=4)
        ranks = [r.rank for r in results]
        assert ranks == list(range(1, len(results) + 1))

    def test_name_property(self, tmp_path: Path, sample_df: pd.DataFrame):
        model_path = tmp_path / "tfidf.pkl"
        matrix_path = tmp_path / "tfidf_matrix.npz"
        retriever = TFIDFRetriever.build(
            df=sample_df, model_path=model_path, matrix_path=matrix_path,
            max_features=500, min_df=1,
        )
        assert retriever.name == "tfidf"


# ---------------------------------------------------------------------------
# BM25 Retriever
# ---------------------------------------------------------------------------

class TestBM25Retriever:
    def test_build_creates_file(self, tmp_path: Path, sample_df: pd.DataFrame):
        index_path = tmp_path / "bm25.pkl"
        retriever = BM25Retriever.build(df=sample_df, index_path=index_path)
        assert index_path.exists()
        assert retriever is not None

    def test_search_returns_results(self, tmp_path: Path, sample_df: pd.DataFrame):
        index_path = tmp_path / "bm25.pkl"
        retriever = BM25Retriever.build(df=sample_df, index_path=index_path)
        results = retriever.search("wizard fantasy music", top_k=3)
        assert len(results) <= 3
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_load_roundtrip(self, tmp_path: Path, sample_df: pd.DataFrame):
        index_path = tmp_path / "bm25.pkl"
        BM25Retriever.build(df=sample_df, index_path=index_path)
        loaded = BM25Retriever.load(index_path=index_path, df=sample_df)
        results = loaded.search("alien invader battle", top_k=2)
        assert len(results) >= 1

    def test_results_are_sorted_by_score(self, tmp_path: Path, sample_df: pd.DataFrame):
        index_path = tmp_path / "bm25.pkl"
        retriever = BM25Retriever.build(df=sample_df, index_path=index_path)
        results = retriever.search("science fiction alien", top_k=4)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_name_property(self, tmp_path: Path, sample_df: pd.DataFrame):
        index_path = tmp_path / "bm25.pkl"
        retriever = BM25Retriever.build(df=sample_df, index_path=index_path)
        assert retriever.name == "bm25"


# ---------------------------------------------------------------------------
# Hybrid RRF Retriever (mocked sub-retrievers)
# ---------------------------------------------------------------------------

class TestHybridRRFRetriever:
    def _make_results(self, isbns: list[str]) -> list[RetrievalResult]:
        return [
            RetrievalResult(isbn13=isbn, score=1.0 / (i + 1), rank=i + 1)
            for i, isbn in enumerate(isbns)
        ]

    def test_fusion_combines_results(self, mock_settings):
        from src.retrieval.hybrid_rrf_retriever import HybridRRFRetriever

        bm25_mock = MagicMock()
        dense_mock = MagicMock()

        bm25_mock.search.return_value = self._make_results(["isbn_A", "isbn_B", "isbn_C"])
        dense_mock.search.return_value = self._make_results(["isbn_C", "isbn_A", "isbn_D"])

        retriever = HybridRRFRetriever(
            bm25_retriever=bm25_mock,
            dense_retriever=dense_mock,
            candidate_pool=3,
            rrf_k=60,
        )
        results = retriever.search("test query", top_k=3)

        assert len(results) <= 3
        isbns = [r.isbn13 for r in results]
        # isbn_A and isbn_C appear in both lists → should rank high
        assert "isbn_A" in isbns or "isbn_C" in isbns

    def test_rrf_scores_are_positive(self, mock_settings):
        from src.retrieval.hybrid_rrf_retriever import HybridRRFRetriever

        bm25_mock = MagicMock()
        dense_mock = MagicMock()
        bm25_mock.search.return_value = self._make_results(["a", "b"])
        dense_mock.search.return_value = self._make_results(["a", "c"])

        retriever = HybridRRFRetriever(
            bm25_retriever=bm25_mock,
            dense_retriever=dense_mock,
            candidate_pool=2,
            rrf_k=60,
        )
        results = retriever.search("query", top_k=3)
        assert all(r.score > 0 for r in results)

    def test_name_property(self, mock_settings):
        from src.retrieval.hybrid_rrf_retriever import HybridRRFRetriever
        retriever = HybridRRFRetriever(
            bm25_retriever=MagicMock(),
            dense_retriever=MagicMock(),
        )
        assert retriever.name == "hybrid_rrf"
