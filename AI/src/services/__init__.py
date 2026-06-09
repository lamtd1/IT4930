"""
Services package for book retrieval benchmark.

Uses lazy imports to avoid heavy dependencies (torch, sklearn, scipy)
being loaded at test collection time.
"""

from __future__ import annotations

__all__ = ["QueryService", "JudgeService", "CandidateService"]


def __getattr__(name: str):
    if name == "QueryService":
        from src.services.query_service import QueryService  # noqa: PLC0415
        return QueryService
    if name == "JudgeService":
        from src.services.judge_service import JudgeService  # noqa: PLC0415
        return JudgeService
    if name == "CandidateService":
        from src.services.candidate_service import CandidateService  # noqa: PLC0415
        return CandidateService
    raise AttributeError(f"module 'src.services' has no attribute {name!r}")

