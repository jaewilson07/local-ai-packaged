"""MongoDB store for memory management (messages, facts, web content)."""

import logging
from typing import Any

from app.capabilities.retrieval.mongo_rag.memory_models import MemoryFact, MemoryMessage, WebContent
from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from shared.stores.base import BaseMongoStore

logger = logging.getLogger(__name__)


class MongoMemoryStore(BaseMongoStore):
    """MongoDB store for managing memory (messages, facts, web content)."""

    def __init__(self, db: Database):
        """
        Initialize memory store.

        Args:
            db: MongoDB database instance
        """
        super().__init__(db)
        self.messages_collection: Collection = db["memory_messages"]
        self.facts_collection: Collection = db["memory_facts"]
        self.web_content_collection: Collection = db["memory_web_content"]

        # Create indexes on initialization
        self._create_indexes()

    @property
    def collection(self) -> Collection:
        """Primary collection is messages."""
        return self.messages_collection

    def _create_indexes(self):
        """Create indexes for efficient queries."""
        # Messages indexes
        self._create_index_safe(
            self.messages_collection,
            [("user_id", ASCENDING), ("persona_id", ASCENDING), ("created_at", DESCENDING)],
        )

        # Facts indexes
        self._create_index_safe(
            self.facts_collection, [("user_id", ASCENDING), ("persona_id", ASCENDING)]
        )
        # Text index for fact search
        self._create_text_index_safe(self.facts_collection, "fact")

        # Web content indexes
        self._create_index_safe(
            self.web_content_collection,
            [("user_id", ASCENDING), ("persona_id", ASCENDING), ("source_url", ASCENDING)],
        )

    def add_message(self, message: MemoryMessage) -> None:
        """Add a message to memory."""
        try:
            self.messages_collection.insert_one(message.dict())
        except Exception as e:
            self._handle_operation_error("adding message", e)

    def get_recent_messages(
        self, user_id: str, persona_id: str | None = None, limit: int = 10
    ) -> list[MemoryMessage]:
        """Get recent messages for a user/persona."""
        try:
            query: dict[str, Any] = {"user_id": user_id}
            if persona_id:
                query["persona_id"] = persona_id

            cursor = (
                self.messages_collection.find(query).sort("created_at", DESCENDING).limit(limit)
            )
            return [MemoryMessage(**doc) for doc in cursor]
        except Exception as e:
            self._handle_operation_error("getting recent messages", e)
            return []

    def add_fact(self, fact: MemoryFact) -> None:
        """Add a fact to memory."""
        try:
            # Check if fact already exists
            existing = self.facts_collection.find_one(
                {"user_id": fact.user_id, "persona_id": fact.persona_id, "fact": fact.fact}
            )

            if not existing:
                self.facts_collection.insert_one(fact.dict())
        except Exception as e:
            self._handle_operation_error("adding fact", e)

    def search_facts(
        self,
        user_id: str,
        persona_id: str | None = None,
        query: str | None = None,
        limit: int = 10,
    ) -> list[MemoryFact]:
        """Search facts by text query."""
        try:
            search_query: dict[str, Any] = {"user_id": user_id}
            if persona_id:
                search_query["persona_id"] = persona_id
            if query:
                search_query["$text"] = {"$search": query}

            cursor = self.facts_collection.find(search_query).limit(limit)
            return [MemoryFact(**doc) for doc in cursor]
        except Exception as e:
            self._handle_operation_error("searching facts", e)
            return []

    def add_web_content(self, content: WebContent) -> None:
        """Add web content to memory."""
        try:
            # Check if content already exists for this URL
            existing = self.web_content_collection.find_one(
                {
                    "user_id": content.user_id,
                    "persona_id": content.persona_id,
                    "source_url": content.source_url,
                }
            )

            if not existing:
                self.web_content_collection.insert_one(content.dict())
        except Exception as e:
            self._handle_operation_error("adding web content", e)

    def get_web_content(
        self,
        user_id: str,
        persona_id: str | None = None,
        source_url: str | None = None,
        limit: int = 10,
    ) -> list[WebContent]:
        """Get web content for a user/persona."""
        try:
            query: dict[str, Any] = {"user_id": user_id}
            if persona_id:
                query["persona_id"] = persona_id
            if source_url:
                query["source_url"] = source_url

            cursor = self.web_content_collection.find(query).limit(limit)
            return [WebContent(**doc) for doc in cursor]
        except Exception as e:
            self._handle_operation_error("getting web content", e)
            return []
