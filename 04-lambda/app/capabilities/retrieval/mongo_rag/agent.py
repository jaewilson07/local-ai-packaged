"""Main MongoDB RAG agent implementation with shared state."""

from app.capabilities.retrieval.mongo_rag.config import config
from app.capabilities.retrieval.mongo_rag.dependencies import AgentDependencies
from app.capabilities.retrieval.mongo_rag.prompts import MAIN_SYSTEM_PROMPT
from app.capabilities.retrieval.mongo_rag.tools import hybrid_search, semantic_search, text_search
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from app.core.llm import get_llm_model
from app.core.wrappers import DepsWrapper

# Optional Neo4j import (only if neo4j package is available)
try:
    from capabilities.retrieval.mongo_rag.neo4j_client import Neo4jClient, Neo4jConfig
except ImportError:
    Neo4jClient = None
    Neo4jConfig = None

from app.capabilities.retrieval.mongo_rag.memory_tools import MemoryTools
from app.capabilities.retrieval.mongo_rag.nodes.citations import extract_citations, format_citations
from app.capabilities.retrieval.mongo_rag.nodes.decompose import decompose_query
from app.capabilities.retrieval.mongo_rag.nodes.grade import grade_documents
from app.capabilities.retrieval.mongo_rag.nodes.rewrite import rewrite_query
from app.capabilities.retrieval.mongo_rag.nodes.synthesize import synthesize_results

# Use shared LLM utility


class RAGState(BaseModel):
    """Minimal shared state for the RAG agent."""


# Create the RAG agent with AgentDependencies
# Changed from StateDeps[RAGState] to AgentDependencies to match tool requirements
rag_agent = Agent(get_llm_model(), deps_type=AgentDependencies, system_prompt=MAIN_SYSTEM_PROMPT)


@rag_agent.tool
async def search_knowledge_base(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: int | None = 5,
    search_type: str | None = "hybrid",
) -> str:
    """
    Search the knowledge base for relevant information.

    Args:
        ctx: Agent runtime context with dependencies (already initialized)
        query: Search query text
        match_count: Number of results to return (default: 5)
        search_type: Type of search - "semantic" or "text" or "hybrid" (default: hybrid)

    Returns:
        String containing the retrieved information formatted for the LLM
    """
    try:
        # Access dependencies from context - they are already initialized
        deps = ctx.deps

        # Create a context wrapper for the search tools
        deps_ctx = DepsWrapper(deps)

        # Perform the search based on type
        if search_type == "hybrid":
            results = await hybrid_search(ctx=deps_ctx, query=query, match_count=match_count)
        elif search_type == "semantic":
            results = await semantic_search(ctx=deps_ctx, query=query, match_count=match_count)
        else:
            results = await text_search(ctx=deps_ctx, query=query, match_count=match_count)

        # Format results as a simple string
        if not results:
            return "No relevant information found in the knowledge base."

        # Build a formatted response
        response_parts = [f"Found {len(results)} relevant documents:\n"]

        for i, result in enumerate(results, 1):
            response_parts.append(
                f"\n--- Document {i}: {result.document_title} (relevance: {result.similarity:.2f}) ---"
            )
            response_parts.append(result.content)

        return "\n".join(response_parts)

    except Exception as e:
        return f"Error searching knowledge base: {e!s}"


