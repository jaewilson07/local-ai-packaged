"""Calendar project configuration."""

from server.config import settings as global_settings


class CalendarConfig:
    """Calendar-specific configuration derived from global settings."""
    
    # Google Calendar OAuth2
    google_calendar_credentials: str | None = global_settings.google_calendar_credentials
    google_calendar_token: str | None = global_settings.google_calendar_token
    google_calendar_credentials_path: str | None = global_settings.google_calendar_credentials_path
    google_calendar_token_path: str | None = global_settings.google_calendar_token_path
    google_calendar_id: str = global_settings.google_calendar_id
    
    # MongoDB for sync state
    mongodb_uri = global_settings.mongodb_uri
    mongodb_database = global_settings.mongodb_database
    mongodb_collection_sync_state = "calendar_sync_state"
    
    # LLM (for agent)
    llm_provider = global_settings.llm_provider
    llm_model = global_settings.llm_model
    llm_base_url = global_settings.llm_base_url
    llm_api_key = global_settings.llm_api_key


config = CalendarConfig()
