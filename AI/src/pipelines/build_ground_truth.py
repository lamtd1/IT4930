"""
Pipeline: Build Ground Truth (qrels.json)

Workflow:
  Books
    ↓
  Batch Query Generation (LLM)
    ↓
  [Concurrent] All 5 Retrievers fetch top-N candidates each
    TF-IDF | BM25 | Dense | Hybrid RRF | Reranking
    ↓
  Union of candidates (dedup by ISBN-13)
    ↓
  LLM Relevance Judging (0/1/2 score per candidate) ← CONCURRENT
    ↓
  Filter by RELEVANCE_THRESHOLD
    ↓
  qrels.json  ← SAVED INCREMENTALLY (Ctrl+C safe)

KEY FEATURES:
  - Checkpoint/Resume: already-processed query_ids are skipped on restart
  - Incremental saving: qrels.json updated after EVERY query
  - Concurrent judging: multiple judge calls per query in parallel
  - Graceful Ctrl+C: saves progress before exiting
  - All 5 retrievers contribute to the candidate pool for better recall

Run as a module:
    python -m src.pipelines.build_ground_truth

Or via the CLI:
    python -m src.main build-ground-truth
"""

from __future__ import annotations

import json
import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.chains.query_generation_chain import build_query_generation_chain
from src.chains.relevance_judge_chain import build_relevance_judge_chain
from src.config.settings import get_settings
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.hybrid_rrf_retriever import HybridRRFRetriever
from src.retrieval.rerank_retriever import RerankRetriever
from src.retrieval.tfidf_retriever import TFIDFRetriever
from src.schemas.benchmark import QrelItem
from src.schemas.query import BookInfo
from src.services.candidate_service import CandidateService
from src.services.judge_service import JudgeService
from src.services.query_service import QueryService
from src.utils.logging_config import setup_logging
from src.utils.text_utils import clean_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _load_checkpoint(qrels_path: Path) -> tuple[list[QrelItem], set[str]]:
    """
    Load existing qrels.json as checkpoint.

    Returns:
        (list of already-saved QrelItems, set of already-processed query_ids)
    """
    if not qrels_path.exists():
        return [], set()

    try:
        with open(qrels_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        qrels = [QrelItem(**item) for item in raw]
        done_ids = {q.query_id for q in qrels}
        logger.info(
            "Checkpoint loaded: %d qrels already done. Resuming from there.",
            len(qrels),
        )
        return qrels, done_ids
    except Exception as exc:
        logger.warning("Could not load checkpoint (%s) – starting fresh.", exc)
        return [], set()


def _save_checkpoint(qrels: list[QrelItem], qrels_path: Path) -> None:
    """Atomically save qrels list to qrels.json via a temp file."""
    qrels_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = qrels_path.with_suffix(".tmp")
    data = [q.model_dump(mode="json") for q in qrels]
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
    tmp_path.replace(qrels_path)  # atomic on most OS


# ---------------------------------------------------------------------------
# Concurrent judging helper
# ---------------------------------------------------------------------------

def _judge_candidates_concurrent(
    query: str,
    candidates,
    judge_service: JudgeService,
    isbn_to_title: dict[str, str],
    isbn_to_desc: dict[str, str],
    max_workers: int = 8,
) -> list[str]:
    """
    Judge all candidates for one query concurrently.

    Returns:
        List of relevant ISBN-13 strings (in retrieval order).
    """
    def _judge_one(candidate) -> tuple[int, str | None]:
        """Return (original_rank, isbn) if relevant, else (rank, None)."""
        isbn = candidate.isbn13
        desc = isbn_to_desc.get(isbn, "")
        if not desc:
            return candidate.rank, None
        try:
            score = judge_service.judge_relevance(
                query=query,
                isbn13=isbn,
                book_title=isbn_to_title.get(isbn, ""),
                book_description=desc,
            )
            return candidate.rank, isbn if judge_service.is_relevant(score) else None
        except Exception as exc:
            logger.error("Judging failed ISBN=%s: %s", isbn, exc)
            return candidate.rank, None

    # Submit all candidates in parallel
    results: dict[int, str | None] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_rank = {
            pool.submit(_judge_one, cand): cand.rank for cand in candidates
        }
        for future in as_completed(future_to_rank):
            rank, isbn_result = future.result()
            results[rank] = isbn_result

    # Restore original retrieval order
    return [
        results[rank]
        for rank in sorted(results)
        if results[rank] is not None
    ]


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(settings=None, append: bool = False) -> list[QrelItem]:
    """
    Execute the ground-truth generation pipeline.

    Supports two modes:

    * **resume** (default, ``append=False``): if ``qrels.json`` already exists,
      already-processed ``query_ids`` are skipped so the run picks up where it
      left off.  Ideal for recovering from interruptions.

    * **append** (``append=True``): existing ``qrels.json`` entries are *kept*
      but the done-filter is disabled, so every query generated in this run is
      processed and appended.  Useful for accumulating results across multiple
      runs with different parameters.

    Args:
        settings: Optional pre-constructed ``Settings`` object.
        append: When ``True``, run in append mode (see above).

    Returns:
        Complete list of ``QrelItem`` objects written to ``qrels.json``.
    """
    if settings is None:
        settings = get_settings()

    setup_logging(log_dir=settings.log_dir)
    logger.info("=" * 60)
    logger.info("BUILD GROUND TRUTH PIPELINE")
    logger.info("mode: %s", "append" if append else "resume")
    logger.info("=" * 60)

    output_dir = Path(settings.eval_output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    qrels_path = output_dir / "qrels.json"

    # ------------------------------------------------------------------
    # 1. Load checkpoint (resume / append support)
    # ------------------------------------------------------------------
    qrels, done_query_ids = _load_checkpoint(qrels_path)

    if append and done_query_ids:
        logger.info(
            "Append mode: keeping %d existing qrels, done-filter cleared – "
            "all new queries will be processed.",
            len(qrels),
        )
        done_query_ids = set()  # process everything; results will be appended

    # ------------------------------------------------------------------
    # 2. Load dataset
    # ------------------------------------------------------------------
    dataset_path = Path(settings.dataset_path)
    logger.info("Loading dataset from '%s'…", dataset_path)
    df_full = pd.read_csv(dataset_path, dtype={"isbn13": str})
    df_full = df_full.dropna(subset=["description", "isbn13"])
    df_full = df_full.drop_duplicates(subset=["isbn13"], keep="first")

    df_full["description"] = df_full["description"].apply(lambda t: clean_text(str(t)))
    df_full = df_full[df_full["description"].str.split().str.len() >= 10].reset_index(drop=True)
    df_full["isbn13"] = df_full["isbn13"].astype(str)
    for col in ["title", "authors", "categories"]:
        if col in df_full.columns:
            df_full[col] = df_full[col].fillna("Unknown")

    logger.info("Full corpus loaded: %d books", len(df_full))

    # Sample books for query generation
    max_books = settings.max_books_to_process
    if len(df_full) > max_books:
        df_queries = df_full.sample(n=max_books, random_state=42).reset_index(drop=True)
        logger.info("Query generation capped to: %d books (MAX_BOOKS_TO_PROCESS=%d)", len(df_queries), max_books)
    else:
        df_queries = df_full
        logger.info("Query generation using full corpus: %d books", len(df_queries))

    # ------------------------------------------------------------------
    # 3. Build BookInfo objects
    # ------------------------------------------------------------------
    books: list[BookInfo] = [
        BookInfo(
            isbn13=str(row["isbn13"]),
            title=str(row.get("title", "")),
            description=str(row["description"]),
            categories=str(row.get("categories", "")),
        )
        for _, row in df_queries.iterrows()
    ]

    # ------------------------------------------------------------------
    # 4. Batch query generation
    # ------------------------------------------------------------------
    logger.info("Generating queries for %d books…", len(books))
    query_chain = build_query_generation_chain(settings)
    query_service = QueryService(chain=query_chain, settings=settings)
    book_queries_list = query_service.generate_queries_batch(books)

    # Flatten: (query_id, isbn13, query) triples
    query_pairs: list[tuple[str, str, str]] = []
    for book_queries in book_queries_list:
        for idx, query in enumerate(book_queries.queries):
            qid = f"q_{book_queries.isbn13}_{idx}"
            query_pairs.append((qid, book_queries.isbn13, query))

    # Filter out already-done query_ids (resume)
    pending = [(qid, isbn, q) for qid, isbn, q in query_pairs if qid not in done_query_ids]
    logger.info(
        "Queries: %d total | %d already done | %d pending",
        len(query_pairs),
        len(done_query_ids),
        len(pending),
    )

    if not pending:
        logger.info("All queries already processed. Nothing to do.")
        return qrels

    # ------------------------------------------------------------------
    # 5. Load ALL retrievers for candidate generation
    # ------------------------------------------------------------------
    logger.info(
        "Loading all retrievers for candidate generation "
        "(pool=%d per retriever)…",
        settings.ground_truth_candidate_pool,
    )

    # 5a. Dense (required by Hybrid & Rerank)
    logger.info("  Loading Dense retriever (ChromaDB: %s)…", settings.chroma_path)
    dense_retriever = DenseRetriever.load(
        chroma_path=Path(settings.chroma_path),
        embedding_model=settings.embedding_model,
        collection_name=settings.chroma_collection_name,
    )
    logger.info("  Dense ✓")

    # 5b. TF-IDF
    logger.info("  Loading TF-IDF retriever…")
    tfidf_retriever = TFIDFRetriever.load(
        model_path=Path(settings.tfidf_model_path),
        matrix_path=Path(settings.tfidf_matrix_path),
        df=df_full,
    )
    logger.info("  TF-IDF ✓")

    # 5c. BM25
    logger.info("  Loading BM25 retriever…")
    bm25_retriever = BM25Retriever.load(
        index_path=Path(settings.bm25_index_path),
        df=df_full,
    )
    logger.info("  BM25 ✓")

    # 5d. Hybrid RRF
    hybrid_retriever = HybridRRFRetriever(
        bm25_retriever=bm25_retriever,
        dense_retriever=dense_retriever,
        candidate_pool=settings.hybrid_candidate_pool,
        rrf_k=settings.rrf_k,
    )
    logger.info("  Hybrid RRF ✓")

    # 5e. Reranking
    rerank_retriever = RerankRetriever(
        dense_retriever=dense_retriever,
        rerank_model=(
            settings.jina_rerank_model if settings.rerank_use_api
            else settings.rerank_model
        ),
        candidate_pool=settings.rerank_candidate_pool,
        use_api=settings.rerank_use_api,
        jina_api_key=settings.jina_api_key,
        rerank_workers=settings.rerank_workers,
    )
    logger.info("  Reranking ✓")

    # Build combined CandidateService (all retrievers contribute candidates)
    all_retrievers = {
        "tfidf": tfidf_retriever,
        "bm25": bm25_retriever,
        "dense": dense_retriever,
        "hybrid_rrf": hybrid_retriever,
        "rerank": rerank_retriever,
    }
    candidate_service = CandidateService(retrievers=all_retrievers, settings=settings)
    logger.info(
        "Candidate pool: %d retrievers × top-%d each → union",
        len(all_retrievers),
        settings.ground_truth_candidate_pool,
    )

    # ------------------------------------------------------------------
    # 6. Build judge service
    # ------------------------------------------------------------------
    judge_chain = build_relevance_judge_chain(settings)
    judge_service = JudgeService(chain=judge_chain, settings=settings)

    isbn_to_desc: dict[str, str] = dict(zip(df_full["isbn13"], df_full["description"]))
    isbn_to_title: dict[str, str] = dict(zip(df_full["isbn13"], df_full.get("title", df_full["isbn13"])))

    # Parallel workers for judging (conservative to respect rate limits)
    judge_workers = getattr(settings, "judge_parallel_workers", 5)

    # ------------------------------------------------------------------
    # 7. Process each pending query with incremental checkpoint saving
    # ------------------------------------------------------------------
    interrupted = False

    def _handle_sigint(sig, frame):
        nonlocal interrupted
        logger.warning("\n[!] Ctrl+C detected – finishing current query then saving checkpoint…")
        interrupted = True

    signal.signal(signal.SIGINT, _handle_sigint)

    total = len(pending)
    for q_num, (query_id, source_isbn, query) in enumerate(pending, start=1):
        if interrupted:
            logger.warning("Stopping early – progress saved to %s", qrels_path)
            break

        logger.info(
            "Query %d/%d | id=%s | '%s'",
            q_num,
            total,
            query_id,
            query[:70],
        )

        # Retrieve candidates from all retrievers (union, dedup)
        candidates = candidate_service.get_candidates(query)
        logger.debug("  Candidates retrieved: %d (union of all retrievers)", len(candidates))

        # Judge all candidates concurrently
        relevant_isbns = _judge_candidates_concurrent(
            query=query,
            candidates=candidates,
            judge_service=judge_service,
            isbn_to_title=isbn_to_title,
            isbn_to_desc=isbn_to_desc,
            max_workers=judge_workers,
        )

        qrel = QrelItem(
            query_id=query_id,
            query=query,
            source_isbn=source_isbn,
            relevant_isbns=relevant_isbns,
            judge_model=settings.openai_model,
            generation_model=settings.openai_model,
        )
        qrels.append(qrel)

        # ── INCREMENTAL SAVE ──────────────────────────────────────────
        _save_checkpoint(qrels, qrels_path)

        logger.info(
            "  → %d relevant | saved %d/%d qrels | judge cache: %d",
            len(relevant_isbns),
            len(qrels),
            len(query_pairs),
            judge_service.cache_size,
        )

    # ------------------------------------------------------------------
    # 8. Final summary
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    if interrupted:
        logger.info("GROUND TRUTH INTERRUPTED (checkpoint saved)")
    else:
        logger.info("GROUND TRUTH COMPLETE")
    logger.info("  mode:                 %s", "append" if append else "resume")
    logger.info("  qrels saved:          %d", len(qrels))
    logger.info("  queries with ≥ 1 rel:  %d", sum(1 for q in qrels if q.relevant_isbns))
    logger.info("  output: %s", qrels_path)
    logger.info("=" * 60)

    return qrels


if __name__ == "__main__":
    run()
