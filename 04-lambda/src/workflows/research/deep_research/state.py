"""State models for LangGraph orchestrator (Phase 4)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class Citation(BaseModel):
    """Citation information for a source."""

    source_id: str = Field(..., description="Source identifier")
    url: str = Field(..., description="Source URL")
    snippet: str = Field(..., description="Relevant snippet from source")
    ingested_at: datetime = Field(
        default_factory=datetime.now, description="When the source was ingested"
    )


class ResearchVector(BaseModel):
    """A research vector (atomic question) to be answered."""

    id: str = Field(..., description="Unique identifier for this vector")
    topic: str = Field(..., description="The research topic/question")
    search_queries: list[str] = Field(
        default_factory=list, description="Search queries to find information"
    )
    status: Literal["pending", "ingesting", "verified", "failed", "incomplete"] = Field(
        default="pending", description="Current status of this research vector"
    )
    feedback_loop_count: int = Field(default=0, description="Number of refinement loops")
    refined_query: str | None = Field(None, description="Refined query if validation failed")
    sources: list[str] = Field(
        default_factory=list, description="URLs of sources ingested for this vector"
    )
    chunks_retrieved: int = Field(default=0, description="Number of relevant chunks retrieved")


class ResearchState(TypedDict):
    """State that flows through the LangGraph."""

    user_query: str
    outline: list[str]
    vectors: list[ResearchVector]
    knowledge_graph_session_id: str
    completed_sections: dict[str, str]  # Map from outline item to written section
    final_report: str | None
    errors: list[str]
    current_vector_index: int
    max_iterations: int
    iteration_count: int
