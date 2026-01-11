"""Core tool implementations for Deep Research Agent."""

import logging
import os
import tempfile
from datetime import datetime
from typing import Any

from pymongo.errors import OperationFailure

from server.projects.crawl4ai_rag.services.crawler import crawl_single_page
from server.projects.deep_research.dependencies import DeepResearchDeps
from server.projects.deep_research.models import (
    DocumentChunk,
    FetchPageRequest,
    FetchPageResponse,
    IngestKnowledgeRequest,
    IngestKnowledgeResponse,
    ParseDocumentRequest,
    ParseDocumentResponse,
    QueryKnowledgeRequest,
    QueryKnowledgeResponse,
    SearchResult,
    SearchWebRequest,
    SearchWebResponse,
)
from server.projects.graphiti_rag.ingestion.graph_builder import ingest_to_graphiti
from server.projects.mongo_rag.config import config as rag_config
from server.projects.mongo_rag.ingestion.chunker import (
    ChunkingConfig,
    DoclingHybridChunker,
)
from server.projects.mongo_rag.ingestion.chunker import (
    DocumentChunk as MongoDocumentChunk,
)

logger = logging.getLogger(__name__)


async def search_web(deps: DeepResearchDeps, request: SearchWebRequest) -> SearchWebResponse:
    """
    Search the web using SearXNG metasearch engine.

    Uses the SearXNG REST API to search multiple search engines and return
    aggregated, ranked results.

    Args:
        deps: DeepResearchDeps with http_client initialized
        request: SearchWebRequest with query and options

    Returns:
        SearchWebResponse with search results

    Raises:
        Exception: If SearXNG is unavailable or request fails
    """
    from server.api.searxng import SearXNGSearchRequest
    from server.api.searxng import search as searxng_search

    try:
        # Ensure HTTP client is initialized
        if not deps.http_client:
            await deps.initialize()

        # Convert our request to SearXNG request format
        searxng_request = SearXNGSearchRequest(
            query=request.query,
            result_count=request.result_count or config.default_result_count,
            categories=None,  # Not in our model yet
            engines=request.engines,
        )

        # Call SearXNG API
        searxng_response = await searxng_search(searxng_request)

        # Convert SearXNG response to our response format
        results = [
            SearchResult(
                title=result.title,
                url=result.url,
                snippet=result.content,
                engine=result.engine,
                score=result.score,
            )
            for result in searxng_response.results
        ]

        return SearchWebResponse(
            query=searxng_response.query,
            results=results,
            count=searxng_response.count,
            success=searxng_response.success,
        )

    except Exception as e:
        logger.exception(f"Error searching web: {e}")
        return SearchWebResponse(query=request.query, results=[], count=0, success=False)


async def fetch_page(deps: DeepResearchDeps, request: FetchPageRequest) -> FetchPageResponse:
    """
    Fetch a single web page using Crawl4AI.

    Args:
        deps: DeepResearchDeps with crawler initialized
        request: FetchPageRequest with URL

    Returns:
        FetchPageResponse with content and metadata

    Raises:
        Exception: If crawling fails
    """
    if not deps.crawler:
        await deps.initialize()

    try:
        # Use existing crawl_single_page function from crawl4ai_rag
        result = await crawl_single_page(deps.crawler, str(request.url))

        if result is None:
            return FetchPageResponse(url=str(request.url), content="", metadata={}, success=False)

        return FetchPageResponse(
            url=result["url"],
            content=result.get("markdown", ""),
            metadata=result.get("metadata", {}),
            success=True,
        )
    except Exception as e:
        logger.exception(f"Error fetching page {request.url}: {e}")
        return FetchPageResponse(
            url=str(request.url), content="", metadata={"error": str(e)}, success=False
        )


