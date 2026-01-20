"""Processing workflow - orchestration logic for content processing."""

from capabilities.processing.ai import ProcessingDeps
from capabilities.processing.openwebui_topics.tools import classify_topics
from capabilities.processing.schemas import (
    TopicClassificationRequest,
    TopicClassificationResponse,
)
from pydantic_ai import RunContext


async def classify_topics_workflow(
    request: TopicClassificationRequest,
    deps: ProcessingDeps | None = None,
) -> TopicClassificationResponse:
    """
    Execute topic classification workflow.

    Args:
        request: Topic classification request
        deps: Optional dependencies. If None, creates from settings

    Returns:
        Topic classification response
    """
    if deps is None:
        deps = ProcessingDeps.from_settings()

    await deps.initialize()
    try:
        # Create run context for tool execution
        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await classify_topics(ctx, request)
        return result
    finally:
        await deps.cleanup()


__all__ = [
    "classify_topics_workflow",
]
