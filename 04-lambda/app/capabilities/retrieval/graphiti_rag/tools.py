"""Core capability functions for Graphiti RAG operations."""

import logging
from typing import Any

from app.capabilities.retrieval.graphiti_rag.config import config
from app.capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps
from app.capabilities.retrieval.graphiti_rag.knowledge_graphs.ai_script_analyzer import AIScriptAnalyzer
from app.capabilities.retrieval.graphiti_rag.knowledge_graphs.hallucination_reporter import (
    HallucinationReporter,
)
from app.capabilities.retrieval.graphiti_rag.knowledge_graphs.hallucination_validator import (
    KnowledgeGraphValidator,
)
from app.capabilities.retrieval.graphiti_rag.knowledge_graphs.repository_parser import (
    DirectNeo4jExtractor,
)
from app.capabilities.retrieval.graphiti_rag.search.graph_search import graphiti_search
from pydantic_ai import RunContext

logger = logging.getLogger(__name__)


async def search_graphiti_knowledge_graph(
    ctx: RunContext[GraphitiRAGDeps], query: str, match_count: int = 10
) -> dict[str, Any]:
    """
    Search the Graphiti knowledge graph for entities and relationships.

    This function performs hybrid search (semantic + keyword + graph traversal)
    to find relevant facts and relationships in the knowledge graph.

    Args:
        ctx: Runtime context with Graphiti dependencies
        query: Search query text
        match_count: Maximum number of results to return (1-50)

    Returns:
        Dictionary with search results including facts, metadata, and similarity scores
    """
    if not ctx.deps.graphiti:
        raise ValueError("Graphiti client is not initialized. Ensure USE_GRAPHITI=true.")

    try:
        results = await graphiti_search(ctx.deps.graphiti, query, match_count)

        formatted_results = [
            {
                "uuid": r.chunk_id,
                "fact": r.content,
                "similarity": r.similarity,
                "metadata": r.metadata,
            }
            for r in results
        ]

        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results),
        }
    except Exception as e:
        logger.exception("Error searching Graphiti")
        return {"success": False, "query": query, "results": [], "count": 0, "error": str(e)}


async def parse_github_repository(
    ctx: RunContext[GraphitiRAGDeps], repo_url: str
) -> dict[str, Any]:
    """
    Parse a GitHub repository into the Neo4j knowledge graph.

    Extracts code structure (classes, methods, functions, imports) for hallucination
    detection. Creates nodes and relationships directly in Neo4j without LLM processing.

    Args:
        ctx: Runtime context with Graphiti dependencies
        repo_url: GitHub repository URL (must end with .git)

    Returns:
        Dictionary with success status and message
    """
    if not config.use_knowledge_graph:
        raise ValueError("Knowledge graph is not enabled. Set USE_KNOWLEDGE_GRAPH=true.")

    if not repo_url.endswith(".git"):
        raise ValueError("Repository URL must end with .git")

    extractor = DirectNeo4jExtractor(config.neo4j_uri, config.neo4j_user, config.neo4j_password)

    try:
        await extractor.initialize()
        await extractor.analyze_repository(repo_url)

        return {
            "success": True,
            "message": f"Repository {repo_url} parsed successfully",
            "repo_url": repo_url,
        }
    except Exception as e:
        logger.exception("Error parsing repository")
        return {
            "success": False,
            "message": f"Failed to parse repository: {e!s}",
            "repo_url": repo_url,
            "error": str(e),
        }
    finally:
        await extractor.close()


async def validate_ai_script(ctx: RunContext[GraphitiRAGDeps], script_path: str) -> dict[str, Any]:
    """
    Check an AI-generated Python script for hallucinations using the knowledge graph.

    Validates imports, method calls, class instantiations, and function calls against
    real repository data stored in Neo4j.

    Args:
        ctx: Runtime context with Graphiti dependencies
        script_path: Absolute path to the Python script to validate

    Returns:
        Dictionary with validation results including confidence, hallucinations, and recommendations
    """
    if not config.use_knowledge_graph:
        raise ValueError("Knowledge graph is not enabled. Set USE_KNOWLEDGE_GRAPH=true.")

    validator = KnowledgeGraphValidator(config.neo4j_uri, config.neo4j_user, config.neo4j_password)

    try:
        await validator.initialize()

        analyzer = AIScriptAnalyzer()
        analysis = analyzer.analyze_script(script_path)
        validation = await validator.validate_script(analysis)
        reporter = HallucinationReporter()
        report = reporter.generate_comprehensive_report(validation)

        return {
            "success": True,
            "overall_confidence": validation.overall_confidence,
            "validation_summary": report["validation_summary"],
            "hallucinations_detected": report["hallucinations_detected"],
            "recommendations": report["recommendations"],
        }
    except Exception as e:
        logger.exception("Error validating script")
        return {
            "success": False,
            "overall_confidence": 0.0,
            "validation_summary": f"Validation failed: {e!s}",
            "hallucinations_detected": [],
            "recommendations": [],
            "error": str(e),
        }
    finally:
        await validator.close()


async def query_knowledge_graph(ctx: RunContext[GraphitiRAGDeps], command: str) -> dict[str, Any]:
    """
    Query and explore the Neo4j knowledge graph containing repository code structure.

    Supported commands:
    - 'repos': List all repositories
    - 'explore <repo>': Get statistics for a repository
    - 'query <cypher>': Execute a Cypher query

    Args:
        ctx: Runtime context with Graphiti dependencies
        command: Command to execute (e.g., 'repos', 'explore <repo>', 'query <cypher>')

    Returns:
        Dictionary with query results or error message
    """
    if not config.use_knowledge_graph:
        raise ValueError("Knowledge graph is not enabled. Set USE_KNOWLEDGE_GRAPH=true.")

    extractor = DirectNeo4jExtractor(config.neo4j_uri, config.neo4j_user, config.neo4j_password)

    try:
        await extractor.initialize()

        parts = command.strip().split()
        cmd = parts[0].lower() if parts else ""

        async with extractor.driver.session() as session:
            if cmd == "repos":
                result_query = await session.run(
                    "MATCH (r:Repository) RETURN r.name as name ORDER BY r.name"
                )
                repos = [record["name"] async for record in result_query]
                return {"success": True, "data": {"repositories": repos}}
            if cmd == "explore" and len(parts) > 1:
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
                    return {
                        "success": True,
                        "data": {"repository": repo_name, "statistics": dict(record)},
                    }
                return {"success": False, "error": f"Repository '{repo_name}' not found"}
            if cmd == "query" and len(parts) > 1:
                cypher = " ".join(parts[1:])
                result_query = await session.run(cypher)
                records = [dict(record) async for record in result_query][:20]
                return {"success": True, "data": {"query": cypher, "results": records}}
            return {
                "success": False,
                "error": f"Unknown command: {command}. Use: repos, explore <repo>, query <cypher>",
            }
    except Exception as e:
        logger.exception("Error querying knowledge graph")
        return {"success": False, "error": str(e)}
    finally:
        await extractor.close()