async def parse_document(
    deps: DeepResearchDeps, request: ParseDocumentRequest
) -> ParseDocumentResponse:
    """
    Parse a document using Docling and chunk it with HybridChunker.

    Args:
        deps: DeepResearchDeps with document_converter initialized
        request: ParseDocumentRequest with content and content_type

    Returns:
        ParseDocumentResponse with structured chunks and metadata

    Raises:
        Exception: If parsing fails
    """
    if not deps.document_converter:
        await deps.initialize()

    try:
        # Create a temporary file with the content
        # Docling's DocumentConverter works with file paths
        file_ext = {"html": ".html", "markdown": ".md", "text": ".txt"}.get(
            request.content_type, ".html"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=file_ext, delete=False) as tmp_file:
            tmp_file.write(request.content)
            tmp_path = tmp_file.name

        try:
            # Convert document using Docling
            result = deps.document_converter.convert(tmp_path)
            docling_doc = result.document
            markdown_content = docling_doc.export_to_markdown()

            # Extract document metadata
            doc_metadata = {"content_type": request.content_type, "source": "parsed_content"}

            # Add Docling document metadata if available
            if hasattr(docling_doc, "metadata") and docling_doc.metadata:
                if isinstance(docling_doc.metadata, dict):
                    doc_metadata.update(docling_doc.metadata)

            # Chunk the document using HybridChunker
            chunking_config = ChunkingConfig(chunk_size=1000, chunk_overlap=200, max_tokens=512)
            chunker = DoclingHybridChunker(chunking_config)

            chunks = await chunker.chunk_document(
                content=markdown_content,
                title=doc_metadata.get("title", "Untitled"),
                source="parsed_content",
                metadata=doc_metadata,
                docling_doc=docling_doc,
            )

            # Convert DocumentChunk objects to Pydantic models
            document_chunks = [
                DocumentChunk(
                    content=chunk.content,
                    index=chunk.index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    metadata=chunk.metadata,
                    token_count=chunk.token_count,
                )
                for chunk in chunks
            ]

            return ParseDocumentResponse(
                chunks=document_chunks, metadata=doc_metadata, success=True
            )

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        logger.exception(f"Error parsing document: {e}")
        return ParseDocumentResponse(chunks=[], metadata={"error": str(e)}, success=False)


async def ingest_knowledge(
    deps: DeepResearchDeps, request: IngestKnowledgeRequest
) -> IngestKnowledgeResponse:
    """
    Ingest document chunks into MongoDB (for vector search) and Graphiti (for knowledge graph).

    Args:
        deps: DeepResearchDeps with MongoDB and Graphiti initialized
        request: IngestKnowledgeRequest with chunks, session_id, source_url, title

    Returns:
        IngestKnowledgeResponse with document_id, chunks_created, facts_added
    """
    if not deps.db:
        await deps.initialize()

    try:
        # Convert Pydantic DocumentChunk to mongo_rag DocumentChunk
        mongo_chunks: list[MongoDocumentChunk] = []
        full_content_parts = []

        for chunk in request.chunks:
            # Add session_id to metadata
            chunk_metadata = {
                **chunk.metadata,
                "session_id": request.session_id,
                "source_url": request.source_url,
            }

            mongo_chunk = MongoDocumentChunk(
                content=chunk.content,
                index=chunk.index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                metadata=chunk_metadata,
                token_count=chunk.token_count,
            )
            mongo_chunks.append(mongo_chunk)
            full_content_parts.append(chunk.content)

        # Combine all chunks into full document content
        full_content = "\n\n".join(full_content_parts)

        # Generate embeddings for all chunks
        logger.info(f"Generating embeddings for {len(mongo_chunks)} chunks")
        for chunk in mongo_chunks:
            if not chunk.embedding:
                chunk.embedding = await deps.get_embedding(chunk.content)

        # Prepare document metadata
        document_metadata = {
            "session_id": request.session_id,
            "source_url": request.source_url,
            "title": request.title or "Untitled",
            "chunk_count": len(mongo_chunks),
            "created_at": datetime.now(),
        }

        # Save to MongoDB
        documents_collection = deps.db[rag_config.mongodb_collection_documents]
        chunks_collection = deps.db[rag_config.mongodb_collection_chunks]

        # Insert document
        document_dict = {
            "title": request.title or "Untitled",
            "source": request.source_url,
            "content": full_content,
            "metadata": document_metadata,
            "created_at": datetime.now(),
        }

        document_result = await documents_collection.insert_one(document_dict)
        document_id = str(document_result.inserted_id)
        logger.info(f"Inserted document with ID: {document_id}")

        # Insert chunks with embeddings
        chunk_dicts = []
        for chunk in mongo_chunks:
            chunk_dict = {
                "document_id": document_result.inserted_id,
                "content": chunk.content,
                "embedding": chunk.embedding,  # Python list
                "chunk_index": chunk.index,
                "metadata": chunk.metadata,
                "token_count": chunk.token_count,
                "created_at": datetime.now(),
            }
            chunk_dicts.append(chunk_dict)

        if chunk_dicts:
            await chunks_collection.insert_many(chunk_dicts, ordered=False)
            logger.info(f"Inserted {len(chunk_dicts)} chunks")

        # Ingest into Graphiti if available
        facts_added = 0
        graphiti_errors = []
        if deps.graphiti_deps and deps.graphiti_deps.graphiti:
            try:
                graphiti_result = await ingest_to_graphiti(
                    graphiti=deps.graphiti_deps.graphiti,
                    document_id=document_id,
                    chunks=mongo_chunks,
                    metadata=document_metadata,
                    title=request.title or "Untitled",
                    source=request.source_url,
                )
                facts_added = graphiti_result.get("facts_added", 0)
                if graphiti_result.get("errors"):
                    graphiti_errors.extend(graphiti_result["errors"])
                logger.info(
                    f"Graphiti ingestion: {facts_added} facts from "
                    f"{graphiti_result.get('chunks_processed', 0)} chunks"
                )
            except Exception as e:
                error_msg = f"Graphiti ingestion failed: {e!s}"
                logger.exception(error_msg)
                graphiti_errors.append(error_msg)

        return IngestKnowledgeResponse(
            document_id=document_id,
            chunks_created=len(mongo_chunks),
            facts_added=facts_added,
            success=True,
            errors=graphiti_errors,
        )

    except Exception as e:
        logger.exception(f"Error ingesting knowledge: {e}")
        return IngestKnowledgeResponse(
            document_id="", chunks_created=0, facts_added=0, success=False, errors=[str(e)]
        )


