"""Query rewriting for better retrieval."""

import logging

import openai
from app.capabilities.retrieval.mongo_rag.config import config

logger = logging.getLogger(__name__)


async def rewrite_query(query: str, llm_client: openai.AsyncOpenAI | None = None) -> str:
    """
    Rewrite query for better retrieval.

    Handles ambiguous or unclear queries by rewriting them to be more
    specific and searchable.

    Args:
        query: Original query
        llm_client: Optional OpenAI client

    Returns:
        Rewritten query
    """
    if not query or not query.strip():
        return query

    if not llm_client:
        llm_client = openai.AsyncOpenAI(api_key=config.llm_api_key, base_url=config.llm_base_url)

    try:
        rewrite_prompt = f"""Rewrite this query to be more specific and searchable for a knowledge base.
Keep the original intent but make it clearer and more focused.

Original query: {query}

Provide only the rewritten query, no additional text."""

        response = await llm_client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": rewrite_prompt}],
            temperature=0.2,
        )

        rewritten = response.choices[0].message.content or query
        return rewritten.strip()

    except Exception as e:
        logger.warning(f"Error rewriting query: {e}")
        return query
