"""FastMCP server for Lambda multi-project server.

This module replaces the custom MCP server implementation with FastMCP 2.0,
providing automatic schema generation from type hints and cleaner code.
"""

import logging
from typing import Any, Literal

from fastapi import HTTPException
from fastmcp import FastMCP
from pydantic import ValidationError
from pymongo.errors import ConnectionFailure, OperationFailure

logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP("Lambda Server")


# ============================================================================
# MongoDB RAG Tools
# ============================================================================


@mcp.tool
async def search_knowledge_base(
    query: str, match_count: int = 5, search_type: Literal["semantic", "text", "hybrid"] = "hybrid"
) -> dict:
    """
    Search the MongoDB RAG knowledge base using semantic, text, or hybrid search.

    Searches across all ingested documents including crawled web pages. Results are
    ranked by relevance and include metadata for filtering and context.

    Args:
        query: Search query text. Can be a question, phrase, or keywords.
        match_count: Number of results to return. Range: 1-50. Default: 5.
        search_type: Type of search to perform. 'semantic' uses vector embeddings
                    (best for conceptual queries), 'text' uses keyword matching
                    (best for exact terms), 'hybrid' combines both using Reciprocal
                    Rank Fusion (recommended). Default: "hybrid".

    Returns:
        Dictionary containing search results with query, results array, and count.
    """
    from server.api.mongo_rag import search
    from server.projects.mongo_rag.models import SearchRequest

    try:
        result = await search(
            SearchRequest(query=query, match_count=match_count, search_type=search_type)
        )
        return result.dict()
    except ValidationError as e:
        logger.warning("mcp_validation_error: search_knowledge_base", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: search_knowledge_base",
            extra={"status_code": e.status_code, "detail": e.detail},
        )
        raise RuntimeError(f"Search failed: {e.detail}")
    except (ConnectionFailure, OperationFailure) as e:
        logger.exception("mcp_database_error: search_knowledge_base", extra={"error": str(e)})
        raise RuntimeError(f"Database operation failed: {e}")


@mcp.tool
async def agent_query(query: str) -> dict:
    """
    Query the conversational RAG agent with natural language.

    The agent can search the knowledge base, synthesize information, and provide
    natural language responses. It automatically decides when to search and how to
    combine search results into coherent answers.

    Args:
        query: Natural language question or query. The agent will determine if a
              search is needed, search the knowledge base if relevant, and synthesize
              results into a coherent answer.

    Returns:
        Dictionary containing query and response text.
    """
    from server.api.mongo_rag import agent
    from server.projects.mongo_rag.models import AgentRequest

    try:
        result = await agent(AgentRequest(query=query))
        return {"query": query, "response": result.response}
    except ValidationError as e:
        logger.warning("mcp_validation_error: agent_query", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: agent_query", extra={"status_code": e.status_code, "detail": e.detail}
        )
        raise RuntimeError(f"Agent query failed: {e.detail}")


@mcp.tool
async def ingest_documents(file_paths: list[str], clean_before: bool = False) -> dict:
    """
    Ingest documents into the MongoDB RAG knowledge base.

    Note: MCP doesn't support file uploads directly - files must already be on the
    server filesystem. For file uploads, use the REST API POST /api/v1/rag/ingest endpoint.
    Supported formats: PDF, Word, PowerPoint, Excel, HTML, Markdown, and audio files
    (with transcription).

    Args:
        file_paths: List of absolute file paths on the server to ingest. Files must
                   already exist on the server filesystem. Supported formats: .pdf,
                   .docx, .doc, .pptx, .ppt, .xlsx, .xls, .md, .markdown, .txt,
                   .html, .htm, .mp3, .wav, .m4a, .flac
        clean_before: If true, deletes all existing documents and chunks before
                     ingestion. Use with caution! Default: False.

    Returns:
        Dictionary with error message indicating REST API should be used.
    """
    return {
        "error": {
            "code": "NOT_IMPLEMENTED",
            "message": "File ingestion via MCP requires files to be on server",
            "details": "Use REST API POST /api/v1/rag/ingest for file uploads",
        }
    }


@mcp.tool
async def search_code_examples(query: str, match_count: int = 5) -> dict:
    """
    Search for code examples in the knowledge base.

    Returns code snippets with summaries, language, and context. Requires
    USE_AGENTIC_RAG=true to be enabled.

    Args:
        query: Search query text to find relevant code examples.
        match_count: Number of results to return. Range: 1-50. Default: 5.

    Returns:
        Dictionary containing code example search results.
    """
    from server.api.mongo_rag import search_code_examples_endpoint
    from server.projects.mongo_rag.models import CodeExampleSearchRequest

    try:
        request = CodeExampleSearchRequest(query=query, match_count=match_count)
        result = await search_code_examples_endpoint(request)
        return result.dict()
    except ValidationError as e:
        logger.warning("mcp_validation_error: search_code_examples", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: search_code_examples",
            extra={"status_code": e.status_code, "detail": e.detail},
        )
        raise RuntimeError(f"Search failed: {e.detail}")


@mcp.tool
async def get_available_sources() -> dict:
    """
    Get all available sources (domains/paths) that have been crawled and stored
    in the database, along with their summaries and statistics.

    Returns:
        Dictionary containing list of sources with metadata.
    """
    from server.api.mongo_rag import get_sources

    try:
        result = await get_sources()
        return result
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: get_available_sources",
            extra={"status_code": e.status_code, "detail": e.detail},
        )
        raise RuntimeError(f"Failed to get sources: {e.detail}")


# ============================================================================
# Graphiti RAG Tools
# ============================================================================


@mcp.tool
async def search_graphiti(query: str, match_count: int = 10) -> dict:
    """
    Search the Graphiti knowledge graph for entities and relationships.

    Returns facts with temporal information and source metadata. Requires
    USE_GRAPHITI=true.

    Args:
        query: Search query text to find relevant facts in the knowledge graph.
        match_count: Number of results to return. Range: 1-50. Default: 10.

    Returns:
        Dictionary containing graphiti search results.
    """
    from server.api.graphiti_rag import search_graphiti_endpoint
    from server.projects.graphiti_rag.models import GraphitiSearchRequest

    try:
        request = GraphitiSearchRequest(query=query, match_count=match_count)
        result = await search_graphiti_endpoint(request)
        return result.dict()
    except ValidationError as e:
        logger.warning("mcp_validation_error: search_graphiti", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: search_graphiti",
            extra={"status_code": e.status_code, "detail": e.detail},
        )
        raise RuntimeError(f"Search failed: {e.detail}")


