"""Configuration for Discord characters project."""

import os

from server.config import settings as global_settings


class DiscordCharactersConfig:
    """Configuration for Discord characters derived from global settings."""

    # MongoDB configuration - use global settings for consistency
    MONGODB_URI: str = global_settings.mongodb_uri
    MONGODB_DB_NAME: str = global_settings.mongodb_database

    # Service URLs (internal)
    PERSONA_SERVICE_URL: str = os.getenv("PERSONA_SERVICE_URL", "http://localhost:8000")
    CONVERSATION_SERVICE_URL: str = os.getenv("CONVERSATION_SERVICE_URL", "http://localhost:8000")

    # Engagement settings
    ENGAGEMENT_PROBABILITY: float = float(os.getenv("ENGAGEMENT_PROBABILITY", "0.15"))
    MAX_CHARACTERS_PER_CHANNEL: int = int(os.getenv("MAX_CHARACTERS_PER_CHANNEL", "5"))
    CONTEXT_MESSAGE_LIMIT: int = int(os.getenv("CONTEXT_MESSAGE_LIMIT", "20"))

    # LLM settings
    OLLAMA_BASE_URL: str | None = os.getenv("OLLAMA_BASE_URL")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    USE_OLLAMA: bool = os.getenv("USE_OLLAMA", "true").lower() == "true"


config = DiscordCharactersConfig()
