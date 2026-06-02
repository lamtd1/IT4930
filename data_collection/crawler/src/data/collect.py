"""Crawl module: Open Library + Google Books → books.csv + lists.csv.

Pipeline:
    Phase 1: fetch_subject_works (seed work IDs)
    Phase 2: fetch_work_detail (per-work metadata + edition)
    Phase 3: fetch_lists_by_query / by_subject / by_work (ground truth)
    Phase 4: augment_with_google_books (description fill)

All public functions accept a shared `requests.Session` for connection reuse.
Rate limiting and retry are handled inside `_get_json`.

Reuse pattern from `.claude/skills/collect-data` (Pattern 3: REST API).
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests

from src import config

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def _make_session() -> requests.Session:
    """Build a requests.Session with identified User-Agent header.

    Open Library guideline asks for identifiable contact in User-Agent
    to avoid being rate-limited as anonymous.

    Returns:
        A configured requests.Session.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT})
    return session


_KEY_RE = re.compile(r"(key=)[^&\s]+", re.IGNORECASE)


def _redact_key(text: str) -> str:
    """Strip any `key=...` value from a string before logging (avoid API-key leak)."""
    return _KEY_RE.sub(r"\1***", text)


class GoogleQuotaExceeded(RuntimeError):
    """Raised when Google Books returns a daily-limit refusal (vs a transient rate limit)."""


def _get_json(
    url: str,
    session: requests.Session,
    params: dict[str, Any] | None = None,
    raise_on_quota: bool = False,
) -> dict | None:
    """GET URL and return parsed JSON, with retry on 429/5xx.

    Uses exponential backoff: wait = RETRY_BACKOFF_BASE * 2^attempt seconds.
    Returns None after all retries exhausted or on 404.

    Args:
        url: Full URL to fetch.
        session: Shared requests.Session.
        params: Optional query parameters.

    Returns:
        Parsed JSON dict or None if unrecoverable.
    """
    for attempt in range(config.MAX_RETRIES):
        try:
            response = session.get(
                url, params=params, timeout=config.REQUEST_TIMEOUT
            )
            if response.status_code == 404:
                return None
            if response.status_code in (429, 403) and raise_on_quota:
                # Distinguish a hard daily-quota refusal (stop) from a transient
                # per-minute rate limit (retry). Google's daily-exhaustion body says
                #: "Quota exceeded ... limit 'Queries per day'".
                body = (response.text or "").lower()
                if "per day" in body or "dailylimitexceeded" in body:
                    raise GoogleQuotaExceeded(
                        f"HTTP {response.status_code}: daily Queries-per-day quota exhausted"
                    )
            if response.status_code in (429, 500, 502, 503, 504):
                wait = config.RETRY_BACKOFF_BASE * (2**attempt)
                logger.warning(
                    f"HTTP {response.status_code} from {_redact_key(url)}; "
                    f"retry in {wait}s (attempt {attempt + 1}/{config.MAX_RETRIES})"
                )
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as exc:
            wait = config.RETRY_BACKOFF_BASE * (2**attempt)
            logger.warning(
                f"Request failed for {_redact_key(url)}: {_redact_key(str(exc))}; "
                f"retry in {wait}s (attempt {attempt + 1}/{config.MAX_RETRIES})"
            )
            time.sleep(wait)
    logger.error(f"Giving up on {_redact_key(url)} after {config.MAX_RETRIES} retries")
    return None


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_WHITESPACE_RE = re.compile(r"\s+")
_YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")


def _clean_html(text: str) -> str:
    """Strip HTML tags, collapse markdown links, normalize whitespace.

    Args:
        text: Raw text potentially containing HTML/markdown.

    Returns:
        Cleaned plain-text string.
    """
    if not text:
        return ""
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)  # [label](url) -> label
    text = _HTML_TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _extract_description(work_json: dict) -> str:
    """Extract description from work JSON, handling both shapes.

    Open Library returns description as either a plain string or
    a dict {"type": "/type/text", "value": "..."}.

    Args:
        work_json: Parsed JSON from /works/{id}.json.

    Returns:
        Cleaned description string (may be empty).
    """
    desc = work_json.get("description", "")
    if isinstance(desc, dict):
        desc = desc.get("value", "")
    if not isinstance(desc, str):
        logger.warning(
            f"Unexpected description type for work "
            f"{work_json.get('key', '?')}: {type(desc).__name__}"
        )
        return ""
    return _clean_html(desc)


