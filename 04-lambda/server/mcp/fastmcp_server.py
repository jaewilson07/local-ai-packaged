"""FastMCP server for Lambda multi-project server.

This module replaces the custom MCP server implementation with FastMCP 2.0,
providing automatic schema generation from type hints and cleaner code.
"""

import json
import logging
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path
from pydantic import ValidationError
from fastapi import HTTPException
from pymongo.errors import ConnectionFailure, OperationFailure

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP("Lambda Server")


# ============================================================================
# MongoDB RAG Tools
# ============================================================================

@mcp.tool
async def search_knowledge_base(
    query: str,
    match_count: int = 5,
    search_type: Literal["semantic", "text", "hybrid"] = "hybrid"
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
        result = await search(SearchRequest(
            query=query,
            match_count=match_count,
            search_type=search_type
        ))
        return result.dict()
    except ValidationError as e:
        logger.warning(f"mcp_validation_error: search_knowledge_base", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(f"mcp_http_error: search_knowledge_base", extra={"status_code": e.status_code, "detail": e.detail})
        raise RuntimeError(f"Search failed: {e.detail}")
    except (ConnectionFailure, OperationFailure) as e:
        logger.error(f"mcp_database_error: search_knowledge_base", extra={"error": str(e)})
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
        logger.warning(f"mcp_validation_error: agent_query", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(f"mcp_http_error: agent_query", extra={"status_code": e.status_code, "detail": e.detail})
        raise RuntimeError(f"Agent query failed: {e.detail}")
    except Exception as e:
        logger.exception(f"mcp_tool_error: agent_query")
        raise RuntimeError(f"An unexpected error occurred: {e}")


@mcp.tool
async def ingest_documents(file_paths: List[str], clean_before: bool = False) -> dict:
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
            "details": "Use REST API POST /api/v1/rag/ingest for file uploads"
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
        logger.warning(f"mcp_validation_error: search_code_examples", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(f"mcp_http_error: search_code_examples", extra={"status_code": e.status_code, "detail": e.detail})
        raise RuntimeError(f"Search failed: {e.detail}")
    except Exception as e:
        logger.exception(f"mcp_tool_error: search_code_examples")
        raise RuntimeError(f"An unexpected error occurred: {e}")


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
        logger.warning(f"mcp_http_error: get_available_sources", extra={"status_code": e.status_code, "detail": e.detail})
        raise RuntimeError(f"Failed to get sources: {e.detail}")
    except Exception as e:
        logger.exception(f"mcp_tool_error: get_available_sources")
        raise RuntimeError(f"An unexpected error occurred: {e}")


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
    from server.api.graphiti_rag import search_graphiti
    from server.projects.graphiti_rag.models import GraphitiSearchRequest
    
    try:
        request = GraphitiSearchRequest(query=query, match_count=match_count)
        result = await search_graphiti(request)
        return result.dict()
    except ValidationError as e:
        logger.warning(f"mcp_validation_error: search_graphiti", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(f"mcp_http_error: search_graphiti", extra={"status_code": e.status_code, "detail": e.detail})
        raise RuntimeError(f"Search failed: {e.detail}")
    except Exception as e:
        logger.exception(f"mcp_tool_error: search_graphiti")
        raise RuntimeError(f"An unexpected error occurred: {e}")


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
    from server.api.graphiti_rag import parse_github_repository
    from server.projects.graphiti_rag.models import ParseRepositoryRequest
    
    try:
        request = ParseRepositoryRequest(repo_url=repo_url)
        result = await parse_github_repository(request)
        return result.dict()
    except ValidationError as e:
        logger.warning(f"mcp_validation_error: parse_github_repository", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(f"mcp_http_error: parse_github_repository", extra={"status_code": e.status_code, "detail": e.detail})
        raise RuntimeError(f"Parse failed: {e.detail}")
    except Exception as e:
        logger.exception(f"mcp_tool_error: parse_github_repository")
        raise RuntimeError(f"An unexpected error occurred: {e}")


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
    from server.api.graphiti_rag import validate_ai_script
    from server.projects.graphiti_rag.models import ValidateScriptRequest
    
    try:
        request = ValidateScriptRequest(script_path=script_path)
        result = await validate_ai_script(request)
        return result.dict()
    except ValidationError as e:
        logger.warning(f"mcp_validation_error: check_ai_script_hallucinations", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(f"mcp_http_error: check_ai_script_hallucinations", extra={"status_code": e.status_code, "detail": e.detail})
        raise RuntimeError(f"Validation failed: {e.detail}")
    except Exception as e:
        logger.exception(f"mcp_tool_error: check_ai_script_hallucinations")
        raise RuntimeError(f"An unexpected error occurred: {e}")


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
    from server.api.graphiti_rag import query_knowledge_graph
    
    try:
        result = await query_knowledge_graph(command)
        return result.dict()
    except HTTPException as e:
        logger.warning(f"mcp_http_error: query_knowledge_graph", extra={"status_code": e.status_code, "detail": e.detail})
        raise RuntimeError(f"Query failed: {e.detail}")
    except Exception as e:
        logger.exception(f"mcp_tool_error: query_knowledge_graph")
        raise RuntimeError(f"An unexpected error occurred: {e}")


# ============================================================================
# Crawl4AI Tools
# ============================================================================

@mcp.tool
async def crawl_single_page(
    url: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> dict:
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
            url=url,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        result = await crawl_single(request)
        return result.dict()
    except Exception as e:
        logger.exception(f"mcp_tool_error: crawl_single_page")
        raise RuntimeError(f"Crawl failed: {e}")


@mcp.tool
async def crawl_deep(
    url: str,
    max_depth: int,
    allowed_domains: Optional[List[str]] = None,
    allowed_subdomains: Optional[List[str]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
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
            chunk_overlap=chunk_overlap
        )
        result = await crawl_deep_endpoint(request)
        return result.dict()
    except Exception as e:
        logger.exception(f"mcp_tool_error: crawl_deep")
        raise RuntimeError(f"Deep crawl failed: {e}")


# ============================================================================
# SearXNG Tools
# ============================================================================

@mcp.tool
async def web_search(
    query: str,
    result_count: int = 10,
    categories: Optional[str] = None,
    engines: Optional[List[str]] = None
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
    from server.api.searxng import search, SearXNGSearchRequest
    
    try:
        request = SearXNGSearchRequest(
            query=query,
            result_count=result_count,
            categories=categories,
            engines=engines
        )
        result = await search(request)
        return result.dict()
    except ValidationError as e:
        logger.warning(f"mcp_validation_error: web_search", extra={"errors": e.errors()})
        raise ValueError(f"Invalid parameters: {e}")
    except HTTPException as e:
        logger.warning(f"mcp_http_error: web_search", extra={"status_code": e.status_code, "detail": e.detail})
        raise RuntimeError(f"Web search failed: {e.detail}")
    except Exception as e:
        logger.exception(f"mcp_tool_error: web_search")
        raise RuntimeError(f"An unexpected error occurred: {e}")


# ============================================================================
# N8N Workflow Tools
# ============================================================================

@mcp.tool
async def create_n8n_workflow(
    name: str,
    nodes: Optional[List[Dict[str, Any]]] = None,
    connections: Optional[Dict[str, Any]] = None,
    active: bool = False,
    settings: Optional[Dict[str, Any]] = None
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
                WorkflowNode(**node) if isinstance(node, dict) else node
                for node in nodes
            ]
        
        request = CreateWorkflowRequest(
            name=name,
            nodes=workflow_nodes or [],
            connections=connections or {},
            active=active,
            settings=settings or {}
        )
        result = await create_workflow_endpoint(request)
        return result.dict()
    except Exception as e:
        logger.exception(f"mcp_tool_error: create_n8n_workflow")
        raise RuntimeError(f"Failed to create workflow: {e}")


@mcp.tool
async def update_n8n_workflow(
    workflow_id: str,
    name: Optional[str] = None,
    nodes: Optional[List[Dict[str, Any]]] = None,
    connections: Optional[Dict[str, Any]] = None,
    active: Optional[bool] = None,
    settings: Optional[Dict[str, Any]] = None
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
                WorkflowNode(**node) if isinstance(node, dict) else node
                for node in nodes
            ]
        
        request = UpdateWorkflowRequest(
            workflow_id=workflow_id,
            name=name,
            nodes=workflow_nodes,
            connections=connections,
            active=active,
            settings=settings
        )
        result = await update_workflow_endpoint(request)
        return result.dict()
    except Exception as e:
        logger.exception(f"mcp_tool_error: update_n8n_workflow")
        raise RuntimeError(f"Failed to update workflow: {e}")


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
        logger.exception(f"mcp_tool_error: delete_n8n_workflow")
        raise RuntimeError(f"Failed to delete workflow: {e}")


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
        logger.exception(f"mcp_tool_error: activate_n8n_workflow")
        raise RuntimeError(f"Failed to activate/deactivate workflow: {e}")


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
        logger.exception(f"mcp_tool_error: list_n8n_workflows")
        raise RuntimeError(f"Failed to list workflows: {e}")


@mcp.tool
async def execute_n8n_workflow(
    workflow_id: str,
    input_data: Optional[Dict[str, Any]] = None
) -> dict:
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
        request = ExecuteWorkflowRequest(
            workflow_id=workflow_id,
            input_data=input_data or {}
        )
        result = await execute_workflow_endpoint(request)
        return result.dict()
    except Exception as e:
        logger.exception(f"mcp_tool_error: execute_n8n_workflow")
        raise RuntimeError(f"Failed to execute workflow: {e}")


@mcp.tool
async def scrape_event_to_calendar(
    url: str,
    event_name_pattern: Optional[str] = None,
    calendar_id: str = "primary",
    timezone: str = "America/New_York",
    location_pattern: Optional[str] = None,
    description_template: Optional[str] = None,
    workflow_name: str = "Scrape Event To Calendar"
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
    from server.config import settings
    
    try:
        # Call the REST API endpoint
        api_url = f"http://localhost:8000/api/v1/calendar/sync"
        payload = {
            "url": url,
            "calendar_id": calendar_id,
            "timezone": timezone
        }
        
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
                "message": result.get("message")
            }
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if e.response else str(e)
        logger.exception(f"mcp_tool_error: scrape_event_to_calendar HTTP {e.response.status_code}")
        raise RuntimeError(f"Calendar sync failed: {error_detail}")
    except Exception as e:
        logger.exception(f"mcp_tool_error: scrape_event_to_calendar")
        raise RuntimeError(f"Failed to scrape event to calendar: {e}")


@mcp.tool
async def discover_n8n_nodes(category: Optional[str] = None) -> str:
    """
    Discover available N8n nodes via API.
    
    Returns list of available node types with descriptions. Use this to see what
    nodes are available before creating workflows.
    
    Args:
        category: Optional category filter (e.g., 'trigger', 'action', 'data').
    
    Returns:
        String containing formatted list of available nodes.
    """
    from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
    from server.projects.n8n_workflow.tools import discover_n8n_nodes
    from pydantic_ai import RunContext
    
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
    query: str,
    match_count: int = 5,
    search_type: Literal["semantic", "text", "hybrid"] = "hybrid"
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
    from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
    from server.projects.n8n_workflow.tools import search_n8n_knowledge_base
    from pydantic_ai import RunContext
    
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
    try:
        result = await search_n8n_knowledge_base(
            run_ctx,
            query,
            match_count,
            search_type
        )
        return result
    finally:
        await deps.cleanup()


@mcp.tool
async def search_n8n_node_examples(
    node_type: Optional[str] = None,
    query: Optional[str] = None,
    match_count: int = 5
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
    from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
    from server.projects.n8n_workflow.tools import search_node_examples
    from pydantic_ai import RunContext
    
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
    try:
        result = await search_node_examples(
            run_ctx,
            node_type,
            query,
            match_count
        )
        return result
    finally:
        await deps.cleanup()


# ============================================================================
# Open WebUI Tools
# ============================================================================

@mcp.tool
async def export_openwebui_conversation(
    conversation_id: str,
    messages: List[Dict[str, Any]],
    user_id: Optional[str] = None,
    title: Optional[str] = None,
    topics: Optional[List[str]] = None
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
    from server.api.openwebui_export import export_conversation
    from server.projects.openwebui_export.models import ConversationExportRequest, ConversationMessage
    
    try:
        # Convert messages to ConversationMessage objects
        conversation_messages = [
            ConversationMessage(**msg) if isinstance(msg, dict) else msg
            for msg in messages
        ]
        
        request = ConversationExportRequest(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            messages=conversation_messages,
            topics=topics,
            metadata={}
        )
        result = await export_conversation(request)
        return result.dict()
    except Exception as e:
        logger.exception(f"mcp_tool_error: export_openwebui_conversation")
        raise RuntimeError(f"Failed to export conversation: {e}")


@mcp.tool
async def classify_conversation_topics(
    conversation_id: str,
    messages: List[Dict[str, Any]],
    title: Optional[str] = None,
    existing_topics: Optional[List[str]] = None
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
    from server.api.openwebui_topics import classify_topics
    from server.projects.openwebui_topics.models import TopicClassificationRequest
    
    try:
        request = TopicClassificationRequest(
            conversation_id=conversation_id,
            title=title,
            messages=messages,
            existing_topics=existing_topics
        )
        result = await classify_topics(request)
        return result.dict()
    except Exception as e:
        logger.exception(f"mcp_tool_error: classify_conversation_topics")
        raise RuntimeError(f"Failed to classify topics: {e}")


@mcp.tool
async def search_conversations(
    query: str,
    match_count: int = 5,
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    topics: Optional[List[str]] = None
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
            topics=topics
        )
        result = await search(request)
        return result.dict()
    except Exception as e:
        logger.exception(f"mcp_tool_error: search_conversations")
        raise RuntimeError(f"Failed to search conversations: {e}")

