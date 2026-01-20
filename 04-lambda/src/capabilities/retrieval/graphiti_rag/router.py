"""REST API endpoints for Graphiti RAG and knowledge graph operations."""

import logging
from typing import Annotated

from capabilities.retrieval.graphiti_rag.config import config as graphiti_config
from capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps
from capabilities.retrieval.graphiti_rag.models import (
    GraphitiSearchRequest,
    GraphitiSearchResponse,
    ParseRepositoryRequest,
    ParseRepositoryResponse,
    QueryKnowledgeGraphRequest,
    QueryKnowledgeGraphResponse,
    ValidateScriptRequest,
    ValidateScriptResponse,
)
from capabilities.retrieval.graphiti_rag.tools import (
    parse_github_repository,
    query_knowledge_graph,
    search_graphiti_knowledge_graph,
    validate_ai_script,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai import RunContext

from shared.dependency_factory import create_dependency_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/graphiti", tags=["graphiti"])

# Use dependency factory to create deps getter (eliminates boilerplate)
get_graphiti_rag_deps = create_dependency_factory(GraphitiRAGDeps)


@router.post("/search", response_model=GraphitiSearchResponse)
async def search_graphiti_endpoint(
    request: GraphitiSearchRequest, deps: Annotated[GraphitiRAGDeps, Depends(get_graphiti_rag_deps)]
):
    """
    Search the Graphiti knowledge graph for entities and relationships.

    Requires USE_GRAPHITI=true to be enabled.
    """
    if not graphiti_config.use_graphiti:
        raise HTTPException(
            status_code=400,
            detail="Graphiti is not enabled. Set USE_GRAPHITI=true in environment variables.",
        )

    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await search_graphiti_knowledge_graph(tool_ctx, request.query, request.match_count)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Search failed"))

        return GraphitiSearchResponse(
            success=result["success"],
            query=result["query"],
            results=result["results"],
            count=result["count"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Error searching Graphiti")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/knowledge-graph/repositories", response_model=ParseRepositoryResponse)
async def parse_github_repository_endpoint(
    request: ParseRepositoryRequest,
    deps: Annotated[GraphitiRAGDeps, Depends(get_graphiti_rag_deps)],
):
    """
    Parse a GitHub repository into the Neo4j knowledge graph.

    Extracts code structure (classes, methods, functions, imports) for hallucination detection.
    Requires USE_KNOWLEDGE_GRAPH=true to be enabled.
    """
    if not graphiti_config.use_knowledge_graph:
        raise HTTPException(
            status_code=400,
            detail="Knowledge graph is not enabled. Set USE_KNOWLEDGE_GRAPH=true in environment variables.",
        )

    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await parse_github_repository(tool_ctx, request.repo_url)

        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get("error", "Repository parsing failed")
            )

        return ParseRepositoryResponse(
            success=result["success"], message=result["message"], repo_url=result["repo_url"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Error parsing repository")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/knowledge-graph/validate", response_model=ValidateScriptResponse)
async def validate_ai_script_endpoint(
    request: ValidateScriptRequest, deps: Annotated[GraphitiRAGDeps, Depends(get_graphiti_rag_deps)]
):
    """
    Check an AI-generated Python script for hallucinations using the knowledge graph.

    Validates imports, method calls, class instantiations, and function calls against
    real repository data stored in Neo4j.
    Requires USE_KNOWLEDGE_GRAPH=true to be enabled.
    """
    if not graphiti_config.use_knowledge_graph:
        raise HTTPException(
            status_code=400,
            detail="Knowledge graph is not enabled. Set USE_KNOWLEDGE_GRAPH=true in environment variables.",
        )

    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await validate_ai_script(tool_ctx, request.script_path)

        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get("error", "Script validation failed")
            )

        return ValidateScriptResponse(
            success=result["success"],
            overall_confidence=result["overall_confidence"],
            validation_summary=result["validation_summary"],
            hallucinations_detected=result["hallucinations_detected"],
            recommendations=result["recommendations"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Error validating script")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/knowledge-graph/query", response_model=QueryKnowledgeGraphResponse)
async def query_knowledge_graph_endpoint(
    request: QueryKnowledgeGraphRequest,
    deps: Annotated[GraphitiRAGDeps, Depends(get_graphiti_rag_deps)],
):
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
            detail="Knowledge graph is not enabled. Set USE_KNOWLEDGE_GRAPH=true in environment variables.",
        )

    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await query_knowledge_graph(tool_ctx, request.command)

        return QueryKnowledgeGraphResponse(
            success=result.get("success", False), data=result.get("data"), error=result.get("error")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Error querying knowledge graph")
        raise HTTPException(status_code=500, detail=str(e)) from e
