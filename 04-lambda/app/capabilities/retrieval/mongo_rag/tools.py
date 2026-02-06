"""Search tools for MongoDB RAG Agent."""

import asyncio
import logging
from typing import Any

from app.capabilities.retrieval.mongo_rag.config import config
from app.capabilities.retrieval.mongo_rag.dependencies import AgentDependencies
from app.capabilities.retrieval.mongo_rag.reranking.reranker import get_reranker, initialize_reranker
from app.capabilities.retrieval.mongo_rag.rls import build_access_filter
from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from pymongo.errors import OperationFailure
from app.core.exceptions import MongoDBException

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """Model for search results."""

    chunk_id: str = Field(..., description="MongoDB ObjectId of chunk as string")
    document_id: str = Field(..., description="Parent document ObjectId as string")
    content: str = Field(..., description="Chunk text content")
    similarity: float = Field(..., description="Relevance score (0-1)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    document_title: str = Field(..., description="Title from document lookup")
    document_source: str = Field(..., description="Source from document lookup")


async def semantic_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: int | None = None,
    filter_dict: dict[str, Any] | None = None,
) -> list[SearchResult]:
    """
    Perform pure semantic search using MongoDB vector similarity.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (default: 10)

    Returns:
        List of search results ordered by similarity

    Raises:
        OperationFailure: If MongoDB operation fails (e.g., missing index)
    """
    try:
        deps = ctx.deps

        # Use default if not specified
        if match_count is None:
            match_count = deps.settings.default_match_count

        # Validate match count
        match_count = min(match_count, deps.settings.max_match_count)

        # Generate embedding for query (already returns list[float])
        query_embedding = await deps.get_embedding(query)

        # Build MongoDB aggregation pipeline
        vector_search_stage = {
            "$vectorSearch": {
                "index": deps.settings.mongodb_vector_index,
                "queryVector": query_embedding,
                "path": "embedding",
                "numCandidates": 100,  # Search space (10x limit is good default)
                "limit": match_count,
            }
        }

        # Add filter to vector search if provided (chunk-level filters only)
        # Note: RLS filtering happens at document level in $lookup
        if filter_dict:
            vector_search_stage["$vectorSearch"]["filter"] = filter_dict

        # Build document access filter for RLS
        document_access_filter = build_access_filter(
            current_user_id=deps.current_user_id or "",
            current_user_email=deps.current_user_email or "",
            user_groups=deps.user_groups,
            is_admin=deps.is_admin,
        )

        pipeline = [
            vector_search_stage,
            {
                "$lookup": {
                    "from": deps.settings.mongodb_collection_documents,
                    "localField": "document_id",
                    "foreignField": "_id",
                    "as": "document_info",
                    "pipeline": [
                        (
                            {"$match": document_access_filter}
                            if document_access_filter
                            else {"$match": {}}
                        )
                    ],
                }
            },
            {"$unwind": "$document_info"},
            # Filter out chunks whose documents don't match RLS (empty document_info after unwind)
            {"$match": {"document_info": {"$exists": True, "$ne": {}}}},
            {
                "$project": {
                    "chunk_id": "$_id",
                    "document_id": 1,
                    "content": 1,
                    "similarity": {"$meta": "vectorSearchScore"},
                    "metadata": 1,
                    "document_title": "$document_info.title",
                    "document_source": "$document_info.source",
                }
            },
        ]

        # Execute aggregation
        collection = deps.db[deps.settings.mongodb_collection_chunks]
        cursor = await collection.aggregate(pipeline)
        results = [doc async for doc in cursor][:match_count]

        # Convert to SearchResult objects (ObjectId → str conversion)
        search_results = [
            SearchResult(
                chunk_id=str(doc["chunk_id"]),
                document_id=str(doc["document_id"]),
                content=doc["content"],
                similarity=doc["similarity"],
                metadata=doc.get("metadata", {}),
                document_title=doc["document_title"],
                document_source=doc["document_source"],
            )
            for doc in results
        ]

        logger.info(
            f"semantic_search_completed: query={query}, results={len(search_results)}, match_count={match_count}"
        )

        return search_results

    except OperationFailure as e:
        error_code = e.code if hasattr(e, "code") else None
        logger.exception(f"semantic_search_failed: query={query}, error={e!s}, code={error_code}")
        # Return empty list on error (graceful degradation)
        return []
    except Exception as e:
        logger.exception(f"semantic_search_error: query={query}, error={e!s}")
        return []


