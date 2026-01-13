"""LangGraph orchestrator for Deep Research Agent (Phase 4-6).

This implements the STORM architecture with:
- Planner node: Generates research outline
- Executor node: Searches, fetches, parses, and ingests
- Auditor node: Validates data before writing
- Writer node: Synthesizes final report
"""

import logging

from langgraph.graph import END, StateGraph
from pydantic_ai import Agent

from server.projects.deep_research.dependencies import DeepResearchDeps
from server.projects.deep_research.models import (
    FetchPageRequest,
    IngestKnowledgeRequest,
    ParseDocumentRequest,
    QueryKnowledgeRequest,
    SearchWebRequest,
)
from server.projects.deep_research.state import ResearchState, ResearchVector
from server.projects.deep_research.tools import (
    fetch_page,
    ingest_knowledge,
    parse_document,
    query_knowledge,
    search_web,
)
from server.projects.shared.llm import get_llm_model

logger = logging.getLogger(__name__)

# Temporary storage for deps (used by nodes)
_current_deps: DeepResearchDeps | None = None


# ============================================================================
# Helper Agents for Each Node
# ============================================================================


def _get_planner_model():
    """Get LLM model for planner."""
    return get_llm_model("DEEP_RESEARCH")


def _get_executor_model():
    """Get LLM model for executor."""
    return get_llm_model("DEEP_RESEARCH")


def _get_auditor_model():
    """Get LLM model for auditor."""
    return get_llm_model("DEEP_RESEARCH")


def _get_writer_model():
    """Get LLM model for writer."""
    return get_llm_model("DEEP_RESEARCH")


# Planner Agent (STORM Pattern)
planner_agent = Agent(
    _get_planner_model(),
    deps_type=DeepResearchDeps,
    system_prompt="""You are a Research Planner. Your task is to:
1. Understand the user's research query
2. Conduct a lightweight pre-search (top 5 results) to understand domain terminology
3. Generate a comprehensive research outline (Table of Contents)
4. Decompose the outline into atomic research vectors (specific questions)

Return a JSON structure with:
- outline: List of section titles
- vectors: List of {id, topic, search_queries} objects
""",
)


# Executor Agent (Hunter Pattern)
executor_agent = Agent(
    _get_executor_model(),
    deps_type=DeepResearchDeps,
    system_prompt="""You are a Research Executor. Your task is to:
1. Search for information using the provided search queries
2. Evaluate search results and select high-value URLs
3. Fetch and parse the selected pages
4. Ingest the content into the knowledge base

You have access to search_web, fetch_page, parse_document, and ingest_knowledge tools.
""",
)


# Auditor Agent (Validation)
auditor_agent = Agent(
    _get_auditor_model(),
    deps_type=DeepResearchDeps,
    system_prompt="""You are a Research Auditor. Your task is to:
1. Query the knowledge base to verify we have sufficient evidence
2. Check if the retrieved chunks actually answer the research vector question
3. Assess confidence level (high/medium/low)
4. If confidence is low, suggest a refined search query

Return a JSON structure with:
- confidence: "high" | "medium" | "low"
- evidence_found: boolean
- refined_query: optional refined query if confidence is low
""",
)


# Writer Agent (Synthesis)
writer_agent = Agent(
    _get_writer_model(),
    deps_type=DeepResearchDeps,
    system_prompt="""You are a Research Writer. Your task is to:
1. Write sections of the research report based ONLY on verified chunks from the knowledge base
2. STRICTLY FORBIDDEN from using pre-trained knowledge
3. Must cite every claim with [SourceID] where SourceID corresponds to chunk_id
4. If information is missing, explicitly state "Information not available in sources"

You are in "closed-book" mode. Only use facts from the retrieved chunks.
""",
)


# ============================================================================
# LangGraph Nodes
# ============================================================================


async def planner_node(state: ResearchState) -> ResearchState:
    """Planner node: Generates research outline and vectors (STORM pattern)."""
    global _current_deps
    deps = _current_deps
    if not deps:
        state["errors"].append("Dependencies not initialized")
        return state

    logger.info(f"Planner node: Processing query: {state['user_query']}")

    try:
        # Pre-search to understand domain
        pre_search_request = SearchWebRequest(query=state["user_query"], result_count=5)
        pre_search_response = await search_web(deps, pre_search_request)

        # Generate outline and vectors using planner agent
        planner_prompt = f"""User Query: {state["user_query"]}

Pre-search results (for context):
{chr(10).join([f"- {r.title}: {r.snippet[:100]}..." for r in pre_search_response.results[:3]])}

Generate a comprehensive research outline and break it down into atomic research vectors.
Each vector should be a specific question that can be answered independently.

Return JSON:
{{
  "outline": ["Section 1", "Section 2", ...],
  "vectors": [
    {{"id": "v1", "topic": "Question 1", "search_queries": ["query1", "query2"]}},
    ...
  ]
}}
"""

        await planner_agent.run(planner_prompt, deps=deps)

        # Parse result (simplified - in production, use structured output)
        # For now, we'll create a simple outline and vectors
        outline = [
            "Introduction",
            "Background and Context",
            "Key Findings",
            "Analysis",
            "Conclusion",
        ]

        vectors = [
            ResearchVector(
                id=f"v{i + 1}",
                topic=section,
                search_queries=[f"{state['user_query']} {section}"],
                status="pending",
            )
            for i, section in enumerate(outline)
        ]

        state["outline"] = outline
        state["vectors"] = vectors
        state["current_vector_index"] = 0

        logger.info(f"Planner generated {len(outline)} sections and {len(vectors)} vectors")
        return state

    except Exception as e:
        logger.exception("Error in planner node")
        state["errors"].append(f"Planner error: {e!s}")
        return state


