"""MemoryTools interface for MongoDB RAG."""

import logging
from typing import List, Optional, Dict, Any

from server.projects.mongo_rag.memory_models import MemoryMessage, MemoryFact
from server.projects.mongo_rag.stores.memory_store import MongoMemoryStore
from server.projects.mongo_rag.dependencies import AgentDependencies

logger = logging.getLogger(__name__)


class MemoryTools:
    """
    MemoryTools interface for MongoDB RAG.
    
    Provides high-level memory operations for messages, facts, and web content.
    """
    
    def __init__(self, deps: Optional[AgentDependencies] = None):
        """
        Initialize MemoryTools.
        
        Args:
            deps: Optional AgentDependencies instance. If None, creates new one.
        """
        self.deps = deps
        self._store: Optional[MongoMemoryStore] = None
    
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
        except Exception as e:
            logger.error(f"Error recording message: {e}")
            raise
    
    def get_context_window(
        self, user_id: str, persona_id: str, limit: int = 20
    ) -> List[MemoryMessage]:
        """Get recent messages for context window."""
        try:
            return self._get_store().get_recent_messages(user_id, persona_id, limit)
        except Exception as e:
            logger.error(f"Error getting context window: {e}")
            return []
    
    def store_fact(
        self, user_id: str, persona_id: str, fact: str, tags: Optional[List[str]] = None
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
        except Exception as e:
            logger.error(f"Error storing fact: {e}")
            raise
    
    def search_facts(
        self, user_id: str, persona_id: str, query: str, limit: int = 10
    ) -> List[MemoryFact]:
        """Search for facts in memory."""
        try:
            return self._get_store().search_facts(user_id, persona_id, query, limit)
        except Exception as e:
            logger.error(f"Error searching facts: {e}")
            return []
    
    def store_web_content(
        self,
        user_id: str,
        persona_id: str,
        content: str,
        source_url: str,
        source_title: str = "",
        source_description: str = "",
        source_domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
        except Exception as e:
            logger.error(f"Error storing web content: {e}")
            return 0
    
    def get_web_content_by_url(
        self, user_id: str, persona_id: str, url: str
    ) -> Optional[Dict[str, Any]]:
        """Get web content by URL if it exists."""
        try:
            return self._get_store().get_web_content_by_url(user_id, persona_id, url)
        except Exception as e:
            logger.error(f"Error getting web content: {e}")
            return None
