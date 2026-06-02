"""Configuration constants for book data collection pipeline.

Centralized constants used across src/data/collect.py and notebooks.
Edit SEED_SUBJECTS / LIST_DISCOVERY_QUERIES here to change crawl scope.
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_RAW: Path = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED: Path = PROJECT_ROOT / "data" / "processed"
INTERMEDIATE: Path = DATA_RAW / "_intermediate"
LOG_FILE: Path = DATA_RAW / "crawl.log"

# --------------------------------------------------------------------------- #
# API endpoints
# --------------------------------------------------------------------------- #
OL_BASE: str = "https://openlibrary.org"
GOOGLE_BOOKS_BASE: str = "https://www.googleapis.com/books/v1/volumes"
OL_COVER_BASE: str = "https://covers.openlibrary.org/b/id"

# --------------------------------------------------------------------------- #
# HTTP behavior
# --------------------------------------------------------------------------- #
# User-Agent identifies the project per Open Library guideline.
# NOTE: If you start getting HTTP 403, OL has rate-limit-blocked this exact
# UA string. Change the version suffix (e.g. /1.1 -> /1.2) to get unblocked.
USER_AGENT: str = "OL-BookCrawl/1.0 (contact: orms147@gmail.com; HUST student IT4142)"

# Sleep between Open Library calls. Set to 3.0s after observing IP-level
# 403 blocks during pilot + first full-crawl attempts.
# Trade-off: 3s × 2 calls/work × 25k works = ~42 hours. Too slow for full
# scope. Realistic plan: 1.5s + scaled-down scope to 15 subjects × 500
# works = ~7500 books, ~6 hours total.
RATE_LIMIT_SLEEP: float = 1.5

# Sleep between Google Books calls. Probed: no per-minute rate limit — the
# throughput ceiling is Google's ~0.9s response latency, so requests are
# latency-bound at ~1/s sequentially. Keep a tiny 0.1s for politeness; the
# real cap is the per-key 1,000/day daily quota.
GOOGLE_RATE_LIMIT_SLEEP: float = 0.1

# HTTP request timeout (seconds).
REQUEST_TIMEOUT: int = 30

# Retry policy.
MAX_RETRIES: int = 3
RETRY_BACKOFF_BASE: float = 5.0  # seconds; actual wait = base * 2^attempt

# --------------------------------------------------------------------------- #
# Crawl scope — 30 SEED SUBJECTS
# --------------------------------------------------------------------------- #
SEED_SUBJECTS: list[str] = [
    # Fiction major genres (10)
    "fantasy",
    "science_fiction",
    "mystery",
    "thriller",
    "romance",
    "historical_fiction",
    "horror",
    "literary_fiction",
    "crime_fiction",
    "adventure",
    # Non-fiction major (10)
    "biography",
    "history",
    "science",
    "philosophy",
    "psychology",
    "business",
    "self-help",
    "economics",
    "religion",
    "sociology",
    # Children & YA (2)
    "young_adult_fiction",
    "children's_fiction",
    # Niche / coverage (8)
    "poetry",
    "graphic_novels",
    "cookbooks",
    "travel",
    "art",
    "medicine",
    "drama",
    "classics",
]

# How many works to fetch per subject in Phase 1.
# Scaled down from 1000 to 500 after IP throttling issues — still gives
# ~10-15k books across 30 subjects after dedup + filter, enough for IR eval.
WORKS_PER_SUBJECT: int = 500
WORKS_PAGE_SIZE: int = 100  # OL `/subjects/{x}.json` — smaller pages, less aggressive

# --------------------------------------------------------------------------- #
# Phase 3 — list discovery
# --------------------------------------------------------------------------- #
LIST_DISCOVERY_QUERIES: list[str] = [
    "best fantasy",
    "best sci-fi",
    "must read classics",
    "best mystery",
    "top thriller",
    "best biography",
    "favorite books",
    "essential reading",
    "best of decade",
    "award winners",
    "best young adult",
    "best romance",
    "best horror",
    "best history books",
    "best science books",
    "100 best novels",
    "books to read before you die",
    "best philosophy",
    "best memoir",
    "Pulitzer",
]

LISTS_PER_QUERY: int = 30  # results per `q=...` query
LISTS_PER_SUBJECT: int = 50  # results per `/subjects/{x}/lists.json`

# Bad list-name regex (case-insensitive). Drops noise lists.
BAD_LIST_NAME_PATTERN: str = (
    r"^(to.?read|tbr|favorites?|my (books|library)|"
    r"homework|reading list|\d+)$"
)

# --------------------------------------------------------------------------- #
# Filters & thresholds
# --------------------------------------------------------------------------- #
NEEDS_AUGMENT_THRESHOLD: int = 20  # words; below this trigger Google Books augment
MAX_SUBJECTS_PER_BOOK: int = 30  # truncate noisy long subject lists
MIN_LIST_SEEDS: int = 5  # drop lists with < N books in our corpus
MAX_LIST_SEEDS: int = 500  # drop oversized generic lists
LANGUAGE_FILTER: str = "eng"  # only English books

# Validation targets (HARD FAIL thresholds in validate_books_csv).
TARGET_BOOK_COUNT_MIN: int = 7_000   # Scaled down from 22k after OL throttling
TARGET_LIST_COUNT_MIN: int = 150     # Scaled down from 300
TARGET_QUALIFIED_LISTS_MIN: int = 100  # Scaled down from 200

# --------------------------------------------------------------------------- #
# Google Books quota
# --------------------------------------------------------------------------- #
# Set very high so our code never self-caps — Google's real daily limit is the
# only stop (surfaced as a GoogleQuotaExceeded on a dailyLimitExceeded refusal).
GOOGLE_DAILY_QUOTA: int = 1_000_000
GOOGLE_QUOTA_BUFFER: int = 50
GOOGLE_QUOTA_FILE: Path = INTERMEDIATE / "google_quota.json"
GOOGLE_AUGMENT_LOG: Path = INTERMEDIATE / "google_augment_log.jsonl"

# Fuzzy match threshold for Tier 3 title+author match.
GOOGLE_TITLE_MATCH_RATIO: float = 0.85

# --------------------------------------------------------------------------- #
# Checkpoint
# --------------------------------------------------------------------------- #
CHECKPOINT_INTERVAL: int = 500  # save chunk every N works
PHASE1_OUTPUT: Path = INTERMEDIATE / "phase1_work_ids.txt"
PHASE2_CHUNK_PREFIX: str = "phase2_chunk_"
PHASE3_LISTS_OUTPUT: Path = INTERMEDIATE / "phase3_lists.jsonl"
PHASE4_AUGMENTED_OUTPUT: Path = INTERMEDIATE / "phase4_augmented.csv"
MISSING_WORKS_LOG: Path = INTERMEDIATE / "missing_works.txt"

# --------------------------------------------------------------------------- #
# Final outputs
# --------------------------------------------------------------------------- #
BOOKS_CSV: Path = DATA_RAW / "books.csv"
LISTS_CSV: Path = DATA_RAW / "lists.csv"
SUBJECTS_CSV: Path = DATA_RAW / "subjects.csv"
METADATA_JSON: Path = DATA_RAW / "metadata.json"