async def executor_node(state: ResearchState) -> ResearchState:
    """Executor node: Searches, fetches, parses, and ingests (Hunter pattern)."""
    global _current_deps
    deps = _current_deps
    if not deps:
        state["errors"].append("Dependencies not initialized")
        return state

    if state["current_vector_index"] >= len(state["vectors"]):
        logger.info("All vectors processed")
        return state

    vector = state["vectors"][state["current_vector_index"]]
    logger.info(f"Executor node: Processing vector {vector.id}: {vector.topic}")

    try:
        vector.status = "ingesting"

        # Search
        search_request = SearchWebRequest(
            query=vector.search_queries[0] if vector.search_queries else vector.topic,
            result_count=5,
        )
        search_response = await search_web(deps, search_request)

        if not search_response.results:
            vector.status = "failed"
            state["current_vector_index"] += 1
            return state

        # Select top result (in production, use LLM to evaluate)
        top_result = search_response.results[0]
        vector.sources.append(top_result.url)

        # Fetch
        fetch_request = FetchPageRequest(url=top_result.url)
        fetch_response = await fetch_page(deps, fetch_request)

        if not fetch_response.success:
            vector.status = "failed"
            state["current_vector_index"] += 1
            return state

        # Parse
        parse_request = ParseDocumentRequest(content=fetch_response.content, content_type="html")
        parse_response = await parse_document(deps, parse_request)

        if not parse_response.success or not parse_response.chunks:
            vector.status = "failed"
            state["current_vector_index"] += 1
            return state

        # Ingest
        ingest_request = IngestKnowledgeRequest(
            chunks=parse_response.chunks,
            session_id=state["knowledge_graph_session_id"],
            source_url=top_result.url,
            title=top_result.title,
        )
        ingest_response = await ingest_knowledge(deps, ingest_request)

        if ingest_response.success:
            vector.status = "ingesting"  # Will be verified by auditor
            logger.info(f"Ingested {ingest_response.chunks_created} chunks for vector {vector.id}")
        else:
            vector.status = "failed"

        state["current_vector_index"] += 1
        return state

    except Exception as e:
        logger.exception("Error in executor node")
        vector.status = "failed"
        state["errors"].append(f"Executor error for {vector.id}: {e!s}")
        state["current_vector_index"] += 1
        return state


async def auditor_node(state: ResearchState) -> ResearchState:
    """Auditor node: Validates that RAG data answers the research vector (Phase 5)."""
    global _current_deps
    deps = _current_deps
    if not deps:
        state["errors"].append("Dependencies not initialized")
        return state

    if state["current_vector_index"] == 0:
        # Reset to start auditing from beginning
        state["current_vector_index"] = 0

    if state["current_vector_index"] >= len(state["vectors"]):
        return state

    vector = state["vectors"][state["current_vector_index"]]

    if vector.status != "ingesting":
        state["current_vector_index"] += 1
        return state

    logger.info(f"Auditor node: Validating vector {vector.id}: {vector.topic}")

    try:
        # Query knowledge base
        query_request = QueryKnowledgeRequest(
            question=vector.topic,
            session_id=state["knowledge_graph_session_id"],
            match_count=5,
            search_type="hybrid",
        )
        query_response = await query_knowledge(deps, query_request)

        if not query_response.success or not query_response.results:
            vector.status = "incomplete"
            vector.feedback_loop_count += 1
            vector.refined_query = f"{vector.topic} detailed information"
            logger.warning(f"Insufficient evidence for vector {vector.id}")
            state["current_vector_index"] += 1
            return state

        # Use auditor agent to assess confidence
        chunks_summary = "\n".join(
            [
                f"[{i + 1}] {chunk.content[:200]}..."
                for i, chunk in enumerate(query_response.results[:3])
            ]
        )

        auditor_prompt = f"""Research Vector: {vector.topic}

Retrieved Chunks:
{chunks_summary}

Assess whether these chunks provide sufficient evidence to answer the research vector.
Return JSON:
{{
  "confidence": "high" | "medium" | "low",
  "evidence_found": true/false,
  "refined_query": "optional refined query if low confidence"
}}
"""

        await auditor_agent.run(auditor_prompt, deps=deps)

        # Simplified: if we have results, mark as verified
        if len(query_response.results) >= 2:
            vector.status = "verified"
            vector.chunks_retrieved = len(query_response.results)
            logger.info(f"Vector {vector.id} verified with {len(query_response.results)} chunks")
        else:
            vector.status = "incomplete"
            vector.feedback_loop_count += 1
            if vector.feedback_loop_count < 3:  # Max 3 refinement attempts
                vector.refined_query = f"{vector.topic} more detailed"
                logger.warning(f"Vector {vector.id} needs refinement")
            else:
                vector.status = "failed"
                logger.error(
                    f"Vector {vector.id} failed after {vector.feedback_loop_count} attempts"
                )

        state["current_vector_index"] += 1
        return state

    except Exception as e:
        logger.exception("Error in auditor node")
        vector.status = "failed"
        state["errors"].append(f"Auditor error for {vector.id}: {e!s}")
        state["current_vector_index"] += 1
        return state