def _parse_year(date_str: Any) -> int | None:
    """Extract 4-digit year from a date string.

    Args:
        date_str: String like "1954", "July 29, 1954", or anything else.

    Returns:
        Year as int, or None if not parseable.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    match = _YEAR_RE.search(date_str)
    return int(match.group(1)) if match else None


def _word_count(text: str) -> int:
    """Count whitespace-separated tokens.

    Args:
        text: Input string.

    Returns:
        Number of tokens (0 if empty).
    """
    if not text:
        return 0
    return len(text.split())


# --------------------------------------------------------------------------- #
# Phase 1 — subject seeding
# --------------------------------------------------------------------------- #
def fetch_subject_works(
    subject: str,
    session: requests.Session,
    max_works: int = config.WORKS_PER_SUBJECT,
    author_cache: dict[str, list[str]] | None = None,
    year_cache: dict[str, int] | None = None,
) -> list[str]:
    """Fetch list of work IDs for a given subject.

    Uses /subjects/{subject}.json with pagination. Returns up to max_works
    work IDs (deduped). Sleeps RATE_LIMIT_SLEEP between calls.

    The /subjects/ endpoint returns enriched data per work including
    author names and first_publish_year. If caches are provided, those
    fields are populated as a side-effect — saving an extra API call later.

    Args:
        subject: Subject slug (e.g., "fantasy").
        session: Shared session.
        max_works: Upper limit on returned IDs.
        author_cache: Optional dict to populate {work_id: [author_name, ...]}.
        year_cache: Optional dict to populate {work_id: year}.

    Returns:
        List of work IDs like ["OL12345W", ...].
    """
    work_ids: list[str] = []
    page_size = config.WORKS_PAGE_SIZE
    offset = 0

    while len(work_ids) < max_works:
        url = f"{config.OL_BASE}/subjects/{subject}.json"
        params = {"limit": page_size, "offset": offset}
        data = _get_json(url, session, params=params)

        if data is None or not data.get("works"):
            break

        for work in data["works"]:
            key = work.get("key", "")  # e.g. "/works/OL123W"
            if not key.startswith("/works/"):
                continue
            work_id = key.removeprefix("/works/")
            work_ids.append(work_id)

            # Stash side-channel data: author names + year from search response
            if author_cache is not None:
                names = [
                    a.get("name", "")
                    for a in work.get("authors", []) or []
                    if a.get("name")
                ]
                if names:
                    author_cache[work_id] = names
            if year_cache is not None:
                year = work.get("first_publish_year")
                if isinstance(year, int):
                    year_cache[work_id] = year

        if len(data["works"]) < page_size:
            break  # last page

        offset += page_size
        time.sleep(config.RATE_LIMIT_SLEEP)

    logger.info(f"Subject '{subject}': fetched {len(work_ids)} work IDs")
    return work_ids[:max_works]


# --------------------------------------------------------------------------- #
# Phase 2 — work detail + edition
# --------------------------------------------------------------------------- #
def fetch_work_detail(
    work_id: str,
    session: requests.Session,
    author_hint: list[str] | None = None,
    year_hint: int | None = None,
) -> dict | None:
    """Fetch full detail for one work, including a sample edition.

    Combines /works/{id}.json + /works/{id}/editions.json (limit=1).
    Applies inline filters: language=eng, non-empty title, has description OR
    subjects.

    Args:
        work_id: OL work ID (e.g., "OL12345W").
        session: Shared session.
        author_hint: Optional list of author names from /subjects/ response.
            Used to populate the `authors` field without an extra /authors/
            API call. /works/ endpoint only returns author IDs, not names.
        year_hint: Optional first_publish_year from /subjects/ response.
            Used as fallback if /works/ first_publish_date is missing/unparseable.

    Returns:
        Dict with crawl fields, or None if filtered out / not found.
    """
    work_url = f"{config.OL_BASE}/works/{work_id}.json"
    work = _get_json(work_url, session)
    if work is None:
        return None

    title = work.get("title", "").strip()
    if not title:
        return None

    description = _extract_description(work)
    subjects = work.get("subjects", []) or []

    if not description and not subjects:
        return None

    time.sleep(config.RATE_LIMIT_SLEEP)

    # Edition: first edition with ISBN
    ed_url = f"{config.OL_BASE}/works/{work_id}/editions.json"
    ed_data = _get_json(ed_url, session, params={"limit": 1})
    edition = ed_data.get("entries", [{}])[0] if ed_data else {}

    # Language filter
    languages = edition.get("languages", []) or []
    lang_codes = [l.get("key", "").removeprefix("/languages/") for l in languages]
    primary_lang = lang_codes[0] if lang_codes else "eng"  # default eng if missing
    if primary_lang != config.LANGUAGE_FILTER:
        return None

    # ISBN
    isbn_13_list = edition.get("isbn_13", []) or []
    isbn_10_list = edition.get("isbn_10", []) or []
    isbn_13 = isbn_13_list[0] if isbn_13_list else None
    isbn_10 = isbn_10_list[0] if isbn_10_list else None

    # Authors
    author_ids: list[str] = []
    for a in work.get("authors", []) or []:
        key = a.get("author", {}).get("key", "")
        if key.startswith("/authors/"):
            author_ids.append(key.removeprefix("/authors/"))

    # Cover
    covers = work.get("covers", []) or []
    cover_id = covers[0] if covers else None

    # Ratings (may be in work or only via /ratings endpoint — skip the latter)
    ratings_info = work.get("ratings") or {}
    summary = ratings_info.get("summary") if isinstance(ratings_info, dict) else None
    ratings_avg = summary.get("average") if summary else None
    ratings_count = summary.get("count") if summary else None

    # Truncate subjects to avoid pathological cases
    if len(subjects) > config.MAX_SUBJECTS_PER_BOOK:
        subjects_truncated = subjects[: config.MAX_SUBJECTS_PER_BOOK]
    else:
        subjects_truncated = subjects

    # Author names: prefer hint from /subjects/ response (cheap, ~free).
    # /works/ only returns author IDs; resolving to names would cost one
    # extra API call per author. We accept empty list if hint missing.
    author_names = list(author_hint) if author_hint else []

    # Year: prefer parsed first_publish_date; fall back to year_hint
    # from /subjects/ response (which OL pre-computes).
    year = _parse_year(work.get("first_publish_date"))
    if year is None and year_hint is not None:
        year = year_hint

    return {
        "work_id": work_id,
        "isbn_13": isbn_13,
        "isbn_10": isbn_10,
        "title": title,
        "subtitle": work.get("subtitle"),
        "authors": author_names,
        "author_ids": author_ids,
        "first_publish_year": year,
        "page_count": edition.get("number_of_pages"),
        "language": primary_lang,
        "description": description,
        "description_word_count": _word_count(description),
        "description_source": "openlibrary" if description else "missing",
        "subjects": subjects_truncated,
        "subjects_count": len(subjects),
        "cover_id": cover_id,
        "ratings_avg": ratings_avg,
        "ratings_count": ratings_count,
        "crawled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# --------------------------------------------------------------------------- #
# Phase 3 — lists discovery (ground truth)
# --------------------------------------------------------------------------- #
def fetch_lists_by_query(
    query: str,
    session: requests.Session,
    limit: int = config.LISTS_PER_QUERY,
) -> list[dict]:
    """Strategy A: search OL lists by free-text query.

    Args:
        query: Search string (e.g., "best fantasy").
        session: Shared session.
        limit: Max results.

    Returns:
        List of list-metadata dicts with keys: list_id, list_url, list_name,
        list_description, creator.
    """
    url = f"{config.OL_BASE}/search/lists.json"
    data = _get_json(url, session, params={"q": query, "limit": limit})
    if data is None:
        return []
    return _parse_lists_search(data)


def fetch_lists_by_subject(
    subject: str,
    session: requests.Session,
    limit: int = config.LISTS_PER_SUBJECT,
) -> list[dict]:
    """Strategy B: fetch lists tagged with a subject.

    Args:
        subject: Subject slug.
        session: Shared session.
        limit: Max results.

    Returns:
        List of list-metadata dicts (same shape as fetch_lists_by_query).
    """
    url = f"{config.OL_BASE}/subjects/{subject}/lists.json"
    data = _get_json(url, session, params={"limit": limit})
    if data is None:
        return []
    return _parse_lists_search(data)


def fetch_lists_by_work(
    work_id: str,
    session: requests.Session,
) -> list[dict]:
    """Strategy C: lists containing a given work (fallback).

    Args:
        work_id: OL work ID.
        session: Shared session.

    Returns:
        List of list-metadata dicts.
    """
    url = f"{config.OL_BASE}/works/{work_id}/lists.json"
    data = _get_json(url, session)
    if data is None:
        return []
    return _parse_lists_search(data)


def _parse_lists_search(data: dict) -> list[dict]:
    """Normalize varied OL list-search responses into a unified shape.

    Args:
        data: Raw JSON from any of the lists endpoints.

    Returns:
        Normalized list of dicts.
    """
    out: list[dict] = []
    entries = data.get("entries") or data.get("docs") or []
    for entry in entries:
        # list URL like "/people/{user}/lists/{id}" or list key like "/lists/{id}"
        list_url = entry.get("url") or entry.get("key") or ""
        if "/lists/" not in list_url:
            continue
        parts = list_url.split("/")
        if "people" in parts:
            try:
                idx_people = parts.index("people")
                creator = parts[idx_people + 1]
                list_id = parts[-1]
            except (ValueError, IndexError):
                creator = None
                list_id = parts[-1]
        else:
            creator = None
            list_id = parts[-1]

        out.append(
            {
                "list_id": list_id,
                "list_url": list_url,
                "list_name": (entry.get("name") or "").strip(),
                "list_description": entry.get("description") or "",
                "creator": creator,
            }
        )
    return out


def fetch_list_seeds(
    list_url: str,
    session: requests.Session,
) -> list[str]:
    """Fetch the list of work IDs (seeds) in an OL list.

    Args:
        list_url: Relative URL like "/people/user/lists/OL97L".
        session: Shared session.

    Returns:
        List of work IDs that are type=/type/work seeds.
    """
    url = f"{config.OL_BASE}{list_url}/seeds.json"
    data = _get_json(url, session)
    if data is None:
        return []
    work_ids: list[str] = []
    for entry in data.get("entries", []):
        # Entry shape: {"url": "/works/OLxxxW", "type": "/type/work", ...}
        entry_url = entry.get("url", "")
        entry_type = entry.get("type", "")
        if entry_type == "/type/work" and entry_url.startswith("/works/"):
            work_ids.append(entry_url.removeprefix("/works/"))
    return work_ids


# --------------------------------------------------------------------------- #
# Phase 4 — Google Books augment
# --------------------------------------------------------------------------- #
def _load_quota(quota_file: Path) -> dict:
    """Load Google Books quota counter, resetting if date rolled over.

    Args:
        quota_file: Path to JSON quota tracker file.

    Returns:
        Dict {"date": "YYYY-MM-DD", "used": int}.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if quota_file.exists():
        try:
            state = json.loads(quota_file.read_text(encoding="utf-8"))
            if state.get("date") == today:
                return state
        except json.JSONDecodeError:
            pass
    return {"date": today, "used": 0}


