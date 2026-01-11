"""Workflow for STORM-based Deep Research Agent (Phase 4-6)."""

import logging
import uuid
from typing import Optional

from server.projects.deep_research.orchestrator import get_research_graph
from server.projects.deep_research.state import ResearchState
from server.projects.deep_research.dependencies import DeepResearchDeps

logger = logging.getLogger(__name__)


async def run_storm_research(
    query: str,
    session_id: Optional[str] = None,
    max_iterations: int = 10
) -> ResearchState:
    """
    Run the STORM-based deep research workflow.
    
    This implements the full LangGraph orchestrator with:
    - Planner: Generates outline and research vectors
    - Executor: Searches, fetches, parses, ingests
    - Auditor: Validates data (Phase 5)
    - Writer: Synthesizes final report
    
    Args:
        query: User's research query
        session_id: Optional session ID (will generate if not provided)
        max_iterations: Maximum number of graph iterations
        
    Returns:
        ResearchState with final_report and all intermediate state
    """
    if not session_id:
        session_id = str(uuid.uuid4())
    
    logger.info(f"Starting STORM research for query: '{query}' with session ID: {session_id}")
    
    # Initialize dependencies
    deps = DeepResearchDeps.from_settings(session_id=session_id)
    await deps.initialize()
    
    try:
        # Initialize state
        initial_state: ResearchState = {
            "user_query": query,
            "outline": [],
            "vectors": [],
            "knowledge_graph_session_id": session_id,
            "completed_sections": {},
            "final_report": None,
            "errors": [],
            "current_vector_index": 0,
            "max_iterations": max_iterations,
            "iteration_count": 0
        }
        
        # Get graph
        graph = get_research_graph()
        
        # Store deps in module-level variable for nodes to access
        # LangGraph nodes don't support dependency injection directly
        import server.projects.deep_research.orchestrator as orchestrator_module
        orchestrator_module._current_deps = deps
        
        try:
            final_state = await graph.ainvoke(initial_state)
        finally:
            orchestrator_module._current_deps = None
        
        logger.info(f"STORM research completed. Report length: {len(final_state.get('final_report', '') or '')}")
        return final_state
        
    except Exception as e:
        logger.exception(f"Error running STORM research: {e}")
        initial_state["errors"].append(str(e))
        initial_state["final_report"] = f"Error: {str(e)}"
        return initial_state
    finally:
        await deps.cleanup()
        logger.info("Dependencies cleaned up")
