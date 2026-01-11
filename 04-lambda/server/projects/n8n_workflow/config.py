"""Configuration for N8n Workflow project."""

from server.config import settings as global_settings


class N8nWorkflowConfig:
    """Project-specific configuration for N8n workflow management."""

    # N8n API connection
    n8n_api_url: str = getattr(global_settings, "n8n_api_url", "http://n8n:5678/api/v1")
    n8n_api_key: str | None = getattr(global_settings, "n8n_api_key", None)

    # LLM configuration (reuse global)
    llm_model: str = global_settings.llm_model
    llm_base_url: str = global_settings.llm_base_url
    llm_api_key: str = global_settings.llm_api_key


config = N8nWorkflowConfig()
