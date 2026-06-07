"""
Integration tests for the Evaluator.

Uses:
- Mock retrievers (no real indexes required)
- Real metric functions (no mocking)
- Sample qrels from conftest.py

Tests validate end-to-end evaluation logic: search → metrics → aggregation.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.evaluation.evaluator import Evaluator
from src.retrieval.base import BaseRetriever
from src.schemas.benchmark import BenchmarkResult, EvalSummary, QrelItem
from src.schemas.retrieval import RetrievalResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class MockRetriever(BaseRetriever):
    """
    A mock retriever that returns a fixed list of ISBNs for any query.
    """

    def __init__(self, name: str, isbns: list[str]) -> None:
        self._name = name
        self._isbns = isbns

    @property
    def name(self) -> str:
        return self._name

    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        return [
            RetrievalResult(isbn13=isbn, score=1.0 / (i + 1), rank=i + 1)
            for i, isbn in enumerate(self._isbns[:top_k])
        ]


class PerfectRetriever(BaseRetriever):
    """Always returns the relevant ISBNs first (requires qrels lookup)."""

    def __init__(self, qrels: list[QrelItem]) -> None:
        self._qrel_map = {q.query: q.relevant_isbns for q in qrels}

    @property
    def name(self) -> str:
        return "perfect"

    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        relevant = self._qrel_map.get(query, [])
        return [
            RetrievalResult(isbn13=isbn, score=1.0, rank=i + 1)
            for i, isbn in enumerate(relevant[:top_k])
        ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEvaluator:
    def test_run_returns_eval_summary(
        self,
        mock_settings,
        sample_qrels: list[QrelItem],
    ):
        retrievers = {
            "mock": MockRetriever("mock", ["9780000000001", "9780000000002"]),
        }
        evaluator = Evaluator(
            retrievers=retrievers,
            qrels=sample_qrels,
            settings=mock_settings,
        )
        summary = evaluator.run()
        assert isinstance(summary, EvalSummary)
        assert "mock" in summary.results

    def test_perfect_retriever_scores_high(
        self,
        mock_settings,
        sample_qrels: list[QrelItem],
    ):
        perfect = PerfectRetriever(sample_qrels)
        evaluator = Evaluator(
            retrievers={"perfect": perfect},
            qrels=sample_qrels,
            settings=mock_settings,
        )
        summary = evaluator.run()
        result = summary.results["perfect"]
        # A perfect retriever should have MRR = 1.0 and positive MAP
        assert result.mrr == pytest.approx(1.0)
        assert result.map_score > 0.0

    def test_empty_retriever_scores_zero(
        self,
        mock_settings,
        sample_qrels: list[QrelItem],
    ):
        """Retriever that returns no results → all metrics = 0."""
        empty = MockRetriever("empty", [])
        evaluator = Evaluator(
            retrievers={"empty": empty},
            qrels=sample_qrels,
            settings=mock_settings,
        )
        summary = evaluator.run()
        result = summary.results["empty"]
        assert result.mrr == pytest.approx(0.0)
        assert result.precision_at_5 == pytest.approx(0.0)

    def test_multiple_retrievers_evaluated(
        self,
        mock_settings,
        sample_qrels: list[QrelItem],
    ):
        retrievers = {
            "r1": MockRetriever("r1", ["9780000000001"]),
            "r2": MockRetriever("r2", ["9780000000099"]),  # irrelevant
        }
        evaluator = Evaluator(
            retrievers=retrievers,
            qrels=sample_qrels,
            settings=mock_settings,
        )
        summary = evaluator.run()
        assert set(summary.results.keys()) == {"r1", "r2"}

    def test_results_saved_to_json(
        self,
        mock_settings,
        sample_qrels: list[QrelItem],
        tmp_path: Path,
    ):
        mock_settings.eval_output_path = tmp_path / "eval"
        retrievers = {"mock": MockRetriever("mock", ["9780000000001"])}
        evaluator = Evaluator(
            retrievers=retrievers,
            qrels=sample_qrels,
            settings=mock_settings,
        )
        evaluator.run()

        results_path = tmp_path / "eval" / "evaluation_results.json"
        assert results_path.exists(), "evaluation_results.json should be created"

        with open(results_path) as f:
            data = json.load(f)
        assert "mock" in data
        assert "_meta" in data

    def test_retriever_failure_is_handled(
        self,
        mock_settings,
        sample_qrels: list[QrelItem],
    ):
        """A retriever that raises should not crash the entire evaluation."""
        broken = MagicMock(spec=BaseRetriever)
        broken.name = "broken"
        broken.search.side_effect = RuntimeError("Simulated retriever crash")

        evaluator = Evaluator(
            retrievers={"broken": broken},
            qrels=sample_qrels,
            settings=mock_settings,
        )
        # Should not raise
        summary = evaluator.run()
        result = summary.results["broken"]
        assert result.num_queries == 0  # All queries skipped due to failure

    def test_num_queries_in_result(
        self,
        mock_settings,
        sample_qrels: list[QrelItem],
    ):
        retrievers = {"mock": MockRetriever("mock", ["9780000000001"])}
        evaluator = Evaluator(
            retrievers=retrievers,
            qrels=sample_qrels,
            settings=mock_settings,
        )
        summary = evaluator.run()
        # 3 qrels, all with relevant_isbns → all evaluated
        assert summary.results["mock"].num_queries == len(sample_qrels)

    def test_latency_is_positive(
        self,
        mock_settings,
        sample_qrels: list[QrelItem],
    ):
        retrievers = {"mock": MockRetriever("mock", ["9780000000001"])}
        evaluator = Evaluator(
            retrievers=retrievers,
            qrels=sample_qrels,
            settings=mock_settings,
        )
        summary = evaluator.run()
        assert summary.results["mock"].latency_ms >= 0.0
