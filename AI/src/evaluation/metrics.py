"""
Information Retrieval evaluation metrics.

All functions are PURE (no side effects, no class state) and fully type-hinted.
They operate on ordered ISBN-13 lists and binary relevance sets so they
are completely retriever-agnostic.

Implemented metrics:
    - Precision@K  (P@K)
    - Recall@K     (R@K)
    - Mean Reciprocal Rank (MRR)
    - NDCG@K       (Normalised Discounted Cumulative Gain)
    - MAP          (Mean Average Precision)

References:
    Manning, C. D., Raghavan, P., & Schütze, H. (2008).
    Introduction to Information Retrieval. Cambridge University Press.
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# Core metric functions
# ---------------------------------------------------------------------------

def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """
    Compute Precision@K.

    Fraction of the top-K retrieved documents that are relevant.

    Args:
        retrieved: Ordered list of retrieved ISBN-13 strings (most relevant first).
        relevant:  Set of ground-truth relevant ISBN-13 strings.
        k:         Cut-off depth.

    Returns:
        Float in [0.0, 1.0].  Returns 0.0 if k ≤ 0.
    """
    if k <= 0 or not retrieved:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for isbn in top_k if isbn in relevant)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """
    Compute Recall@K.

    Fraction of all relevant documents that appear in the top-K results.

    Args:
        retrieved: Ordered list of retrieved ISBN-13 strings.
        relevant:  Set of ground-truth relevant ISBN-13 strings.
        k:         Cut-off depth.

    Returns:
        Float in [0.0, 1.0].  Returns 0.0 if ``relevant`` is empty.
    """
    if not relevant or k <= 0:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for isbn in top_k if isbn in relevant)
    return hits / len(relevant)


def mrr(retrieved: list[str], relevant: set[str], max_k: int = 1000) -> float:
    """
    Compute Mean Reciprocal Rank (MRR) for a single query.

    The reciprocal rank is 1/rank of the first relevant document.
    Returns 0.0 if no relevant document is found within ``max_k``.

    Args:
        retrieved: Ordered list of retrieved ISBN-13 strings.
        relevant:  Set of ground-truth relevant ISBN-13 strings.
        max_k:     Maximum rank to consider.

    Returns:
        Float in [0.0, 1.0].
    """
    for rank, isbn in enumerate(retrieved[:max_k], start=1):
        if isbn in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """
    Compute NDCG@K (Normalised Discounted Cumulative Gain).

    Uses binary relevance (gain = 1 if relevant, 0 otherwise).
    The ideal DCG assumes all relevant documents are ranked first.

    Args:
        retrieved: Ordered list of retrieved ISBN-13 strings.
        relevant:  Set of ground-truth relevant ISBN-13 strings.
        k:         Cut-off depth.

    Returns:
        Float in [0.0, 1.0].  Returns 0.0 if ``relevant`` is empty.
    """
    if not relevant or k <= 0:
        return 0.0

    def _dcg(ranked: list[str], rel: set[str], depth: int) -> float:
        """Compute DCG for a ranked list."""
        gain = 0.0
        for i, isbn in enumerate(ranked[:depth], start=1):
            if isbn in rel:
                gain += 1.0 / math.log2(i + 1)
        return gain

    dcg = _dcg(retrieved, relevant, k)

    # Ideal DCG: top min(|relevant|, k) positions are all relevant
    ideal_top = ["rel"] * min(len(relevant), k)
    ideal_rel = {"rel"}
    idcg = _dcg(ideal_top, ideal_rel, k)

    return dcg / idcg if idcg > 0.0 else 0.0


def map_score(retrieved: list[str], relevant: set[str]) -> float:
    """
    Compute Average Precision (AP) for a single query.

    AP is the area under the precision-recall curve, computed as the
    mean of Precision@K values at each position where a relevant
    document is retrieved.

    Note: When aggregated across queries, AP becomes MAP.

    Args:
        retrieved: Ordered list of retrieved ISBN-13 strings.
        relevant:  Set of ground-truth relevant ISBN-13 strings.

    Returns:
        Float in [0.0, 1.0].  Returns 0.0 if ``relevant`` is empty.
    """
    if not relevant:
        return 0.0

    hits = 0
    sum_precision = 0.0

    for rank, isbn in enumerate(retrieved, start=1):
        if isbn in relevant:
            hits += 1
            sum_precision += hits / rank

    if hits == 0:
        return 0.0

    return sum_precision / len(relevant)


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

def compute_all_metrics(
    retrieved: list[str],
    relevant: set[str],
    k: int = 10,
) -> dict[str, float]:
    """
    Compute all evaluation metrics in one call.

    Args:
        retrieved: Ordered list of retrieved ISBN-13 strings.
        relevant:  Set of ground-truth relevant ISBN-13 strings.
        k:         Evaluation depth (used for P@K, R@K, NDCG@K).

    Returns:
        Dictionary with keys:
        ``precision_at_5``, ``precision_at_10``,
        ``recall_at_5``, ``recall_at_10``,
        ``mrr``, ``ndcg_at_k``, ``map_score``.
    """
    return {
        "precision_at_5": precision_at_k(retrieved, relevant, k=5),
        "precision_at_10": precision_at_k(retrieved, relevant, k=10),
        "recall_at_5": recall_at_k(retrieved, relevant, k=5),
        "recall_at_10": recall_at_k(retrieved, relevant, k=10),
        "mrr": mrr(retrieved, relevant),
        "ndcg_at_k": ndcg_at_k(retrieved, relevant, k=k),
        "map_score": map_score(retrieved, relevant),
    }
