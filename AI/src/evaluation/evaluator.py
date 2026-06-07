"""
Evaluator – runs all retrievers against all qrels and aggregates metrics.

Responsibilities:
- Iterate over every (retriever, query) pair
- Measure retrieval latency per query
- Compute all IR metrics using the metrics module
- Macro-average metrics across all queries per retriever
- Persist results to ``evaluation_results.json``
- Log progress at INFO level and per-query details at DEBUG level
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from src.config.settings import Settings
from src.evaluation.metrics import compute_all_metrics
from src.retrieval.base import BaseRetriever
from src.schemas.benchmark import BenchmarkResult, EvalSummary, QrelItem

logger = logging.getLogger(__name__)


class Evaluator:
    """
    Evaluates a set of retrievers against a qrels ground-truth dataset.

    Args:
        retrievers: Mapping of retriever name → ``BaseRetriever`` instance.
        qrels:      List of ``QrelItem`` ground-truth entries.
        settings:   Application settings (eval_top_k, eval_output_path).
    """

    def __init__(
        self,
        retrievers: dict[str, BaseRetriever],
        qrels: list[QrelItem],
        settings: Settings,
    ) -> None:
        self._retrievers = retrievers
        self._qrels = qrels
        self._settings = settings

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> EvalSummary:
        """
        Evaluate all retrievers and return a complete ``EvalSummary``.

        For each retriever:
        1. Loop over all qrel entries (queries)
        2. Call ``retriever.search(query, top_k)``
        3. Compute all IR metrics against the qrel's relevant_isbns
        4. Macro-average metrics across all queries
        5. Record average latency

        Returns:
            ``EvalSummary`` containing ``BenchmarkResult`` per retriever.
        """
        top_k = self._settings.eval_top_k
        results: dict[str, BenchmarkResult] = {}

        logger.info(
            "Starting evaluation: %d retrievers × %d queries @ top_k=%d",
            len(self._retrievers),
            len(self._qrels),
            top_k,
        )

        for retriever_name, retriever in self._retrievers.items():
            logger.info("─── Evaluating retriever: %s ───", retriever_name)
            result = self._evaluate_retriever(retriever, top_k)
            results[retriever_name] = result
            logger.info(
                "%s → P@5=%.4f | P@10=%.4f | R@5=%.4f | R@10=%.4f | "
                "MRR=%.4f | NDCG@%d=%.4f | MAP=%.4f | Latency=%.1fms",
                retriever_name,
                result.precision_at_5,
                result.precision_at_10,
                result.recall_at_5,
                result.recall_at_10,
                result.mrr,
                top_k,
                result.ndcg_at_10,
                result.map_score,
                result.latency_ms,
            )

        summary = EvalSummary(
            results=results,
            eval_top_k=top_k,
            num_qrels=len(self._qrels),
        )

        self._save_results(summary)
        return summary

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _evaluate_retriever(
        self,
        retriever: BaseRetriever,
        top_k: int,
    ) -> BenchmarkResult:
        """Evaluate a single retriever over all qrels."""
        metric_accumulators: dict[str, list[float]] = {
            "precision_at_5": [],
            "precision_at_10": [],
            "recall_at_5": [],
            "recall_at_10": [],
            "mrr": [],
            "ndcg_at_k": [],
            "map_score": [],
        }
        latency_ms_list: list[float] = []
        skipped = 0

        for qrel in self._qrels:
            relevant_set = set(qrel.relevant_isbns)

            if not relevant_set:
                logger.debug(
                    "Skipping query '%s' – no relevant ISBNs in qrel", qrel.query_id
                )
                skipped += 1
                continue

            # Time the retrieval
            t_start = time.perf_counter()
            try:
                search_results = retriever.search(qrel.query, top_k=top_k)
            except Exception as exc:
                logger.error(
                    "Retriever '%s' failed on query '%s': %s",
                    retriever.name,
                    qrel.query_id,
                    exc,
                    exc_info=True,
                )
                skipped += 1
                continue
            elapsed_ms = (time.perf_counter() - t_start) * 1000

            retrieved_isbns = [r.isbn13 for r in search_results]
            metrics = compute_all_metrics(retrieved_isbns, relevant_set, k=top_k)

            for key in metric_accumulators:
                metric_accumulators[key].append(metrics[key])
            latency_ms_list.append(elapsed_ms)

            logger.debug(
                "%s | query_id=%s | retrieved=%d | relevant=%d | P@10=%.3f | MRR=%.3f",
                retriever.name,
                qrel.query_id,
                len(retrieved_isbns),
                len(relevant_set),
                metrics["precision_at_10"],
                metrics["mrr"],
            )

        num_evaluated = len(self._qrels) - skipped

        def _mean(values: list[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        return BenchmarkResult(
            retriever_name=retriever.name,
            precision_at_5=_mean(metric_accumulators["precision_at_5"]),
            precision_at_10=_mean(metric_accumulators["precision_at_10"]),
            recall_at_5=_mean(metric_accumulators["recall_at_5"]),
            recall_at_10=_mean(metric_accumulators["recall_at_10"]),
            mrr=_mean(metric_accumulators["mrr"]),
            ndcg_at_10=_mean(metric_accumulators["ndcg_at_k"]),
            map_score=_mean(metric_accumulators["map_score"]),
            num_queries=num_evaluated,
            latency_ms=_mean(latency_ms_list),
        )

    def _save_results(self, summary: EvalSummary) -> None:
        """Persist the evaluation summary to ``evaluation_results.json``."""
        output_path = Path(self._settings.eval_output_path) / "evaluation_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use Pydantic's model_dump for clean serialisation
        payload = {
            name: result.model_dump()
            for name, result in summary.results.items()
        }
        payload["_meta"] = {
            "eval_top_k": summary.eval_top_k,
            "num_qrels": summary.num_qrels,
            "created_at": summary.created_at.isoformat(),
        }

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)

        logger.info("Evaluation results saved to %s", output_path)
