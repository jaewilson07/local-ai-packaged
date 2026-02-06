"""Knowledge project agent for event extraction."""

import logging

from app.capabilities.knowledge_graph.knowledge.dependencies import KnowledgeDeps
from app.capabilities.knowledge_graph.knowledge.tools import (
    extract_events_from_content,
    extract_events_from_crawled_pages,
)
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, StateDeps

from app.core.llm import get_llm_model

logger = logging.getLogger(__name__)


class KnowledgeState(BaseModel):
    """Minimal shared state for the Knowledge agent."""


KNOWLEDGE_SYSTEM_PROMPT = """You are a knowledge extraction agent that extracts structured event information from web content.

You can:
- Extract events from web content (HTML, markdown, text)
- Extract events from multiple crawled pages
- Use regex-based extraction (fast) or LLM-based extraction (accurate)
- Return structured event data with title, date, time, location, instructor

Always extract events accurately and provide complete information when available.
"""


knowledge_agent = Agent(
    get_llm_model(), deps_type=StateDeps[KnowledgeState], system_prompt=KNOWLEDGE_SYSTEM_PROMPT
)


@knowledge_agent.tool
async def extract_events_tool(
    ctx: RunContext[StateDeps[KnowledgeState]],
    content: str = Field(..., description="Web content (HTML, markdown, or plain text)"),
    url: str | None = Field(None, description="Source URL"),
    use_llm: bool | None = Field(None, description="Use LLM for extraction (overrides default)"),
) -> str:
    """
    Extract event information from web content.

    Extracts structured event data (title, date, time, location, instructor) from web content.
    Can use fast regex-based extraction or accurate LLM-based extraction.

    Args:
        ctx: Agent runtime context
        content: Web content to extract events from
        url: Source URL (optional)
        use_llm: Whether to use LLM for extraction (optional, overrides default)

    Returns:
        JSON string containing extracted events
    """
    # Initialize dependencies
    deps = KnowledgeDeps.from_settings(use_llm=use_llm)
    await deps.initialize()

    try:
        # Create RunContext for tools
        from pydantic_ai import RunContext as ToolRunContext

        tool_ctx = ToolRunContext(deps=deps, state={}, agent=None, run_id="")

        # Call underlying capability
        events = await extract_events_from_content(tool_ctx, content, url, use_llm)

        # Format result
        import json

        return json.dumps(
            {"success": True, "events": [event.dict() for event in events], "count": len(events)},
            indent=2,
        )
    finally:
        await deps.cleanup()


@knowledge_agent.tool
async def extract_events_from_crawled_tool(
    ctx: RunContext[StateDeps[KnowledgeState]],
    crawled_pages: list[dict] = Field(..., description="List of crawled page dictionaries"),
    use_llm: bool | None = Field(None, description="Use LLM for extraction (overrides default)"),
) -> str:
    """
    Extract events from multiple crawled pages.

    Processes multiple crawled pages and extracts event information from each one.

    Args:
        ctx: Agent runtime context
        crawled_pages: List of crawled page dictionaries with 'content' and 'url' keys
        use_llm: Whether to use LLM for extraction (optional, overrides default)

    Returns:
        JSON string containing extracted events
    """
    # Initialize dependencies
    deps = KnowledgeDeps.from_settings(use_llm=use_llm)
    await deps.initialize()

    try:
        # Create RunContext for tools
        from pydantic_ai import RunContext as ToolRunContext

        tool_ctx = ToolRunContext(deps=deps, state={}, agent=None, run_id="")

        # Call underlying capability
        events = await extract_events_from_crawled_pages(tool_ctx, crawled_pages, use_llm)

        # Format result
        import json

        return json.dumps(
            {"success": True, "events": [event.dict() for event in events], "count": len(events)},
            indent=2,
        )
    finally:
        await deps.cleanup()
