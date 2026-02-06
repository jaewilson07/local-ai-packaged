"""User-related schemas for Supabase."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCredentials(BaseModel):
    """External service credentials stored in Supabase."""

    mongodb_username: str | None = None
    mongodb_password: str | None = None
    immich_user_id: str | None = None
    immich_api_key: str | None = None
    discord_user_id: str | None = None


class SupabaseUser(BaseModel):
    """User model from Supabase profiles table."""

    id: UUID = Field(..., description="User UUID")
    email: EmailStr = Field(..., description="User email address")
    role: str = Field(default="user", description="User role (user, admin)")
    tier: str = Field(default="free", description="User tier (free, pro, enterprise)")
    created_at: datetime | None = Field(None, description="Account creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    # External service credentials
    credentials: UserCredentials = Field(
        default_factory=UserCredentials, description="External service credentials"
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat()}


class CreateUserRequest(BaseModel):
    """Request to create a new user."""

    email: EmailStr
    role: str = "user"
    tier: str = "free"
    credentials: UserCredentials | None = None


class UpdateCredentialsRequest(BaseModel):
    """Request to update user credentials."""

    email: EmailStr
    credentials: UserCredentials