async def text_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: int | None = None,
    filter_dict: dict[str, Any] | None = None,
) -> list[SearchResult]:
    """
    Perform full-text search using MongoDB Atlas Search.

    Uses $search operator for keyword matching, fuzzy matching, and phrase matching.
    Works on all Atlas tiers including M0 (free tier).

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (default: 10)

    Returns:
        List of search results ordered by text relevance

    Raises:
        OperationFailure: If MongoDB operation fails (e.g., missing index)
    """
    try:
        deps = ctx.deps

        # Use default if not specified
        if match_count is None:
            match_count = deps.settings.default_match_count

        # Validate match count
        match_count = min(match_count, deps.settings.max_match_count)

        # Build document access filter for RLS
        document_access_filter = build_access_filter(
            current_user_id=deps.current_user_id or "",
            current_user_email=deps.current_user_email or "",
            user_groups=deps.user_groups,
            is_admin=deps.is_admin,
        )

        # Build MongoDB Atlas Search aggregation pipeline
        search_stage = {
            "$search": {
                "index": deps.settings.mongodb_text_index,
                "text": {
                    "query": query,
                    "path": "content",
                    "fuzzy": {"maxEdits": 2, "prefixLength": 3},
                },
            }
        }

        # Add filter to search if provided
        if filter_dict:
            search_stage["$search"]["filter"] = filter_dict

        pipeline = [
            search_stage,
            {"$limit": match_count * 2},  # Over-fetch for better RRF results
            {
                "$lookup": {
                    "from": deps.settings.mongodb_collection_documents,
                    "localField": "document_id",
                    "foreignField": "_id",
                    "as": "document_info",
                    "pipeline": [
                        (
                            {"$match": document_access_filter}
                            if document_access_filter
                            else {"$match": {}}
                        )
                    ],
                }
            },
            {"$unwind": "$document_info"},
            # Filter out chunks whose documents don't match RLS (empty document_info after unwind)
            {"$match": {"document_info": {"$exists": True, "$ne": {}}}},
            {
                "$project": {
                    "chunk_id": "$_id",
                    "document_id": 1,
                    "content": 1,
                    "similarity": {"$meta": "searchScore"},  # Text relevance score
                    "metadata": 1,
                    "document_title": "$document_info.title",
                    "document_source": "$document_info.source",
                }
            },
        ]

        # Execute aggregation
        collection = deps.db[deps.settings.mongodb_collection_chunks]
        cursor = await collection.aggregate(pipeline)
        results = [doc async for doc in cursor][: match_count * 2]

        # Convert to SearchResult objects (ObjectId → str conversion)
        search_results = [
            SearchResult(
                chunk_id=str(doc["chunk_id"]),
                document_id=str(doc["document_id"]),
                content=doc["content"],
                similarity=doc["similarity"],
                metadata=doc.get("metadata", {}),
                document_title=doc["document_title"],
                document_source=doc["document_source"],
            )
            for doc in results
        ]

        logger.info(
            f"text_search_completed: query={query}, results={len(search_results)}, match_count={match_count}"
        )

        return search_results

    except OperationFailure as e:
        error_code = e.code if hasattr(e, "code") else None
        logger.exception(f"text_search_failed: query={query}, error={e!s}, code={error_code}")
        # Return empty list on error (graceful degradation)
        return []
    except Exception as e:
        logger.exception(f"text_search_error: query={query}, error={e!s}")
        return []


