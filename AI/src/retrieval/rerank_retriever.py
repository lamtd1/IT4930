"""
Reranking Retriever: Dense retrieval followed by reranking.

Supports two reranking backends:
  1. **Local CrossEncoder** (default) – sentence-transformers CrossEncoder run
     in-process.  No API key required, but requires model to be downloaded.
  2. **Jina Reranker API** – calls ``https://api.jina.ai/v1/rerank`` with the
     configured model (e.g. ``jina-reranker-v3``).  Requires JINA_API_KEY.

Workflow:
    Query
      ↓
    Dense Retrieval (candidate_pool candidates)
      ↓
    [Concurrent] Reranker scoring of (query, description) pairs
        – 5 threads by default, each scoring one candidate via API/local model
      ↓
    Reranked final results (top_k)

Configuration (all via Settings / .env):
    RERANK_USE_API          = true | false   (default: false)
    JINA_API_KEY            = jina_...
    JINA_RERANK_MODEL       = jina-reranker-v3
    RERANK_CANDIDATE_POOL   = 100
    RERANK_WORKERS          = 5
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from tenacity import stop_after_attempt, wait_exponential, retry

from src.retrieval.base import BaseRetriever
from src.schemas.retrieval import RetrievalResult

if TYPE_CHECKING:
    from src.retrieval.dense_retriever import DenseRetriever

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Jina API helper
# ---------------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2),
)
def _jina_rerank(
    query: str,
    documents: list[str],
    model: str,
    api_key: str,
    top_n: int | None = None,
) -> list[float]:
    """
    Call the Jina Reranker REST API and return per-document relevance scores
    in the same order as ``documents``.

    Args:
        query:     The search query.
        documents: List of document texts to score.
        model:     Jina model name, e.g. ``"jina-reranker-v3"``.
        api_key:   Jina API key (``JINA_API_KEY``).
        top_n:     If provided, only the top-n documents are returned by the
                   API (may change ordering).  Pass ``None`` to get all.

    Returns:
        List of float scores, one per input document, in the **original order**.
    """
    import httpx  # noqa: PLC0415  – lazy import to avoid hard dependency

    url = "https://api.jina.ai/v1/rerank"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "model": model,
        "query": query,
        "documents": documents,
        "return_documents": False,
    }
    if top_n is not None:
        payload["top_n"] = top_n

    response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
    response.raise_for_status()
    data = response.json()

    # Map index → relevance_score (API may return subset / reordered)
    score_map: dict[int, float] = {}
    for item in data["results"]:
        score_map[item["index"]] = item["relevance_score"]

    return [score_map.get(i, 0.0) for i in range(len(documents))]


# ---------------------------------------------------------------------------
# RerankRetriever
# ---------------------------------------------------------------------------

class RerankRetriever(BaseRetriever):
    """
    Two-stage retriever: Dense bi-encoder → Reranker.

    The reranker backend is selected by ``use_api``:
      - ``use_api=False`` (default): local ``sentence-transformers`` CrossEncoder.
      - ``use_api=True``:  Jina Reranker REST API (``jina-reranker-v3`` etc.).

    Scoring of individual candidates is done **concurrently** using
    ``rerank_workers`` threads.  Each thread scores one (query, document) pair
    independently; results are collected and re-sorted.

    Args:
        dense_retriever:  Initialised DenseRetriever for first-stage recall.
        rerank_model:     Model name/path for the local CrossEncoder **or** the
                          Jina model name when ``use_api=True``.
        candidate_pool:   Number of dense candidates passed to the reranker.
                          Must be ≥ ``top_k``.
        use_api:          If ``True``, use the Jina Reranker API instead of a
                          local CrossEncoder.
        jina_api_key:     Jina API key (required when ``use_api=True``).
        rerank_workers:   Number of concurrent threads for API scoring.
                          Ignored for local mode (batch inference is used).
    """

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        rerank_model: str,
        candidate_pool: int = 100,
        use_api: bool = False,
        jina_api_key: str = "",
        rerank_workers: int = 5,
    ) -> None:
        self._dense = dense_retriever
        self._rerank_model_name = rerank_model
        self._candidate_pool = candidate_pool
        self._use_api = use_api
        self._jina_api_key = jina_api_key
        self._rerank_workers = rerank_workers
        self._cross_encoder = None  # lazy-loaded for local mode

    @property
    def name(self) -> str:
        return "rerank"

    # ------------------------------------------------------------------
    # Local CrossEncoder (lazy load)
    # ------------------------------------------------------------------
    def _get_cross_encoder(self):
        """Lazy-load the local CrossEncoder model."""
        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder  # noqa: PLC0415
            logger.info("Loading CrossEncoder: %s", self._rerank_model_name)
            self._cross_encoder = CrossEncoder(self._rerank_model_name, max_length=512)
        return self._cross_encoder

    # ------------------------------------------------------------------
    # Scoring backends
    # ------------------------------------------------------------------
    def _score_local(
        self,
        query: str,
        descriptions: list[str],
    ) -> list[float]:
        """Score all (query, doc) pairs with the local CrossEncoder (batch)."""
        cross_encoder = self._get_cross_encoder()
        pairs = [(query, desc) for desc in descriptions]
        scores = cross_encoder.predict(pairs, show_progress_bar=False)
        return [float(s) for s in scores]

    def _score_api_concurrent(
        self,
        query: str,
        candidates: list[tuple[int, str]],  # (original_rank_index, description)
    ) -> list[tuple[int, float]]:
        """
        Score candidates via the Jina API using ``rerank_workers`` threads.

        Each thread handles ONE candidate independently (1 retrieval per thread).
        Results are returned as ``(original_rank_index, score)`` tuples so the
        caller can restore original ordering.

        Args:
            query:      The search query.
            candidates: List of ``(index, description)`` pairs to score.

        Returns:
            List of ``(index, score)`` pairs (unordered; caller sorts).
        """
        def _score_one(idx: int, doc: str) -> tuple[int, float]:
            try:
                scores = _jina_rerank(
                    query=query,
                    documents=[doc],
                    model=self._rerank_model_name,
                    api_key=self._jina_api_key,
                    top_n=1,
                )
                return idx, scores[0]
            except Exception as exc:
                logger.error(
                    "Jina API scoring failed for candidate %d: %s", idx, exc
                )
                return idx, 0.0

        results: list[tuple[int, float]] = []
        with ThreadPoolExecutor(max_workers=self._rerank_workers) as pool:
            futures = {
                pool.submit(_score_one, idx, doc): idx
                for idx, doc in candidates
            }
            for future in as_completed(futures):
                results.append(future.result())

        return results

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Retrieve and rerank top-k documents.

        Step 1: Dense retrieval fetches ``candidate_pool`` candidates.
        Step 2: Fetch descriptions from ChromaDB.
        Step 3: Score (query, description) pairs via selected backend.
              – Local: batch CrossEncoder prediction.
              – API:   concurrent Jina API calls (``rerank_workers`` threads,
                       one call per candidate).
        Step 4: Re-sort by score; return top-k.

        Args:
            query:  Natural-language search query.
            top_k:  Number of final results after reranking.

        Returns:
            Ranked list of ``RetrievalResult`` with reranker scores.
        """
        pool_size = max(self._candidate_pool, top_k)

        backend = "jina-api" if self._use_api else "local-crossencoder"
        logger.debug(
            "Rerank search: query='%s', pool=%d, top_k=%d, backend=%s, workers=%d",
            query[:60],
            pool_size,
            top_k,
            backend,
            self._rerank_workers if self._use_api else 1,
        )

        # Stage 1: Dense recall
        dense_results = self._dense.search(query, top_k=pool_size)

        if not dense_results:
            logger.warning("Dense retriever returned no results for query: %s", query)
            return []

        # Stage 2: Fetch descriptions from ChromaDB
        collection = self._dense._get_collection()  # type: ignore[attr-defined]
        isbn_list = [r.isbn13 for r in dense_results]

        raw = collection.get(ids=isbn_list, include=["documents", "metadatas"])

        isbn_to_desc: dict[str, str] = {}
        isbn_to_title: dict[str, str] = {}
        for isbn, doc, meta in zip(raw["ids"], raw["documents"], raw["metadatas"]):
            isbn_to_desc[isbn] = doc or ""
            isbn_to_title[isbn] = meta.get("title", "") if meta else ""

        descriptions = [isbn_to_desc.get(r.isbn13, "") for r in dense_results]

        # Stage 3: Reranker scoring
        if self._use_api:
            if not self._jina_api_key:
                raise ValueError(
                    "JINA_API_KEY is required when RERANK_USE_API=true. "
                    "Set it in .env or pass jina_api_key= to RerankRetriever."
                )
            try:
                scores = _jina_rerank(
                    query=query,
                    documents=descriptions,
                    model=self._rerank_model_name,
                    api_key=self._jina_api_key,
                )
            except Exception as exc:
                logger.error("Jina API batch scoring failed: %s", exc)
                scores = [0.0] * len(dense_results)
        else:
            scores = self._score_local(query, descriptions)

        # Stage 4: Re-sort and return top-k
        scored: list[tuple[RetrievalResult, float]] = list(zip(dense_results, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        results: list[RetrievalResult] = []
        for rank, (result, score) in enumerate(scored[:top_k], start=1):
            results.append(
                RetrievalResult(
                    isbn13=result.isbn13,
                    title=isbn_to_title.get(result.isbn13, result.title),
                    score=float(score),
                    rank=rank,
                )
            )

        return results
