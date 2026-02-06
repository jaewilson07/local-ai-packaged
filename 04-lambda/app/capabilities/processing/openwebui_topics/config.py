"""OpenWebUI Topics project configuration."""

from app.core.config import settings as global_settings


class OpenWebUITopicsConfig:
    """OpenWebUI Topics-specific configuration derived from global settings."""

    # MongoDB
    mongodb_uri = global_settings.mongodb_uri
    mongodb_database = global_settings.mongodb_database

    # LLM settings
    llm_model = global_settings.llm_model
    llm_base_url = global_settings.llm_base_url
    llm_api_key = global_settings.llm_api_key

    # Topic settings
    max_topics = 5


config = OpenWebUITopicsConfig()

__all__ = ["OpenWebUITopicsConfig", "config"]