def reciprocal_rank_fusion(
    search_results_list: list[list[SearchResult]], k: int = 60
) -> list[SearchResult]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion.

    RRF is a simple yet effective algorithm for combining results from different
    search methods. It works by scoring each document based on its rank position
    in each result list.

    Args:
        search_results_list: List of ranked result lists from different searches
        k: RRF constant (default: 60, standard in literature)

    Returns:
        Unified list of results sorted by combined RRF score

    Algorithm:
        For each document d appearing in result lists:
            RRF_score(d) = Σ(1 / (k + rank_i(d)))
        Where rank_i(d) is the position of document d in result list i.

    References:
        - Cormack et al. (2009): "Reciprocal Rank Fusion outperforms the best system"
        - Standard k=60 performs well across various datasets
    """
    # Build score dictionary by chunk_id
    rrf_scores: dict[str, float] = {}
    chunk_map: dict[str, SearchResult] = {}

    # Process each search result list
    for results in search_results_list:
        for rank, result in enumerate(results):
            chunk_id = result.chunk_id

            # Calculate RRF contribution: 1 / (k + rank)
            rrf_score = 1.0 / (k + rank)

            # Accumulate score (automatic deduplication)
            if chunk_id in rrf_scores:
                rrf_scores[chunk_id] += rrf_score
            else:
                rrf_scores[chunk_id] = rrf_score
                chunk_map[chunk_id] = result

    # Sort by combined RRF score (descending)
    sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    # Build final result list with updated similarity scores
    merged_results = []
    for chunk_id, rrf_score in sorted_chunks:
        result = chunk_map[chunk_id]
        # Create new result with updated similarity (RRF score)
        merged_result = SearchResult(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            content=result.content,
            similarity=rrf_score,  # Combined RRF score
            metadata=result.metadata,
            document_title=result.document_title,
            document_source=result.document_source,
        )
        merged_results.append(merged_result)

    logger.info(
        f"RRF merged {len(search_results_list)} result lists into {len(merged_results)} unique results"
    )

    return merged_results


async def hybrid_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: int | None = None,
    filter_dict: dict[str, Any] | None = None,
    text_weight: float | None = None,
) -> list[SearchResult]:
    """
    Perform hybrid search combining semantic and keyword matching.

    Uses manual Reciprocal Rank Fusion (RRF) to merge vector and text search results.
    Works on all Atlas tiers including M0 (free tier) - no M10+ required!

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (default: 10)
        text_weight: Weight for text matching (0-1, not used with RRF)

    Returns:
        List of search results sorted by combined RRF score

    Algorithm:
        1. Run semantic search (vector similarity)
        2. Run text search (keyword/fuzzy matching)
        3. Merge results using Reciprocal Rank Fusion
        4. Return top N results by combined score
    """
    try:
        deps = ctx.deps

        # Use defaults if not specified
        if match_count is None:
            match_count = deps.settings.default_match_count

        # Validate match count
        match_count = min(match_count, deps.settings.max_match_count)

        # Over-fetch for better RRF results (2x requested count)
        fetch_count = match_count * 2

        logger.info(f"hybrid_search starting: query='{query}', match_count={match_count}")

        # Prepare search tasks (with filter)
        search_tasks = [
            semantic_search(ctx, query, fetch_count, filter_dict),
            text_search(ctx, query, fetch_count, filter_dict),
        ]

        # Add Graphiti search if available
        # Import here to avoid circular import
        graphiti_results = []
        if deps.graphiti_deps and deps.graphiti_deps.graphiti:
            from capabilities.retrieval.graphiti_rag.search.graph_search import graphiti_search

            search_tasks.append(graphiti_search(deps.graphiti_deps.graphiti, query, fetch_count))

        # Run all searches concurrently for performance
        search_results_list = await asyncio.gather(
            *search_tasks,
            return_exceptions=True,  # Don't fail if one search errors
        )

        # Extract results and handle errors gracefully
        semantic_results = search_results_list[0]
        text_results = search_results_list[1]

        if isinstance(semantic_results, Exception):
            logger.warning(f"Semantic search failed: {semantic_results}, using other results")
            semantic_results = []
        if isinstance(text_results, Exception):
            logger.warning(f"Text search failed: {text_results}, using other results")
            text_results = []

        # Extract Graphiti results if available
        if len(search_results_list) > 2:
            graphiti_results = search_results_list[2]
            if isinstance(graphiti_results, Exception):
                logger.warning(
                    f"Graphiti search failed: {graphiti_results}, using MongoDB results only"
                )
                graphiti_results = []

        # If all failed, return empty
        if not semantic_results and not text_results and not graphiti_results:
            logger.error("All search methods failed")
            return []

        # Merge results using Reciprocal Rank Fusion (2 or 3 sources)
        sources_to_merge = [semantic_results, text_results]
        if graphiti_results:
            sources_to_merge.append(graphiti_results)

        merged_results = reciprocal_rank_fusion(sources_to_merge, k=60)  # Standard RRF constant

        # Apply reranking if enabled
        if config.use_reranking:
            reranker = get_reranker()
            if reranker is None:
                # Initialize reranker on first use
                reranker = initialize_reranker()

            if reranker and reranker.model:
                merged_results = reranker.rerank_results(query, merged_results)

        # Return top N results
        final_results = merged_results[:match_count]

        logger.info(
            f"hybrid_search_completed: query='{query}', "
            f"semantic={len(semantic_results)}, text={len(text_results)}, "
            f"graphiti={len(graphiti_results) if graphiti_results else 0}, "
            f"merged={len(merged_results)}, returned={len(final_results)}"
        )

        return final_results

    except Exception as e:
        logger.exception(f"hybrid_search_error: query={query}, error={e!s}")
        # Graceful degradation: try semantic-only as last resort
        try:
            logger.info("Falling back to semantic search only")
            return await semantic_search(ctx, query, match_count)
        except (MongoDBException, RuntimeError, ValueError):
            return []
