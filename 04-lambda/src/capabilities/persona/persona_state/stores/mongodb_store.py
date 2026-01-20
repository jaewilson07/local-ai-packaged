"""MongoDB implementation of PersonaStore protocol."""

import logging
from datetime import datetime
from typing import Any

# Import directly from submodules to avoid circular imports
from capabilities.persona.persona_state.config import config
from capabilities.persona.persona_state.models import (
    ActivePersona,
    ConversationContext,
    MoodState,
    Personality,
    RelationshipState,
)
from pymongo import ASCENDING
from pymongo.database import Database

from shared.stores.base import BaseMongoStore

logger = logging.getLogger(__name__)


class MongoPersonaStore(BaseMongoStore):
    """MongoDB implementation of persona store."""

    def __init__(self, db: Database):
        """
        Initialize MongoDB persona store.

        Args:
            db: MongoDB database instance
        """
        super().__init__(db)
        self.profiles_collection = db[config.mongodb_collection_profiles]
        self.state_collection = db[config.mongodb_collection_state]
        self.interactions_collection = db[config.mongodb_collection_interactions]

        # Create indexes
        self._create_indexes()

    def _create_indexes(self):
        """Create indexes for efficient queries."""
        # Profiles indexes
        self._create_index_safe(self.profiles_collection, [("id", ASCENDING)], unique=True)

        # State indexes
        self._create_index_safe(
            self.state_collection, [("user_id", ASCENDING), ("persona_id", ASCENDING)], unique=True
        )

        # Interactions indexes
        self._create_index_safe(
            self.interactions_collection,
            [("user_id", ASCENDING), ("persona_id", ASCENDING), ("timestamp", ASCENDING)],
        )

    def get_personality(self, persona_id: str) -> Personality | None:
        """Load personality by ID."""
        try:
            doc = self.profiles_collection.find_one({"id": persona_id})
            if doc:
                # Remove _id for Pydantic
                doc.pop("_id", None)
                return Personality(**doc)
            return None
        except Exception:
            logger.exception("Error getting personality")
            return None

    def list_personalities(self) -> list[str]:
        """List available personality IDs."""
        try:
            cursor = self.profiles_collection.find({}, {"id": 1})
            return [doc["id"] for doc in cursor]
        except Exception:
            logger.exception("Error listing personalities")
            return []

    def get_active_persona(self, interface: str = "cli") -> ActivePersona | None:
        """Get active persona for interface."""
        # For now, return default
        # Can be enhanced to store active personas per interface
        return ActivePersona()

    def set_active_persona(self, persona_id: str, interface: str = "cli") -> bool:
        """Set active persona for interface."""
        # For now, just return success
        # Can be enhanced to store active personas
        return True

    def get_mood(self, user_id: str, persona_id: str) -> MoodState | None:
        """Get current mood state."""
        try:
            doc = self.state_collection.find_one({"user_id": user_id, "persona_id": persona_id})
            if doc and "current_mood" in doc:
                mood_data = doc["current_mood"]
                if isinstance(mood_data.get("timestamp"), str):
                    mood_data["timestamp"] = datetime.fromisoformat(mood_data["timestamp"])
                return MoodState(**mood_data)
            return None
        except Exception:
            logger.exception("Error getting mood")
            return None

    def update_mood(self, user_id: str, persona_id: str, mood: MoodState) -> None:
        """Update mood state."""
        try:
            self.state_collection.update_one(
                {"user_id": user_id, "persona_id": persona_id},
                {"$set": {"current_mood": mood.model_dump(), "updated_at": datetime.now()}},
                upsert=True,
            )
        except Exception:
            logger.exception("Error updating mood")
            raise

    def get_relationship(self, user_id: str, persona_id: str) -> RelationshipState | None:
        """Get relationship state with user."""
        try:
            doc = self.state_collection.find_one({"user_id": user_id, "persona_id": persona_id})
            if doc and "relationships" in doc:
                rel_data = doc["relationships"].get(user_id)
                if rel_data:
                    if isinstance(rel_data.get("last_interaction"), str):
                        rel_data["last_interaction"] = datetime.fromisoformat(
                            rel_data["last_interaction"]
                        )
                    return RelationshipState(**rel_data)
            return None
        except Exception:
            logger.exception("Error getting relationship")
            return None

    def update_relationship(
        self, user_id: str, persona_id: str, relationship: RelationshipState
    ) -> None:
        """Update relationship state."""
        try:
            self.state_collection.update_one(
                {"user_id": user_id, "persona_id": persona_id},
                {
                    "$set": {
                        f"relationships.{user_id}": relationship.model_dump(),
                        "updated_at": datetime.now(),
                    }
                },
                upsert=True,
            )
        except Exception:
            logger.exception("Error updating relationship")
            raise

    def get_conversation_context(self, user_id: str, persona_id: str) -> ConversationContext | None:
        """Get current conversation context."""
        try:
            doc = self.state_collection.find_one({"user_id": user_id, "persona_id": persona_id})
            if doc and "current_context" in doc:
                return ConversationContext(**doc["current_context"])
            return None
        except Exception:
            logger.exception("Error getting conversation context")
            return None

    def update_conversation_context(
        self, user_id: str, persona_id: str, context: ConversationContext
    ) -> None:
        """Update conversation context."""
        try:
            self.state_collection.update_one(
                {"user_id": user_id, "persona_id": persona_id},
                {"$set": {"current_context": context.model_dump(), "updated_at": datetime.now()}},
                upsert=True,
            )
        except Exception:
            logger.exception("Error updating conversation context")
            raise

    def get_persona_state(self, user_id: str, persona_id: str) -> dict[str, Any] | None:
        """Get complete persona state."""
        try:
            doc = self.state_collection.find_one({"user_id": user_id, "persona_id": persona_id})
            if doc:
                doc.pop("_id", None)
                return doc
            return None
        except Exception:
            logger.exception("Error getting persona state")
            return None
