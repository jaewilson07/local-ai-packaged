"""Persona project configuration."""

from server.config import settings as global_settings


class PersonaConfig:
    """Persona-specific configuration derived from global settings."""
    
    # MongoDB for persona storage
    mongodb_uri = global_settings.mongodb_uri
    mongodb_database = global_settings.mongodb_database
    mongodb_collection_profiles = "persona_profiles"
    mongodb_collection_state = "persona_state"
    mongodb_collection_interactions = "persona_interactions"
    
    # LLM (for agent and mood/relationship analysis)
    llm_provider = global_settings.llm_provider
    llm_model = global_settings.llm_model
    llm_base_url = global_settings.llm_base_url
    llm_api_key = global_settings.llm_api_key


config = PersonaConfig()
