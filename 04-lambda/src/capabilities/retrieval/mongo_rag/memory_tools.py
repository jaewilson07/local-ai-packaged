"""MemoryTools interface for MongoDB RAG."""

import logging
from typing import Any

from server.projects.mongo_rag.dependencies import AgentDependencies
from server.projects.mongo_rag.memory_models import MemoryFact, MemoryMessage
from server.projects.mongo_rag.stores.memory_store import MongoMemoryStore

logger = logging.getLogger(__name__)


class MemoryTools:
    """
    MemoryTools interface for MongoDB RAG.

    Provides high-level memory operations for messages, facts, and web content.
    """

    def __init__(self, deps: AgentDependencies | None = None):
        """
        Initialize MemoryTools.

        Args:
            deps: Optional AgentDependencies instance. If None, creates new one.
        """
        self.deps = deps
        self._store: MongoMemoryStore | None = None

    def _get_store(self) -> MongoMemoryStore:
        """Get or create memory store."""
        if self._store is None:
            if self.deps and self.deps.db:
                self._store = MongoMemoryStore(self.deps.db)
            else:
                raise ValueError("MemoryTools requires initialized dependencies with database")
        return self._store

    def record_message(
        self, user_id: str, persona_id: str, content: str, role: str = "user"
    ) -> None:
        """Record a message in memory."""
        try:
            message = MemoryMessage(
                user_id=user_id,
                persona_id=persona_id,
                role=role,
                content=content,
            )
            self._get_store().add_message(message)
        except Exception:
            logger.exception("Error recording message")
            raise

    def get_context_window(
        self, user_id: str, persona_id: str, limit: int = 20
    ) -> list[MemoryMessage]:
        """Get recent messages for context window."""
        try:
            return self._get_store().get_recent_messages(user_id, persona_id, limit)
        except Exception:
            logger.exception("Error getting context window")
            return []

    def store_fact(
        self, user_id: str, persona_id: str, fact: str, tags: list[str] | None = None
    ) -> None:
        """Store a fact in memory."""
        try:
            memory_fact = MemoryFact(
                user_id=user_id,
                persona_id=persona_id,
                fact=fact,
                tags=tags,
            )
            self._get_store().add_fact(memory_fact)
        except Exception:
            logger.exception("Error storing fact")
            raise

    def search_facts(
        self, user_id: str, persona_id: str, query: str, limit: int = 10
    ) -> list[MemoryFact]:
        """Search for facts in memory."""
        try:
            return self._get_store().search_facts(user_id, persona_id, query, limit)
        except Exception:
            logger.exception("Error searching facts")
            return []

    def store_web_content(
        self,
        user_id: str,
        persona_id: str,
        content: str,
        source_url: str,
        source_title: str = "",
        source_description: str = "",
        source_domain: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Store web content in memory."""
        try:
            return self._get_store().add_web_content(
                user_id=user_id,
                persona_id=persona_id,
                content=content,
                source_url=source_url,
                source_title=source_title,
                source_description=source_description,
                source_domain=source_domain,
                tags=tags,
                metadata=metadata,
            )
        except Exception:
            logger.exception("Error storing web content")
            return 0

    def get_web_content_by_url(
        self, user_id: str, persona_id: str, url: str
    ) -> dict[str, Any] | None:
        """Get web content by URL if it exists."""
        try:
            return self._get_store().get_web_content_by_url(user_id, persona_id, url)
        except Exception:
            logger.exception("Error getting web content")
            return None
