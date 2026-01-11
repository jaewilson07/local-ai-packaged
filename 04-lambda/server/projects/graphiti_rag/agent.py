"""Main Graphiti RAG agent implementation."""

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from server.projects.graphiti_rag.dependencies import GraphitiRAGDeps
from server.projects.graphiti_rag.tools import (
    parse_github_repository,
    query_knowledge_graph,
    search_graphiti_knowledge_graph,
    validate_ai_script,
)
from server.projects.shared.llm import get_llm_model as _get_graphiti_model


class GraphitiRAGState(BaseModel):
    """State for Graphiti RAG agent operations."""


# Create agent instance with GraphitiRAGDeps
# Changed from state_type=GraphitiRAGState to deps_type=GraphitiRAGDeps to match tool requirements
agent = Agent(
    model=_get_graphiti_model(),
    system_prompt="""You are a Graphiti RAG assistant that helps users search knowledge graphs,
parse GitHub repositories, validate AI-generated scripts, and query code structure.

You have access to:
- Graphiti knowledge graph search (semantic + keyword + graph traversal)
- GitHub repository parsing (extracts code structure to Neo4j)
- AI script validation (checks for hallucinations against knowledge graph)
- Knowledge graph queries (explore repositories and code structure)

Use the available tools to help users with their queries.""",
    deps_type=GraphitiRAGDeps,
)


@agent.tool
async def search_graphiti(
    ctx: RunContext[GraphitiRAGDeps],
    query: str = Field(..., description="Search query text"),
    match_count: int = Field(10, ge=1, le=50, description="Number of results to return"),
) -> str:
    """
    Search the Graphiti knowledge graph for entities and relationships.

    Performs hybrid search (semantic + keyword + graph traversal) to find
    relevant facts and relationships in the knowledge graph.

    Args:
        query: Search query text
        match_count: Maximum number of results to return (1-50)

    Returns:
        JSON string with search results
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    try:
        # Create RunContext for tools

        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await search_graphiti_knowledge_graph(tool_ctx, query, match_count)

        import json

        return json.dumps(result, indent=2)
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.exception(f"Error in search_graphiti tool: {e}")
        return f"Error: {e!s}"


@agent.tool
async def parse_repository(
    ctx: RunContext[GraphitiRAGDeps],
    repo_url: str = Field(..., description="GitHub repository URL (must end with .git)"),
) -> str:
    """
    Parse a GitHub repository into the Neo4j knowledge graph.

    Extracts code structure (classes, methods, functions, imports) for hallucination
    detection. Creates nodes and relationships directly in Neo4j.

    Args:
        repo_url: GitHub repository URL (must end with .git)

    Returns:
        JSON string with parse results
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await parse_github_repository(tool_ctx, repo_url)

        import json

        return json.dumps(result, indent=2)
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.exception(f"Error in parse_repository tool: {e}")
        return f"Error: {e!s}"


@agent.tool
async def validate_script(
    ctx: RunContext[GraphitiRAGDeps],
    script_path: str = Field(..., description="Absolute path to the Python script to validate"),
) -> str:
    """
    Check an AI-generated Python script for hallucinations using the knowledge graph.

    Validates imports, method calls, class instantiations, and function calls against
    real repository data stored in Neo4j.

    Args:
        script_path: Absolute path to the Python script to validate

    Returns:
        JSON string with validation results
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await validate_ai_script(tool_ctx, script_path)

        import json

        return json.dumps(result, indent=2)
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.exception(f"Error in validate_script tool: {e}")
        return f"Error: {e!s}"


@agent.tool
async def query_graph(
    ctx: RunContext[GraphitiRAGDeps],
    command: str = Field(
        ..., description="Command to execute (e.g., 'repos', 'explore <repo>', 'query <cypher>')"
    ),
) -> str:
    """
    Query and explore the Neo4j knowledge graph containing repository code structure.

    Supported commands:
    - 'repos': List all repositories
    - 'explore <repo>': Get statistics for a repository
    - 'query <cypher>': Execute a Cypher query

    Args:
        command: Command to execute

    Returns:
        JSON string with query results
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await query_knowledge_graph(tool_ctx, command)

        import json

        return json.dumps(result, indent=2)
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.exception(f"Error in query_graph tool: {e}")
        return f"Error: {e!s}"
