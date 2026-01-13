"""MongoDB RAG project REST API."""

import logging
import shutil
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from src.capabilities.retrieval.mongo_rag.agent import rag_agent
from src.capabilities.retrieval.mongo_rag.dependencies import AgentDependencies
from src.capabilities.retrieval.mongo_rag.ingestion.pipeline import (
    DocumentIngestionPipeline,
    IngestionConfig,
)
from src.capabilities.retrieval.mongo_rag.models import (
    AgentRequest,
    AgentResponse,
    IngestContentRequest,
    IngestContentResponse,
    IngestResponse,
    SearchRequest,
    SearchResponse,
)
from src.capabilities.retrieval.mongo_rag.sources import get_available_sources
from src.capabilities.retrieval.mongo_rag.tools import hybrid_search, semantic_search, text_search
from src.capabilities.retrieval.mongo_rag.tools_code import search_code_examples
from src.services.auth.dependencies import get_current_user
from src.services.auth.models import User
from src.services.database.supabase import SupabaseClient, SupabaseConfig

router = APIRouter()
logger = logging.getLogger(__name__)


# FastAPI dependency function with yield pattern for resource cleanup
async def get_agent_deps(
    user: User = Depends(get_current_user),
) -> AsyncGenerator[AgentDependencies, None]:
    """
    FastAPI dependency that yields AgentDependencies for Pydantic AI agent.

    Automatically extracts user context from JWT and creates user-based MongoDB connection.
    """
    # Get MongoDB credentials from Supabase
    supabase_config = SupabaseConfig()
    supabase_service = SupabaseClient(supabase_config)
    mongodb_username, mongodb_password = await supabase_service.get_mongodb_credentials(user.email)

    # Check if user is admin
    is_admin = user.role == "admin"

    # Create dependencies with user context
    deps = AgentDependencies.from_settings(
        user_id=str(user.id),
        user_email=user.email,
        is_admin=is_admin,
        user_groups=[],  # TODO: Implement group membership lookup
        mongodb_username=mongodb_username,
        mongodb_password=mongodb_password,
    )
    await deps.initialize()
    try:
        yield deps  # Injected into endpoint, passed to agent.run()
    finally:
        await deps.cleanup()  # Cleanup after response


