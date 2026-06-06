"""Split the team's 50 eval queries into a dev set (tune) and a test set (final).

Why: hyper-parameters (RRF k, BM25 k1/b, rerank pool size...) must be tuned on a
held-out *dev* set, never on the *test* set used for the reported numbers —
otherwise the score is optimistic (tuning-on-test leakage).

Split = 30 dev / 20 test, stratified by primary genre so both sets cover the
same genres, deterministic (fixed SEED). Output files are plain JSON arrays in
the SAME shape as test_queries.json, so they drop straight into the team eval.

Run from the _team_repo directory:
    python data_collection/split_queries.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "AI" / "data" / "eval" / "test_queries.json"
OUT_DIR = PROJECT_ROOT / "AI" / "data" / "eval"

SEED = 42
N_TEST = 20  # 50 - 20 = 30 dev
GENERIC = {"fiction", "non-fiction", "nonfiction"}


def stratum(query: dict) -> str:
    "Primary genre = first relevant_category that is not the generic 'Fiction'."
    cats = query["relevant_categories"]
    for c in cats:
        if c.strip().lower() not in GENERIC:
            return c
    return cats[0]


def main() -> None:
    queries = json.loads(SRC.read_text(encoding="utf-8"))
    n = len(queries)
    test_frac = N_TEST / n

    # Group by genre, shuffle each group deterministically.
    groups: dict[str, list[dict]] = {}
    for q in queries:
        groups.setdefault(stratum(q), []).append(q)

    rng = random.Random(SEED)
    test: list[dict] = []
    # Largest genres first so proportional rounding is stable; tie-break by name.
    for genre in sorted(groups, key=lambda g: (-len(groups[g]), g)):
        items = groups[genre][:]
        rng.shuffle(items)
        k = round(len(items) * test_frac)  # share of this genre going to test
        test.extend(items[:k])

    # Correct rounding drift to hit exactly N_TEST.
    test_keys = {q["query"] for q in test}
    remaining = [q for q in queries if q["query"] not in test_keys]
    rng.shuffle(remaining)
    while len(test) < N_TEST:
        test.append(remaining.pop())
    while len(test) > N_TEST:
        moved = test.pop()
        remaining.append(moved)

    test_keys = {q["query"] for q in test}
    dev = [q for q in queries if q["query"] not in test_keys]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "queries_dev.json").write_text(
        json.dumps(dev, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "queries_test.json").write_text(
        json.dumps(test, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"seed={SEED} | dev={len(dev)} | test={len(test)} (from {n})")
    print("genre balance (genre: dev/test):")
    for genre in sorted(groups, key=lambda g: (-len(groups[g]), g)):
        d = sum(1 for q in dev if stratum(q) == genre)
        t = sum(1 for q in test if stratum(q) == genre)
        print(f"  {genre:28s} {d}/{t}")


if __name__ == "__main__":
    main()