@mcp.tool
async def parse_github_repository(repo_url: str) -> dict:
    """
    Parse a GitHub repository into the Neo4j knowledge graph for code structure analysis.

    Extracts classes, methods, functions, and their relationships. Requires
    USE_KNOWLEDGE_GRAPH=true.

    Args:
        repo_url: GitHub repository URL (e.g., 'https://github.com/user/repo.git').
                 Must end with .git.

    Returns:
        Dictionary containing parse results.
    """
    from server.api.graphiti_rag import parse_github_repository_endpoint
    from server.projects.graphiti_rag.models import ParseRepositoryRequest

    try:
        request = ParseRepositoryRequest(repo_url=repo_url)
        result = await parse_github_repository_endpoint(request)
        return result.dict()
    except ValidationError as e:
        logger.warning(
            "mcp_validation_error: parse_github_repository", extra={"errors": e.errors()}
        )
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: parse_github_repository",
            extra={"status_code": e.status_code, "detail": e.detail},
        )
        raise RuntimeError(f"Parse failed: {e.detail}")


@mcp.tool
async def check_ai_script_hallucinations(script_path: str) -> dict:
    """
    Check an AI-generated Python script for hallucinations using the knowledge graph.

    Validates imports, method calls, class instantiations, and function calls against
    real repository data. Requires USE_KNOWLEDGE_GRAPH=true.

    Args:
        script_path: Absolute path to the Python script to analyze.

    Returns:
        Dictionary containing validation results.
    """
    from server.api.graphiti_rag import validate_ai_script_endpoint
    from server.projects.graphiti_rag.models import ValidateScriptRequest

    try:
        request = ValidateScriptRequest(script_path=script_path)
        result = await validate_ai_script_endpoint(request)
        return result.dict()
    except ValidationError as e:
        logger.warning(
            "mcp_validation_error: check_ai_script_hallucinations", extra={"errors": e.errors()}
        )
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: check_ai_script_hallucinations",
            extra={"status_code": e.status_code, "detail": e.detail},
        )
        raise RuntimeError(f"Validation failed: {e.detail}")


@mcp.tool
async def query_knowledge_graph(command: str) -> dict:
    """
    Query and explore the Neo4j knowledge graph containing repository code structure.

    Supports commands: repos, explore <repo>, classes [repo], class <name>,
    method <name> [class], query <cypher>. Requires USE_KNOWLEDGE_GRAPH=true.

    Args:
        command: Command to execute. Examples: 'repos', 'explore pydantic-ai',
                'classes pydantic-ai', 'class Agent', 'method run_stream',
                'query MATCH (c:Class) RETURN c.name LIMIT 5'

    Returns:
        Dictionary containing query results.
    """
    from server.api.graphiti_rag import query_knowledge_graph_endpoint
    from server.projects.graphiti_rag.models import QueryKnowledgeGraphRequest

    try:
        request = QueryKnowledgeGraphRequest(command=command)
        result = await query_knowledge_graph_endpoint(request)
        return result.dict()
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: query_knowledge_graph",
            extra={"status_code": e.status_code, "detail": e.detail},
        )
        raise RuntimeError(f"Query failed: {e.detail}")


# ============================================================================
# Crawl4AI Tools
# ============================================================================