def _build_search_filter(request: SearchRequest) -> dict[str, Any]:
    """
    Build MongoDB filter for search request.

    Supports filtering by:
    - source_type: Filter by document source (e.g., 'openwebui_conversation')
    - user_id: Filter by user ID (for conversations)
    - conversation_id: Filter by conversation ID
    - topics: Filter by topics (for conversations)

    Args:
        request: Search request with optional filters

    Returns:
        MongoDB filter dictionary
    """
    filter_dict = {}

    # Filter by source type
    if request.source_type:
        filter_dict["metadata.source"] = request.source_type

    # Filter by user ID (for conversations)
    if request.user_id:
        filter_dict["metadata.user_id"] = request.user_id

    # Filter by conversation ID
    if request.conversation_id:
        filter_dict["metadata.conversation_id"] = request.conversation_id

    # Filter by topics (for conversations)
    if request.topics:
        filter_dict["metadata.topics"] = {"$in": request.topics}

    return filter_dict


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, deps: Annotated[Any, Depends(get_agent_deps)]):
    """
    Search the MongoDB RAG knowledge base using semantic, text, or hybrid search.

    This endpoint searches across all ingested documents (including crawled web pages)
    using vector embeddings, full-text search, or a combination of both. Results are
    ranked by relevance and include metadata for filtering and context.

    **Use Cases:**
    - Find relevant information from ingested documents
    - Search crawled web content alongside uploaded documents
    - Get semantically similar content even without exact keyword matches
    - Combine keyword and semantic matching for best results

    **Request Body:**
    ```json
    {
        "query": "how to configure authentication",
        "match_count": 5,
        "search_type": "hybrid"
    }
    ```

    **Response:**
    ```json
    {
        "query": "how to configure authentication",
        "results": [
            {
                "chunk_id": "507f1f77bcf86cd799439011",
                "document_id": "507f1f77bcf86cd799439010",
                "content": "To configure authentication, you need to...",
                "similarity": 0.87,
                "metadata": {"url": "https://docs.example.com/auth", ...},
                "document_title": "Authentication Guide",
                "document_source": "https://docs.example.com/auth"
            }
        ],
        "count": 5
    }
    ```

    **Parameters:**
    - `query` (required): Search query text. Can be a question, phrase, or keywords.
    - `match_count` (optional, default: 10): Number of results to return. Range: 1-50.
    - `search_type` (optional, default: "hybrid"): Type of search to perform.
      - `"semantic"`: Pure vector similarity search (best for conceptual queries)
      - `"text"`: Keyword and fuzzy matching (best for exact terms, function names)
      - `"hybrid"`: Combines both using Reciprocal Rank Fusion (recommended)

    **Search Types Explained:**
    - **Semantic**: Uses embeddings to find conceptually similar content. Good for:
      - Questions and natural language queries
      - Finding related concepts even without exact keywords
      - Understanding intent and context
    - **Text**: Uses MongoDB Atlas Search for keyword matching. Good for:
      - Exact function names, API endpoints, technical terms
      - Code snippets and technical documentation
      - When you know the exact terminology
    - **Hybrid**: Runs both searches and merges results. Best for:
      - General-purpose search
      - When you want both semantic understanding and keyword precision
      - Production use cases requiring robust results

    **Returns:**
    - `SearchResponse` with query, results array, and count
    - Results include similarity scores, metadata, and document context

    **Errors:**
    - `500`: If MongoDB connection fails
    - `500`: If search indexes are not configured (vector_index, text_index)
    - Gracefully degrades: if one search type fails, others may still work

    **Integration:**
    - Also available as MCP tool: `search_knowledge_base`
    - Searches all documents regardless of source (uploaded files, crawled pages)
    - Results can be filtered by metadata fields (e.g., `source_type: "web_crawl"`)

    **Example Usage:**
    ```bash
    # Hybrid search (recommended)
    curl -X POST http://localhost:8000/api/v1/rag/search \
      -H "Content-Type: application/json" \
      -d '{
        "query": "authentication setup",
        "match_count": 10,
        "search_type": "hybrid"
      }'

    # Semantic search for conceptual queries
    curl -X POST http://localhost:8000/api/v1/rag/search \
      -H "Content-Type: application/json" \
      -d '{
        "query": "how do I secure my API?",
        "search_type": "semantic"
      }'

    # Text search for exact terms
    curl -X POST http://localhost:8000/api/v1/rag/search \
      -H "Content-Type: application/json" \
      -d '{
        "query": "OAuth2 token refresh",
        "search_type": "text"
      }'
    ```

    **Performance Notes:**
    - Semantic search: ~100-200ms per query
    - Text search: ~50-150ms per query
    - Hybrid search: ~150-300ms (runs both searches concurrently)
    - Results are cached at MongoDB level for repeated queries
    """

    # Build filter from request
    search_filter = _build_search_filter(request)

    # Create context wrapper
    class Ctx:
        def __init__(self, d):
            self.deps = d

    ctx = Ctx(deps)

    # Execute search based on type (with filter)
    # RLS is automatically applied in the search functions
    if request.search_type == "hybrid":
        results = await hybrid_search(ctx, request.query, request.match_count, search_filter)
    elif request.search_type == "semantic":
        results = await semantic_search(ctx, request.query, request.match_count, search_filter)
    else:
        results = await text_search(ctx, request.query, request.match_count, search_filter)

    return SearchResponse(
        query=request.query, results=[r.dict() for r in results], count=len(results)
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    files: list[UploadFile] = File(...),
    clean_before: bool = False,
    user: User = Depends(get_current_user),
):
    """
    Upload and ingest documents into the MongoDB RAG knowledge base.

    This endpoint accepts multiple file uploads, processes them using Docling for format
    conversion, chunks them intelligently, generates embeddings, and stores everything in
    MongoDB. Supported formats include PDF, Word, PowerPoint, Excel, HTML, Markdown, and
    audio files (with transcription).

    **Use Cases:**
    - Upload documentation PDFs
    - Ingest Word documents and presentations
    - Add markdown files to knowledge base
    - Transcribe and index audio files

    **Request:**
    - Content-Type: `multipart/form-data`
    - Body: Form data with `files` field (multiple files supported)
    - Query parameter: `clean_before` (optional, default: false)

    **Response:**
    ```json
    {
        "documents_processed": 3,
        "chunks_created": 127,
        "errors": []
    }
    ```

    **Parameters:**
    - `files` (required): One or more files to upload. Supported formats:
      - Documents: `.pdf`, `.docx`, `.doc`, `.pptx`, `.ppt`, `.xlsx`, `.xls`
      - Text: `.md`, `.markdown`, `.txt`
      - Web: `.html`, `.htm`
      - Audio: `.mp3`, `.wav`, `.m4a`, `.flac` (transcribed with Whisper ASR)
    - `clean_before` (optional, default: false): If true, deletes all existing documents
      and chunks before ingestion. Use with caution!

    **Returns:**
    - `IngestResponse` with count of processed documents, total chunks created, and errors

    **Processing Pipeline:**
    1. Files are saved to `/app/uploads` directory
    2. Docling converts documents to markdown (preserves structure)
    3. Audio files are transcribed using Whisper ASR
    4. Content is chunked using DoclingHybridChunker (respects document structure)
    5. Embeddings are generated for each chunk
    6. Documents and chunks are stored in MongoDB

    **Errors:**
    - `400`: If no files provided or invalid file format
    - `500`: If document conversion fails
    - `500`: If MongoDB connection fails
    - Individual file errors are collected in the `errors` array

    **Integration:**
    - Also available as MCP tool: `ingest_documents` (requires files on server)
    - Ingested documents are searchable via `/api/v1/rag/search` immediately
    - Uses same MongoDB collections as crawled content (`documents`, `chunks`)

    **Example Usage:**
    ```bash
    # Upload single file
    curl -X POST http://localhost:8000/api/v1/rag/ingest \
      -F "files=@document.pdf"

    # Upload multiple files
    curl -X POST http://localhost:8000/api/v1/rag/ingest \
      -F "files=@doc1.pdf" \
      -F "files=@doc2.docx" \
      -F "files=@guide.md"

    # Clean and re-ingest
    curl -X POST "http://localhost:8000/api/v1/rag/ingest?clean_before=true" \
      -F "files=@updated-docs.pdf"
    ```

    **Performance Notes:**
    - PDF processing: ~2-5 seconds per page
    - Audio transcription: ~1-2x audio duration (Whisper ASR)
    - Embedding generation: ~1-2 seconds per document
    - Total time scales with document size and count
    """

    upload_dir = Path("/app/uploads")
    upload_dir.mkdir(exist_ok=True, parents=True)

    # Save uploaded files
    file_paths = []
    for file in files:
        path = upload_dir / file.filename
        with path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        file_paths.append(str(path))
        logger.info(f"saved_file: {file.filename}")

    # Ingest with user context
    config = IngestionConfig()
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder=str(upload_dir),
        clean_before_ingest=clean_before,
        user_id=str(user.id),
        user_email=user.email,
    )

    try:
        await pipeline.initialize()
        results = await pipeline.ingest_documents()

        return IngestResponse(
            documents_processed=len(results),
            chunks_created=sum(r.chunks_created for r in results),
            errors=[r.errors for r in results if r.errors],
        )
    finally:
        await pipeline.close()