def _save_quota(state: dict, quota_file: Path) -> None:
    """Persist quota state to disk."""
    quota_file.parent.mkdir(parents=True, exist_ok=True)
    quota_file.write_text(json.dumps(state), encoding="utf-8")


def augment_with_google_books(
    isbn_13: str | None,
    isbn_10: str | None,
    title: str,
    author: str | None,
    api_key: str,
    session: requests.Session,
    quota_file: Path = config.GOOGLE_QUOTA_FILE,
) -> tuple[str, str]:
    """Try to fetch a richer description from Google Books.

    Tier 1: ISBN-13 match (unconditional accept).
    Tier 2: ISBN-10 match (unconditional accept).
    Tier 3: title+author match (validate fuzzy ratio).
    Tier 4: skip → returns ("", "skipped").

    Tracks quota in `quota_file`; raises RuntimeError if exhausted.

    Args:
        isbn_13: ISBN-13 if available.
        isbn_10: ISBN-10 if available.
        title: Book title.
        author: Primary author name (or None).
        api_key: Google Books API key.
        session: Shared session.
        quota_file: Path to quota tracker.

    Returns:
        Tuple (description, source_tag) where source_tag is one of
        "google_books_isbn13", "google_books_isbn10", "google_books_title",
        or "skipped".

    Raises:
        RuntimeError: If quota exhausted.
    """
    state = _load_quota(quota_file)
    if state["used"] >= (config.GOOGLE_DAILY_QUOTA - config.GOOGLE_QUOTA_BUFFER):
        raise RuntimeError(
            f"Google Books quota near exhausted ({state['used']}/"
            f"{config.GOOGLE_DAILY_QUOTA}). Resume tomorrow."
        )

    def _query(q: str, validate_title: bool = False) -> str | None:
        """Helper: call Google Books, increment quota."""
        params = {"q": q, "key": api_key, "maxResults": 1}
        data = _get_json(config.GOOGLE_BOOKS_BASE, session, params=params)
        state["used"] += 1
        _save_quota(state, quota_file)
        time.sleep(config.GOOGLE_RATE_LIMIT_SLEEP)
        if not data or not data.get("items"):
            return None
        vol = data["items"][0].get("volumeInfo", {})
        desc = vol.get("description", "") or ""
        desc = _clean_html(desc)
        if _word_count(desc) < 30:
            return None
        if validate_title:
            g_title = (vol.get("title") or "").lower()
            ratio = SequenceMatcher(None, g_title, title.lower()).ratio()
            if ratio < config.GOOGLE_TITLE_MATCH_RATIO:
                return None
        return desc

    # Tier 1: ISBN-13
    if isbn_13:
        result = _query(f"isbn:{isbn_13}")
        if result:
            return result, "google_books_isbn13"

    # Tier 2: ISBN-10
    if isbn_10:
        result = _query(f"isbn:{isbn_10}")
        if result:
            return result, "google_books_isbn10"

    # Tier 3: title + author
    if title and author:
        result = _query(
            f'intitle:"{title}"+inauthor:"{author}"', validate_title=True
        )
        if result:
            return result, "google_books_title"

    return "", "skipped"


