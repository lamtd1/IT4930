"""
Unit tests for the relevance judge chain and JudgeService.

Uses mocked LLM chains – no actual OpenAI API calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.schemas.relevance import RelevanceScore
from src.services.judge_service import JudgeService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def score_relevant() -> RelevanceScore:
    return RelevanceScore(score=2, reason="Directly matches query themes and subject matter.")


@pytest.fixture
def score_somewhat() -> RelevanceScore:
    return RelevanceScore(score=1, reason="Partially related but not a strong match.")


@pytest.fixture
def score_not_relevant() -> RelevanceScore:
    return RelevanceScore(score=0, reason="Book is completely off-topic for this query.")


@pytest.fixture
def mock_judge_chain(score_relevant: RelevanceScore) -> MagicMock:
    chain = MagicMock()
    chain.invoke.return_value = score_relevant
    return chain


# ---------------------------------------------------------------------------
# RelevanceScore schema validation
# ---------------------------------------------------------------------------

class TestRelevanceScoreSchema:
    def test_valid_score_0(self):
        s = RelevanceScore(score=0, reason="Not relevant")
        assert s.score == 0

    def test_valid_score_1(self):
        s = RelevanceScore(score=1, reason="Somewhat")
        assert s.score == 1

    def test_valid_score_2(self):
        s = RelevanceScore(score=2, reason="Highly relevant")
        assert s.score == 2

    def test_invalid_score_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RelevanceScore(score=3, reason="Out of range")

    def test_negative_score_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RelevanceScore(score=-1, reason="Negative")

    def test_reason_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RelevanceScore(score=1)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# JudgeService
# ---------------------------------------------------------------------------

class TestJudgeService:
    def test_returns_relevance_score(
        self,
        mock_judge_chain: MagicMock,
        mock_settings,
        score_relevant: RelevanceScore,
    ):
        service = JudgeService(chain=mock_judge_chain, settings=mock_settings)
        result = service.judge_relevance(
            query="alien invasion sci-fi",
            isbn13="9780000000001",
            book_title="The Dark Forest",
            book_description="A sci-fi epic about alien threats.",
        )
        assert isinstance(result, RelevanceScore)
        assert result.score == 2

    def test_caching_avoids_second_call(
        self,
        mock_judge_chain: MagicMock,
        mock_settings,
    ):
        service = JudgeService(chain=mock_judge_chain, settings=mock_settings)
        service.judge_relevance("query", "isbn1", "Title", "Desc", use_cache=True)
        service.judge_relevance("query", "isbn1", "Title", "Desc", use_cache=True)
        # Chain should only be called once (second call hits cache)
        assert mock_judge_chain.invoke.call_count == 1

    def test_cache_disabled_calls_chain_twice(
        self,
        mock_judge_chain: MagicMock,
        mock_settings,
    ):
        service = JudgeService(chain=mock_judge_chain, settings=mock_settings)
        service.judge_relevance("query", "isbn1", "Title", "Desc", use_cache=False)
        service.judge_relevance("query", "isbn1", "Title", "Desc", use_cache=False)
        assert mock_judge_chain.invoke.call_count == 2

    def test_different_queries_not_cached_together(
        self,
        mock_judge_chain: MagicMock,
        mock_settings,
    ):
        service = JudgeService(chain=mock_judge_chain, settings=mock_settings)
        service.judge_relevance("query A", "isbn1", "Title", "Desc")
        service.judge_relevance("query B", "isbn1", "Title", "Desc")
        assert mock_judge_chain.invoke.call_count == 2

    def test_is_relevant_threshold_1(
        self,
        mock_judge_chain: MagicMock,
        mock_settings,
        score_relevant: RelevanceScore,
        score_not_relevant: RelevanceScore,
    ):
        mock_settings.relevance_threshold = 1
        service = JudgeService(chain=mock_judge_chain, settings=mock_settings)
        assert service.is_relevant(score_relevant) is True
        assert service.is_relevant(score_not_relevant) is False

    def test_is_relevant_threshold_2(
        self,
        mock_judge_chain: MagicMock,
        mock_settings,
        score_relevant: RelevanceScore,
        score_somewhat: RelevanceScore,
    ):
        mock_settings.relevance_threshold = 2
        service = JudgeService(chain=mock_judge_chain, settings=mock_settings)
        assert service.is_relevant(score_relevant) is True
        assert service.is_relevant(score_somewhat) is False

    def test_cache_size_increments(
        self,
        mock_judge_chain: MagicMock,
        mock_settings,
    ):
        service = JudgeService(chain=mock_judge_chain, settings=mock_settings)
        assert service.cache_size == 0
        service.judge_relevance("q1", "isbn1", "T", "D")
        assert service.cache_size == 1
        service.judge_relevance("q2", "isbn1", "T", "D")
        assert service.cache_size == 2
        # Same key again – cache size stays at 2
        service.judge_relevance("q1", "isbn1", "T", "D")
        assert service.cache_size == 2