@router.post("/ingest/content", response_model=IngestContentResponse)
async def ingest_content(
    request: IngestContentRequest,
    user: User = Depends(get_current_user),
):
    """
    Ingest arbitrary markdown/text content into the MongoDB RAG knowledge base.

    This endpoint accepts content directly (no file upload needed), making it ideal for:
    - Web crawlers that have already extracted markdown content
    - YouTube transcript ingestion
    - Article scrapers that have pre-processed content
    - Any programmatic content submission

    **Use Cases:**
    - Ingest crawled web page content
    - Store YouTube video transcripts
    - Import markdown articles
    - Add any text content to knowledge base

    **Request Body:**
    ```json
    {
        "content": "# My Document\\n\\nThis is the content...",
        "title": "My Document Title",
        "source": "https://example.com/article",
        "source_type": "web",
        "metadata": {"domain": "example.com", "author": "John Doe"},
        "use_docling": true,
        "skip_duplicates": true
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "document_id": "507f1f77bcf86cd799439011",
        "title": "My Document Title",
        "source": "https://example.com/article",
        "source_type": "web",
        "chunks_created": 12,
        "processing_time_ms": 1523.4,
        "skipped": false,
        "skip_reason": "",
        "errors": []
    }
    ```

    **Parameters:**
    - `content` (required): Markdown or plain text content to ingest
    - `title` (required): Document title for display and search
    - `source` (required): Source URL or unique identifier for deduplication
    - `source_type` (optional, default: "custom"): Type of source:
      - "web" - Web page content
      - "youtube" - YouTube video transcript
      - "article" - Scraped article
      - "custom" - Any other content type
    - `metadata` (optional): Additional metadata dictionary to store with document
    - `use_docling` (optional, default: true): Parse through Docling for structure-aware
      chunking. Recommended for better RAG results.
    - `skip_duplicates` (optional, default: true): Skip if content from this source
      already exists in the knowledge base

    **Processing Pipeline:**
    1. Check for duplicate source (if skip_duplicates=true)
    2. Optionally convert markdown to DoclingDocument for structure-aware chunking
    3. Chunk content using HybridChunker (or fallback to simple chunking)
    4. Generate embeddings for each chunk
    5. Store documents and chunks with RLS fields (user_id, user_email)
    6. Optionally ingest to Graphiti knowledge graph
    7. Optionally extract code examples

    **Benefits over file upload:**
    - No file system overhead
    - Direct content submission
    - Better for programmatic workflows
    - Consistent with crawler pipelines

    **Example Usage:**
    ```bash
    # Ingest web content
    curl -X POST http://localhost:8000/api/v1/rag/ingest/content \\
      -H "Content-Type: application/json" \\
      -H "Cf-Access-Jwt-Assertion: $JWT_TOKEN" \\
      -d '{
        "content": "# Getting Started\\n\\nThis guide explains...",
        "title": "Getting Started Guide",
        "source": "https://docs.example.com/getting-started",
        "source_type": "web",
        "metadata": {"domain": "docs.example.com"}
      }'

    # Ingest YouTube transcript
    curl -X POST http://localhost:8000/api/v1/rag/ingest/content \\
      -H "Content-Type: application/json" \\
      -H "Cf-Access-Jwt-Assertion: $JWT_TOKEN" \\
      -d '{
        "content": "# Video Title\\n\\n[00:00] Welcome to...",
        "title": "Tutorial: Building APIs",
        "source": "https://youtube.com/watch?v=abc123",
        "source_type": "youtube",
        "metadata": {"channel": "TechChannel", "duration_seconds": 1234}
      }'
    ```

    **Performance Notes:**
    - Docling conversion: ~1-3 seconds for typical documents
    - Embedding generation: ~0.5-1 second per chunk
    - MongoDB storage: ~100ms for typical documents
    - Total time: 2-5 seconds for most content

    **Integration:**
    - Crawl4AI now uses this endpoint for content storage
    - YouTube RAG uses this for transcript storage
    - Sample scripts use this for article ingestion
    """
    from src.capabilities.retrieval.mongo_rag.ingestion.content_service import (
        ContentIngestionService,
    )

    service = ContentIngestionService()

    try:
        await service.initialize()

        # Check for duplicates if requested
        if request.skip_duplicates:
            existing_id = await service.check_duplicate(request.source)
            if existing_id:
                return IngestContentResponse(
                    success=True,
                    document_id=existing_id,
                    title=request.title,
                    source=request.source,
                    source_type=request.source_type,
                    chunks_created=0,
                    processing_time_ms=0,
                    skipped=True,
                    skip_reason=f"Document from source already exists (id: {existing_id})",
                    errors=[],
                )

        # Ingest content
        result = await service.ingest_content(
            content=request.content,
            title=request.title,
            source=request.source,
            source_type=request.source_type,
            metadata=request.metadata,
            user_id=str(user.id),
            user_email=user.email,
            use_docling=request.use_docling,
        )

        return IngestContentResponse(
            success=len(result.errors) == 0,
            document_id=result.document_id,
            title=result.title,
            source=result.source,
            source_type=result.source_type,
            chunks_created=result.chunks_created,
            processing_time_ms=result.processing_time_ms,
            skipped=False,
            skip_reason="",
            errors=result.errors,
        )

    except Exception as e:
        logger.exception(f"Content ingestion failed: {e}")
        return IngestContentResponse(
            success=False,
            errors=[str(e)],
        )
    finally:
        await service.close()