def fetch_google_metadata(
    isbn_13: str | None,
    isbn_10: str | None,
    title: str,
    author: str | None,
    api_key: str,
    session: requests.Session,
    quota_file: Path = config.GOOGLE_QUOTA_FILE,
) -> dict:
    """Fetch full Google Books metadata for one book (not just description).

    Captures the fields the team IR pipeline needs — crucially `categories`
    in Google Books' own taxonomy (the same taxonomy the eval test queries
    use) — plus description, rating, thumbnail, ISBN-13, pages, year.

    Tier order: ISBN-13 -> ISBN-10 -> title+author (fuzzy-validated).
    Increments the shared daily quota counter; raises RuntimeError if exhausted.

    Returns:
        Dict with keys: description, categories, average_rating, ratings_count,
        thumbnail, isbn_13, page_count, published_year, match_tier. Fields are
        empty/None when unavailable; match_tier is one of
        "isbn13" | "isbn10" | "title" | "skipped".
    """
    state = _load_quota(quota_file)
    if state["used"] >= (config.GOOGLE_DAILY_QUOTA - config.GOOGLE_QUOTA_BUFFER):
        raise RuntimeError(
            f"Google Books quota near exhausted ({state['used']}/"
            f"{config.GOOGLE_DAILY_QUOTA}). Resume tomorrow."
        )

    empty: dict[str, Any] = {
        "title": "",
        "subtitle": "",
        "authors": "",
        "description": "",
        "categories": "",
        "average_rating": None,
        "ratings_count": None,
        "thumbnail": None,
        "isbn_13": None,
        "page_count": None,
        "published_year": None,
        "language": None,
        "publisher": None,
        "match_tier": "skipped",
    }

    def _extract(vol: dict) -> dict:
        ids = vol.get("industryIdentifiers") or []
        isbn13 = next(
            (i.get("identifier") for i in ids if i.get("type") == "ISBN_13"), None
        )
        img = (vol.get("imageLinks") or {}).get("thumbnail")
        year_match = re.match(r"(\d{4})", vol.get("publishedDate") or "")
        return {
            "title": vol.get("title") or "",
            "subtitle": vol.get("subtitle") or "",
            "authors": ", ".join(vol.get("authors") or []),
            "description": _clean_html(vol.get("description", "") or ""),
            "categories": "|".join(vol.get("categories") or []),
            "average_rating": vol.get("averageRating"),
            "ratings_count": vol.get("ratingsCount"),
            "thumbnail": img.replace("http://", "https://") if img else None,
            "isbn_13": isbn13,
            "page_count": vol.get("pageCount"),
            "published_year": int(year_match.group(1)) if year_match else None,
            "language": vol.get("language"),
            "publisher": vol.get("publisher"),
        }

    def _query(q: str, validate_title: bool = False) -> dict | None:
        params = {"q": q, "key": api_key, "maxResults": 1}
        data = _get_json(
            config.GOOGLE_BOOKS_BASE, session, params=params, raise_on_quota=True
        )
        state["used"] += 1
        _save_quota(state, quota_file)
        time.sleep(config.GOOGLE_RATE_LIMIT_SLEEP)
        if not data or not data.get("items"):
            return None
        vol = data["items"][0].get("volumeInfo", {})
        if validate_title:
            g_title = (vol.get("title") or "").lower()
            if (
                SequenceMatcher(None, g_title, title.lower()).ratio()
                < config.GOOGLE_TITLE_MATCH_RATIO
            ):
                return None
        return vol

    tiers: list[tuple[str | None, str, bool]] = [
        (f"isbn:{isbn_13}" if isbn_13 else None, "isbn13", False),
        (f"isbn:{isbn_10}" if isbn_10 else None, "isbn10", False),
        (
            f'intitle:"{title}"+inauthor:"{author}"' if title and author else None,
            "title",
            True,
        ),
    ]
    for query, tier, validate in tiers:
        if not query:
            continue
        vol = _query(query, validate)
        if vol:
            result = _extract(vol)
            result["match_tier"] = tier
            return result

    return dict(empty)


