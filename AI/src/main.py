"""
Book Retrieval Benchmark – CLI Entry Point

Usage:
    python -m src.main [COMMAND] [OPTIONS]

Commands:
    build-indexes      Build TF-IDF, BM25, and Dense retrieval indexes
    build-ground-truth Generate evaluation queries and LLM-judged qrels
    prune-qrels        Remove qrel entries that have 0 relevant books
    evaluate           Run all retrievers against qrels and produce results

Options common to all commands:
    --log-level TEXT   Logging level [default: INFO]
    --help             Show this message and exit.

Examples:
    # Build indexes on first 100 books (set in .env: MAX_BOOKS_TO_PROCESS=100)
    python -m src.main build-indexes

    # Generate ground truth with default settings from .env
    python -m src.main build-ground-truth

    # Override specific parameters without touching .env
    python -m src.main build-ground-truth --pool-size 50 --batch-size 5 --queries-per-book 1

    # Append new results to existing qrels.json (ignores done_query_ids filter)
    python -m src.main build-ground-truth --pool-size 30 --queries-per-book 2 --append

    # Remove qrel entries that have no relevant books
    python -m src.main prune-qrels

    # Evaluate all retrievers
    python -m src.main evaluate

    # Run full pipeline end-to-end
    python -m src.main build-indexes && python -m src.main build-ground-truth && python -m src.main evaluate
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

# Ensure the project root is importable when run with `python -m src.main`
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

app = typer.Typer(
    name="book-retrieval-benchmark",
    help="Book Retrieval Benchmark – build indexes, generate ground truth, and evaluate retrievers.",
    add_completion=False,
)

# ---------------------------------------------------------------------------
# Shared option
# ---------------------------------------------------------------------------
LogLevelOption = Annotated[
    str,
    typer.Option("--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR)."),
]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command("build-indexes")
def build_indexes_cmd(
    log_level: LogLevelOption = "INFO",
) -> None:
    """
    Build TF-IDF, BM25, and Dense (ChromaDB) retrieval indexes.

    Reads configuration from .env / environment variables.
    """
    from src.config.settings import get_settings  # noqa: PLC0415
    from src.pipelines.build_indexes import run  # noqa: PLC0415
    from src.utils.logging_config import setup_logging  # noqa: PLC0415

    settings = get_settings()
    setup_logging(log_level=log_level, log_dir=settings.log_dir)

    typer.echo(typer.style("Building retrieval indexes…", fg=typer.colors.CYAN, bold=True))
    try:
        run(settings=settings)
        typer.echo(typer.style("Indexes built successfully.", fg=typer.colors.GREEN, bold=True))
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED, bold=True), err=True)
        raise typer.Exit(code=1)


@app.command("build-ground-truth")
def build_ground_truth_cmd(
    log_level: LogLevelOption = "INFO",
    pool_size: Annotated[
        Optional[int],
        typer.Option(
            "--pool-size",
            help=(
                "Override GROUND_TRUTH_CANDIDATE_POOL: number of dense candidates retrieved "
                "per query for LLM judging. Larger = better recall, more API calls. "
                "[default: value from .env]"
            ),
            min=1,
        ),
    ] = None,
    batch_size: Annotated[
        Optional[int],
        typer.Option(
            "--batch-size",
            help=(
                "Override QUERY_GENERATION_BATCH_SIZE: number of books sent to the LLM "
                "in a single batch call. [default: value from .env]"
            ),
            min=1,
        ),
    ] = None,
    queries_per_book: Annotated[
        Optional[int],
        typer.Option(
            "--queries-per-book",
            help=(
                "Override QUERIES_PER_BOOK: number of search queries generated per book. "
                "[default: value from .env]"
            ),
            min=1,
        ),
    ] = None,
    append: Annotated[
        bool,
        typer.Option(
            "--append/--resume",
            help=(
                "--append: keep existing qrels.json entries and append ALL new results "
                "(ignores done_query_ids filter, useful for multi-run accumulation). "
                "--resume (default): skip queries already present in qrels.json."
            ),
        ),
    ] = False,
) -> None:
    """
    Generate evaluation queries via LLM and build LLM-judged qrels.json.

    Requires OPENAI_API_KEY in .env. Dense indexes must be built first.

    The three --pool-size / --batch-size / --queries-per-book flags let you
    override the corresponding .env values directly from the command line,
    which is handy for quick experiments without editing .env.

    Use --append to accumulate results across multiple runs (new entries are
    appended to the existing qrels.json without skipping any queries).
    """
    from src.config.settings import get_settings  # noqa: PLC0415
    from src.pipelines.build_ground_truth import run  # noqa: PLC0415
    from src.utils.logging_config import setup_logging  # noqa: PLC0415

    settings = get_settings()
    setup_logging(log_level=log_level, log_dir=settings.log_dir)

    # Apply CLI overrides (only when the flag was explicitly provided)
    if pool_size is not None:
        settings.ground_truth_candidate_pool = pool_size
        typer.echo(f"[override] ground_truth_candidate_pool = {pool_size}")
    if batch_size is not None:
        settings.query_generation_batch_size = batch_size
        typer.echo(f"[override] query_generation_batch_size = {batch_size}")
    if queries_per_book is not None:
        settings.queries_per_book = queries_per_book
        typer.echo(f"[override] queries_per_book = {queries_per_book}")
    if append:
        typer.echo(typer.style("[mode] --append: existing qrels kept, all new queries will be processed.", fg=typer.colors.YELLOW))

    if not settings.openai_api_key:
        typer.echo(
            typer.style("OPENAI_API_KEY is not set. Please add it to .env.", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(typer.style("Building ground truth (qrels.json)…", fg=typer.colors.CYAN, bold=True))
    typer.echo(
        f"  pool_size={settings.ground_truth_candidate_pool} | "
        f"batch_size={settings.query_generation_batch_size} | "
        f"queries_per_book={settings.queries_per_book} | "
        f"mode={'append' if append else 'resume'}"
    )
    try:
        qrels = run(settings=settings, append=append)
        typer.echo(
            typer.style(
                f"Ground truth built: {len(qrels)} qrel entries.",
                fg=typer.colors.GREEN,
                bold=True,
            )
        )
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED, bold=True), err=True)
        raise typer.Exit(code=1)


@app.command("evaluate")
def evaluate_cmd(
    log_level: LogLevelOption = "INFO",
) -> None:
    """
    Evaluate all retrievers (TF-IDF, BM25, Dense, Hybrid RRF, Reranking).

    Requires all indexes and qrels.json to be built first.
    """
    from src.config.settings import get_settings  # noqa: PLC0415
    from src.pipelines.evaluate_retrievers import run  # noqa: PLC0415
    from src.utils.logging_config import setup_logging  # noqa: PLC0415

    settings = get_settings()
    setup_logging(log_level=log_level, log_dir=settings.log_dir)

    typer.echo(typer.style("Running retriever evaluation…", fg=typer.colors.CYAN, bold=True))
    try:
        run(settings=settings)
        typer.echo(
            typer.style("Evaluation complete. See data/eval/evaluation_results.json", fg=typer.colors.GREEN, bold=True)
        )
    except Exception as exc:
        typer.echo(typer.style(f"Error: {exc}", fg=typer.colors.RED, bold=True), err=True)
        raise typer.Exit(code=1)


@app.command("prune-qrels")
def prune_qrels_cmd(
    log_level: LogLevelOption = "INFO",
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--execute",
            help="--dry-run (default): only report what would be removed without modifying the file. "
                 "--execute: actually remove the entries and overwrite qrels.json.",
        ),
    ] = True,
    no_backup: Annotated[
        bool,
        typer.Option(
            "--no-backup",
            help="Skip creating a .bak backup before overwriting qrels.json (only relevant with --execute).",
        ),
    ] = False,
) -> None:
    """
    Remove qrel entries with zero relevant books from qrels.json.

    Entries where ``relevant_isbns`` is empty are useless for evaluation
    (they contribute nothing to any metric) and inflate the query count.
    This command finds and optionally removes them.

    By default runs in --dry-run mode (safe preview).  Pass --execute to
    actually write the pruned file.  A .bak backup is created automatically
    unless --no-backup is given.
    """
    import json  # noqa: PLC0415
    import shutil  # noqa: PLC0415
    from src.config.settings import get_settings  # noqa: PLC0415
    from src.utils.logging_config import setup_logging  # noqa: PLC0415

    settings = get_settings()
    setup_logging(log_level=log_level, log_dir=settings.log_dir)

    qrels_path = Path(settings.eval_output_path) / "qrels.json"

    if not qrels_path.exists():
        typer.echo(
            typer.style(f"qrels.json not found at '{qrels_path}'.", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1)

    with open(qrels_path, encoding="utf-8") as fh:
        raw: list[dict] = json.load(fh)

    total = len(raw)
    kept   = [entry for entry in raw if entry.get("relevant_isbns")]
    pruned = total - len(kept)

    typer.echo(
        f"qrels.json: {total} entries total | "
        f"{typer.style(str(len(kept)), fg=typer.colors.GREEN)} with relevants | "
        f"{typer.style(str(pruned), fg=typer.colors.YELLOW)} with 0 relevant books"
    )

    if pruned == 0:
        typer.echo(typer.style("Nothing to prune.", fg=typer.colors.GREEN))
        return

    if dry_run:
        typer.echo(
            typer.style(
                f"[dry-run] Would remove {pruned} entries. Re-run with --execute to apply.",
                fg=typer.colors.YELLOW,
            )
        )
        return

    # --execute path
    if not no_backup:
        backup_path = qrels_path.with_suffix(".bak.json")
        shutil.copy2(qrels_path, backup_path)
        typer.echo(f"Backup saved to: {backup_path}")

    tmp_path = qrels_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(kept, fh, indent=2, default=str)
    tmp_path.replace(qrels_path)

    typer.echo(
        typer.style(
            f"Pruned {pruned} entries. qrels.json now has {len(kept)} entries.",
            fg=typer.colors.GREEN,
            bold=True,
        )
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
