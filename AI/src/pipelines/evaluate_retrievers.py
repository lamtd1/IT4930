"""
Pipeline: Evaluate Retrievers

Loads all five retrievers and qrels, runs the Evaluator, and saves
``evaluation_results.json``.

Evaluated retrievers:
  1. TF-IDF
  2. BM25
  3. Dense
  4. Hybrid RRF (BM25 + Dense)
  5. Reranking (Dense + Cross-Encoder)

Run as a module:
    python -m src.pipelines.evaluate_retrievers

Or via the CLI:
    python -m src.main evaluate
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.config.settings import get_settings
from src.evaluation.evaluator import Evaluator
from src.retrieval.base import BaseRetriever
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.hybrid_rrf_retriever import HybridRRFRetriever
from src.retrieval.rerank_retriever import RerankRetriever
from src.retrieval.tfidf_retriever import TFIDFRetriever
from src.schemas.benchmark import QrelItem
from src.utils.logging_config import setup_logging
from src.utils.text_utils import clean_text

logger = logging.getLogger(__name__)


def load_qrels(qrels_path: Path) -> list[QrelItem]:
    """Load qrels from JSON file and deserialise into ``QrelItem`` objects."""
    if not qrels_path.exists():
        raise FileNotFoundError(
            f"qrels.json not found at '{qrels_path}'. "
            "Run 'build-ground-truth' pipeline first."
        )
    with open(qrels_path, encoding="utf-8") as fh:
        raw = json.load(fh)
    qrels = [QrelItem(**item) for item in raw]
    logger.info("Loaded %d qrel entries from '%s'", len(qrels), qrels_path)
    return qrels


def load_dataframe(settings) -> pd.DataFrame:
    """Load and minimal-clean the books dataset."""
    dataset_path = Path(settings.dataset_path)
    df = pd.read_csv(dataset_path, dtype={"isbn13": str})
    df = df.dropna(subset=["description", "isbn13"])
    df = df.drop_duplicates(subset=["isbn13"], keep="first")

    max_books = settings.max_books_to_process
    if len(df) > max_books:
        df = df.head(max_books).copy()

    df["description"] = df["description"].apply(lambda t: clean_text(str(t)))
    df = df[df["description"].str.split().str.len() >= 10].reset_index(drop=True)
    df["isbn13"] = df["isbn13"].astype(str)
    for col in ["title", "authors", "categories", "thumbnail"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")
    return df


def run(settings=None) -> None:
    """
    Execute the retriever evaluation pipeline.

    Args:
        settings: Optional pre-constructed ``Settings`` object.
    """
    if settings is None:
        settings = get_settings()

    setup_logging(log_dir=settings.log_dir)
    logger.info("=" * 60)
    logger.info("EVALUATE RETRIEVERS PIPELINE")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. Load prerequisites
    # ------------------------------------------------------------------
    df = load_dataframe(settings)
    logger.info("Dataset loaded: %d books", len(df))

    qrels_path = Path(settings.eval_output_path) / "qrels.json"
    qrels = load_qrels(qrels_path)

    # ------------------------------------------------------------------
    # 2. Instantiate retrievers
    # ------------------------------------------------------------------
    logger.info("Loading retrievers…")

    tfidf = TFIDFRetriever.load(
        model_path=Path(settings.tfidf_model_path),
        matrix_path=Path(settings.tfidf_matrix_path),
        df=df,
    )
    logger.info("  TF-IDF loaded ✓")

    bm25 = BM25Retriever.load(
        index_path=Path(settings.bm25_index_path),
        df=df,
    )
    logger.info("  BM25 loaded ✓")

    dense = DenseRetriever.load(
        chroma_path=Path(settings.chroma_path),
        embedding_model=settings.embedding_model,
        collection_name=settings.chroma_collection_name,
    )
    logger.info("  Dense (ChromaDB) connected ✓")

    hybrid = HybridRRFRetriever(
        bm25_retriever=bm25,
        dense_retriever=dense,
        candidate_pool=settings.hybrid_candidate_pool,
        rrf_k=settings.rrf_k,
    )
    logger.info("  Hybrid RRF configured ✓")

    rerank = RerankRetriever(
        dense_retriever=dense,
        rerank_model=settings.jina_rerank_model if settings.rerank_use_api else settings.rerank_model,
        candidate_pool=settings.rerank_candidate_pool,
        use_api=settings.rerank_use_api,
        jina_api_key=settings.jina_api_key,
        rerank_workers=settings.rerank_workers,
    )
    backend = "Jina API" if settings.rerank_use_api else "local CrossEncoder"
    logger.info("  Reranking retriever configured ✓ (backend=%s, workers=%d)", backend, settings.rerank_workers)

    retrievers: dict[str, BaseRetriever] = {
        "tfidf": tfidf,
        "bm25": bm25,
        "dense": dense,
        "hybrid_rrf": hybrid,
        "rerank": rerank,
    }

    # ------------------------------------------------------------------
    # 3. Run evaluation
    # ------------------------------------------------------------------
    evaluator = Evaluator(
        retrievers=retrievers,
        qrels=qrels,
        settings=settings,
    )
    summary = evaluator.run()

    # ------------------------------------------------------------------
    # 4. Print final summary table
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("=" * 80)
    logger.info("FINAL EVALUATION RESULTS (top_k=%d, n_queries=%d)", summary.eval_top_k, summary.num_qrels)
    logger.info("=" * 80)
    header = f"{'Retriever':<15} {'P@5':>6} {'P@10':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6} {'NDCG@10':>8} {'MAP':>6} {'ms':>7}"
    logger.info(header)
    logger.info("-" * 80)
    for name, result in summary.results.items():
        row = (
            f"{name:<15} "
            f"{result.precision_at_5:>6.4f} "
            f"{result.precision_at_10:>6.4f} "
            f"{result.recall_at_5:>6.4f} "
            f"{result.recall_at_10:>6.4f} "
            f"{result.mrr:>6.4f} "
            f"{result.ndcg_at_10:>8.4f} "
            f"{result.map_score:>6.4f} "
            f"{result.latency_ms:>7.1f}"
        )
        logger.info(row)
    logger.info("=" * 80)
    logger.info(
        "Results saved to: %s",
        Path(settings.eval_output_path) / "evaluation_results.json",
    )


if __name__ == "__main__":
    run()