@router.post("/agent", response_model=AgentResponse)
async def agent(request: AgentRequest, deps: Annotated[Any, Depends(get_agent_deps)]):
    """
    Query the conversational RAG agent with natural language.

    This endpoint provides a conversational interface to the knowledge base. The agent
    can search the knowledge base, synthesize information, and provide natural language
    responses. It automatically decides when to search and how to combine search results
    into coherent answers.

    **Use Cases:**
    - Ask questions about ingested content
    - Get explanations synthesized from multiple sources
    - Have natural conversations about the knowledge base
    - Get contextual answers rather than raw search results

    **Request Body:**
    ```json
    {
        "query": "How do I set up authentication in the system?"
    }
    ```

    **Response:**
    ```json
    {
        "query": "How do I set up authentication in the system?",
        "response": "To set up authentication, you need to... [synthesized answer based on knowledge base]"
    }
    ```

    **Parameters:**
    - `query` (required): Natural language question or query. The agent will:
      - Determine if a search is needed
      - Search the knowledge base if relevant
      - Synthesize results into a coherent answer
      - Provide citations when appropriate

    **Returns:**
    - `AgentResponse` with the original query and synthesized response

    **Agent Behavior:**
    - Automatically uses hybrid search when knowledge base queries are detected
    - Can answer general questions without searching (greetings, etc.)
    - Synthesizes information from multiple search results
    - Provides conversational, natural language responses
    - Cites sources when information comes from the knowledge base

    **Errors:**
    - `500`: If agent execution fails
    - `500`: If MongoDB connection fails
    - `500`: If LLM provider is unavailable

    **Integration:**
    - Also available as MCP tool: `agent_query`
    - Uses the same knowledge base as search endpoint
    - Can answer questions about both uploaded documents and crawled content

    **Example Usage:**
    ```bash
    # Ask a question
    curl -X POST http://localhost:8000/api/v1/rag/agent \
      -H "Content-Type: application/json" \
      -d '{
        "query": "What are the main features of the authentication system?"
      }'

    # General conversation (no search needed)
    curl -X POST http://localhost:8000/api/v1/rag/agent \
      -H "Content-Type: application/json" \
      -d '{
        "query": "Hello, what can you help me with?"
      }'
    ```

    **Performance Notes:**
    - Response time: 2-5 seconds (includes search + LLM generation)
    - Uses configured LLM provider (default: Ollama)
    - Search results are limited to top matches for efficiency
    """

    # Agent now uses AgentDependencies directly, not StateDeps
    try:
        result = await rag_agent.run(request.query, deps=deps)

        return AgentResponse(query=request.query, response=result.data)
    except Exception as e:
        # Log error and return 500
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e!s}") from e


