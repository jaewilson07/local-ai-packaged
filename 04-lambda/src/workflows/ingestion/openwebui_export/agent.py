"""Main Open WebUI Export agent implementation."""

from pydantic_ai import Agent, RunContext
from workflows.ingestion.openwebui_export.dependencies import OpenWebUIExportDeps
from workflows.ingestion.openwebui_export.models import (
    ConversationExportRequest,
    ConversationMessage,
)
from workflows.ingestion.openwebui_export.tools import (
    export_conversation,
    get_conversation,
    get_conversations,
)

from shared.llm import get_llm_model as _get_openwebui_export_model

# Create the Open WebUI export agent with OpenWebUIExportDeps
openwebui_export_agent = Agent(
    _get_openwebui_export_model(),
    deps_type=OpenWebUIExportDeps,
    system_prompt=(
        "You are an expert assistant for exporting Open WebUI conversations to MongoDB RAG. "
        "You help users export conversations, retrieve conversation data, and manage conversation exports. "
        "Always provide clear, helpful responses about export status and results."
    ),
)


# Register tools - create wrapper functions that bridge StateDeps to OpenWebUIExportDeps
@openwebui_export_agent.tool
async def export_conversation_tool(
    ctx: RunContext[OpenWebUIExportDeps],
    conversation_id: str,
    messages: list[ConversationMessage],
    user_id: str | None = None,
    title: str | None = None,
    topics: list[str] | None = None,
    metadata: dict | None = None,
) -> str:
    """
    Export a conversation from Open WebUI to MongoDB RAG system.

    This tool takes a conversation (messages, metadata, topics) and exports it
    to the MongoDB RAG system where it becomes searchable via vector search.

    Args:
        ctx: Agent runtime context with state dependencies
        conversation_id: Open WebUI conversation ID
        user_id: User ID (optional)
        title: Conversation title (optional)
        messages: List of conversation messages
        topics: Conversation topics (optional)
        metadata: Additional metadata (optional)

    Returns:
        String describing the export result
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    request = ConversationExportRequest(
        conversation_id=conversation_id,
        user_id=user_id,
        title=title,
        messages=messages,
        topics=topics,
        metadata=metadata or {},
    )

    # Create RunContext for tools.py
    tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
    result = await export_conversation(tool_ctx, request)

    if result["success"]:
        return (
            f"Conversation exported successfully. "
            f"Document ID: {result['document_id']}, "
            f"Chunks created: {result['chunks_created']}"
        )
    return f"Export failed: {result['message']}"


@openwebui_export_agent.tool
async def get_conversations_tool(
    ctx: RunContext[OpenWebUIExportDeps],
    user_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> str:
    """
    Get list of conversations from Open WebUI.

    Args:
        ctx: Agent runtime context with state dependencies
        user_id: Filter by user ID (optional)
        limit: Maximum number of conversations to return (default: 100)
        offset: Offset for pagination (default: 0)

    Returns:
        String describing the conversations retrieved
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
    result = await get_conversations(tool_ctx, user_id, limit, offset)

    if "error" in result:
        return f"Failed to get conversations: {result['error']}"

    return (
        f"Retrieved {result['total']} conversations. "
        f"Limit: {result['limit']}, Offset: {result['offset']}"
    )


@openwebui_export_agent.tool
async def get_conversation_tool(ctx: RunContext[OpenWebUIExportDeps], conversation_id: str) -> str:
    """
    Get a specific conversation by ID from Open WebUI.

    Args:
        ctx: Agent runtime context with state dependencies
        conversation_id: Conversation ID

    Returns:
        String describing the conversation data
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
    result = await get_conversation(tool_ctx, conversation_id)

    if "error" in result:
        return f"Failed to get conversation: {result['error']}"

    return f"Retrieved conversation {conversation_id}"
