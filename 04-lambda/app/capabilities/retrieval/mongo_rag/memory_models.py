"""Memory models for MongoDB RAG."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class MemoryMessage:
    """Message stored in memory."""

    user_id: str
    persona_id: str
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime | None = None
    # Sharing fields for RLS
    is_public: bool = False
    shared_with: list[str] | None = None
    group_ids: list[str] | None = None


@dataclass
class MemoryFact:
    """Fact stored in memory."""

    user_id: str
    persona_id: str
    fact: str
    tags: list[str] | None = None
    created_at: datetime | None = None
    # Sharing fields for RLS
    is_public: bool = False
    shared_with: list[str] | None = None
    group_ids: list[str] | None = None


@dataclass
class WebContent:
    """Web content stored in memory."""

    user_id: str
    persona_id: str
    content: str
    source_url: str
    source_title: str = ""
    source_description: str = ""
    source_domain: str | None = None
    content_type: str = "web_crawl"
    content_format: str = "markdown"
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None
    # Sharing fields for RLS
    is_public: bool = False
    shared_with: list[str] | None = None
    group_ids: list[str] | None = None
