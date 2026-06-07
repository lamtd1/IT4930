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

Your task is to generate realistic search queries that a user might type into a book search engine.

For EACH book in the list:
1. Generate exactly {queries_per_book} queries
2. Queries must vary in length:
   - At least 1 SHORT query (1–4 words, e.g., "dragon fantasy adventure")
   - At least 1 MEDIUM query (5–10 words, e.g., "coming of age story in a small southern town")
   - At least 1 LONG query (11+ words, e.g., "psychological thriller where the protagonist cannot trust her own memory after a traumatic accident")
3. DO NOT repeat or closely paraphrase the book title
4. Focus on: themes, plot elements, characters, emotional tone, setting, topics
5. Make queries feel like genuine user searches – not descriptions of the book

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
