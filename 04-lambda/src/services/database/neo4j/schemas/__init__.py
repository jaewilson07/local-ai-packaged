from datetime import datetime

from pydantic import BaseModel, Field


class UserNode(BaseModel):
    """Neo4j User node representation."""

    email: str = Field(description="User email address")
    created_at: datetime | None = Field(None, description="User creation timestamp")


class Neo4jConnectionStatus(BaseModel):
    """Neo4j connection health status."""

    status: str = Field(description="Connection status (healthy/unhealthy)")
    message: str | None = Field(None, description="Status message or error")
    driver_active: bool = Field(description="Whether driver is active")


class ProvisionUserRequest(BaseModel):
    """Request to provision a Neo4j user."""

    email: str = Field(description="User email address")
