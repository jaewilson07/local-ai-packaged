"""Core capability tools for Knowledge project."""

import logging
from typing import Any

from app.capabilities.knowledge_graph.knowledge.dependencies import KnowledgeDeps
from app.capabilities.knowledge_graph.knowledge.event_extractor import EventExtractor, ExtractedEvent
from pydantic_ai import RunContext

logger = logging.getLogger(__name__)


async def extract_events_from_content(
    ctx: RunContext[KnowledgeDeps],
    content: str,
    url: str | None = None,
    use_llm: bool | None = None,
) -> list[ExtractedEvent]:
    """
    Extract event information from web content.

    Args:
        ctx: Agent runtime context with dependencies
        content: Web content (HTML, markdown, or plain text)
        url: Source URL (optional)
        use_llm: Whether to use LLM for extraction (overrides deps.use_llm if provided)

    Returns:
        List of extracted events
    """
    deps = ctx.deps
    use_llm_flag = use_llm if use_llm is not None else deps.use_llm

    try:
        extractor = EventExtractor(use_llm=use_llm_flag)
        events = extractor.extract_events_from_content(content=content, url=url)

        logger.info(
            "events_extracted",
            extra={"count": len(events), "use_llm": use_llm_flag, "has_url": bool(url)},
        )

        return events
    except Exception as e:
        logger.exception("event_extraction_failed", extra={"error": str(e)})
        raise


async def extract_events_from_crawled_pages(
    ctx: RunContext[KnowledgeDeps], crawled_pages: list[dict[str, Any]], use_llm: bool | None = None
) -> list[ExtractedEvent]:
    """
    Extract events from multiple crawled pages.

    Args:
        ctx: Agent runtime context with dependencies
        crawled_pages: List of crawled page dictionaries with 'content' and 'url' keys
        use_llm: Whether to use LLM for extraction (overrides deps.use_llm if provided)

    Returns:
        List of extracted events
    """
    deps = ctx.deps
    use_llm_flag = use_llm if use_llm is not None else deps.use_llm

    try:
        extractor = EventExtractor(use_llm=use_llm_flag)
        events = extractor.extract_events_from_crawled_pages(crawled_pages)

        logger.info(
            "events_extracted_from_crawled",
            extra={
                "count": len(events),
                "pages_processed": len(crawled_pages),
                "use_llm": use_llm_flag,
            },
        )

        return events
    except Exception as e:
        logger.exception("event_extraction_from_crawled_failed", extra={"error": str(e)})
        raise
