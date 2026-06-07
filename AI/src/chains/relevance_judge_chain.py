"""
Relevance Judge LangChain Chain.

Uses an LLM-as-judge approach to score the relevance of a single
(query, book) pair.

Chain input:
    - ``query``            (str): the search query
    - ``book_title``       (str): the candidate book's title
    - ``book_description`` (str): the candidate book's description

Chain output (structured):
    ``RelevanceScore`` with:
    - ``score`` (int):  0 = not relevant, 1 = somewhat relevant, 2 = highly relevant
    - ``reason`` (str): 1-3 sentence justification for auditing / debugging

Key design decisions:
- No global LLM state: factory function injects settings
- ``llm.with_structured_output()`` for reliable Pydantic parsing
- ``reason`` field mandated for reproducibility and debugging
- Strict scoring rubric in prompt to minimise ambiguity
"""

from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from src.config.settings import Settings
from src.schemas.relevance import RelevanceScore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are a strict relevance judge for a book retrieval benchmark.

Your task is to evaluate whether a book is relevant to a given search query.

Scoring rubric:
  0 - NOT RELEVANT: The book does not match the query's intent, themes, or subject.
      Use this when the book is clearly off-topic.

  1 - SOMEWHAT RELEVANT: The book partially matches the query (e.g., shares a theme
      or genre but not the specific topic, or is tangentially related).
      Use this when a user might consider it but it is not a strong match.

  2 - HIGHLY RELEVANT: The book directly matches the query's intent.
      A user searching with this query would very likely want this book.
      Use this for clear, strong matches.

Always provide a concise reason (1-3 sentences) explaining your judgment.
"""

_HUMAN_PROMPT = """\
Search Query: {query}

Candidate Book:
  Title: {book_title}
  Description: {book_description}

Evaluate the relevance of this book to the search query using the scoring rubric.
"""


def build_relevance_judge_chain(settings: Settings) -> Runnable:
    """
    Build and return a LangChain relevance judge chain.

    The chain takes a dict with keys:
        - ``query``            (str): the search query
        - ``book_title``       (str): candidate book title
        - ``book_description`` (str): candidate book description (may be truncated)

    And returns a ``RelevanceScore`` Pydantic object.

    Args:
        settings: Application settings (model name, temperature, API key).

    Returns:
        A LangChain ``Runnable`` that outputs ``RelevanceScore``.
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

    chain: Runnable = prompt | llm.with_structured_output(RelevanceScore)

    logger.info(
        "Relevance judge chain built: model=%s, temp=%.1f",
        settings.openai_model,
        settings.temperature,
    )

    return chain
