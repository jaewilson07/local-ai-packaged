"""Pydantic models for Graphiti RAG API."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class GraphitiSearchRequest(BaseModel):
    """Request model for Graphiti search."""
    query: str = Field(..., description="Search query text")
    match_count: int = Field(10, ge=1, le=50, description="Number of results to return")


class GraphitiSearchResponse(BaseModel):
    """Response model for Graphiti search."""
    success: bool
    query: str
    results: List[Dict[str, Any]]
    count: int


class ParseRepositoryRequest(BaseModel):
    """Request model for parsing a GitHub repository."""
    repo_url: str = Field(..., description="GitHub repository URL (must end with .git)")


class ParseRepositoryResponse(BaseModel):
    """Response model for repository parsing."""
    success: bool
    message: str
    repo_url: str


class ValidateScriptRequest(BaseModel):
    """Request model for script validation."""
    script_path: str = Field(..., description="Absolute path to the Python script to validate")


class ValidateScriptResponse(BaseModel):
    """Response model for script validation."""
    success: bool
    overall_confidence: float
    validation_summary: str
    hallucinations_detected: List[Dict[str, Any]]
    recommendations: List[str]


class QueryKnowledgeGraphRequest(BaseModel):
    """Request model for knowledge graph queries."""
    command: str = Field(..., description="Command to execute (e.g., 'repos', 'explore <repo>', 'query <cypher>')")


class QueryKnowledgeGraphResponse(BaseModel):
    """Response model for knowledge graph queries."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
