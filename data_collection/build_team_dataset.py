"""Build the team-schema dataset from the Google-Books crawl.

Reads the raw crawl (raw/google_search.jsonl) and writes books.csv in the EXACT
12-column schema the team pipeline (_team_repo/AI/run_pipeline.py) expects, ready
to drop in as `data/raw/books.csv`.

Self-contained (only stdlib + pandas). Run from this folder:
    python build_team_dataset.py

The pipeline does its own cleaning (HTML strip, dedup, outlier/length filters),
so this step only does the lossless field mapping + the one filter the pipeline
hard-requires anyway: a valid 13-digit ISBN-13 (it is the pipeline's primary key
and ChromaDB id, and rows without it are dropped — run_pipeline.py:42-43).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE / "raw" / "google_search.jsonl"
OUT = HERE / "books.csv"

# crawl field  ->  team books.csv column   (language/publisher dropped: unused)
COLUMN_MAP = {
    "isbn_13": "isbn13",
    "isbn_10": "isbn10",
    "title": "title",
    "subtitle": "subtitle",
    "authors": "authors",
    "categories": "categories",
    "thumbnail": "thumbnail",
    "description": "description",
    "published_year": "published_year",
    "average_rating": "average_rating",
    "page_count": "num_pages",
    "ratings_count": "ratings_count",
}
FINAL_COLUMNS = [
    "isbn13", "isbn10", "title", "subtitle", "authors", "categories",
    "thumbnail", "description", "published_year", "average_rating",
    "num_pages", "ratings_count",
]


def _valid_isbn13(value: object) -> bool:
    s = str(value or "").strip()
    return len(s) == 13 and s.isdigit()


def main() -> None:
    # split on "\n" (NOT splitlines(): it also breaks on U+2028/U+2029, which
    # JSON permits raw inside strings — Google descriptions occasionally have them).
    records = [json.loads(line) for line in SRC.read_text(encoding="utf-8").split("\n") if line.strip()]
    df = pd.DataFrame(records)

    # Keep only rows the pipeline could use anyway: a valid 13-digit ISBN-13.
    df = df[df["isbn_13"].apply(_valid_isbn13)].copy()
    df = df.rename(columns=COLUMN_MAP)

    # ISBN-13 as integer so pandas re-reads it as int64 (no "...e+12"/".0").
    df["isbn13"] = df["isbn13"].astype("int64")
    # Authors: the team/Kaggle convention separates with ';' (display only).
    df["authors"] = df["authors"].fillna("").str.replace("|", ";", regex=False)
    # Dedup on the primary key, keep the richest description.
    df["_len"] = df["description"].fillna("").str.split().str.len()
    df = df.sort_values("_len", ascending=False).drop_duplicates("isbn13", keep="first")

    # Strip raw line-separator chars from text fields so any CSV/JSON reader
    # downstream (e.g. the team's pandas) parses cleanly.
    for col in ["title", "subtitle", "authors", "categories", "description"]:
        df[col] = df[col].str.replace(chr(0x2028), chr(0x20)).str.replace(chr(0x2029), chr(0x20))

    df = df[FINAL_COLUMNS].sort_values("isbn13").reset_index(drop=True)
    df.to_csv(OUT, index=False, encoding="utf-8")

    print(f"wrote {OUT.name}: {len(df):,} books x {len(FINAL_COLUMNS)} cols")
    print(f"  categories non-empty: {df['categories'].fillna('').str.strip().astype(bool).mean()*100:.1f}%")
    print(f"  median description words: {int(df['description'].fillna('').str.split().str.len().median())}")


if __name__ == "__main__":
    main()
