"""
Search router — POST /search and POST /search/compare

Calls the AI retriever's search() method, enriches results with full
book metadata from the in-memory DataFrame, and returns JSON.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Request

from schemas import (
    EMOTIONS,
    BookResult,
    CompareRequest,
    SearchRequest,
    SearchResponse,
)

router = APIRouter()
logger = logging.getLogger("backend.search")


def _build_book_result(row, score: float) -> BookResult:
    """Convert a DataFrame row + retrieval score into a BookResult."""
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
    if isinstance(thumbnail, float):  # NaN
        thumbnail = None

    average_rating = 0.0
    try:
        average_rating = round(float(row.get("average_rating", 0) or 0), 4)
    except (ValueError, TypeError):
        average_rating = 0.0

    ratings_count = 0
    try:
        ratings_count = int(row.get("ratings_count", 0) or 0)
    except (ValueError, TypeError):
        ratings_count = 0

    return BookResult(
        isbn13=str(row.get("isbn13", "")),
        title=str(row.get("title", "")),
        authors=str(row.get("authors", "")),
        description=str(row.get("description", "")),
        thumbnail=thumbnail,
        categories=str(row.get("categories", "")),
        published_year=int(row.get("published_year", 0)),
        average_rating=average_rating,
        ratings_count=ratings_count,
        top_emotions=top_emotions,
        similarity_score=round(score, 4),
        emotion_scores=emotion_scores,
    )


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request):
    """
    Search books using one of 5 retrieval methods.

    The retriever returns isbn13 + score, then we enrich each result
    with full metadata from the DataFrame.
    """
    retrievers = request.app.state.retrievers
    df = request.app.state.df

    if req.method not in retrievers:
        raise HTTPException(400, f"Unknown method '{req.method}'")

    if not req.query or not req.query.strip():
        return SearchResponse(
            results=[], method_used=req.method, total_results=0, query_time_ms=0,
        )

    retriever = retrievers[req.method]

    # Run retrieval
    t0 = time.perf_counter()
    try:
        retrieval_results = retriever.search(req.query.strip(), top_k=req.top_k * 2)
    except Exception as exc:
        logger.error("Retriever '%s' failed: %s", req.method, exc, exc_info=True)
        raise HTTPException(500, f"Search failed: {exc}")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Enrich with full book metadata
    isbn_set = set(df["isbn13"].values)
    results: list[BookResult] = []

    for rr in retrieval_results:
        if rr.isbn13 not in isbn_set:
            continue

        book_row = df.loc[df["isbn13"] == rr.isbn13].iloc[0]

        # Apply emotion filter
        if req.filter_emotions:
            passes = False
            for em in req.filter_emotions:
                try:
                    if float(book_row.get(em, 0)) >= 0.28:
                        passes = True
                        break
                except (ValueError, TypeError):
                    pass
            if not passes:
                continue

        results.append(_build_book_result(book_row, rr.score))

        if len(results) >= req.top_k:
            break

    return SearchResponse(
        results=results,
        method_used=req.method,
        total_results=len(results),
        query_time_ms=round(elapsed_ms, 1),
    )


@router.post("/search/compare")
async def compare_methods(req: CompareRequest, request: Request):
    """
    Run multiple retrieval methods on the same query and return
    results grouped by method.
    """
    all_results = {}

    for method in req.methods:
        if method not in request.app.state.retrievers:
            continue
        search_req = SearchRequest(
            query=req.query, top_k=req.top_k, method=method,
        )
        try:
            response = await search(search_req, request)
            all_results[method] = response.model_dump()
        except HTTPException:
            all_results[method] = {"error": f"Method '{method}' failed"}

    return all_results
