"""
Query Generation LangChain Chain.

Generates realistic search queries for a BATCH of books in a single LLM call
to minimise API round-trips and token overhead.

Chain input:
    A formatted list of books (title, isbn13, description, categories).

Chain output (structured):
    ``BatchQueryResponse`` – one ``BookQueries`` entry per input book.

Key design decisions:
- Batch generation: N books → 1 API call (configurable batch size)
- No global LLM state: factory function injects settings
- ``llm.with_structured_output()`` for reliable Pydantic parsing
- Queries vary in length: short / medium / long
- Queries avoid repeating the book title verbatim
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from src.config.settings import Settings
from src.schemas.query import BatchQueryResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are an expert book search query generator for an information retrieval benchmark.

Your task is to generate SEMANTIC search queries that test whether a retrieval system understands 
themes, emotions, and plot concepts – not just keyword matching.

CRITICAL RULES - To avoid bias toward keyword-matching models:
1. DO NOT use category/genre terms directly (e.g., avoid "mystery", "fantasy", "thriller" as standalone)
2. DO NOT generate short keyword phrases (≤3 words)
3. DO generate DESCRIPTIVE semantic queries that convey themes/emotions/plot
4. DO generate SYNONYM VARIATIONS (same book, different wording)
5. DO ensure queries would match MULTIPLE semantically similar books, not just keyword-exact matches

For EACH book in the list:
1. Generate exactly {queries_per_book} queries
2. Query strategy:
   - THEME-BASED: "a story about X overcoming Y" (semantic, not keyword)
   - EMOTION-BASED: "narratives exploring X emotion" (tests understanding)
   - PLOT-BASED: "protagonist journey from X to Y" (descriptive, not categorical)
   - SYNONYM: Paraphrase the same book concept differently (e.g., 
     "detective solving a case" vs "investigator uncovering hidden truth")
3. Query length: 5-20 words (avoid single-phrase keywords)
4. DO NOT repeat or closely paraphrase the book title
5. Focus on: emotional journey, thematic elements, character struggles, philosophical questions
6. Make queries feel like genuine user searches from someone describing what they want to read

EXAMPLES OF WHAT TO GENERATE:
   ✓ "a coming-of-age story about self-discovery in a small community"
   ✓ "narratives exploring the tension between duty and personal freedom"
   ✓ "stories where characters must navigate moral ambiguity and consequences"
   ✗ "coming of age" (too short, keyword-like)
   ✗ "mystery" (single genre, not descriptive)
   ✗ "detective solving crime" (too similar to original title reference)

Return a JSON object matching the BatchQueryResponse schema with one entry per book.
The `isbn13` field in each BookQueries entry must match the isbn13 from the input.
"""

_HUMAN_PROMPT = """\
Generate {queries_per_book} search queries for each of the following {num_books} book(s):

{books_text}

Remember:
- Vary query length (short / medium / long)
- Do not repeat the book title
- Focus on themes, emotions, plot, and characters
"""


def build_query_generation_chain(settings: Settings) -> Runnable:
    """
    Build and return a LangChain query generation chain.

    The chain takes a dict with keys:
        - ``queries_per_book`` (int): target queries per book
        - ``num_books`` (int): number of books in this batch
        - ``books_text`` (str): formatted multi-book text block

    And returns a ``BatchQueryResponse`` Pydantic object.

    Args:
        settings: Application settings (used for model name, temperature, API key).

    Returns:
        A LangChain ``Runnable`` that outputs ``BatchQueryResponse``.
    """
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.temperature,
        api_key=settings.openai_api_key,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            ("human", _HUMAN_PROMPT),
        ]
    )

    chain: Runnable = prompt | llm.with_structured_output(BatchQueryResponse)

    logger.info(
        "Query generation chain built: model=%s, temp=%.1f",
        settings.openai_model,
        settings.temperature,
    )

    return chain


def format_books_for_prompt(books: list[Any]) -> str:
    """
    Format a list of ``BookInfo`` objects into a readable text block for the LLM.

    Args:
        books: List of ``BookInfo`` instances.

    Returns:
        Multi-line string with numbered book entries.
    """
    lines: list[str] = []
    for i, book in enumerate(books, start=1):
        lines.append(f"Book {i}:")
        lines.append(f"  ISBN-13: {book.isbn13}")
        lines.append(f"  Title: {book.title}")
        if book.categories:
            lines.append(f"  Categories: {book.categories}")
        lines.append(f"  Description: {book.description[:600]}")  # truncate to ~150 tokens
        lines.append("")  # blank line between books
    return "\n".join(lines)