async def writer_node(state: ResearchState) -> ResearchState:
    """Writer node: Synthesizes verified sections into final report."""
    global _current_deps
    deps = _current_deps
    if not deps:
        state["errors"].append("Dependencies not initialized")
        state["final_report"] = "Error: Dependencies not initialized"
        return state

    logger.info("Writer node: Generating final report")

    try:
        # Collect all verified vectors
        verified_vectors = [v for v in state["vectors"] if v.status == "verified"]

        if not verified_vectors:
            state["final_report"] = "No verified information available to generate report."
            return state

        # For each outline section, write based on verified vectors
        sections = []
        for i, section_title in enumerate(state["outline"]):
            # Find relevant vectors for this section
            relevant_vectors = [v for v in verified_vectors if i < len(verified_vectors)]

            if not relevant_vectors:
                continue

            # Query knowledge base for this section
            query_request = QueryKnowledgeRequest(
                question=f"{state['user_query']} {section_title}",
                session_id=state["knowledge_graph_session_id"],
                match_count=10,
                search_type="hybrid",
            )
            query_response = await query_knowledge(deps, query_request)

            if not query_response.results:
                continue

            # Build citation map
            citations = {}
            for idx, chunk in enumerate(query_response.results):
                citations[f"[{idx + 1}]"] = {
                    "chunk_id": chunk.chunk_id,
                    "url": chunk.document_source,
                }

            # Use writer agent to synthesize section
            chunks_text = "\n\n".join(
                [f"[{i + 1}] {chunk.content}" for i, chunk in enumerate(query_response.results)]
            )

            writer_prompt = f"""Section: {section_title}

Retrieved Facts (with citations):
{chunks_text}

Write this section of the research report. You MUST:
1. Only use facts from the retrieved chunks above
2. Cite every claim with [1], [2], etc. matching the chunk numbers
3. Do NOT use any pre-trained knowledge
4. If information is missing, state "Information not available in sources"

Write the section now:
"""

            result = await writer_agent.run(writer_prompt, deps=deps)
            section_text = result.data if isinstance(result.data, str) else str(result.data)

            sections.append(f"## {section_title}\n\n{section_text}\n")
            state["completed_sections"][section_title] = section_text

        # Combine sections into final report
        report = f"# Research Report: {state['user_query']}\n\n"
        report += "\n".join(sections)

        # Add sources section
        all_sources = set()
        for vector in verified_vectors:
            all_sources.update(vector.sources)

        if all_sources:
            report += "\n## Sources\n\n"
            for i, source in enumerate(sorted(all_sources), 1):
                report += f"{i}. {source}\n"

        state["final_report"] = report
        logger.info(f"Generated report with {len(sections)} sections")
        return state

    except Exception as e:
        logger.exception("Error in writer node")
        state["errors"].append(f"Writer error: {e!s}")
        state["final_report"] = f"Error generating report: {e!s}"
        return state


# ============================================================================
# Graph Construction
# ============================================================================


def should_continue_executor(state: ResearchState) -> str:
    """Determine if we should continue executing or move to auditor."""
    if state["current_vector_index"] < len(state["vectors"]):
        return "executor"
    return "auditor"


def should_continue_auditor(state: ResearchState) -> str:
    """Determine if we should continue auditing or move to writer."""
    if state["current_vector_index"] < len(state["vectors"]):
        return "auditor"
    return "writer"


def create_research_graph() -> StateGraph:
    """Create the LangGraph StateGraph for deep research."""
    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("auditor", auditor_node)
    workflow.add_node("writer", writer_node)

    # Set entry point
    workflow.set_entry_point("planner")

    # Add edges
    workflow.add_edge("planner", "executor")
    workflow.add_conditional_edges(
        "executor", should_continue_executor, {"executor": "executor", "auditor": "auditor"}
    )
    workflow.add_conditional_edges(
        "auditor", should_continue_auditor, {"auditor": "auditor", "writer": "writer"}
    )
    workflow.add_edge("writer", END)

    return workflow.compile()


# Global graph instance
_research_graph = None


def get_research_graph() -> StateGraph:
    """Get or create the research graph instance."""
    global _research_graph
    if _research_graph is None:
        _research_graph = create_research_graph()
    return _research_graph