# --------------------------------------------------------------------------- #
# Checkpoint
# --------------------------------------------------------------------------- #
def save_checkpoint(
    records: list[dict],
    chunk_idx: int,
    prefix: str = config.PHASE2_CHUNK_PREFIX,
    out_dir: Path = config.INTERMEDIATE,
) -> Path:
    """Write records as JSONL chunk for resume support.

    Args:
        records: List of dicts (one per work).
        chunk_idx: 0-based chunk index.
        prefix: Filename prefix.
        out_dir: Directory to write into.

    Returns:
        Path to written file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    fpath = out_dir / f"{prefix}{chunk_idx:03d}.jsonl"
    with fpath.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, default=str) + "\n")
    logger.info(f"Saved checkpoint {fpath.name} ({len(records)} records)")
    return fpath


def load_checkpoints(
    prefix: str = config.PHASE2_CHUNK_PREFIX,
    in_dir: Path = config.INTERMEDIATE,
) -> list[dict]:
    """Load all existing chunks matching prefix, for resume support.

    Args:
        prefix: Filename prefix.
        in_dir: Directory to scan.

    Returns:
        Flat list of all records across chunks.
    """
    if not in_dir.exists():
        return []
    records: list[dict] = []
    for fpath in sorted(in_dir.glob(f"{prefix}*.jsonl")):
        with fpath.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    if records:
        logger.info(f"Loaded {len(records)} records from existing checkpoints")
    return records


# --------------------------------------------------------------------------- #
# Assembly + validation
# --------------------------------------------------------------------------- #
def build_books_dataframe(records: list[dict]):
    """Convert list of dicts to a clean DataFrame for books.csv.

    Joins list-typed columns (authors, author_ids, subjects) with "|".
    Drops duplicates by work_id.

    Args:
        records: Output of fetch_work_detail across works.

    Returns:
        pandas.DataFrame.
    """
    import pandas as pd

    df = pd.DataFrame.from_records(records)
    if df.empty:
        logger.warning("No records to build DataFrame")
        return df

    df = df.drop_duplicates(subset=["work_id"], keep="first")

    # Join list columns with "|"
    for col in ("authors", "author_ids", "subjects"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v: "|".join(v) if isinstance(v, list) else (v or "")
            )

    # Coerce numeric types
    if "first_publish_year" in df.columns:
        df["first_publish_year"] = (
            df["first_publish_year"].astype("Int64")
        )
    if "page_count" in df.columns:
        df["page_count"] = (
            df["page_count"]
            .apply(lambda v: v if isinstance(v, (int, float)) else None)
            .astype("Int64")
        )
    if "cover_id" in df.columns:
        df["cover_id"] = (
            df["cover_id"]
            .apply(lambda v: v if isinstance(v, (int, float)) else None)
            .astype("Int64")
        )
    if "ratings_count" in df.columns:
        df["ratings_count"] = (
            df["ratings_count"]
            .apply(lambda v: v if isinstance(v, (int, float)) else None)
            .astype("Int64")
        )

    return df


def validate_books_csv(df_books, df_lists) -> dict:
    """Run validation checks on books + lists DataFrames.

    Args:
        df_books: pandas.DataFrame from build_books_dataframe.
        df_lists: pandas.DataFrame of lists with seed_count.

    Returns:
        Dict {check_name: {"passed": bool, "value": ..., "severity": str}}.
    """
    import pandas as pd  # noqa: F401

    checks: dict[str, dict] = {}

    n_books = len(df_books)
    checks["row_count"] = {
        "value": n_books,
        "passed": n_books >= config.TARGET_BOOK_COUNT_MIN,
        "severity": "HARD",
        "target": f">= {config.TARGET_BOOK_COUNT_MIN}",
    }

    n_unique = df_books["work_id"].nunique() if "work_id" in df_books.columns else 0
    checks["unique_work_id"] = {
        "value": n_unique == n_books,
        "passed": n_unique == n_books,
        "severity": "HARD",
        "target": "True",
    }

    title_complete = (
        df_books["title"].notna().mean() if "title" in df_books.columns else 0
    )
    checks["no_missing_title"] = {
        "value": float(title_complete),
        "passed": title_complete == 1.0,
        "severity": "HARD",
        "target": "== 1.0",
    }

    desc_quality = (
        (df_books["description_word_count"] >= 20).mean()
        if "description_word_count" in df_books.columns
        else 0
    )
    desc_severity = (
        "HARD" if desc_quality < 0.70 else ("SOFT" if desc_quality < 0.85 else "PASS")
    )
    checks["description_quality"] = {
        "value": float(desc_quality),
        "passed": desc_quality >= 0.85,
        "severity": desc_severity,
        "target": ">= 0.85",
    }

    lang_share = (
        df_books["language"].eq(config.LANGUAGE_FILTER).mean()
        if "language" in df_books.columns
        else 0
    )
    checks["language_eng"] = {
        "value": float(lang_share),
        "passed": lang_share >= 0.95,
        "severity": "SOFT",
        "target": ">= 0.95",
    }

    n_lists = len(df_lists)
    checks["lists_count"] = {
        "value": n_lists,
        "passed": n_lists >= config.TARGET_LIST_COUNT_MIN,
        "severity": "HARD",
        "target": f">= {config.TARGET_LIST_COUNT_MIN}",
    }

    qualified = (
        (df_lists["seed_count"] >= 5).sum() if "seed_count" in df_lists.columns else 0
    )
    checks["qualified_lists"] = {
        "value": int(qualified),
        "passed": qualified >= config.TARGET_QUALIFIED_LISTS_MIN,
        "severity": "HARD",
        "target": f">= {config.TARGET_QUALIFIED_LISTS_MIN}",
    }

    return checks


# --------------------------------------------------------------------------- #
# Logging convenience
# --------------------------------------------------------------------------- #
def setup_logging(log_file: Path = config.LOG_FILE) -> None:
    """Configure root logger to write to both console and file.

    Idempotent: removes existing handlers before adding new ones.

    Args:
        log_file: Path to log file.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)
