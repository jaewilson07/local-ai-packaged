"""Configuration for Discord characters project."""

import os
from typing import Optional


class DiscordCharactersConfig:
    """Configuration for Discord characters."""
    
    # MongoDB configuration
    MONGODB_URL: str = os.getenv(
        "MONGODB_URL",
        "mongodb://mongodb:27017"
    )
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "localai")
    
    # Service URLs (internal)
    PERSONA_SERVICE_URL: str = os.getenv(
        "PERSONA_SERVICE_URL",
        "http://localhost:8000"
    )
    CONVERSATION_SERVICE_URL: str = os.getenv(
        "CONVERSATION_SERVICE_URL",
        "http://localhost:8000"
    )
    
    # Engagement settings
    ENGAGEMENT_PROBABILITY: float = float(os.getenv("ENGAGEMENT_PROBABILITY", "0.15"))
    MAX_CHARACTERS_PER_CHANNEL: int = int(os.getenv("MAX_CHARACTERS_PER_CHANNEL", "5"))
    CONTEXT_MESSAGE_LIMIT: int = int(os.getenv("CONTEXT_MESSAGE_LIMIT", "20"))
    
    # LLM settings
    OLLAMA_BASE_URL: Optional[str] = os.getenv("OLLAMA_BASE_URL")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    USE_OLLAMA: bool = os.getenv("USE_OLLAMA", "true").lower() == "true"


config = DiscordCharactersConfig()