@rag_agent.tool
async def find_related_entities(
    ctx: RunContext[AgentDependencies], name: str, depth: int = 1
) -> str:
    """
    Traverse the knowledge graph to find entities related to the given name.

    Args:
        ctx: Agent runtime context
        name: Seed entity name
        depth: Traversal depth (1-3 recommended)

    Returns:
        Human-readable list of related entities
    """
    try:
        if Neo4jClient is None:
            return "Graph traversal unavailable: Neo4j package is not installed."
        if not config.neo4j_uri or not config.neo4j_password:
            return "Graph traversal unavailable: Neo4j is not configured."

        client = Neo4jClient(
            Neo4jConfig(
                uri=config.neo4j_uri,
                username=config.neo4j_username,
                password=config.neo4j_password,
            )
        )
        await client.connect()

        related = await client.find_related_entities(name=name, depth=max(1, min(depth, 3)))
        await client.close()

        if not related:
            return f"No related entities found for '{name}'."

        lines = [f"Related entities for '{name}':"]
        for e in related:
            conf = f" (conf {e.confidence:.2f})" if e.confidence is not None else ""
            lines.append(f"- {e.name} [{e.type}]{conf}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error traversing graph: {e!s}"


@rag_agent.tool
async def get_entity_timeline(ctx: RunContext[AgentDependencies], name: str) -> str:
    """
    Return a simple temporal timeline of relationships for an entity.

    Args:
        ctx: Agent runtime context
        name: Entity name

    Returns:
        Timeline entries as readable text
    """
    try:
        if Neo4jClient is None:
            return "Graph timeline unavailable: Neo4j package is not installed."
        if not config.neo4j_uri or not config.neo4j_password:
            return "Graph timeline unavailable: Neo4j is not configured."

        client = Neo4jClient(
            Neo4jConfig(
                uri=config.neo4j_uri,
                username=config.neo4j_username,
                password=config.neo4j_password,
            )
        )
        await client.connect()
        timeline = await client.get_entity_timeline(name)
        await client.close()

        if not timeline:
            return f"No timeline entries found for '{name}'."

        lines = [f"Timeline for '{name}':"]
        for t in timeline:
            lines.append(
                f"- {t['relation']} -> {t['target']} (from {t['valid_from']} to {t['valid_to']})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error retrieving timeline: {e!s}"


@rag_agent.tool
async def record_message(
    ctx: RunContext[AgentDependencies],
    user_id: str,
    persona_id: str,
    content: str,
    role: str = "user",
) -> str:
    """
    Record a message in memory for context window management.

    Args:
        ctx: Agent runtime context with dependencies (already initialized)
        user_id: User ID
        persona_id: Persona ID
        content: Message content
        role: Message role ("user" or "assistant")

    Returns:
        Success message
    """
    try:
        # Access dependencies from context - they are already initialized
        deps = ctx.deps

        memory_tools = MemoryTools(deps=deps)
        memory_tools.record_message(user_id, persona_id, content, role)
        return f"Message recorded successfully for {user_id}/{persona_id}"
    except Exception as e:
        return f"Error recording message: {e!s}"


@rag_agent.tool
async def get_context_window(
    ctx: RunContext[AgentDependencies], user_id: str, persona_id: str, limit: int = 20
) -> str:
    """
    Get recent messages for context window.

    Args:
        ctx: Agent runtime context with dependencies (already initialized)
        user_id: User ID
        persona_id: Persona ID
        limit: Maximum number of messages to return

    Returns:
        Formatted context window as string
    """
    try:
        # Access dependencies from context - they are already initialized
        deps = ctx.deps

        memory_tools = MemoryTools(deps=deps)
        messages = memory_tools.get_context_window(user_id, persona_id, limit)

        if not messages:
            return "No messages found in context window."

        formatted = [f"Context Window ({len(messages)} messages):"]
        for msg in messages:
            formatted.append(f"{msg.role}: {msg.content}")

        return "\n".join(formatted)
    except Exception as e:
        return f"Error getting context window: {e!s}"


@rag_agent.tool
async def store_fact(
    ctx: RunContext[AgentDependencies],
    user_id: str,
    persona_id: str,
    fact: str,
    tags: list[str] | None = None,
) -> str:
    """
    Store a fact in memory.

    Args:
        ctx: Agent runtime context with dependencies (already initialized)
        user_id: User ID
        persona_id: Persona ID
        fact: Fact to store
        tags: Optional tags for the fact

    Returns:
        Success message
    """
    try:
        # Access dependencies from context - they are already initialized
        deps = ctx.deps

        memory_tools = MemoryTools(deps=deps)
        memory_tools.store_fact(user_id, persona_id, fact, tags)
        return f"Fact stored successfully: {fact[:50]}..."
    except Exception as e:
        return f"Error storing fact: {e!s}"


@rag_agent.tool
async def search_facts(
    ctx: RunContext[AgentDependencies], user_id: str, persona_id: str, query: str, limit: int = 10
) -> str:
    """
    Search for facts in memory.

    Args:
        ctx: Agent runtime context with dependencies (already initialized)
        user_id: User ID
        persona_id: Persona ID
        query: Search query
        limit: Maximum number of facts to return

    Returns:
        Formatted search results
    """
    try:
        # Access dependencies from context - they are already initialized
        deps = ctx.deps

        memory_tools = MemoryTools(deps=deps)
        facts = memory_tools.search_facts(user_id, persona_id, query, limit)

        if not facts:
            return f"No facts found matching '{query}'"

        formatted = [f"Found {len(facts)} facts matching '{query}':"]
        for fact in facts:
            tags_str = f" [{', '.join(fact.tags)}]" if fact.tags else ""
            formatted.append(f"- {fact.fact}{tags_str}")

        return "\n".join(formatted)
    except Exception as e:
        return f"Error searching facts: {e!s}"


@rag_agent.tool
async def store_web_content(
    ctx: RunContext[AgentDependencies],
    user_id: str,
    persona_id: str,
    content: str,
    source_url: str,
    source_title: str = "",
    source_description: str = "",
    tags: list[str] | None = None,
) -> str:
    """
    Store web content in memory.

    Args:
        ctx: Agent runtime context with dependencies (already initialized)
        user_id: User ID
        persona_id: Persona ID
        content: Web content to store
        source_url: Source URL
        source_title: Source title
        source_description: Source description
        tags: Optional tags

    Returns:
        Success message
    """
    try:
        # Access dependencies from context - they are already initialized
        deps = ctx.deps

        memory_tools = MemoryTools(deps=deps)
        chunks = memory_tools.store_web_content(
            user_id, persona_id, content, source_url, source_title, source_description, tags
        )
        return f"Web content stored successfully ({chunks} chunks) from {source_url}"
    except Exception as e:
        return f"Error storing web content: {e!s}"


@rag_agent.tool
async def enhanced_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: int | None = 5,
    use_decomposition: bool = True,
    use_grading: bool = True,
    use_citations: bool = True,
    use_rewrite: bool = False,
) -> str:
    """
    Enhanced search with query decomposition, document grading, and citation extraction.

    This tool provides advanced RAG capabilities including:
    - Query decomposition for complex multi-part questions
    - Document grading to filter irrelevant results
    - Citation extraction for source tracking
    - Result synthesis from multiple sub-queries

    Args:
        ctx: Agent runtime context with dependencies (already initialized)
        query: Search query text
        match_count: Number of results per sub-query (default: 5)
        use_decomposition: Whether to decompose complex queries (default: True)
        use_grading: Whether to grade documents for relevance (default: True)
        use_citations: Whether to extract citations (default: True)
        use_rewrite: Whether to rewrite query first (default: False)

    Returns:
        Formatted search results with citations
    """
    try:
        # Access dependencies from context - they are already initialized
        deps = ctx.deps

        # Step 1: Optionally rewrite query
        if use_rewrite:
            rewritten_query = await rewrite_query(query, deps.openai_client)
            query = rewritten_query

        # Step 2: Decompose query if needed
        sub_queries = [query]
        if use_decomposition:
            _needs_decomp, sub_queries = await decompose_query(query, deps.openai_client)

        # Step 3: Search for each sub-query
        all_results = []

        # Create a context wrapper for the search tools
        deps_ctx = DepsWrapper(deps)

        for sub_query in sub_queries:
            # Perform hybrid search
            results = await hybrid_search(ctx=deps_ctx, query=sub_query, match_count=match_count)

            # Convert SearchResult to dict format
            result_dicts = [
                {
                    "content": r.content,
                    "metadata": r.metadata,
                    "similarity": r.similarity,
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "document_source": r.document_source,
                }
                for r in results
            ]

            all_results.append({"query": sub_query, "results": result_dicts})

        # Step 4: Grade documents if enabled
        if use_grading and deps.openai_client:
            graded_results = []
            for sub_result in all_results:
                results = sub_result["results"]
                filtered, _scores = await grade_documents(
                    query=sub_result["query"], documents=results, llm_client=deps.openai_client
                )
                graded_results.append({"query": sub_result["query"], "results": filtered})
            all_results = graded_results

        # Step 5: Extract citations if enabled
        citations_list = []
        if use_citations:
            for sub_result in all_results:
                citations = extract_citations(sub_result["results"])
                citations_list.extend(citations)

        # Step 6: Synthesize results if multiple sub-queries
        if len(sub_queries) > 1:
            synthesized = await synthesize_results(
                query=query, sub_query_results=all_results, llm_client=deps.openai_client
            )

            response_parts = [synthesized]
            if citations_list:
                response_parts.append("\n\n" + format_citations(citations_list))

            return "\n".join(response_parts)
        # Single query, format normally
        results = all_results[0]["results"] if all_results else []
        if not results:
            return "No relevant information found."

        response_parts = [f"Found {len(results)} relevant documents:\n"]
        for i, result in enumerate(results, 1):
            response_parts.append(
                f"\n--- Document {i}: {result.get('document_title', 'Unknown')} "
                f"(relevance: {result.get('similarity', 0):.2f}) ---"
            )
            response_parts.append(result.get("content", ""))

        if citations_list:
            response_parts.append("\n\n" + format_citations(citations_list))

        return "\n".join(response_parts)

    except Exception as e:
        return f"Error in enhanced search: {e!s}"
