"""
Unit tests for IR evaluation metrics.

All tests use pure inputs (lists and sets of strings) with no external
dependencies – no LLM, no retriever, no database.
"""

from __future__ import annotations

import math

import pytest

from src.evaluation.metrics import (
    compute_all_metrics,
    map_score,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

RETRIEVED_ALL_RELEVANT = ["a", "b", "c", "d", "e"]
RETRIEVED_NONE_RELEVANT = ["x", "y", "z", "w", "v"]
RETRIEVED_MIXED = ["a", "x", "b", "y", "c"]  # relevant at positions 1, 3, 5
RELEVANT_SET = {"a", "b", "c"}


# ---------------------------------------------------------------------------
# precision_at_k
# ---------------------------------------------------------------------------

class TestPrecisionAtK:
    def test_all_relevant(self):
        assert precision_at_k(RETRIEVED_ALL_RELEVANT, RELEVANT_SET, k=3) == pytest.approx(1.0)

    def test_none_relevant(self):
        assert precision_at_k(RETRIEVED_NONE_RELEVANT, RELEVANT_SET, k=3) == pytest.approx(0.0)

    def test_mixed(self):
        # hits at rank 1 (a) and 3 (b) out of top 3
        result = precision_at_k(RETRIEVED_MIXED, RELEVANT_SET, k=3)
        assert result == pytest.approx(2 / 3)

    def test_k_zero_returns_zero(self):
        assert precision_at_k(RETRIEVED_ALL_RELEVANT, RELEVANT_SET, k=0) == 0.0

    def test_empty_retrieved(self):
        assert precision_at_k([], RELEVANT_SET, k=5) == 0.0

    def test_k_larger_than_results(self):
        # k=10 but only 5 results — denominator is still k
        result = precision_at_k(RETRIEVED_ALL_RELEVANT, RELEVANT_SET, k=10)
        assert result == pytest.approx(3 / 10)

    def test_p_at_1_first_relevant(self):
        assert precision_at_k(["a", "x", "y"], RELEVANT_SET, k=1) == pytest.approx(1.0)

    def test_p_at_1_first_not_relevant(self):
        assert precision_at_k(["x", "a", "y"], RELEVANT_SET, k=1) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# recall_at_k
# ---------------------------------------------------------------------------

class TestRecallAtK:
    def test_all_relevant_retrieved(self):
        # all 3 relevant retrieved in top 3
        assert recall_at_k(RETRIEVED_ALL_RELEVANT, RELEVANT_SET, k=3) == pytest.approx(1.0)

    def test_none_relevant(self):
        assert recall_at_k(RETRIEVED_NONE_RELEVANT, RELEVANT_SET, k=5) == pytest.approx(0.0)

    def test_partial(self):
        # 2 of 3 relevant retrieved in top 4 (a at 1, b at 3)
        result = recall_at_k(RETRIEVED_MIXED, RELEVANT_SET, k=4)
        assert result == pytest.approx(2 / 3)

    def test_empty_relevant_returns_zero(self):
        assert recall_at_k(RETRIEVED_ALL_RELEVANT, set(), k=5) == 0.0

    def test_k_zero_returns_zero(self):
        assert recall_at_k(RETRIEVED_ALL_RELEVANT, RELEVANT_SET, k=0) == 0.0


# ---------------------------------------------------------------------------
# mrr
# ---------------------------------------------------------------------------

class TestMRR:
    def test_first_result_relevant(self):
        assert mrr(["a", "x", "y"], RELEVANT_SET) == pytest.approx(1.0)

    def test_second_result_relevant(self):
        assert mrr(["x", "a", "y"], RELEVANT_SET) == pytest.approx(0.5)

    def test_third_result_relevant(self):
        assert mrr(["x", "y", "a"], RELEVANT_SET) == pytest.approx(1 / 3)

    def test_no_relevant(self):
        assert mrr(["x", "y", "z"], RELEVANT_SET) == pytest.approx(0.0)

    def test_empty_retrieved(self):
        assert mrr([], RELEVANT_SET) == pytest.approx(0.0)

    def test_max_k_limits_search(self):
        # relevant doc is at rank 3 but max_k=2 → not found
        assert mrr(["x", "y", "a"], RELEVANT_SET, max_k=2) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# ndcg_at_k
# ---------------------------------------------------------------------------

class TestNDCGAtK:
    def test_perfect_ranking(self):
        # All relevant docs at top positions → NDCG = 1.0
        result = ndcg_at_k(["a", "b", "c", "x", "y"], RELEVANT_SET, k=5)
        assert result == pytest.approx(1.0)

    def test_no_relevant(self):
        assert ndcg_at_k(RETRIEVED_NONE_RELEVANT, RELEVANT_SET, k=5) == pytest.approx(0.0)

    def test_empty_relevant_set(self):
        assert ndcg_at_k(RETRIEVED_ALL_RELEVANT, set(), k=5) == pytest.approx(0.0)

    def test_partial_ranking(self):
        # DCG: 1/log2(2) + 1/log2(4) + 1/log2(6) for positions 1,3,5
        # IDCG: 1/log2(2) + 1/log2(3) + 1/log2(4) for ideal
        retrieved = ["a", "x", "b", "y", "c"]
        dcg = 1 / math.log2(2) + 1 / math.log2(4) + 1 / math.log2(6)
        idcg = 1 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4)
        expected = dcg / idcg
        result = ndcg_at_k(retrieved, RELEVANT_SET, k=5)
        assert result == pytest.approx(expected, abs=1e-6)

    def test_k_zero_returns_zero(self):
        assert ndcg_at_k(RETRIEVED_ALL_RELEVANT, RELEVANT_SET, k=0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# map_score
# ---------------------------------------------------------------------------

class TestMAPScore:
    def test_perfect_ranking(self):
        # P@1=1, P@2=1, P@3=1 → AP = (1+1+1)/3 = 1.0
        assert map_score(["a", "b", "c", "x", "y"], RELEVANT_SET) == pytest.approx(1.0)

    def test_no_relevant(self):
        assert map_score(RETRIEVED_NONE_RELEVANT, RELEVANT_SET) == pytest.approx(0.0)

    def test_empty_relevant(self):
        assert map_score(RETRIEVED_ALL_RELEVANT, set()) == pytest.approx(0.0)

    def test_partial(self):
        # a at rank 1 → P@1=1/1=1; b at rank 3 → P@3=2/3; c at rank 5 → P@5=3/5
        # AP = (1 + 2/3 + 3/5) / 3
        retrieved = ["a", "x", "b", "y", "c"]
        expected = (1.0 + 2 / 3 + 3 / 5) / 3
        assert map_score(retrieved, RELEVANT_SET) == pytest.approx(expected, abs=1e-6)

    def test_single_relevant_not_retrieved(self):
        assert map_score(["x", "y", "z"], {"a"}) == pytest.approx(0.0)

    def test_single_relevant_at_rank_1(self):
        assert map_score(["a", "x", "y"], {"a"}) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_all_metrics
# ---------------------------------------------------------------------------

class TestComputeAllMetrics:
    def test_returns_all_keys(self):
        result = compute_all_metrics(["a", "b", "c"], RELEVANT_SET, k=5)
        expected_keys = {
            "precision_at_5", "precision_at_10",
            "recall_at_5", "recall_at_10",
            "mrr", "ndcg_at_k", "map_score",
        }
        assert set(result.keys()) == expected_keys

    def test_values_are_floats_in_unit_interval(self):
        result = compute_all_metrics(RETRIEVED_MIXED, RELEVANT_SET, k=5)
        for key, val in result.items():
            assert isinstance(val, float), f"{key} should be float"
            assert 0.0 <= val <= 1.0, f"{key}={val} out of [0, 1]"

    def test_perfect_score(self):
        result = compute_all_metrics(["a", "b", "c"], {"a", "b", "c"}, k=5)
        assert result["mrr"] == pytest.approx(1.0)
        assert result["precision_at_5"] == pytest.approx(3 / 5)  # P@5, only 3 retrieved
