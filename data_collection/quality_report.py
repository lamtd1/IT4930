"""Data-quality report for the crawl, judged by exactly what the team IR pipeline
consumes: `description` (retrieval text for all 5 models) and `categories` (the
evaluation ground-truth). Uses the same is_relevant() as run_pipeline.py so the
numbers reflect what evaluation will actually see.

Self-contained. Run from this folder:
    python quality_report.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "raw" / "google_search.jsonl"
TEST_QUERIES = HERE / "raw" / "test_queries.json"


def is_relevant(book_category: str, relevant_categories: list[str]) -> bool:
    """Verbatim from run_pipeline.py lines 234-237."""
    if not isinstance(book_category, str):
        return False
    bc = book_category.lower()
    return any(rc.lower() in bc or bc in rc.lower() for rc in relevant_categories)


def pct(n: int, d: int) -> str:
    return f"{n:,} ({100*n/d:.1f}%)" if d else "0"


def main() -> None:
    recs = [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").split("\n") if l.strip()]
    n = len(recs)
    print(f"=== CORPUS: {n:,} records ===\n")

    has_isbn = [r for r in recs if (r.get("isbn_13") or "").strip()]
    survivors = {r["isbn_13"]: r for r in recs
                 if (r.get("isbn_13") or "").strip()
                 and len((r.get("description") or "").split()) >= 10}
    print("--- survives pipeline filters (isbn13 + desc>=10w + dedup) ---")
    print(f"  has isbn_13        : {pct(len(has_isbn), n)}")
    print(f"  FINAL usable books : {len(survivors):,}\n")

    wc = sorted(len((r.get("description") or "").split()) for r in recs)
    def qtl(p): return wc[int(p * (len(wc) - 1))]
    print("--- description word count ---")
    print(f"  min {wc[0]} | p25 {qtl(.25)} | median {qtl(.5)} | p75 {qtl(.75)} | max {wc[-1]}")
    print(f"  >=20w {pct(sum(w>=20 for w in wc), n)} | >=50w {pct(sum(w>=50 for w in wc), n)} "
          f"| >=100w {pct(sum(w>=100 for w in wc), n)}\n")

    has_cat = [r for r in recs if (r.get("categories") or "").strip()]
    cat_counter = Counter(c.strip() for r in has_cat for c in r["categories"].split("|") if c.strip())
    print("--- categories coverage ---")
    print(f"  non-empty categories: {pct(len(has_cat), n)}")
    print(f"  distinct categories : {len(cat_counter):,}")
    for cat, c in cat_counter.most_common(15):
        print(f"    {c:>5}  {cat}")
    print()

    if TEST_QUERIES.exists():
        queries = json.loads(TEST_QUERIES.read_text(encoding="utf-8"))
        usable = list(survivors.values())
        counts = sorted(sum(1 for r in usable if is_relevant(r.get("categories") or "", it.get("relevant_categories", [])))
                        for it in queries)
        print(f"--- per-query relevant coverage ({len(queries)} queries / {len(usable):,} books) ---")
        print(f"  relevant books per query: min {counts[0]} | median {counts[len(counts)//2]} | max {counts[-1]}")
        print(f"  queries with <30 relevant: {sum(c < 30 for c in counts)}")

    langs = Counter(r.get("language") or "?" for r in recs)
    print(f"\n--- sanity ---")
    print(f"  languages   : {dict(langs)}")
    print(f"  empty title : {sum(1 for r in recs if not (r.get('title') or '').strip())}")


if __name__ == "__main__":
    main()
