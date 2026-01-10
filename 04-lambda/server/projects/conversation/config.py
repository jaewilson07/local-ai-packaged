"""Conversation project configuration."""

from server.config import settings as global_settings


class ConversationConfig:
    """Conversation-specific configuration derived from global settings."""
    
    # LLM
    llm_provider = global_settings.llm_provider
    llm_model = global_settings.llm_model
    llm_base_url = global_settings.llm_base_url
    llm_api_key = global_settings.llm_api_key


config = ConversationConfig()
