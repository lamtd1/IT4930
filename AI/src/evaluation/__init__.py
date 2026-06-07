"""
Evaluation package for book retrieval benchmark.

Metric functions are eagerly imported (pure Python, no heavy deps).
Evaluator is lazily imported to avoid loading retrieval dependencies
at test collection time.
"""

from __future__ import annotations

from src.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    mrr,
    ndcg_at_k,
    map_score,
    compute_all_metrics,
)

__all__ = [
    "precision_at_k",
    "recall_at_k",
    "mrr",
    "ndcg_at_k",
    "map_score",
    "compute_all_metrics",
    "Evaluator",
]


def __getattr__(name: str):
    if name == "Evaluator":
        from src.evaluation.evaluator import Evaluator  # noqa: PLC0415
        return Evaluator
    raise AttributeError(f"module 'src.evaluation' has no attribute {name!r}")

