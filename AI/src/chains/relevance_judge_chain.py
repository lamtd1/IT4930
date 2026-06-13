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
You are a strict relevance judge for an information retrieval benchmark.

Your task is to determine whether a candidate book satisfies the user's search intent.

Focus on intent matching, not merely thematic similarity.

Scoring rubric:

2 - HIGHLY RELEVANT

* The book directly satisfies the query.
* The main topic, genre, subject, setting, character type, or information need closely matches the query.
* A user issuing this query would be very likely to click or select this book.

1 - SOMEWHAT RELEVANT

* The book has meaningful overlap with the query.
* It shares some themes, genre, topics, or concepts.
* However, it does not fully satisfy the query intent.
* A user might consider the book as an alternative, but it is not an obvious match.

0 - NOT RELEVANT

* The book does not satisfy the query intent.
* Similarity is weak, generic, incidental, or based only on broad genre overlap.
* A user searching with this query would be unlikely to find the book useful.

Important guidelines:

* Judge based on the query intent, not overall book quality.
* Do not give score 1 simply because two books share a broad genre.
* Prefer score 0 when overlap is weak or indirect.
* Use score 2 sparingly and only for strong matches.
* Be conservative when assigning relevance.

Always provide a concise reason (1-2 sentences).
"""

_HUMAN_PROMPT = """\
Search Query:
{query}

Candidate Book:

Title: {book_title}

Description:
{book_description}

Evaluate whether this book satisfies the user's search intent.

Return:

* score (0, 1, or 2)
* concise reason
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
