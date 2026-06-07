"""
Benchmark and evaluation Pydantic schemas.

Defines the data contracts for:
- qrels (ground-truth relevance judgments)
- per-retriever benchmark results
- final evaluation summary
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Legacy alias kept for backwards compatibility with existing code that
# imports QuerySet from schemas.benchmark
# ---------------------------------------------------------------------------
class QuerySet(BaseModel):
    """Simple list of search query strings (legacy / chain output)."""

    queries: list[str] = Field(
        description="Generated search queries for a single book.",
        min_length=1,
    )


# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------
class QrelItem(BaseModel):
    """
    A single ground-truth relevance entry (query + relevant book set).

    This is the format persisted in ``qrels.json`` and loaded by the evaluator.
    """

    query_id: str = Field(
        description="Unique identifier for this query (e.g. 'q_<isbn>_<idx>').",
    )
    query: str = Field(description="The natural-language search query string.")
    source_isbn: str = Field(
        description="ISBN-13 of the book that the query was generated from.",
    )
    relevant_isbns: list[str] = Field(
        description="ISBN-13 identifiers of all books judged as relevant (score ≥ threshold).",
    )
    judge_model: str = Field(
        description="LLM model used for relevance judging (for reproducibility).",
    )
    generation_model: str = Field(
        description="LLM model used to generate the query (for reproducibility).",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when this qrel entry was created.",
    )


# ---------------------------------------------------------------------------
# Evaluation results
# ---------------------------------------------------------------------------
class BenchmarkResult(BaseModel):
    """
    Aggregated evaluation metrics for a single retriever.

    All metric values are macro-averaged over all evaluation queries.
    """

    retriever_name: str = Field(description="Human-readable retriever identifier.")
    precision_at_5: float = Field(description="Mean Precision@5 across all queries.")
    precision_at_10: float = Field(description="Mean Precision@10 across all queries.")
    recall_at_5: float = Field(description="Mean Recall@5 across all queries.")
    recall_at_10: float = Field(description="Mean Recall@10 across all queries.")
    mrr: float = Field(description="Mean Reciprocal Rank (MRR) across all queries.")
    ndcg_at_10: float = Field(description="Mean NDCG@10 across all queries.")
    map_score: float = Field(description="Mean Average Precision (MAP) across all queries.")
    num_queries: int = Field(description="Number of queries used in evaluation.")
    latency_ms: float = Field(
        default=0.0,
        description="Average retrieval latency per query in milliseconds.",
    )


class EvalSummary(BaseModel):
    """
    Complete evaluation summary containing results for all retrievers.

    This is the top-level object serialised to ``evaluation_results.json``.
    """

    results: dict[str, BenchmarkResult] = Field(
        description="Mapping of retriever name → BenchmarkResult.",
    )
    eval_top_k: int = Field(description="Evaluation depth (K) used for all metrics.")
    num_qrels: int = Field(description="Total number of qrel entries evaluated.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this evaluation was completed.",
    )