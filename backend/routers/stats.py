"""
Stats router — GET /stats

Returns aggregate statistics computed from the in-memory DataFrame.
"""

from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, Request

from schemas import EMOTIONS, StatsResponse

router = APIRouter()
logger = logging.getLogger("backend.stats")


@router.get("/stats", response_model=StatsResponse)
async def get_stats(request: Request):
    """Return dataset-level aggregate statistics."""
    df: pd.DataFrame = request.app.state.df

    # Emotion distribution (mean across all books)
    emotion_distribution = {}
    for em in EMOTIONS:
        if em in df.columns:
            emotion_distribution[em] = round(float(df[em].mean()), 4)
        else:
            emotion_distribution[em] = 0.0

    # Category count
    total_categories = 0
    if "categories" in df.columns:
        total_categories = int(df["categories"].nunique())

    return StatsResponse(
        total_books=len(df),
        total_categories=total_categories,
        emotion_distribution=emotion_distribution,
    )
