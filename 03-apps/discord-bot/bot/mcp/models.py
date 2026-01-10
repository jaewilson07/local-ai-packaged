"""Pydantic models for MCP tools."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ServerInfo(BaseModel):
    """Discord server information."""
    id: str = Field(..., description="Server ID")
    name: str = Field(..., description="Server name")
    member_count: int = Field(..., description="Number of members")
    owner_id: str = Field(..., description="Server owner user ID")
    icon_url: Optional[str] = Field(None, description="Server icon URL")


class ChannelInfo(BaseModel):
    """Discord channel information."""
    id: str = Field(..., description="Channel ID")
    name: str = Field(..., description="Channel name")
    type: str = Field(..., description="Channel type (text, voice, category, etc.)")
    category_id: Optional[str] = Field(None, description="Parent category ID")
    position: int = Field(..., description="Channel position")


class MemberInfo(BaseModel):
    """Discord member information."""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    display_name: Optional[str] = Field(None, description="Display name (nickname)")
    roles: List[str] = Field(default_factory=list, description="List of role IDs")
    joined_at: Optional[str] = Field(None, description="When user joined the server")


class UserInfo(BaseModel):
    """Discord user information."""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    discriminator: str = Field(..., description="User discriminator")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    bot: bool = Field(False, description="Whether user is a bot")


class MessageInfo(BaseModel):
    """Discord message information."""
    id: str = Field(..., description="Message ID")
    content: str = Field(..., description="Message content")
    author_id: str = Field(..., description="Author user ID")
    author_username: str = Field(..., description="Author username")
    channel_id: str = Field(..., description="Channel ID")
    timestamp: str = Field(..., description="Message timestamp (ISO format)")
    attachments: List[str] = Field(default_factory=list, description="Attachment URLs")


class ScheduledEventInfo(BaseModel):
    """Discord scheduled event information."""
    id: str = Field(..., description="Event ID")
    name: str = Field(..., description="Event name")
    description: Optional[str] = Field(None, description="Event description")
    start_time: str = Field(..., description="Start time (ISO format)")
    end_time: Optional[str] = Field(None, description="End time (ISO format)")
    location: Optional[str] = Field(None, description="Event location")
    event_type: Literal["external", "voice", "stage"] = Field(..., description="Event type")
    status: str = Field(..., description="Event status")
