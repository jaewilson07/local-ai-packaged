"""Main MongoDB RAG agent implementation with shared state."""

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from typing import Optional
from pydantic_ai.ag_ui import StateDeps
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel

from server.projects.mongo_rag.config import config
from server.projects.mongo_rag.dependencies import AgentDependencies
from server.projects.mongo_rag.prompts import MAIN_SYSTEM_PROMPT
from server.projects.mongo_rag.tools import semantic_search, hybrid_search, text_search
from server.projects.mongo_rag.neo4j_client import Neo4jClient, Neo4jConfig


def get_llm_model(model_choice: Optional[str] = None) -> OpenAIModel:
    """
    Get LLM model configuration based on environment variables.
    Supports any OpenAI-compatible API provider.

    Args:
        model_choice: Optional override for model choice

    Returns:
        Configured OpenAI-compatible model
    """
    llm_choice = model_choice or config.llm_model
    base_url = config.llm_base_url
    api_key = config.llm_api_key

    # Create provider based on configuration
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)

    return OpenAIModel(llm_choice, provider=provider)


class RAGState(BaseModel):
    """Minimal shared state for the RAG agent."""
    pass


# Create the RAG agent with AGUI support
rag_agent = Agent(
    get_llm_model(),
    deps_type=StateDeps[RAGState],
    system_prompt=MAIN_SYSTEM_PROMPT
)


@rag_agent.tool
async def search_knowledge_base(
    ctx: RunContext[StateDeps[RAGState]],
    query: str,
    match_count: Optional[int] = 5,
    search_type: Optional[str] = "hybrid"
) -> str:
    """
    Search the knowledge base for relevant information.

    Args:
        ctx: Agent runtime context with state dependencies
        query: Search query text
        match_count: Number of results to return (default: 5)
        search_type: Type of search - "semantic" or "text" or "hybrid" (default: hybrid)

    Returns:
        String containing the retrieved information formatted for the LLM
    """
    try:
        # Initialize database connection
        agent_deps = AgentDependencies()
        await agent_deps.initialize()

        # Create a context wrapper for the search tools
        class DepsWrapper:
            def __init__(self, deps):
                self.deps = deps

        deps_ctx = DepsWrapper(agent_deps)

        # Perform the search based on type
        if search_type == "hybrid":
            results = await hybrid_search(
                ctx=deps_ctx,
                query=query,
                match_count=match_count
            )
        elif search_type == "semantic":
            results = await semantic_search(
                ctx=deps_ctx,
                query=query,
                match_count=match_count
            )
        else:
            results = await text_search(
                ctx=deps_ctx,
                query=query,
                match_count=match_count
            )

        # Clean up
        await agent_deps.cleanup()

        # Format results as a simple string
        if not results:
            return "No relevant information found in the knowledge base."

        # Build a formatted response
        response_parts = [f"Found {len(results)} relevant documents:\n"]

        for i, result in enumerate(results, 1):
            response_parts.append(f"\n--- Document {i}: {result.document_title} (relevance: {result.similarity:.2f}) ---")
            response_parts.append(result.content)

        return "\n".join(response_parts)

    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"


@rag_agent.tool
async def find_related_entities(
    ctx: RunContext[StateDeps[RAGState]],
    name: str,
    depth: int = 1
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
        return f"Error traversing graph: {str(e)}"


@rag_agent.tool
async def get_entity_timeline(
    ctx: RunContext[StateDeps[RAGState]],
    name: str
) -> str:
    """
    Return a simple temporal timeline of relationships for an entity.

    Args:
        ctx: Agent runtime context
        name: Entity name

    Returns:
        Timeline entries as readable text
    """
    try:
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
        return f"Error retrieving timeline: {str(e)}"

