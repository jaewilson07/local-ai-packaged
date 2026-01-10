"""REST API endpoints for Graphiti RAG and knowledge graph operations."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic_ai import RunContext

from server.core.api_utils import with_dependencies
from server.projects.graphiti_rag.dependencies import GraphitiRAGDeps
from server.projects.graphiti_rag.config import config as graphiti_config
from server.projects.graphiti_rag.models import (
    GraphitiSearchRequest, GraphitiSearchResponse,
    ParseRepositoryRequest, ParseRepositoryResponse,
    ValidateScriptRequest, ValidateScriptResponse,
    QueryKnowledgeGraphRequest, QueryKnowledgeGraphResponse
)
from server.projects.graphiti_rag.tools import (
    search_graphiti_knowledge_graph,
    parse_github_repository,
    validate_ai_script,
    query_knowledge_graph
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/graphiti", tags=["graphiti"])


@router.post("/search", response_model=GraphitiSearchResponse)
@with_dependencies(GraphitiRAGDeps)
async def search_graphiti_endpoint(request: GraphitiSearchRequest, deps: GraphitiRAGDeps):
    """
    Search the Graphiti knowledge graph for entities and relationships.
    
    Requires USE_GRAPHITI=true to be enabled.
    """
    if not graphiti_config.use_graphiti:
        raise HTTPException(
            status_code=400,
            detail="Graphiti is not enabled. Set USE_GRAPHITI=true in environment variables."
        )
    
    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await search_graphiti_knowledge_graph(
            tool_ctx,
            request.query,
            request.match_count
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Search failed")
            )
        
        return GraphitiSearchResponse(
            success=result["success"],
            query=result["query"],
            results=result["results"],
            count=result["count"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error searching Graphiti: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-graph/repositories", response_model=ParseRepositoryResponse)
@with_dependencies(GraphitiRAGDeps)
async def parse_github_repository_endpoint(request: ParseRepositoryRequest, deps: GraphitiRAGDeps):
    """
    Parse a GitHub repository into the Neo4j knowledge graph.
    
    Extracts code structure (classes, methods, functions, imports) for hallucination detection.
    Requires USE_KNOWLEDGE_GRAPH=true to be enabled.
    """
    if not graphiti_config.use_knowledge_graph:
        raise HTTPException(
            status_code=400,
            detail="Knowledge graph is not enabled. Set USE_KNOWLEDGE_GRAPH=true in environment variables."
        )
    
    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await parse_github_repository(tool_ctx, request.repo_url)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Repository parsing failed")
            )
        
        return ParseRepositoryResponse(
            success=result["success"],
            message=result["message"],
            repo_url=result["repo_url"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error parsing repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-graph/validate", response_model=ValidateScriptResponse)
@with_dependencies(GraphitiRAGDeps)
async def validate_ai_script_endpoint(request: ValidateScriptRequest, deps: GraphitiRAGDeps):
    """
    Check an AI-generated Python script for hallucinations using the knowledge graph.
    
    Validates imports, method calls, class instantiations, and function calls against
    real repository data stored in Neo4j.
    Requires USE_KNOWLEDGE_GRAPH=true to be enabled.
    """
    if not graphiti_config.use_knowledge_graph:
        raise HTTPException(
            status_code=400,
            detail="Knowledge graph is not enabled. Set USE_KNOWLEDGE_GRAPH=true in environment variables."
        )
    
    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await validate_ai_script(tool_ctx, request.script_path)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Script validation failed")
            )
        
        return ValidateScriptResponse(
            success=result["success"],
            overall_confidence=result["overall_confidence"],
            validation_summary=result["validation_summary"],
            hallucinations_detected=result["hallucinations_detected"],
            recommendations=result["recommendations"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error validating script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-graph/query", response_model=QueryKnowledgeGraphResponse)
@with_dependencies(GraphitiRAGDeps)
async def query_knowledge_graph_endpoint(request: QueryKnowledgeGraphRequest, deps: GraphitiRAGDeps):
    """
    Query and explore the Neo4j knowledge graph containing repository code structure.
    
    Supported commands:
    - 'repos': List all repositories
    - 'explore <repo>': Get statistics for a repository
    - 'query <cypher>': Execute a Cypher query
    
    Requires USE_KNOWLEDGE_GRAPH=true to be enabled.
    """
    if not graphiti_config.use_knowledge_graph:
        raise HTTPException(
            status_code=400,
            detail="Knowledge graph is not enabled. Set USE_KNOWLEDGE_GRAPH=true in environment variables."
        )
    
    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await query_knowledge_graph(tool_ctx, request.command)
        
        return QueryKnowledgeGraphResponse(
            success=result.get("success", False),
            data=result.get("data"),
            error=result.get("error")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error querying knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

