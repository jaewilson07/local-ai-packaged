"""REST API endpoints for Graphiti RAG and knowledge graph operations."""

import logging
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any

from server.projects.graphiti_rag.search.graph_search import graphiti_search
from server.projects.graphiti_rag.dependencies import GraphitiRAGDeps
from server.projects.graphiti_rag.config import config as graphiti_config
from server.projects.graphiti_rag.models import (
    GraphitiSearchRequest, GraphitiSearchResponse,
    ParseRepositoryRequest, ParseRepositoryResponse,
    ValidateScriptRequest, ValidateScriptResponse,
    QueryKnowledgeGraphResponse
)
from server.projects.graphiti_rag.knowledge_graphs.repository_parser import DirectNeo4jExtractor
from server.projects.graphiti_rag.knowledge_graphs.ai_script_analyzer import AIScriptAnalyzer
from server.projects.graphiti_rag.knowledge_graphs.hallucination_validator import KnowledgeGraphValidator
from server.projects.graphiti_rag.knowledge_graphs.hallucination_reporter import HallucinationReporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/graphiti", tags=["graphiti"])


@router.post("/search", response_model=GraphitiSearchResponse)
async def search_graphiti(request: GraphitiSearchRequest):
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
        deps = GraphitiRAGDeps.from_settings()
        await deps.initialize()
        
        if not deps.graphiti:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize Graphiti client"
            )
        
        results = await graphiti_search(
            deps.graphiti,
            request.query,
            request.match_count
        )
        
        await deps.cleanup()
        
        formatted_results = [
            {
                "uuid": r.chunk_id,
                "fact": r.content,
                "similarity": r.similarity,
                "metadata": r.metadata
            }
            for r in results
        ]
        
        return GraphitiSearchResponse(
            success=True,
            query=request.query,
            results=formatted_results,
            count=len(formatted_results)
        )
        
    except Exception as e:
        logger.exception(f"Error searching Graphiti: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-graph/repositories", response_model=ParseRepositoryResponse)
async def parse_github_repository(request: ParseRepositoryRequest):
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
        extractor = DirectNeo4jExtractor(
            graphiti_config.neo4j_uri,
            graphiti_config.neo4j_user,
            graphiti_config.neo4j_password
        )
        await extractor.initialize()
        
        try:
            await extractor.analyze_repository(request.repo_url)
            return ParseRepositoryResponse(
                success=True,
                message=f"Repository {request.repo_url} parsed successfully",
                repo_url=request.repo_url
            )
        finally:
            await extractor.close()
            
    except Exception as e:
        logger.exception(f"Error parsing repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-graph/validate", response_model=ValidateScriptResponse)
async def validate_ai_script(request: ValidateScriptRequest):
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
        validator = KnowledgeGraphValidator(
            graphiti_config.neo4j_uri,
            graphiti_config.neo4j_user,
            graphiti_config.neo4j_password
        )
        await validator.initialize()
        
        try:
            analyzer = AIScriptAnalyzer()
            analysis = analyzer.analyze_script(request.script_path)
            validation = await validator.validate_script(analysis)
            reporter = HallucinationReporter()
            report = reporter.generate_comprehensive_report(validation)
            
            return ValidateScriptResponse(
                success=True,
                overall_confidence=validation.overall_confidence,
                validation_summary=report["validation_summary"],
                hallucinations_detected=report["hallucinations_detected"],
                recommendations=report["recommendations"]
            )
        finally:
            await validator.close()
            
    except Exception as e:
        logger.exception(f"Error validating script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-graph/query", response_model=QueryKnowledgeGraphResponse)
async def query_knowledge_graph(command: str):
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
        extractor = DirectNeo4jExtractor(
            graphiti_config.neo4j_uri,
            graphiti_config.neo4j_user,
            graphiti_config.neo4j_password
        )
        await extractor.initialize()
        
        try:
            parts = command.strip().split()
            cmd = parts[0].lower() if parts else ""
            
            async with extractor.driver.session() as session:
                if cmd == "repos":
                    result_query = await session.run("MATCH (r:Repository) RETURN r.name as name ORDER BY r.name")
                    repos = [record['name'] async for record in result_query]
                    return QueryKnowledgeGraphResponse(
                        success=True,
                        data={"repositories": repos}
                    )
                elif cmd == "explore" and len(parts) > 1:
                    repo_name = parts[1]
                    stats_query = """
                    MATCH (r:Repository {name: $repo_name})
                    OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
                    OPTIONAL MATCH (f)-[:DEFINES]->(c:Class)
                    OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
                    OPTIONAL MATCH (f)-[:DEFINES]->(func:Function)
                    RETURN count(DISTINCT f) as files, count(DISTINCT c) as classes, 
                           count(DISTINCT m) as methods, count(DISTINCT func) as functions
                    """
                    result_query = await session.run(stats_query, repo_name=repo_name)
                    record = await result_query.single()
                    if record:
                        return QueryKnowledgeGraphResponse(
                            success=True,
                            data={"repository": repo_name, "statistics": dict(record)}
                        )
                    else:
                        return QueryKnowledgeGraphResponse(
                            success=False,
                            error=f"Repository '{repo_name}' not found"
                        )
                elif cmd == "query" and len(parts) > 1:
                    cypher = " ".join(parts[1:])
                    result_query = await session.run(cypher)
                    records = [dict(record) async for record in result_query][:20]
                    return QueryKnowledgeGraphResponse(
                        success=True,
                        data={"query": cypher, "results": records}
                    )
                else:
                    return QueryKnowledgeGraphResponse(
                        success=False,
                        error=f"Unknown command: {command}. Use: repos, explore <repo>, query <cypher>"
                    )
        finally:
            await extractor.close()
            
    except Exception as e:
        logger.exception(f"Error querying knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

