"""Memory models for MongoDB RAG."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class MemoryMessage:
    """Message stored in memory."""
    user_id: str
    persona_id: str
    role: str  # "user" or "assistant"
    content: str
    created_at: Optional[datetime] = None


@dataclass
class MemoryFact:
    """Fact stored in memory."""
    user_id: str
    persona_id: str
    fact: str
    tags: Optional[List[str]] = None
    created_at: Optional[datetime] = None


@dataclass
class WebContent:
    """Web content stored in memory."""
    user_id: str
    persona_id: str
    content: str
    source_url: str
    source_title: str = ""
    source_description: str = ""
    source_domain: Optional[str] = None
    content_type: str = "web_crawl"
    content_format: str = "markdown"
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
