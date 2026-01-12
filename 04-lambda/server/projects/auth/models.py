"""Pydantic models for auth project."""

from uuid import UUID

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """User profile response model."""

    uid: UUID = Field(description="User unique identifier (UUID)")
    email: str = Field(description="User email address")
    role: str = Field(description="User role: 'user' or 'admin'")
    tier: str = Field(description="User tier: 'free' or 'pro'")
    services_enabled: list[str] = Field(
        default_factory=list,
        description="List of enabled services (e.g., 'supabase', 'immich', 'n8n')",
    )


class User(BaseModel):
    """Internal user model for database operations."""

    id: UUID = Field(description="User UUID")
    email: str = Field(description="User email address")
    role: str = Field(default="user", description="User role")
    tier: str = Field(default="free", description="User tier")
    created_at: str | None = Field(None, description="User creation timestamp")


# Data summary models
class RAGSummary(BaseModel):
    """RAG data summary across MongoDB and Supabase."""

    mongodb_documents: int = Field(default=0, description="Number of documents in MongoDB")
    mongodb_chunks: int = Field(default=0, description="Number of chunks in MongoDB")
    mongodb_sources: int = Field(default=0, description="Number of sources in MongoDB")
    supabase_items: int = Field(default=0, description="Number of items in Supabase")
    supabase_workflows: int = Field(default=0, description="Number of workflows in Supabase")
    supabase_workflow_runs: int = Field(
        default=0, description="Number of workflow runs in Supabase"
    )
    total_data_points: int = Field(
        default=0, description="Total data points across all RAG sources"
    )


class ImmichSummary(BaseModel):
    """Immich data summary."""

    total_photos: int = Field(default=0, description="Total number of photos")
    total_videos: int = Field(default=0, description="Total number of videos")
    total_albums: int = Field(default=0, description="Total number of albums")
    total_size_bytes: int = Field(default=0, description="Total storage size in bytes")
    message: str | None = Field(None, description="Status message (e.g., if service unavailable)")


class LoRASummary(BaseModel):
    """LoRA models summary."""

    total_models: int = Field(default=0, description="Total number of LoRA models")
    total_size_bytes: int = Field(default=0, description="Total size of all LoRA models in bytes")
    models: list[dict] = Field(default_factory=list, description="List of LoRA model metadata")


class CalendarSummary(BaseModel):
    """Calendar events summary."""

    total_events: int = Field(default=0, description="Total synced calendar events")
    events_by_calendar: dict[str, int] = Field(
        default_factory=dict, description="Event count per calendar ID"
    )
    calendars_count: int = Field(default=0, description="Number of calendars with synced events")
    last_synced_at: str | None = Field(None, description="Most recent sync timestamp")


class DataSummary(BaseModel):
    """Complete data summary across all services."""

    rag: RAGSummary = Field(description="RAG data summary")
    immich: ImmichSummary = Field(description="Immich data summary")
    loras: LoRASummary = Field(description="LoRA models summary")
    calendar: CalendarSummary = Field(description="Calendar events summary")