class CodeExampleSearchRequest(BaseModel):
    """Request model for code example search."""

    query: str = Field(..., description="Search query text")
    match_count: int = Field(5, ge=1, le=50, description="Number of results to return")


class CodeExampleSearchResponse(BaseModel):
    """Response model for code example search."""

    success: bool
    query: str
    results: list[dict[str, Any]]
    count: int


@router.post("/code-examples/search", response_model=CodeExampleSearchResponse)
async def search_code_examples_endpoint(
    request: CodeExampleSearchRequest, deps: Annotated[Any, Depends(get_agent_deps)]
):
    """
    Search for code examples in the knowledge base.

    Returns code snippets with summaries, language, and context.
    Requires USE_AGENTIC_RAG=true to be enabled.
    """
    from src.shared.wrappers import DepsWrapper

    ctx = DepsWrapper(deps)
    results = await search_code_examples(ctx, request.query, request.match_count)

    formatted_results = [
        {
            "code_example_id": r.code_example_id,
            "document_id": r.document_id,
            "code": r.code,
            "summary": r.summary,
            "language": r.language,
            "similarity": r.similarity,
            "source": r.source,
            "metadata": r.metadata,
        }
        for r in results
    ]

    return CodeExampleSearchResponse(
        success=True, query=request.query, results=formatted_results, count=len(formatted_results)
    )


