"""Tests for Deep Research state models."""

from datetime import datetime

from server.projects.deep_research.state import Citation, ResearchState, ResearchVector

# ============================================================================
# ResearchState Tests
# ============================================================================


def test_research_state_creation():
    """Test ResearchState creation with all fields."""
    state: ResearchState = {
        "user_query": "What is deep research?",
        "outline": ["Introduction", "Background", "Conclusion"],
        "vectors": [],
        "knowledge_graph_session_id": "test-session-123",
        "completed_sections": {},
        "final_report": None,
        "errors": [],
        "current_vector_index": 0,
        "max_iterations": 10,
        "iteration_count": 0,
    }

    assert state["user_query"] == "What is deep research?"
    assert len(state["outline"]) == 3
    assert state["knowledge_graph_session_id"] == "test-session-123"
    assert state["current_vector_index"] == 0


def test_research_state_typing():
    """Test ResearchState TypedDict validation."""
    state: ResearchState = {
        "user_query": "Test query",
        "outline": [],
        "vectors": [],
        "knowledge_graph_session_id": "session-123",
        "completed_sections": {},
        "final_report": None,
        "errors": [],
        "current_vector_index": 0,
        "max_iterations": 10,
        "iteration_count": 0,
    }

    # TypedDict should accept this structure
    assert isinstance(state, dict)
    assert "user_query" in state
    assert "outline" in state
    assert "vectors" in state


def test_research_state_defaults():
    """Test ResearchState default value handling."""
    state: ResearchState = {
        "user_query": "Test query",
        "outline": [],
        "vectors": [],
        "knowledge_graph_session_id": "session-123",
        "completed_sections": {},
        "final_report": None,
        "errors": [],
        "current_vector_index": 0,
        "max_iterations": 10,
        "iteration_count": 0,
    }

    # Defaults should be set
    assert state["errors"] == []
    assert state["completed_sections"] == {}
    assert state["current_vector_index"] == 0


# ============================================================================
# ResearchVector Tests
# ============================================================================


def test_research_vector_creation():
    """Test ResearchVector creation."""
    vector = ResearchVector(
        id="v1",
        topic="What is deep research?",
        search_queries=["deep research", "research methodology"],
        status="pending",
    )

    assert vector.id == "v1"
    assert vector.topic == "What is deep research?"
    assert len(vector.search_queries) == 2
    assert vector.status == "pending"
    assert vector.feedback_loop_count == 0


def test_research_vector_status_transitions():
    """Test ResearchVector status state machine."""
    vector = ResearchVector(id="v1", topic="Test topic", search_queries=["test"], status="pending")

    # Test valid transitions
    vector.status = "ingesting"
    assert vector.status == "ingesting"

    vector.status = "verified"
    assert vector.status == "verified"

    vector.status = "failed"
    assert vector.status == "failed"

    vector.status = "incomplete"
    assert vector.status == "incomplete"


def test_research_vector_refinement():
    """Test refinement loop tracking."""
    vector = ResearchVector(id="v1", topic="Test topic", search_queries=["test"], status="pending")

    assert vector.feedback_loop_count == 0
    assert vector.refined_query is None

    # Simulate refinement
    vector.feedback_loop_count = 1
    vector.refined_query = "refined test query"
    vector.status = "incomplete"

    assert vector.feedback_loop_count == 1
    assert vector.refined_query == "refined test query"
    assert vector.status == "incomplete"


def test_research_vector_sources():
    """Test source URL tracking."""
    vector = ResearchVector(id="v1", topic="Test topic", search_queries=["test"], status="pending")

    assert len(vector.sources) == 0

    vector.sources.append("https://example.com/source1")
    vector.sources.append("https://example.com/source2")

    assert len(vector.sources) == 2
    assert "https://example.com/source1" in vector.sources


def test_research_vector_chunks_retrieved():
    """Test chunks retrieved tracking."""
    vector = ResearchVector(id="v1", topic="Test topic", search_queries=["test"], status="pending")

    assert vector.chunks_retrieved == 0

    vector.chunks_retrieved = 5
    assert vector.chunks_retrieved == 5


# ============================================================================
# Citation Tests
# ============================================================================


def test_citation_creation():
    """Test Citation model creation."""
    citation = Citation(
        source_id="source-123",
        url="https://example.com/source",
        snippet="Relevant snippet from source",
        ingested_at=datetime.now(),
    )

    assert citation.source_id == "source-123"
    assert citation.url == "https://example.com/source"
    assert citation.snippet == "Relevant snippet from source"
    assert isinstance(citation.ingested_at, datetime)


def test_citation_metadata():
    """Test Citation metadata handling."""
    citation = Citation(
        source_id="source-123",
        url="https://example.com/source",
        snippet="Relevant snippet",
        ingested_at=datetime.now(),
    )

    # Citation is a Pydantic model, so it should have proper validation
    assert citation.source_id is not None
    assert citation.url is not None
    assert citation.snippet is not None


def test_citation_default_ingested_at():
    """Test Citation default ingested_at."""
    citation = Citation(
        source_id="source-123", url="https://example.com/source", snippet="Relevant snippet"
    )

    # Should have default datetime.now()
    assert isinstance(citation.ingested_at, datetime)


# ============================================================================
# Integration Tests
# ============================================================================


def test_research_state_with_vectors():
    """Test ResearchState with ResearchVectors."""
    vectors = [
        ResearchVector(id="v1", topic="Topic 1", search_queries=["query1"], status="pending"),
        ResearchVector(id="v2", topic="Topic 2", search_queries=["query2"], status="pending"),
    ]

    state: ResearchState = {
        "user_query": "Test query",
        "outline": ["Section 1", "Section 2"],
        "vectors": vectors,
        "knowledge_graph_session_id": "session-123",
        "completed_sections": {},
        "final_report": None,
        "errors": [],
        "current_vector_index": 0,
        "max_iterations": 10,
        "iteration_count": 0,
    }

    assert len(state["vectors"]) == 2
    assert state["vectors"][0].id == "v1"
    assert state["vectors"][1].id == "v2"


def test_research_state_completed_sections():
    """Test ResearchState completed_sections tracking."""
    state: ResearchState = {
        "user_query": "Test query",
        "outline": ["Section 1", "Section 2"],
        "vectors": [],
        "knowledge_graph_session_id": "session-123",
        "completed_sections": {
            "Section 1": "Content for section 1",
            "Section 2": "Content for section 2",
        },
        "final_report": None,
        "errors": [],
        "current_vector_index": 0,
        "max_iterations": 10,
        "iteration_count": 0,
    }

    assert len(state["completed_sections"]) == 2
    assert "Section 1" in state["completed_sections"]
    assert "Section 2" in state["completed_sections"]


def test_research_state_error_collection():
    """Test ResearchState error collection."""
    state: ResearchState = {
        "user_query": "Test query",
        "outline": [],
        "vectors": [],
        "knowledge_graph_session_id": "session-123",
        "completed_sections": {},
        "final_report": None,
        "errors": ["Error 1", "Error 2"],
        "current_vector_index": 0,
        "max_iterations": 10,
        "iteration_count": 0,
    }

    assert len(state["errors"]) == 2
    assert "Error 1" in state["errors"]
    assert "Error 2" in state["errors"]
