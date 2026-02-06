"""Code example search tools for MongoDB RAG Agent."""

import logging

from app.capabilities.retrieval.mongo_rag.dependencies import AgentDependencies
from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)


class CodeExampleResult(BaseModel):
    """Model for code example search results."""

    code_example_id: str = Field(..., description="MongoDB ObjectId of code example as string")
    document_id: str = Field(..., description="Parent document ObjectId as string")
    code: str = Field(..., description="Code example content")
    summary: str = Field(..., description="Summary of the code example")
    language: str = Field(..., description="Programming language")
    similarity: float = Field(..., description="Relevance score (0-1)")
    metadata: dict = Field(default_factory=dict, description="Code example metadata")
    source: str = Field(..., description="Document source")


async def search_code_examples(
    ctx: RunContext[AgentDependencies], query: str, match_count: int | None = None
) -> list[CodeExampleResult]:
    """
    Search for code examples using MongoDB vector similarity.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (default: 10)

    Returns:
        List of code example results ordered by similarity
    """
    try:
        deps = ctx.deps

        # Use default if not specified
        if match_count is None:
            match_count = deps.settings.default_match_count

        # Validate match count
        match_count = min(match_count, deps.settings.max_match_count)

        # Generate embedding for query
        query_embedding = await deps.get_embedding(query)

        # Build MongoDB aggregation pipeline for code examples
        pipeline = [
            {
                "$vectorSearch": {
                    "index": deps.settings.mongodb_vector_index,
                    "queryVector": query_embedding,
                    "path": "embedding",
                    "numCandidates": 100,
                    "limit": match_count,
                }
            },
            {
                "$lookup": {
                    "from": deps.settings.mongodb_collection_documents,
                    "localField": "document_id",
                    "foreignField": "_id",
                    "as": "document_info",
                }
            },
            {"$unwind": {"path": "$document_info", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "code_example_id": "$_id",
                    "document_id": 1,
                    "code": 1,
                    "summary": 1,
                    "language": 1,
                    "similarity": {"$meta": "vectorSearchScore"},
                    "metadata": 1,
                    "source": {"$ifNull": ["$source", "$document_info.source"]},
                }
            },
        ]

        # Execute aggregation
        collection = deps.db["code_examples"]
        cursor = await collection.aggregate(pipeline)
        results = [doc async for doc in cursor][:match_count]

        # Convert to CodeExampleResult objects
        code_results = [
            CodeExampleResult(
                code_example_id=str(doc["code_example_id"]),
                document_id=str(doc["document_id"]),
                code=doc["code"],
                summary=doc.get("summary", ""),
                language=doc.get("language", ""),
                similarity=doc["similarity"],
                metadata=doc.get("metadata", {}),
                source=doc.get("source", "Unknown"),
            )
            for doc in results
        ]

        logger.info(
            f"code_example_search_completed: query={query}, "
            f"results={len(code_results)}, match_count={match_count}"
        )

        return code_results

    except OperationFailure as e:
        error_code = e.code if hasattr(e, "code") else None
        logger.exception(
            f"code_example_search_failed: query={query}, error={e!s}, code={error_code}"
        )
        return []
    except Exception as e:
        logger.exception(f"code_example_search_error: query={query}, error={e!s}")
        return []
