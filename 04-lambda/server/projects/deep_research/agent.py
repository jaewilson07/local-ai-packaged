"""Linear Researcher Agent - Phase 3 Implementation.

A simple Pydantic-AI agent that executes a fixed sequence:
1. Search the web
2. Fetch top result
3. Parse document
4. Ingest knowledge
5. Query knowledge base
6. Write answer based on retrieved facts only
"""

import logging
import uuid

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from server.projects.deep_research.dependencies import DeepResearchDeps
from server.projects.deep_research.models import (
    DocumentChunk,
    FetchPageRequest,
    IngestKnowledgeRequest,
    ParseDocumentRequest,
    QueryKnowledgeRequest,
    SearchWebRequest,
)
from server.projects.deep_research.tools import (
    fetch_page,
    ingest_knowledge,
    parse_document,
    query_knowledge,
    search_web,
)
from server.projects.shared.llm import get_llm_model

logger = logging.getLogger(__name__)


# ============================================================================
# Response Model
# ============================================================================


class ResearchResponse(BaseModel):
    """Structured response from the Linear Researcher agent."""

    answer: str = Field(..., description="The answer to the user's question")
    sources: list[str] = Field(default_factory=list, description="List of source URLs used")
    citations: list[str] = Field(
        default_factory=list, description="List of citation markers [1], [2], etc."
    )
    session_id: str = Field(..., description="Session ID for this research session")


# ============================================================================
# System Prompt
# ============================================================================

LINEAR_RESEARCHER_SYSTEM_PROMPT = """You are a Linear Researcher agent that conducts research using a strict, sequential workflow.

CRITICAL RULES:
1. You MUST follow this exact sequence for every research query:
   a. Search the web using search_web tool
   b. Select the top result URL
   c. Fetch the page using fetch_page tool
   d. Parse the document using parse_document tool
   e. Ingest the knowledge using ingest_knowledge tool
   f. Query the knowledge base using query_knowledge tool
   g. Write your answer based ONLY on facts retrieved from the knowledge base

2. CLOSED-BOOK MODE: You are STRICTLY FORBIDDEN from using any pre-trained knowledge.
   - You may ONLY write sentences supported by facts retrieved from the knowledge base
   - If you cannot find information in the knowledge base, you must say "I could not find sufficient information to answer this question."

3. CITATION REQUIREMENT: Every claim must reference a source.
   - Use citation markers like [1], [2], etc.
   - Each citation must correspond to a source URL in the sources list

4. ACCURACY: Never hallucinate or make up information.
   - If the knowledge base doesn't contain the answer, admit it
   - Do not infer or guess based on partial information

5. SEQUENCE: Do not skip steps. Complete each step before moving to the next.

Your goal is to produce accurate, well-sourced answers based entirely on ingested knowledge."""


# ============================================================================
# Agent Definition
# ============================================================================

linear_researcher_agent = Agent(
    get_llm_model(),
    deps_type=DeepResearchDeps,
    system_prompt=LINEAR_RESEARCHER_SYSTEM_PROMPT,
    retries=2,
)


# ============================================================================
# Tools - Wrapping Phase 1 & 2 MCP Tools
# ============================================================================


@linear_researcher_agent.tool
async def search_web_tool(
    ctx: RunContext[DeepResearchDeps], query: str, result_count: int = 5
) -> str:
    """
    Search the web using SearXNG metasearch engine.

    This is the first step in the research workflow. Use this to find relevant URLs
    for your research query.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query string
        result_count: Number of results to return (default: 5)

    Returns:
        Formatted string with search results including URLs and snippets
    """
    try:
        deps = ctx.deps

        # Ensure session_id is set
        if not deps.session_id:
            deps.session_id = str(uuid.uuid4())

        request = SearchWebRequest(query=query, result_count=result_count)

        result = await search_web(deps, request)

        if not result.success or not result.results:
            return f"No results found for query: {query}"

        # Format results for the agent
        formatted = [f"Found {len(result.results)} search results for '{query}':\n"]
        for i, res in enumerate(result.results, 1):
            formatted.append(f"{i}. {res.title}")
            formatted.append(f"   URL: {res.url}")
            formatted.append(f"   Snippet: {res.snippet[:200]}...")
            formatted.append("")

        return "\n".join(formatted)

    except Exception as e:
        logger.exception(f"Error in search_web_tool: {e}")
        return f"Error searching the web: {e!s}"


@linear_researcher_agent.tool
async def fetch_page_tool(ctx: RunContext[DeepResearchDeps], url: str) -> str:
    """
    Fetch a single web page using Crawl4AI.

    This is step 2 in the research workflow. Use this to get the full content
    of a URL found in search results.

    Args:
        ctx: Agent runtime context with dependencies
        url: URL of the page to fetch

    Returns:
        Formatted string with page content and metadata
    """
    try:
        deps = ctx.deps

        if not deps.session_id:
            deps.session_id = str(uuid.uuid4())

        request = FetchPageRequest(url=url)
        result = await fetch_page(deps, request)

        if not result.success:
            return f"Failed to fetch page: {url}. Error: {result.metadata.get('error', 'Unknown error')}"

        # Format result for the agent
        formatted = [
            f"Successfully fetched page: {url}\n",
            f"Content length: {len(result.content)} characters\n",
            f"Content preview:\n{result.content[:500]}...\n",
        ]

        if result.metadata:
            formatted.append(f"Metadata: {result.metadata}")

        return "\n".join(formatted)

    except Exception as e:
        logger.exception(f"Error in fetch_page_tool: {e}")
        return f"Error fetching page: {e!s}"


