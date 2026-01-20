"""Workflow functions for the Linear Researcher agent.

Convenience functions that initialize dependencies and run the agent.
"""

import logging
import uuid
from typing import Any

from workflows.research.deep_research.agent import linear_researcher_agent
from workflows.research.deep_research.dependencies import DeepResearchDeps

logger = logging.getLogger(__name__)


async def run_linear_research(query: str, session_id: str | None = None, http_client=None) -> Any:
    """
    Run the Linear Researcher agent on a query.

    This function:
    1. Initializes dependencies
    2. Runs the agent with the query
    3. Cleans up dependencies
    4. Returns the structured response

    Args:
        query: Research question to answer
        session_id: Optional session ID (will generate if not provided)
        http_client: Optional httpx client (will create if not provided)

    Returns:
        RunResult containing ResearchResponse with answer, sources, and citations

    Example:
        ```python
        result = await run_linear_research("Who is the CEO of Anthropic?")
        print(result.data.answer)
        print(result.data.sources)
        ```
    """
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    # Initialize dependencies
    deps = DeepResearchDeps.from_settings(http_client=http_client, session_id=session_id)

    try:
        # Initialize all connections
        await deps.initialize()
        logger.info(f"Initialized dependencies for session {session_id}")

        # Run the agent
        logger.info(f"Running linear researcher agent with query: {query}")
        result = await linear_researcher_agent.run(query, deps=deps)

        logger.info(f"Agent completed. Answer length: {len(result.data.answer)}")
        return result

    except Exception:
        logger.exception("Error running linear research")
        raise

    finally:
        # Cleanup
        await deps.cleanup()
        logger.info(f"Cleaned up dependencies for session {session_id}")