async def query_knowledge(
    deps: DeepResearchDeps, request: QueryKnowledgeRequest
) -> QueryKnowledgeResponse:
    """
    Query the knowledge base using hybrid search (vector + text) filtered by session_id.

    Phase 6 Enhancement: If use_graphiti=True, also performs graph traversal for
    multi-hop reasoning using Graphiti knowledge graph.

    Args:
        deps: DeepResearchDeps with MongoDB and optionally Graphiti initialized
        request: QueryKnowledgeRequest with question, session_id, match_count, search_type, use_graphiti

    Returns:
        QueryKnowledgeResponse with cited chunks
    """
    if not deps.db:
        await deps.initialize()

    try:
        # Phase 6: Graph-enhanced reasoning with Graphiti
        graph_results = []
        if request.use_graphiti and deps.graphiti_deps and deps.graphiti_deps.graphiti:
            try:
                from server.projects.graphiti_rag.search.graph_search import graphiti_search

                logger.info(f"Performing Graphiti graph search for: {request.question}")
                graph_search_results = await graphiti_search(
                    deps.graphiti_deps.graphiti, request.question, match_count=request.match_count
                )

                # Convert Graphiti results to CitedChunk format
                # Graphiti results may reference chunk_ids that we need to fetch from MongoDB
                for graph_result in graph_search_results:
                    # Extract chunk_id from metadata if available
                    chunk_id = (
                        graph_result.metadata.get("chunk_id")
                        if hasattr(graph_result, "metadata")
                        else None
                    )
                    document_id = (
                        graph_result.metadata.get("document_id")
                        if hasattr(graph_result, "metadata")
                        else None
                    )

                    # If we have chunk_id, fetch full chunk from MongoDB
                    if chunk_id:
                        from bson import ObjectId

                        try:
                            chunk_doc = await deps.db[
                                rag_config.mongodb_collection_chunks
                            ].find_one(
                                {
                                    "_id": ObjectId(chunk_id),
                                    "metadata.session_id": request.session_id,
                                }
                            )
                            if chunk_doc:
                                # Get document info
                                doc_info = await deps.db[
                                    rag_config.mongodb_collection_documents
                                ].find_one({"_id": chunk_doc.get("document_id")})

                                from server.projects.deep_research.models import CitedChunk

                                graph_results.append(
                                    CitedChunk(
                                        chunk_id=str(chunk_id),
                                        content=chunk_doc.get(
                                            "content",
                                            (
                                                graph_result.content
                                                if hasattr(graph_result, "content")
                                                else ""
                                            ),
                                        ),
                                        document_id=(
                                            str(document_id)
                                            if document_id
                                            else str(chunk_doc.get("document_id", ""))
                                        ),
                                        document_source=(
                                            doc_info.get("source", "") if doc_info else ""
                                        ),
                                        similarity=(
                                            graph_result.similarity
                                            if hasattr(graph_result, "similarity")
                                            else 0.8
                                        ),
                                        metadata=(
                                            graph_result.metadata
                                            if hasattr(graph_result, "metadata")
                                            else {}
                                        ),
                                    )
                                )
                        except Exception as e:
                            logger.warning(f"Could not fetch chunk {chunk_id} from MongoDB: {e}")
                            # Fall back to using Graphiti result directly
                            from server.projects.deep_research.models import CitedChunk

                            graph_results.append(
                                CitedChunk(
                                    chunk_id=str(chunk_id) if chunk_id else "graphiti",
                                    content=(
                                        graph_result.content
                                        if hasattr(graph_result, "content")
                                        else str(graph_result)
                                    ),
                                    document_id=str(document_id) if document_id else "unknown",
                                    document_source=(
                                        graph_result.metadata.get("source", "")
                                        if hasattr(graph_result, "metadata")
                                        else ""
                                    ),
                                    similarity=(
                                        graph_result.similarity
                                        if hasattr(graph_result, "similarity")
                                        else 0.8
                                    ),
                                    metadata=(
                                        graph_result.metadata
                                        if hasattr(graph_result, "metadata")
                                        else {}
                                    ),
                                )
                            )
                    else:
                        # No chunk_id, use Graphiti result directly
                        from server.projects.deep_research.models import CitedChunk

                        graph_results.append(
                            CitedChunk(
                                chunk_id="graphiti",
                                content=(
                                    graph_result.content
                                    if hasattr(graph_result, "content")
                                    else str(graph_result)
                                ),
                                document_id="unknown",
                                document_source="",
                                similarity=(
                                    graph_result.similarity
                                    if hasattr(graph_result, "similarity")
                                    else 0.8
                                ),
                                metadata=(
                                    graph_result.metadata
                                    if hasattr(graph_result, "metadata")
                                    else {}
                                ),
                            )
                        )

                logger.info(f"Graphiti search returned {len(graph_results)} results")

            except Exception as e:
                logger.warning(f"Graphiti search failed, falling back to standard search: {e}")

        # If using graph-only search, return graph results
        if request.search_type == "graph" and graph_results:
            return QueryKnowledgeResponse(
                results=graph_results[: request.match_count], count=len(graph_results), success=True
            )

        # Continue with standard search
        # Build filter for session_id
        filter_dict = {"metadata.session_id": request.session_id}

        # Get collections
        deps.db[rag_config.mongodb_collection_documents]
        chunks_collection = deps.db[rag_config.mongodb_collection_chunks]

        results = []

        if request.search_type in ["semantic", "hybrid"]:
            # Vector search
            query_embedding = await deps.get_embedding(request.question)

            vector_search_stage = {
                "$vectorSearch": {
                    "index": rag_config.mongodb_vector_index,
                    "queryVector": query_embedding,
                    "path": "embedding",
                    "numCandidates": 100,
                    "limit": (
                        request.match_count * 2
                        if request.search_type == "hybrid"
                        else request.match_count
                    ),
                    "filter": filter_dict,
                }
            }

            vector_pipeline = [
                vector_search_stage,
                {
                    "$lookup": {
                        "from": rag_config.mongodb_collection_documents,
                        "localField": "document_id",
                        "foreignField": "_id",
                        "as": "document_info",
                    }
                },
                {"$unwind": "$document_info"},
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

            vector_cursor = await chunks_collection.aggregate(vector_pipeline)
            vector_results = [doc async for doc in vector_cursor]
            results.extend(vector_results)

        if request.search_type in ["text", "hybrid"]:
            # Text search
            text_search_stage = {
                "$search": {
                    "index": rag_config.mongodb_text_index,
                    "text": {
                        "query": request.question,
                        "path": "content",
                        "fuzzy": {"maxEdits": 2, "prefixLength": 3},
                    },
                    "filter": filter_dict,
                }
            }

            text_pipeline = [
                text_search_stage,
                {
                    "$limit": (
                        request.match_count * 2
                        if request.search_type == "hybrid"
                        else request.match_count
                    )
                },
                {
                    "$lookup": {
                        "from": rag_config.mongodb_collection_documents,
                        "localField": "document_id",
                        "foreignField": "_id",
                        "as": "document_info",
                    }
                },
                {"$unwind": "$document_info"},
                {
                    "$project": {
                        "chunk_id": "$_id",
                        "document_id": 1,
                        "content": 1,
                        "similarity": {"$meta": "searchScore"},
                        "metadata": 1,
                        "document_title": "$document_info.title",
                        "document_source": "$document_info.source",
                    }
                },
            ]

            try:
                text_cursor = await chunks_collection.aggregate(text_pipeline)
                text_results = [doc async for doc in text_cursor]
                results.extend(text_results)
            except OperationFailure as e:
                # Text search might not be available (e.g., no Atlas Search index)
                logger.warning(f"Text search failed (may not be configured): {e}")
                if request.search_type == "text":
                    # If text-only search fails, fall back to semantic
                    logger.info("Falling back to semantic search")
                    query_embedding = await deps.get_embedding(request.question)
                    vector_search_stage = {
                        "$vectorSearch": {
                            "index": rag_config.mongodb_vector_index,
                            "queryVector": query_embedding,
                            "path": "embedding",
                            "numCandidates": 100,
                            "limit": request.match_count,
                            "filter": filter_dict,
                        }
                    }
                    vector_pipeline = [
                        vector_search_stage,
                        {
                            "$lookup": {
                                "from": rag_config.mongodb_collection_documents,
                                "localField": "document_id",
                                "foreignField": "_id",
                                "as": "document_info",
                            }
                        },
                        {"$unwind": "$document_info"},
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
                    vector_cursor = await chunks_collection.aggregate(vector_pipeline)
                    results = [doc async for doc in vector_cursor]

        # For hybrid search, combine and deduplicate results using RRF
        if request.search_type == "hybrid" and len(results) > 0:
            # Simple RRF: combine by chunk_id, average scores
            chunk_scores: dict[str, dict[str, Any]] = {}
            for doc in results:
                chunk_id = str(doc["chunk_id"])
                if chunk_id not in chunk_scores:
                    chunk_scores[chunk_id] = {"doc": doc, "scores": []}
                chunk_scores[chunk_id]["scores"].append(doc.get("similarity", 0.0))

            # Average scores and sort
            combined_results = []
            for chunk_id, data in chunk_scores.items():
                avg_score = sum(data["scores"]) / len(data["scores"])
                doc = data["doc"]
                doc["similarity"] = avg_score
                combined_results.append(doc)

            # Sort by similarity and limit
            combined_results.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
            results = combined_results[: request.match_count]
        else:
            # For single search type, just sort and limit
            results.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
            results = results[: request.match_count]

        # Convert to CitedChunk objects
        cited_chunks = [
            CitedChunk(
                chunk_id=str(doc["chunk_id"]),
                content=doc["content"],
                document_id=str(doc["document_id"]),
                document_source=doc.get("document_source", ""),
                similarity=doc.get("similarity", 0.0),
                metadata=doc.get("metadata", {}),
            )
            for doc in results
        ]

        # Phase 6: Combine graph results with standard search results if both enabled
        if request.use_graphiti and graph_results:
            # Merge graph results with standard results, deduplicate by chunk_id
            existing_ids = {chunk.chunk_id for chunk in cited_chunks}
            for graph_chunk in graph_results:
                if graph_chunk.chunk_id not in existing_ids:
                    cited_chunks.append(graph_chunk)
                    existing_ids.add(graph_chunk.chunk_id)

            # Re-sort by similarity
            cited_chunks.sort(key=lambda x: x.similarity, reverse=True)
            cited_chunks = cited_chunks[: request.match_count]

        logger.info(
            f"query_knowledge completed: question={request.question}, "
            f"session_id={request.session_id}, results={len(cited_chunks)}, "
            f"graph_results={len(graph_results) if request.use_graphiti else 0}"
        )

        return QueryKnowledgeResponse(results=cited_chunks, count=len(cited_chunks), success=True)

    except Exception as e:
        logger.exception(f"Error querying knowledge: {e}")
        return QueryKnowledgeResponse(results=[], count=0, success=False)
