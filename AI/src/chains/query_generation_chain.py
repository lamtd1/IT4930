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
You are an expert information retrieval query generator.

Your task is to generate realistic search queries for evaluating book retrieval systems.

The objective is NOT to describe books.

The objective is to simulate how real users search for books in search engines, online bookstores, recommendation systems, and library catalogs.

For EACH book in the input list:

1. Generate exactly {queries_per_book} queries.

2. Queries must be diverse and represent different search behaviors.

3. Cover multiple query styles whenever possible:

   * Keyword query
     Examples:

     * wizard school
     * detective mystery
     * historical romance

   * Topic query
     Examples:

     * world cup statistics
     * grief and healing
     * cold war espionage

   * Genre/theme query
     Examples:

     * dystopian fiction
     * coming of age fantasy
     * psychological thriller

   * Recommendation query
     Examples:

     * books like harry potter
     * mystery novels similar to agatha christie

   * Natural language query
     Examples:

     * books about a young wizard learning magic
     * novels set in ancient rome with political intrigue

4. Query length should vary:

   * SHORT: 1–4 words
   * MEDIUM: 5–10 words
   * LONG: 11+ words

5. Queries should resemble genuine search inputs.

6. Prefer concise search intent rather than detailed descriptions.

7. Users rarely type complete plot summaries.
   Avoid generating summary-like queries.

8. DO NOT:

   * copy the title
   * closely paraphrase the title
   * mention ISBNs
   * mention author names unless a real user would naturally search by author
   * generate book summaries

9. Good queries should help distinguish relevant books from irrelevant books.

GOOD:

* wizard school
* books like harry potter
* detective mystery london
* historical fiction ancient rome
* grief and healing novels
* books about political intrigue in royal courts

BAD:

* a coming of age story about a young wizard discovering his destiny
* an emotional tale of friendship and personal growth
* a fantasy adventure following a brave hero on a dangerous journey

Return a JSON object matching the BatchQueryResponse schema.

The isbn13 field in each BookQueries entry must exactly match the isbn13 from the input.
"""

_HUMAN_PROMPT = """\
Generate exactly {queries_per_book} realistic search queries for each of the following {num_books} book(s):

{books_text}

Requirements:

- Mix SHORT, MEDIUM, and LONG queries
- Use diverse search intents
- Prefer search keywords over full sentences
- Avoid plot summaries
- Avoid repeating the title
- Focus on searchable concepts:
  * genre
  * themes
  * topics
  * setting
  * character archetypes
  * tropes
  * emotional tone

Think like a user searching for a book, not a reviewer describing a book.

Return valid JSON only.
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