@mcp.tool
async def crawl_single_page(url: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> dict:
    """
    Crawl a single web page and automatically ingest it into the MongoDB RAG knowledge base.

    The page becomes immediately searchable via search endpoints. Extracts page metadata
    including title, description, language, images, and links.

    Args:
        url: URL to crawl. Must be a valid HTTP/HTTPS URL.
        chunk_size: Chunk size for document splitting. Range: 100-5000. Larger chunks
                   preserve more context but may exceed embedding model limits.
                   Default: 1000.
        chunk_overlap: Chunk overlap size. Range: 0-500. Overlap helps maintain context
                      across chunk boundaries. Default: 200.

    Returns:
        Dictionary containing crawl results with success status, pages crawled,
        chunks created, document IDs, and any errors.
    """
    from server.api.crawl4ai_rag import crawl_single
    from server.projects.crawl4ai_rag.models import CrawlSinglePageRequest

    try:
        request = CrawlSinglePageRequest(
            url=url, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        result = await crawl_single(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def crawl_deep(
    url: str,
    max_depth: int,
    allowed_domains: list[str] | None = None,
    allowed_subdomains: list[str] | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> dict:
    """
    Deep crawl a website recursively and ingest all discovered pages into MongoDB.

    Follows internal links up to specified depth with optional domain/subdomain filtering.
    All pages become immediately searchable. Each page's metadata includes crawl depth
    and parent URL for traceability.

    Args:
        url: Starting URL for the crawl. Must be a valid HTTP/HTTPS URL.
        max_depth: Maximum recursion depth. Range: 1-10. Depth 1 = starting page only,
                  Depth 2 = starting page + 1 level of links, Depth 3 = starting page + 2 levels
                  (recommended for most sites).
        allowed_domains: List of allowed domains for exact matching. If not provided, allows
                        all domains from the starting URL. Example: ["example.com", "docs.example.com"]
        allowed_subdomains: List of allowed subdomain prefixes. If not provided, allows all
                           subdomains. Example: ["docs", "api", "blog"] matches docs.example.com,
                           api.example.com, etc.
        chunk_size: Chunk size for document splitting. Range: 100-5000. Larger chunks preserve
                   more context but may exceed embedding model limits. Default: 1000.
        chunk_overlap: Chunk overlap size. Range: 0-500. Overlap helps maintain context across
                      chunk boundaries. Default: 200.

    Returns:
        Dictionary containing crawl results with success status, pages crawled,
        chunks created, document IDs, and any errors.
    """
    from server.api.crawl4ai_rag import crawl_deep_endpoint
    from server.projects.crawl4ai_rag.models import CrawlDeepRequest

    try:
        request = CrawlDeepRequest(
            url=url,
            max_depth=max_depth,
            allowed_domains=allowed_domains,
            allowed_subdomains=allowed_subdomains,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        result = await crawl_deep_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


# ============================================================================
# SearXNG Tools
# ============================================================================


@mcp.tool
async def web_search(
    query: str,
    result_count: int = 10,
    categories: str | None = None,
    engines: list[str] | None = None,
) -> dict:
    """
    Search the web using SearXNG metasearch engine.

    Use this when you need current information, real-time data, or information not
    in the knowledge base. Automatically searches multiple search engines and returns
    ranked results.

    Args:
        query: Search query string. Can be a question, phrase, or keywords.
        result_count: Number of results to return. Range: 1-20. Default: 10.
        categories: Filter by category (general, news, images, etc.). Optional.
        engines: Filter by specific search engines. Optional.

    Returns:
        Dictionary containing search results with query, results array, and count.
    """
    from server.api.searxng import SearXNGSearchRequest, search

    try:
        request = SearXNGSearchRequest(
            query=query, result_count=result_count, categories=categories, engines=engines
        )
        result = await search(request)
        return result.dict()
    except ValidationError as e:
        logger.warning("mcp_validation_error: web_search", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: web_search", extra={"status_code": e.status_code, "detail": e.detail}
        )
        raise RuntimeError(f"Web search failed: {e.detail}")


# ============================================================================
# N8N Workflow Tools
# ============================================================================


@mcp.tool
async def create_n8n_workflow(
    name: str,
    nodes: list[dict[str, Any]] | None = None,
    connections: dict[str, Any] | None = None,
    active: bool = False,
    settings: dict[str, Any] | None = None,
) -> dict:
    """
    Create a new N8n workflow with nodes and connections.

    Workflows automate processes by connecting nodes that perform actions,
    transformations, or triggers.

    Args:
        name: Name of the workflow.
        nodes: List of workflow nodes. Each node should have: name, type, typeVersion,
              position, parameters. Optional.
        connections: Workflow connections mapping nodes together. Format:
                    {source_node: [{node: target_node, type: 'main', index: 0}]}. Optional.
        active: Whether to activate the workflow immediately. Default: False.
        settings: Workflow settings. Optional.

    Returns:
        Dictionary containing created workflow details.
    """
    from server.api.n8n_workflow import create_workflow_endpoint
    from server.projects.n8n_workflow.models import CreateWorkflowRequest, WorkflowNode

    try:
        # Convert nodes if provided
        workflow_nodes = None
        if nodes:
            workflow_nodes = [
                WorkflowNode(**node) if isinstance(node, dict) else node for node in nodes
            ]

        request = CreateWorkflowRequest(
            name=name,
            nodes=workflow_nodes or [],
            connections=connections or {},
            active=active,
            settings=settings or {},
        )
        result = await create_workflow_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def update_n8n_workflow(
    workflow_id: str,
    name: str | None = None,
    nodes: list[dict[str, Any]] | None = None,
    connections: dict[str, Any] | None = None,
    active: bool | None = None,
    settings: dict[str, Any] | None = None,
) -> dict:
    """
    Update an existing N8n workflow.

    Can update name, nodes, connections, activation status, or settings.

    Args:
        workflow_id: ID of the workflow to update.
        name: New workflow name. Optional.
        nodes: New workflow nodes. Optional.
        connections: New workflow connections. Optional.
        active: Whether to activate/deactivate the workflow. Optional.
        settings: New workflow settings. Optional.

    Returns:
        Dictionary containing updated workflow details.
    """
    from server.api.n8n_workflow import update_workflow_endpoint
    from server.projects.n8n_workflow.models import UpdateWorkflowRequest, WorkflowNode

    try:
        workflow_nodes = None
        if nodes:
            workflow_nodes = [
                WorkflowNode(**node) if isinstance(node, dict) else node for node in nodes
            ]

        request = UpdateWorkflowRequest(
            workflow_id=workflow_id,
            name=name,
            nodes=workflow_nodes,
            connections=connections,
            active=active,
            settings=settings,
        )
        result = await update_workflow_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def delete_n8n_workflow(workflow_id: str) -> dict:
    """
    Delete an N8n workflow permanently.

    Args:
        workflow_id: ID of the workflow to delete.

    Returns:
        Dictionary containing deletion confirmation.
    """
    from server.api.n8n_workflow import delete_workflow_endpoint
    from server.projects.n8n_workflow.models import DeleteWorkflowRequest

    try:
        request = DeleteWorkflowRequest(workflow_id=workflow_id)
        result = await delete_workflow_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def activate_n8n_workflow(workflow_id: str, active: bool) -> dict:
    """
    Activate or deactivate an N8n workflow.

    Active workflows run automatically based on their triggers.

    Args:
        workflow_id: ID of the workflow.
        active: True to activate, False to deactivate.

    Returns:
        Dictionary containing activation status.
    """
    from server.api.n8n_workflow import activate_workflow_endpoint
    from server.projects.n8n_workflow.models import ActivateWorkflowRequest

    try:
        request = ActivateWorkflowRequest(workflow_id=workflow_id, active=active)
        result = await activate_workflow_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def list_n8n_workflows(active_only: bool = False) -> dict:
    """
    List all N8n workflows.

    Returns workflow IDs, names, and activation status.

    Args:
        active_only: If true, only return active workflows. Default: False.

    Returns:
        Dictionary containing list of workflows.
    """
    from server.api.n8n_workflow import list_workflows_endpoint

    try:
        result = await list_workflows_endpoint(active_only=active_only)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def execute_n8n_workflow(workflow_id: str, input_data: dict[str, Any] | None = None) -> dict:
    """
    Execute an N8n workflow manually.

    Note: Some workflows require triggers (webhooks, schedules) and cannot be
    executed directly.

    Args:
        workflow_id: ID of the workflow to execute.
        input_data: Input data for workflow execution. Optional.

    Returns:
        Dictionary containing execution results.
    """
    from server.api.n8n_workflow import execute_workflow_endpoint
    from server.projects.n8n_workflow.models import ExecuteWorkflowRequest

    try:
        request = ExecuteWorkflowRequest(workflow_id=workflow_id, input_data=input_data or {})
        result = await execute_workflow_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def scrape_event_to_calendar(
    url: str,
    event_name_pattern: str | None = None,
    calendar_id: str = "primary",
    timezone: str = "America/New_York",
    location_pattern: str | None = None,
    description_template: str | None = None,
    workflow_name: str = "Scrape Event To Calendar",
) -> dict:
    """
    Scrape event information from a website and create/update a Google Calendar event.

    This tool first checks if the website content already exists in the RAG knowledge base.
    If found, it extracts event data from the cached HTML content. If not found, it crawls the
    website (which automatically ingests it into RAG), then extracts event data.
    Finally, it creates or updates a Google Calendar event via the n8n workflow.

    Args:
        url: Website URL to scrape for event information.
        event_name_pattern: Optional pattern or name to use for the event. If not provided,
                          will try to extract from the website.
        calendar_id: Google Calendar ID (default: "primary").
        timezone: Timezone for the event (default: "America/New_York").
        location_pattern: Optional location pattern or specific location string.
        description_template: Optional description template or specific description.
        workflow_name: Name of the n8n workflow to use (default: "Scrape Event To Calendar").

    Returns:
        Dictionary containing the calendar event details (action, eventId, summary, start, end).
    """
    import httpx

    try:
        # Call the REST API endpoint
        api_url = "http://localhost:8000/api/v1/calendar/sync"
        payload = {"url": url, "calendar_id": calendar_id, "timezone": timezone}

        if event_name_pattern:
            payload["event_name_pattern"] = event_name_pattern
        if location_pattern:
            payload["location_pattern"] = location_pattern
        if description_template:
            payload["description_template"] = description_template
        if workflow_name:
            payload["workflow_name"] = workflow_name

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, json=payload)
            response.raise_for_status()
            result = response.json()

            # Convert API response to MCP tool format
            return {
                "action": result.get("action"),
                "eventId": result.get("event_id"),
                "summary": result.get("summary"),
                "start": result.get("start"),
                "end": result.get("end"),
                "success": result.get("success"),
                "message": result.get("message"),
            }
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if e.response else str(e)
        logger.exception(f"mcp_tool_error: scrape_event_to_calendar HTTP {e.response.status_code}")
        raise RuntimeError(f"Calendar sync failed: {error_detail}")


@mcp.tool
async def discover_n8n_nodes(category: str | None = None) -> str:
    """
    Discover available N8n nodes via API.

    Returns list of available node types with descriptions. Use this to see what
    nodes are available before creating workflows.

    Args:
        category: Optional category filter (e.g., 'trigger', 'action', 'data').

    Returns:
        String containing formatted list of available nodes.
    """
    from pydantic_ai import RunContext

    from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
    from server.projects.n8n_workflow.tools import discover_n8n_nodes

    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
    try:
        result = await discover_n8n_nodes(run_ctx, category)
        return result
    finally:
        await deps.cleanup()


@mcp.tool
async def search_n8n_knowledge_base(
    query: str, match_count: int = 5, search_type: Literal["semantic", "text", "hybrid"] = "hybrid"
) -> str:
    """
    Search the knowledge base for N8n-related information.

    Includes node documentation, workflow examples, best practices, and configuration
    guides. ALWAYS use this before creating workflows to find relevant information.

    Args:
        query: Search query text (e.g., 'webhook node', 'HTTP request workflow',
              'n8n error handling').
        match_count: Number of results to return. Range: 1-50. Default: 5.
        search_type: Type of search. 'semantic' uses vector embeddings, 'text' uses
                    keyword matching, 'hybrid' combines both (recommended).
                    Default: "hybrid".

    Returns:
        String containing formatted search results.
    """
    from pydantic_ai import RunContext

    from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
    from server.projects.n8n_workflow.tools import search_n8n_knowledge_base

    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
    try:
        result = await search_n8n_knowledge_base(run_ctx, query, match_count, search_type)
        return result
    finally:
        await deps.cleanup()


@mcp.tool
async def search_n8n_node_examples(
    node_type: str | None = None, query: str | None = None, match_count: int = 5
) -> str:
    """
    Search for specific N8n node usage examples and configurations in the knowledge base.

    Use this to find how to configure specific nodes with real examples.

    Args:
        node_type: Optional node type to filter by (e.g., 'webhook', 'HTTP Request', 'Code').
        query: Optional search query for use cases or examples (e.g., 'authentication',
              'error handling').
        match_count: Number of results to return. Range: 1-50. Default: 5.

    Returns:
        String containing formatted examples.
    """
    from pydantic_ai import RunContext

    from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
    from server.projects.n8n_workflow.tools import search_node_examples

    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
    try:
        result = await search_node_examples(run_ctx, node_type, query, match_count)
        return result
    finally:
        await deps.cleanup()


# ============================================================================
# Open WebUI Tools
# ============================================================================


@mcp.tool
async def export_openwebui_conversation(
    conversation_id: str,
    messages: list[dict[str, Any]],
    user_id: str | None = None,
    title: str | None = None,
    topics: list[str] | None = None,
) -> dict:
    """
    Export an Open WebUI conversation to the MongoDB RAG system.

    Makes it searchable via vector search. The conversation is chunked, embedded,
    and stored in the knowledge base.

    Args:
        conversation_id: Open WebUI conversation ID.
        messages: List of conversation messages with role and content.
        user_id: User ID. Optional.
        title: Conversation title. Optional.
        topics: Conversation topics. Optional.

    Returns:
        Dictionary containing export results.
    """
    from server.api.openwebui_export import export_conversation_endpoint
    from server.projects.openwebui_export.models import (
        ConversationExportRequest,
        ConversationMessage,
    )

    try:
        # Convert messages to ConversationMessage objects
        conversation_messages = [
            ConversationMessage(**msg) if isinstance(msg, dict) else msg for msg in messages
        ]

        request = ConversationExportRequest(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            messages=conversation_messages,
            topics=topics,
            metadata={},
        )
        result = await export_conversation_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def classify_conversation_topics(
    conversation_id: str,
    messages: list[dict[str, Any]],
    title: str | None = None,
    existing_topics: list[str] | None = None,
) -> dict:
    """
    Classify topics for an Open WebUI conversation using LLM.

    Analyzes the conversation content and suggests 3-5 relevant topics.

    Args:
        conversation_id: Conversation ID.
        messages: Conversation messages.
        title: Conversation title. Optional.
        existing_topics: Existing topics to consider. Optional.

    Returns:
        Dictionary containing classified topics.
    """
    from server.api.openwebui_topics import classify_topics_endpoint
    from server.projects.openwebui_topics.models import TopicClassificationRequest

    try:
        request = TopicClassificationRequest(
            conversation_id=conversation_id,
            title=title,
            messages=messages,
            existing_topics=existing_topics,
        )
        result = await classify_topics_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def search_conversations(
    query: str,
    match_count: int = 5,
    user_id: str | None = None,
    conversation_id: str | None = None,
    topics: list[str] | None = None,
) -> dict:
    """
    Search conversations in the RAG system.

    Filters results to only include Open WebUI conversations. Supports filtering
    by user_id, conversation_id, and topics.

    Args:
        query: Search query text.
        match_count: Number of results to return. Range: 1-50. Default: 5.
        user_id: Filter by user ID. Optional.
        conversation_id: Filter by conversation ID. Optional.
        topics: Filter by topics. Optional.

    Returns:
        Dictionary containing search results.
    """
    from server.api.mongo_rag import search
    from server.projects.mongo_rag.models import SearchRequest

    try:
        request = SearchRequest(
            query=query,
            match_count=match_count,
            search_type="hybrid",
            source_type="openwebui_conversation",
            user_id=user_id,
            conversation_id=conversation_id,
            topics=topics,
        )
        result = await search(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


# ============================================================================
# Calendar Tools
# ============================================================================


@mcp.tool
async def create_calendar_event(
    user_id: str,
    persona_id: str,
    local_event_id: str,
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    timezone: str = "America/Los_Angeles",
    calendar_id: str = "primary",
    attendees: list[str] | None = None,
) -> dict:
    """
    Create a new calendar event in Google Calendar.

    Creates a new event in Google Calendar and tracks the sync state to prevent duplicates.
    The event is stored with a unique local_event_id that can be used for future updates.

    Args:
        user_id: User ID
        persona_id: Persona ID
        local_event_id: Unique local event identifier
        summary: Event title/summary
        start: Start datetime (ISO format)
        end: End datetime (ISO format)
        description: Event description. Optional.
        location: Event location. Optional.
        timezone: Timezone string. Default: "America/Los_Angeles"
        calendar_id: Google Calendar ID. Default: "primary"
        attendees: List of attendee emails. Optional.

    Returns:
        Dictionary containing the created event details.
    """
    from server.api.calendar import create_calendar_event_endpoint
    from server.projects.calendar.models import CalendarEventData, CreateCalendarEventRequest

    try:
        event_data = CalendarEventData(
            summary=summary,
            start=start,
            end=end,
            description=description,
            location=location,
            timezone=timezone,
            attendees=attendees,
        )
        request = CreateCalendarEventRequest(
            user_id=user_id,
            persona_id=persona_id,
            local_event_id=local_event_id,
            event_data=event_data,
            calendar_id=calendar_id,
        )
        result = await create_calendar_event_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def update_calendar_event(
    user_id: str,
    persona_id: str,
    local_event_id: str,
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
    timezone: str = "America/Los_Angeles",
    calendar_id: str = "primary",
    attendees: list[str] | None = None,
) -> dict:
    """
    Update an existing calendar event in Google Calendar.

    Updates an existing event in Google Calendar. The event is identified by the
    local_event_id. Only provided fields will be updated.

    Args:
        user_id: User ID
        persona_id: Persona ID
        local_event_id: Local event identifier
        summary: Event title/summary. Optional.
        start: Start datetime (ISO format). Optional.
        end: End datetime (ISO format). Optional.
        description: Event description. Optional.
        location: Event location. Optional.
        timezone: Timezone string. Default: "America/Los_Angeles"
        calendar_id: Google Calendar ID. Default: "primary"
        attendees: List of attendee emails. Optional.

    Returns:
        Dictionary containing the updated event details.
    """
    from server.api.calendar import update_calendar_event_endpoint
    from server.projects.calendar.models import CalendarEventData, UpdateCalendarEventRequest

    try:
        event_data = CalendarEventData(
            summary=summary or "Untitled Event",
            start=start or "",
            end=end or "",
            description=description,
            location=location,
            timezone=timezone,
            attendees=attendees,
        )
        request = UpdateCalendarEventRequest(
            user_id=user_id,
            persona_id=persona_id,
            local_event_id=local_event_id,
            event_data=event_data,
            calendar_id=calendar_id,
        )
        result = await update_calendar_event_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def delete_calendar_event(user_id: str, event_id: str, calendar_id: str = "primary") -> dict:
    """
    Delete a calendar event from Google Calendar.

    Deletes an event from Google Calendar. The event is identified by the Google Calendar event ID.

    Args:
        user_id: User ID
        event_id: Google Calendar event ID
        calendar_id: Google Calendar ID. Default: "primary"

    Returns:
        Dictionary containing the deletion result.
    """
    from server.api.calendar import delete_calendar_event_endpoint
    from server.projects.calendar.models import DeleteCalendarEventRequest

    try:
        request = DeleteCalendarEventRequest(
            user_id=user_id, event_id=event_id, calendar_id=calendar_id
        )
        result = await delete_calendar_event_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def list_calendar_events(
    user_id: str,
    calendar_id: str = "primary",
    start_time: str | None = None,
    end_time: str | None = None,
    timezone: str = "America/Los_Angeles",
) -> dict:
    """
    List calendar events from Google Calendar.

    Retrieves a list of events from Google Calendar within a specified time range.
    If no time range is provided, it defaults to the next 30 days.

    Args:
        user_id: User ID
        calendar_id: Google Calendar ID. Default: "primary"
        start_time: Start time (ISO format). Optional.
        end_time: End time (ISO format). Optional.
        timezone: Timezone string. Default: "America/Los_Angeles"

    Returns:
        Dictionary containing the list of events and count.
    """
    from server.api.calendar import list_calendar_events_endpoint

    try:
        result = await list_calendar_events_endpoint(
            user_id=user_id,
            calendar_id=calendar_id,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
        )
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


# ============================================================================
# Event Extraction Tools
# ============================================================================


@mcp.tool
async def extract_events_from_content(
    content: str, url: str | None = None, use_llm: bool = False
) -> dict:
    """
    Extract event information from web content.

    Extracts event details (title, date, time, location, instructor) from web content
    using regex patterns or LLM-based extraction.

    Args:
        content: Web content (HTML, markdown, or plain text)
        url: Source URL. Optional.
        use_llm: Use LLM for extraction (more accurate but slower). Default: False

    Returns:
        Dictionary containing extracted events.
    """
    from server.api.knowledge import extract_events_endpoint
    from server.projects.knowledge.models import ExtractEventsRequest

    try:
        request = ExtractEventsRequest(content=content, url=url, use_llm=use_llm)
        result = await extract_events_endpoint(request)
        return result.dict()
    except ValidationError as e:
        logger.warning(
            "mcp_validation_error: extract_events_from_content", extra={"errors": e.errors()}
        )
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: extract_events_from_content",
            extra={"status_code": e.status_code, "detail": e.detail},
        )
        raise RuntimeError(f"Event extraction failed: {e.detail}")


@mcp.tool
async def extract_events_from_crawled(
    crawled_pages: list[dict[str, Any]], use_llm: bool = False
) -> dict:
    """
    Extract events from multiple crawled pages.

    Processes multiple crawled pages and extracts event information from each one.

    Args:
        crawled_pages: List of crawled page dictionaries with 'content' and 'url' keys
        use_llm: Use LLM for extraction (more accurate but slower). Default: False

    Returns:
        Dictionary containing extracted events.
    """
    from server.api.knowledge import extract_events_from_crawled_endpoint
    from server.projects.knowledge.models import ExtractEventsFromCrawledRequest

    try:
        request = ExtractEventsFromCrawledRequest(crawled_pages=crawled_pages, use_llm=use_llm)
        result = await extract_events_from_crawled_endpoint(request)
        return result.dict()
    except ValidationError as e:
        logger.warning(
            "mcp_validation_error: extract_events_from_crawled", extra={"errors": e.errors()}
        )
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: extract_events_from_crawled",
            extra={"status_code": e.status_code, "detail": e.detail},
        )
        raise RuntimeError(f"Event extraction failed: {e.detail}")


# ============================================================================
# Blob Storage Tools
# ============================================================================


@mcp.tool
async def upload_file_to_storage(
    user_id: str,
    file_data: str,
    filename: str,
    content_type: str | None = None,
) -> dict:
    """
    Upload a file to user's blob storage.

    Files are stored in MinIO under user-specific prefixes for data isolation.

    Args:
        user_id: User UUID as string
        file_data: File content as base64-encoded string
        filename: Filename
        content_type: Optional content type (auto-detected if not provided)

    Returns:
        Dictionary containing upload response with file key and metadata.
    """
    import base64
    from uuid import UUID

    from server.api.blob_storage import upload_file_endpoint

    try:
        user_uuid = UUID(user_id)
        file_bytes = base64.b64decode(file_data)

        result = await upload_file_endpoint(
            user_id=user_uuid,
            file_data=file_bytes,
            filename=filename,
            content_type=content_type,
        )
        return result.dict()
    except ValueError as e:
        logger.warning("mcp_validation_error: upload_file_to_storage", extra={"error": str(e)})
        raise ValueError(f"Invalid parameters: {e}")


@mcp.tool
async def list_storage_files(
    user_id: str,
    prefix: str | None = None,
) -> dict:
    """
    List files for a user in blob storage.

    Args:
        user_id: User UUID as string
        prefix: Optional prefix to filter files (e.g., "loras/" for LoRA models)

    Returns:
        Dictionary containing list of files with metadata.
    """
    from uuid import UUID

    from server.api.blob_storage import list_files_endpoint

    try:
        user_uuid = UUID(user_id)

        result = await list_files_endpoint(
            user_id=user_uuid,
            prefix=prefix,
        )
        return result.dict()
    except ValueError as e:
        logger.warning("mcp_validation_error: list_storage_files", extra={"error": str(e)})
        raise ValueError(f"Invalid parameters: {e}")


@mcp.tool
async def download_file_from_storage(
    user_id: str,
    filename: str,
) -> dict:
    """
    Download a file from user's blob storage.

    Args:
        user_id: User UUID as string
        filename: Filename to download

    Returns:
        Dictionary containing file content as base64-encoded string.
    """
    import base64
    from uuid import UUID

    from server.api.blob_storage import download_file_endpoint

    try:
        user_uuid = UUID(user_id)

        file_data = await download_file_endpoint(
            user_id=user_uuid,
            filename=filename,
        )

        return {
            "success": True,
            "filename": filename,
            "data": base64.b64encode(file_data).decode("utf-8"),
            "size": len(file_data),
        }
    except ValueError as e:
        logger.warning("mcp_validation_error: download_file_from_storage", extra={"error": str(e)})
        raise ValueError(f"Invalid parameters: {e}")


@mcp.tool
async def delete_file_from_storage(
    user_id: str,
    filename: str,
) -> dict:
    """
    Delete a file from user's blob storage.

    Args:
        user_id: User UUID as string
        filename: Filename to delete

    Returns:
        Dictionary containing delete response with status.
    """
    from uuid import UUID

    from server.api.blob_storage import delete_file_endpoint

    try:
        user_uuid = UUID(user_id)

        result = await delete_file_endpoint(
            user_id=user_uuid,
            filename=filename,
        )
        return result.dict()
    except ValueError as e:
        logger.warning("mcp_validation_error: delete_file_from_storage", extra={"error": str(e)})
        raise ValueError(f"Invalid parameters: {e}")


@mcp.tool
async def get_storage_file_url(
    user_id: str,
    filename: str,
    expires_in: int = 3600,
) -> dict:
    """
    Generate a presigned URL for a file in blob storage.

    Args:
        user_id: User UUID as string
        filename: Filename to generate URL for
        expires_in: URL expiration time in seconds (default: 3600, max: 604800)

    Returns:
        Dictionary containing presigned URL response.
    """
    from uuid import UUID

    from server.api.blob_storage import get_file_url_endpoint

    try:
        user_uuid = UUID(user_id)

        if expires_in < 60 or expires_in > 604800:
            raise ValueError("expires_in must be between 60 and 604800 seconds")

        result = await get_file_url_endpoint(
            user_id=user_uuid,
            filename=filename,
            expires_in=expires_in,
        )
        return result.dict()
    except ValueError as e:
        logger.warning("mcp_validation_error: get_storage_file_url", extra={"error": str(e)})
        raise ValueError(f"Invalid parameters: {e}")


# ============================================================================
# Memory Tools
# ============================================================================


@mcp.tool
async def record_message(user_id: str, persona_id: str, content: str, role: str = "user") -> dict:
    """
    Record a message in memory for context window management.

    Args:
        user_id: User ID
        persona_id: Persona ID
        content: Message content
        role: Message role ("user" or "assistant"). Default: "user"

    Returns:
        Dictionary with success status.
    """
    from server.api.mongo_rag import record_message_endpoint

    try:
        result = await record_message_endpoint(user_id, persona_id, content, role)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def get_context_window(user_id: str, persona_id: str, limit: int = 20) -> dict:
    """
    Get recent messages for context window.

    Args:
        user_id: User ID
        persona_id: Persona ID
        limit: Maximum number of messages to return. Default: 20

    Returns:
        Dictionary containing messages and count.
    """
    from server.api.mongo_rag import get_context_window_endpoint

    try:
        result = await get_context_window_endpoint(user_id, persona_id, limit)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def store_fact(
    user_id: str, persona_id: str, fact: str, tags: list[str] | None = None
) -> dict:
    """
    Store a fact in memory.

    Args:
        user_id: User ID
        persona_id: Persona ID
        fact: Fact to store
        tags: Optional tags for the fact

    Returns:
        Dictionary with success status.
    """
    from server.api.mongo_rag import store_fact_endpoint

    try:
        result = await store_fact_endpoint(user_id, persona_id, fact, tags)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def search_facts(user_id: str, persona_id: str, query: str, limit: int = 10) -> dict:
    """
    Search for facts in memory.

    Args:
        user_id: User ID
        persona_id: Persona ID
        query: Search query
        limit: Maximum number of facts to return. Default: 10

    Returns:
        Dictionary containing facts and count.
    """
    from server.api.mongo_rag import search_facts_endpoint

    try:
        result = await search_facts_endpoint(user_id, persona_id, query, limit)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def store_web_content(
    user_id: str,
    persona_id: str,
    content: str,
    source_url: str,
    source_title: str = "",
    source_description: str = "",
    tags: list[str] | None = None,
) -> dict:
    """
    Store web content in memory.

    Args:
        user_id: User ID
        persona_id: Persona ID
        content: Web content to store
        source_url: Source URL
        source_title: Source title. Optional.
        source_description: Source description. Optional.
        tags: Optional tags

    Returns:
        Dictionary with success status and chunks count.
    """
    from server.api.mongo_rag import store_web_content_endpoint

    try:
        result = await store_web_content_endpoint(
            user_id, persona_id, content, source_url, source_title, source_description, tags
        )
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


# ============================================================================
# Enhanced RAG Tools
# ============================================================================


@mcp.tool
async def enhanced_search(
    query: str,
    match_count: int = 5,
    use_decomposition: bool = True,
    use_grading: bool = True,
    use_citations: bool = True,
    use_rewrite: bool = False,
) -> dict:
    """
    Enhanced search with query decomposition, document grading, and citation extraction.

    Provides advanced RAG capabilities including:
    - Query decomposition for complex multi-part questions
    - Document grading to filter irrelevant results
    - Citation extraction for source tracking
    - Result synthesis from multiple sub-queries

    Args:
        query: Search query text
        match_count: Number of results per sub-query. Default: 5
        use_decomposition: Whether to decompose complex queries. Default: True
        use_grading: Whether to grade documents for relevance. Default: True
        use_citations: Whether to extract citations. Default: True
        use_rewrite: Whether to rewrite query first. Default: False

    Returns:
        Dictionary containing search results with citations.
    """
    from server.api.mongo_rag import enhanced_search_endpoint

    try:
        result = await enhanced_search_endpoint(
            query=query,
            match_count=match_count,
            use_decomposition=use_decomposition,
            use_grading=use_grading,
            use_citations=use_citations,
            use_rewrite=use_rewrite,
        )
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


# ============================================================================
# Persona Tools
# ============================================================================


@mcp.tool
async def get_persona_voice_instructions(user_id: str, persona_id: str) -> dict:
    """
    Generate dynamic style instructions based on current persona state.

    Returns prompt injection with current emotional state, relationship context,
    and conversation mode to guide persona responses.

    Args:
        user_id: User ID
        persona_id: Persona ID

    Returns:
        Dictionary containing voice instructions.
    """
    from server.api.persona import get_voice_instructions_endpoint
    from server.projects.persona.models import GetVoiceInstructionsRequest

    try:
        request = GetVoiceInstructionsRequest(user_id=user_id, persona_id=persona_id)
        result = await get_voice_instructions_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def record_persona_interaction(
    user_id: str, persona_id: str, user_message: str, bot_response: str
) -> dict:
    """
    Record an interaction to update persona state (mood, relationship, context).

    Args:
        user_id: User ID
        persona_id: Persona ID
        user_message: User's message
        bot_response: Bot's response

    Returns:
        Dictionary containing updated state.
    """
    from server.api.persona import record_interaction_endpoint
    from server.projects.persona.models import RecordInteractionRequest

    try:
        request = RecordInteractionRequest(
            user_id=user_id,
            persona_id=persona_id,
            user_message=user_message,
            bot_response=bot_response,
        )
        result = await record_interaction_endpoint(request)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def get_persona_state(user_id: str, persona_id: str) -> dict:
    """
    Get current persona state including mood, relationship, and context.

    Args:
        user_id: User ID
        persona_id: Persona ID

    Returns:
        Dictionary containing persona state.
    """
    from server.api.persona import get_persona_state_endpoint

    try:
        result = await get_persona_state_endpoint(user_id, persona_id)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def update_persona_mood(
    user_id: str, persona_id: str, primary_emotion: str, intensity: float
) -> dict:
    """
    Update persona mood state.

    Args:
        user_id: User ID
        persona_id: Persona ID
        primary_emotion: Primary emotion (happy, sad, excited, neutral, etc.)
        intensity: Emotional intensity (0.0 to 1.0)

    Returns:
        Dictionary containing updated mood.
    """
    from server.api.persona import update_mood_endpoint
    from server.projects.persona.models import UpdateMoodRequest

    try:
        request = UpdateMoodRequest(
            user_id=user_id,
            persona_id=persona_id,
            primary_emotion=primary_emotion,
            intensity=intensity,
        )
        result = await update_mood_endpoint(request)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


# ============================================================================
# Conversation Orchestration Tools
# ============================================================================


@mcp.tool
async def orchestrate_conversation(user_id: str, persona_id: str, message: str) -> dict:
    """
    Orchestrate a conversation by coordinating multiple agents and tools.

    This tool coordinates memory, knowledge, persona, and calendar systems
    to generate context-aware responses.

    Args:
        user_id: User ID
        persona_id: Persona ID
        message: User message

    Returns:
        Dictionary containing response and metadata.
    """
    from server.api.conversation import orchestrate_conversation_endpoint
    from server.projects.conversation.models import ConversationRequest

    try:
        request = ConversationRequest(user_id=user_id, persona_id=persona_id, message=message)
        result = await orchestrate_conversation_endpoint(request)
        return result.dict()
    except Exception as e:
        return {"error": str(e), "success": False}


# ============================================================================
# Discord Character Management Tools
# ============================================================================


@mcp.tool
async def add_discord_character(
    channel_id: str, character_id: str, persona_id: str | None = None
) -> dict:
    """
    Add a character to a Discord channel.

    Args:
        channel_id: Discord channel ID
        character_id: Character identifier (persona ID)
        persona_id: Optional persona ID (defaults to character_id)

    Returns:
        Dictionary with success status and message.
    """
    from server.projects.discord_characters.tools import add_discord_character_tool

    try:
        result = await add_discord_character_tool(channel_id, character_id, persona_id)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def remove_discord_character(channel_id: str, character_id: str) -> dict:
    """
    Remove a character from a Discord channel.

    Args:
        channel_id: Discord channel ID
        character_id: Character identifier

    Returns:
        Dictionary with success status and message.
    """
    from server.projects.discord_characters.tools import remove_discord_character_tool

    try:
        result = await remove_discord_character_tool(channel_id, character_id)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def list_discord_characters(channel_id: str) -> list[dict]:
    """
    List all characters in a Discord channel.

    Args:
        channel_id: Discord channel ID

    Returns:
        List of character dictionaries with channel_id, character_id, persona_id, etc.
    """
    from server.projects.discord_characters.tools import list_discord_characters_tool

    try:
        result = await list_discord_characters_tool(channel_id)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def clear_discord_history(channel_id: str, character_id: str | None = None) -> dict:
    """
    Clear conversation history for a Discord channel.

    Args:
        channel_id: Discord channel ID
        character_id: Optional character ID to clear specific character history

    Returns:
        Dictionary with success status and message.
    """
    from server.projects.discord_characters.tools import clear_discord_history_tool

    try:
        result = await clear_discord_history_tool(channel_id, character_id)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


@mcp.tool
async def chat_with_discord_character(
    channel_id: str, character_id: str, user_id: str, message: str
) -> dict:
    """
    Generate a character response to a message in a Discord channel.

    Args:
        channel_id: Discord channel ID
        character_id: Character identifier
        user_id: Discord user ID
        message: User message content

    Returns:
        Dictionary with success status, response text, and character_id.
    """
    from server.projects.discord_characters.tools import chat_with_discord_character_tool

    try:
        result = await chat_with_discord_character_tool(channel_id, character_id, user_id, message)
        return result
    except Exception as e:
        return {"error": str(e), "success": False}


# ============================================================================
# Deep Research Tools
# ============================================================================


@mcp.tool
async def search_web(query: str, engines: list[str] | None = None, result_count: int = 5) -> dict:
    """
    Search the web using SearXNG metasearch engine.

    SearXNG aggregates results from multiple search engines and returns
    ranked, deduplicated results. Use this for current information, real-time
    data, or information not available in the knowledge base.

    Args:
        query: Search query string. Can be a question, phrase, or keywords.
        engines: Optional list of search engine filters. Optional.
        result_count: Number of results to return. Range: 1-20. Default: 5.

    Returns:
        Dictionary containing search results with query, results array, and count.
        Each result includes title, url, snippet, engine, and score.
    """
    from server.projects.deep_research.dependencies import DeepResearchDeps
    from server.projects.deep_research.models import SearchWebRequest
    from server.projects.deep_research.tools import search_web as search_web_tool

    try:
        deps = DeepResearchDeps.from_settings()
        await deps.initialize()

        try:
            request = SearchWebRequest(query=query, engines=engines, result_count=result_count)
            result = await search_web_tool(deps, request)
            return result.dict()
        finally:
            await deps.cleanup()
    except NotImplementedError:
        # Re-raise NotImplementedError as-is
        raise
    except ValidationError as e:
        logger.warning("mcp_validation_error: search_web", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")


@mcp.tool
async def fetch_page(url: str) -> dict:
    """
    Fetch a single web page using Crawl4AI.

    Crawls a webpage and extracts its content as markdown along with metadata.
    The page content can then be parsed and chunked for further processing.

    Args:
        url: URL to fetch. Must be a valid HTTP/HTTPS URL.

    Returns:
        Dictionary containing url, content (markdown), metadata, and success status.
    """
    from server.projects.deep_research.dependencies import DeepResearchDeps
    from server.projects.deep_research.models import FetchPageRequest
    from server.projects.deep_research.tools import fetch_page as fetch_page_tool

    try:
        deps = DeepResearchDeps.from_settings()
        await deps.initialize()

        try:
            request = FetchPageRequest(url=url)
            result = await fetch_page_tool(deps, request)
            return result.dict()
        finally:
            await deps.cleanup()
    except ValidationError as e:
        logger.warning("mcp_validation_error: fetch_page", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(
            "mcp_http_error: fetch_page", extra={"status_code": e.status_code, "detail": e.detail}
        )
        raise RuntimeError(f"Fetch failed: {e.detail}")


@mcp.tool
async def parse_document(
    content: str, content_type: Literal["html", "markdown", "text"] = "html"
) -> dict:
    """
    Parse a document using Docling and chunk it with HybridChunker.

    Converts raw content (HTML, markdown, or text) into structured chunks
    using Docling's document converter and HybridChunker. Preserves document
    structure and creates token-aware chunks suitable for embedding.

    Args:
        content: Raw content to parse (HTML, markdown, or plain text).
        content_type: Content type hint for parsing. Default: "html".

    Returns:
        Dictionary containing chunks (list of structured chunks), metadata, and success status.
    """
    from server.projects.deep_research.dependencies import DeepResearchDeps
    from server.projects.deep_research.models import ParseDocumentRequest
    from server.projects.deep_research.tools import parse_document as parse_document_tool

    try:
        deps = DeepResearchDeps.from_settings()
        await deps.initialize()

        try:
            request = ParseDocumentRequest(content=content, content_type=content_type)
            result = await parse_document_tool(deps, request)
            return result.dict()
        finally:
            await deps.cleanup()
    except ValidationError as e:
        logger.warning("mcp_validation_error: parse_document", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")


@mcp.tool
async def ingest_knowledge(
    chunks: list[dict], session_id: str, source_url: str, title: str | None = None
) -> dict:
    """
    Ingest document chunks into MongoDB (for vector search) and Graphiti (for knowledge graph).

    Takes chunks from parse_document, generates embeddings, and stores them in MongoDB and Neo4j.
    All data is isolated by session_id for multi-tenant support.

    Args:
        chunks: List of document chunks (from parse_document). Each chunk should have:
                content, index, start_char, end_char, metadata, token_count.
        session_id: Session ID for data isolation. All chunks will be tagged with this session.
        source_url: Source URL of the document (for citation).
        title: Optional document title. If not provided, will use "Untitled".

    Returns:
        Dictionary containing document_id, chunks_created, facts_added, success, and errors.
    """
    from server.projects.deep_research.dependencies import DeepResearchDeps
    from server.projects.deep_research.models import DocumentChunk, IngestKnowledgeRequest
    from server.projects.deep_research.tools import ingest_knowledge as ingest_knowledge_tool

    try:
        deps = DeepResearchDeps.from_settings(session_id=session_id)
        await deps.initialize()

        try:
            # Convert dict chunks to DocumentChunk models
            document_chunks = [DocumentChunk(**chunk) for chunk in chunks]

            request = IngestKnowledgeRequest(
                chunks=document_chunks, session_id=session_id, source_url=source_url, title=title
            )
            result = await ingest_knowledge_tool(deps, request)
            return result.dict()
        finally:
            await deps.cleanup()
    except ValidationError as e:
        logger.warning("mcp_validation_error: ingest_knowledge", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")


@mcp.tool
async def query_knowledge(
    question: str,
    session_id: str,
    match_count: int = 5,
    search_type: Literal["semantic", "text", "hybrid"] = "hybrid",
) -> dict:
    """
    Query the knowledge base using hybrid search (vector + text) filtered by session_id.

    Performs semantic search (vector similarity) and/or text search (keyword matching)
    on chunks stored in MongoDB, filtered by session_id. Results are ranked by relevance
    and include citation information.

    Args:
        question: Question or query text to search for.
        session_id: Session ID to filter results. Only returns chunks from this session.
        match_count: Number of results to return. Range: 1-50. Default: 5.
        search_type: Type of search to perform:
                    - "semantic": Vector similarity search only
                    - "text": Keyword/text search only
                    - "hybrid": Combines both using Reciprocal Rank Fusion (default)

    Returns:
        Dictionary containing results (list of cited chunks), count, and success status.
        Each result includes: chunk_id, content, document_id, document_source, similarity, metadata.
    """
    from server.projects.deep_research.dependencies import DeepResearchDeps
    from server.projects.deep_research.models import QueryKnowledgeRequest
    from server.projects.deep_research.tools import query_knowledge as query_knowledge_tool

    try:
        deps = DeepResearchDeps.from_settings(session_id=session_id)
        await deps.initialize()

        try:
            request = QueryKnowledgeRequest(
                question=question,
                session_id=session_id,
                match_count=match_count,
                search_type=search_type,
            )
            result = await query_knowledge_tool(deps, request)
            return result.dict()
        finally:
            await deps.cleanup()
    except ValidationError as e:
        logger.warning("mcp_validation_error: query_knowledge", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