@linear_researcher_agent.tool
async def parse_document_tool(
    ctx: RunContext[DeepResearchDeps], content: str, content_type: str = "html"
) -> str:
    """
    Parse a document (HTML, Markdown, or text) into structured chunks using Docling.

    This is step 3 in the research workflow. Use this to process the content
    fetched from a web page.

    Args:
        ctx: Agent runtime context with dependencies
        content: The content of the document to parse
        content_type: The type of the content (e.g., "html", "markdown", "text")

    Returns:
        Formatted string with chunk information
    """
    try:
        deps = ctx.deps

        request = ParseDocumentRequest(content=content, content_type=content_type)

        result = await parse_document(deps, request)

        if not result.success:
            return (
                f"Failed to parse document. Error: {result.metadata.get('error', 'Unknown error')}"
            )

        # Format result for the agent
        formatted = [
            f"Successfully parsed document into {len(result.chunks)} chunks\n",
            "Chunk details:\n",
        ]

        for i, chunk in enumerate(result.chunks[:5], 1):  # Show first 5 chunks
            formatted.append(f"  Chunk {i}: {len(chunk.content)} chars, {chunk.token_count} tokens")

        if len(result.chunks) > 5:
            formatted.append(f"  ... and {len(result.chunks) - 5} more chunks")

        return "\n".join(formatted)

    except Exception as e:
        logger.exception(f"Error in parse_document_tool: {e}")
        return f"Error parsing document: {e!s}"


@linear_researcher_agent.tool
async def ingest_knowledge_tool(
    ctx: RunContext[DeepResearchDeps],
    chunks: list[dict],
    source_url: str,
    title: str | None = None,
) -> str:
    """
    Ingest document chunks into MongoDB (for vector search) and Graphiti (for knowledge graph).

    This is step 4 in the research workflow. Use this to store parsed chunks
    so they can be retrieved later.

    Args:
        ctx: Agent runtime context with dependencies
        chunks: List of document chunks (from parse_document_tool)
        source_url: Source URL of the document
        title: Optional title of the document

    Returns:
        Success message with document ID and ingestion stats
    """
    try:
        deps = ctx.deps

        if not deps.session_id:
            deps.session_id = str(uuid.uuid4())

        # Convert dict chunks to Pydantic models
        pydantic_chunks = [DocumentChunk(**chunk) for chunk in chunks]

        request = IngestKnowledgeRequest(
            chunks=pydantic_chunks, session_id=deps.session_id, source_url=source_url, title=title
        )

        result = await ingest_knowledge(deps, request)

        if not result.success:
            errors = ", ".join(result.errors) if result.errors else "Unknown error"
            return f"Failed to ingest knowledge: {errors}"

        return (
            f"Successfully ingested knowledge:\n"
            f"  Document ID: {result.document_id}\n"
            f"  Chunks created: {result.chunks_created}\n"
            f"  Facts added to graph: {result.facts_added}\n"
            f"  Session ID: {deps.session_id}"
        )

    except Exception as e:
        logger.exception(f"Error in ingest_knowledge_tool: {e}")
        return f"Error ingesting knowledge: {e!s}"


@linear_researcher_agent.tool
async def query_knowledge_tool(
    ctx: RunContext[DeepResearchDeps], question: str, match_count: int = 5
) -> str:
    """
    Query the knowledge base using hybrid search filtered by session_id.

    This is step 5 in the research workflow. Use this to retrieve relevant
    facts from the knowledge base that was populated by ingest_knowledge_tool.

    Args:
        ctx: Agent runtime context with dependencies
        question: Question to query the knowledge base
        match_count: Number of results to return (default: 5)

    Returns:
        Formatted string with relevant search results and sources
    """
    try:
        deps = ctx.deps

        if not deps.session_id:
            return "Error: No session_id set. You must ingest knowledge first."

        request = QueryKnowledgeRequest(
            question=question,
            session_id=deps.session_id,
            match_count=match_count,
            search_type="hybrid",
        )

        result = await query_knowledge(deps, request)

        if not result.success:
            errors = ", ".join(result.errors) if result.errors else "Unknown error"
            return f"Failed to query knowledge base: {errors}"

        if not result.results:
            return f"No relevant information found in knowledge base for: {question}"

        # Format results with citations
        formatted = [f"Found {len(result.results)} relevant results for '{question}':\n"]

        for i, res in enumerate(result.results, 1):
            formatted.append(f"[{i}] {res.title or 'Untitled'}")
            formatted.append(f"    Source: {res.url}")
            formatted.append(f"    Relevance: {res.score:.2f}")
            formatted.append(f"    Content: {res.snippet[:300]}...")
            formatted.append("")

        return "\n".join(formatted)

    except Exception as e:
        logger.exception(f"Error in query_knowledge_tool: {e}")
        return f"Error querying knowledge base: {e!s}"
