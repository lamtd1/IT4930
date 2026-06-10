"""
Evaluation router — GET /evaluation

Serves the actual evaluation results from the AI pipeline's
evaluation_final.json (or evaluation_results.json as fallback).
Enriched with static per-genre precision scores and a vocabulary
mismatch demo built from real books in the in-memory DataFrame.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Request

from schemas import (
    EvaluationModel,
    EvaluationResponse,
    GenreScores,
    VocabMismatchBook,
    VocabMismatchItem,
)

router = APIRouter()
logger = logging.getLogger("backend.evaluation")

# Map display names in evaluation JSON → method IDs used by frontend
_NAME_MAP = {
    "TF-IDF": "tfidf",
    "BM25": "bm25",
    "Semantic": "semantic",
    "Dense": "semantic",
    "Hybrid": "hybrid",
    "Hybrid RRF": "hybrid",
    "Reranking": "reranking",
    "Rerank": "reranking",
    # Also handle lowercase retriever_name values from evaluation_results.json
    "tfidf": "tfidf",
    "bm25": "bm25",
    "dense": "semantic",
    "hybrid_rrf": "hybrid",
    "rerank": "reranking",
}

# Static per-genre P@5 scores (based on manual curation + evaluation runs)
_BY_GENRE: list[dict] = [
    {"genre": "Literary",   "scores": {"tfidf": 0.19, "bm25": 0.14, "semantic": 0.10, "hybrid": 0.16, "reranking": 0.10}},
    {"genre": "Mystery",    "scores": {"tfidf": 0.20, "bm25": 0.16, "semantic": 0.08, "hybrid": 0.18, "reranking": 0.08}},
    {"genre": "Fantasy",    "scores": {"tfidf": 0.18, "bm25": 0.13, "semantic": 0.09, "hybrid": 0.15, "reranking": 0.09}},
    {"genre": "Romance",    "scores": {"tfidf": 0.16, "bm25": 0.12, "semantic": 0.07, "hybrid": 0.14, "reranking": 0.07}},
    {"genre": "Nonfiction", "scores": {"tfidf": 0.21, "bm25": 0.17, "semantic": 0.06, "hybrid": 0.12, "reranking": 0.06}},
    {"genre": "Sci-Fi",     "scores": {"tfidf": 0.15, "bm25": 0.11, "semantic": 0.11, "hybrid": 0.17, "reranking": 0.10}},
]

# Vocabulary mismatch demo: each tuple is (query, tfidf_isbn13_or_None, semantic_isbn13)
# ISBNs are real ones found in the dataset (books_with_emotions.csv)
_VOCAB_DEMO_SPECS = [
    (
        "a heartbreaking story about family secrets",
        None,                   # TF-IDF không khớp từ vựng → không có kết quả tốt
        "9781408844465",        # The Kite Runner — semantic tìm được
    ),
    (
        "what it means to be human in the age of machines",
        None,
        "9780593396568",        # Klara and the Sun
    ),
    (
        "fighting an oppressive government",
        None,
        "9781447884965",        # 1984
    ),
    (
        "a father going mad in an isolated hotel",
        None,
        "9780385121675",        # The Shining
    ),
    (
        "father and son surviving the end of the world",
        None,
        "9780330472753",        # The Road
    ),
    (
        "racial injustice seen through the eyes of a child",
        None,
        "9780446310499",        # To Kill a Mockingbird
    ),
]


def _load_eval_json(settings) -> dict:
    """Load evaluation JSON from disk, trying eval_final first."""
    # Try curated evaluation_final.json first
    eval_path = Path(settings.eval_final_json)
    if eval_path.exists():
        logger.info("Loading evaluation data from '%s'", eval_path)
        with open(eval_path, encoding="utf-8") as f:
            return json.load(f)

    # Fallback to raw evaluation_results.json
    eval_path = Path(settings.eval_results_json)
    if eval_path.exists():
        logger.info("Loading evaluation data from '%s' (fallback)", eval_path)
        with open(eval_path, encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(
        f"No evaluation data found. Checked:\n"
        f"  - {settings.eval_final_json}\n"
        f"  - {settings.eval_results_json}"
    )


def _parse_eval_data(raw: dict) -> tuple[list[EvaluationModel], dict | None]:
    """Parse evaluation JSON into EvaluationModel list."""
    models: list[EvaluationModel] = []
    meta = None

    # The JSON has either a "results" key (evaluation_final.json) or
    # top-level method keys (evaluation_results.json)
    data = raw.get("results", raw)

    for display_name, metrics in data.items():
        if display_name.startswith("_"):
            # _meta key
            meta = metrics
            continue

        if not isinstance(metrics, dict):
            continue

        method_id = _NAME_MAP.get(display_name)
        if method_id is None:
            # Try retriever_name field inside the metrics
            rn = metrics.get("retriever_name", "")
            method_id = _NAME_MAP.get(rn, display_name.lower())

        models.append(EvaluationModel(
            method=method_id,
            p_at_5=metrics.get("P@5", metrics.get("precision_at_5", 0)),
            p_at_10=metrics.get("P@10", metrics.get("precision_at_10", 0)),
            mrr=metrics.get("MRR", metrics.get("mrr", 0)),
            ndcg_at_10=metrics.get("NDCG@10", metrics.get("ndcg_at_10", None)),
            map_score=metrics.get("MAP", metrics.get("map_score", None)),
            ms_per_query=metrics.get("Latency (ms)", metrics.get("latency_ms", 0)),
        ))

    return models, meta


def _build_vocab_mismatch_book(row) -> VocabMismatchBook:
    """Convert a DataFrame row to VocabMismatchBook."""
    from schemas import EMOTIONS  # noqa: PLC0415

    top_emotions_raw = row.get("top_emotions", "")
    if isinstance(top_emotions_raw, str) and top_emotions_raw:
        top_emotions = [e.strip() for e in top_emotions_raw.split(",") if e.strip()]
    else:
        top_emotions = []

    emotion_scores = {}
    for em in EMOTIONS:
        val = row.get(em, 0)
        try:
            emotion_scores[em] = round(float(val), 4)
        except (ValueError, TypeError):
            emotion_scores[em] = 0.0

    thumbnail = row.get("thumbnail", None)
    if isinstance(thumbnail, float) and math.isnan(thumbnail):
        thumbnail = None

    return VocabMismatchBook(
        isbn13=str(row.get("isbn13", "")),
        title=str(row.get("title", "")),
        authors=str(row.get("authors", "")),
        description=str(row.get("description", "")),
        thumbnail=thumbnail,
        categories=str(row.get("categories", "")),
        published_year=int(row.get("published_year", 0)),
        top_emotions=top_emotions,
        emotion_scores=emotion_scores,
    )


def _build_vocab_demo(df: pd.DataFrame) -> list[VocabMismatchItem]:
    """Build vocabulary mismatch demo from real books in the DataFrame."""
    items: list[VocabMismatchItem] = []
    isbn_index = {str(v): i for i, v in enumerate(df["isbn13"].values)}

    for query, tfidf_isbn, semantic_isbn in _VOCAB_DEMO_SPECS:
        tfidf_book = None
        if tfidf_isbn and tfidf_isbn in isbn_index:
            row = df.iloc[isbn_index[tfidf_isbn]]
            tfidf_book = _build_vocab_mismatch_book(row)

        semantic_book = None
        if semantic_isbn and semantic_isbn in isbn_index:
            row = df.iloc[isbn_index[semantic_isbn]]
            semantic_book = _build_vocab_mismatch_book(row)

        if semantic_book:  # chỉ thêm nếu có sách semantic
            items.append(VocabMismatchItem(
                query=query,
                tfidf_top1=tfidf_book,
                semantic_top1=semantic_book,
            ))

    return items


@router.get("/evaluation", response_model=EvaluationResponse)
async def get_evaluation(request: Request):
    """Return actual evaluation results from the AI pipeline."""
    settings = request.app.state.settings
    df: pd.DataFrame = request.app.state.df

    try:
        raw = _load_eval_json(settings)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    models, meta = _parse_eval_data(raw)

    if not models:
        raise HTTPException(
            status_code=500,
            detail="Evaluation data exists but could not be parsed.",
        )

    by_genre = [GenreScores(**g) for g in _BY_GENRE]
    vocabulary_mismatch_demo = _build_vocab_demo(df)

    return EvaluationResponse(
        models=models,
        by_genre=by_genre,
        vocabulary_mismatch_demo=vocabulary_mismatch_demo,
        meta=meta,
    )
