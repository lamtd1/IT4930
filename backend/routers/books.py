"""
Books router — GET /books/{isbn13}

Returns full book detail including all 7 emotion scores.
Data comes from the in-memory DataFrame.
"""

from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, HTTPException, Request

from schemas import EMOTIONS, BookDetail

router = APIRouter()
logger = logging.getLogger("backend.books")


@router.get("/books/{isbn13}", response_model=BookDetail)
async def get_book(isbn13: str, request: Request):
    """Return full book detail for a given ISBN-13."""
    df: pd.DataFrame = request.app.state.df

    book_rows = df.loc[df["isbn13"] == isbn13]
    if book_rows.empty:
        raise HTTPException(status_code=404, detail="Book not found")

    row = book_rows.iloc[0]

    # Parse top_emotions
    top_emotions_raw = row.get("top_emotions", "")
    if isinstance(top_emotions_raw, str) and top_emotions_raw:
        top_emotions = [e.strip() for e in top_emotions_raw.split(",") if e.strip()]
    else:
        top_emotions = []

    # Build emotion scores dict
    emotion_scores = {}
    for em in EMOTIONS:
        val = row.get(em, 0)
        try:
            emotion_scores[em] = round(float(val), 4)
        except (ValueError, TypeError):
            emotion_scores[em] = 0.0

    # Handle nullable fields
    thumbnail = row.get("thumbnail", None)
    if isinstance(thumbnail, float):  # NaN
        thumbnail = None

    num_pages = None
    if pd.notna(row.get("num_pages")):
        try:
            num_pages = int(row["num_pages"])
        except (ValueError, TypeError):
            num_pages = None

    description_length = None
    if pd.notna(row.get("description_length")):
        try:
            description_length = int(row["description_length"])
        except (ValueError, TypeError):
            description_length = None

    book_age = None
    if pd.notna(row.get("book_age")):
        try:
            book_age = int(row["book_age"])
        except (ValueError, TypeError):
            book_age = None

    return BookDetail(
        isbn13=str(row.get("isbn13", "")),
        title=str(row.get("title", "")),
        authors=str(row.get("authors", "")),
        description=str(row.get("description", "")),
        thumbnail=thumbnail,
        categories=str(row.get("categories", "")),
        tag_clean=str(row.get("tag_clean", "")) if pd.notna(row.get("tag_clean")) else None,
        published_year=int(row.get("published_year", 0)),
        num_pages=num_pages,
        description_length=description_length,
        book_age=book_age,
        top_emotions=top_emotions,
        emotion_scores=emotion_scores,
    )