@router.get("/sources")
async def get_sources(deps: Annotated[Any, Depends(get_agent_deps)]):
    """
    Get all available sources (domains/paths) that have been crawled and stored.

    Returns summaries and statistics for each source.
    """
    sources = await get_available_sources(deps.mongo_client)

    return {"success": True, "sources": sources, "count": len(sources)}


# ============================================================================
# Memory Tools Endpoints
# ============================================================================


@router.post("/memory/record")
async def record_message_endpoint(
    persona_id: str,
    content: str,
    deps: Annotated[Any, Depends(get_agent_deps)],
    user: User = Depends(get_current_user),
    role: str = "user",
):
    """Record a message in memory."""
    from src.capabilities.retrieval.mongo_rag.memory_tools import MemoryTools

    memory_tools = MemoryTools(deps=deps)
    memory_tools.record_message(str(user.id), persona_id, content, role)
    return {"success": True, "message": "Message recorded successfully"}


@router.get("/memory/context")
async def get_context_window_endpoint(
    persona_id: str,
    deps: Annotated[Any, Depends(get_agent_deps)],
    user: User = Depends(get_current_user),
    limit: int = 20,
):
    """Get recent messages for context window."""
    from src.capabilities.retrieval.mongo_rag.memory_tools import MemoryTools

    memory_tools = MemoryTools(deps=deps)
    messages = memory_tools.get_context_window(str(user.id), persona_id, limit)

    return {
        "success": True,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ],
        "count": len(messages),
    }


@router.post("/memory/facts")
async def store_fact_endpoint(
    persona_id: str,
    fact: str,
    deps: Annotated[Any, Depends(get_agent_deps)],
    user: User = Depends(get_current_user),
    tags: list[str] | None = None,
):
    """Store a fact in memory."""
    from src.capabilities.retrieval.mongo_rag.memory_tools import MemoryTools

    memory_tools = MemoryTools(deps=deps)
    memory_tools.store_fact(str(user.id), persona_id, fact, tags)
    return {"success": True, "message": "Fact stored successfully"}


@router.get("/memory/facts/search")
async def search_facts_endpoint(
    persona_id: str,
    query: str,
    deps: Annotated[Any, Depends(get_agent_deps)],
    user: User = Depends(get_current_user),
    limit: int = 10,
):
    """Search for facts in memory."""
    from src.capabilities.retrieval.mongo_rag.memory_tools import MemoryTools

    memory_tools = MemoryTools(deps=deps)
    facts = memory_tools.search_facts(str(user.id), persona_id, query, limit)

    return {
        "success": True,
        "facts": [
            {
                "fact": fact.fact,
                "tags": fact.tags or [],
                "created_at": fact.created_at.isoformat() if fact.created_at else None,
            }
            for fact in facts
        ],
        "count": len(facts),
    }


@router.post("/memory/web-content")
async def store_web_content_endpoint(
    persona_id: str,
    content: str,
    source_url: str,
    deps: Annotated[Any, Depends(get_agent_deps)],
    user: User = Depends(get_current_user),
    source_title: str = "",
    source_description: str = "",
    tags: list[str] | None = None,
):
    """Store web content in memory."""
    from src.capabilities.retrieval.mongo_rag.memory_tools import MemoryTools

    memory_tools = MemoryTools(deps=deps)
    chunks = memory_tools.store_web_content(
        str(user.id), persona_id, content, source_url, source_title, source_description, tags
    )
    return {"success": True, "message": "Web content stored successfully", "chunks": chunks}
