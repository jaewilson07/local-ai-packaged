"""LLM model factory and utilities.

Centralized LLM model creation for consistent configuration across capabilities.
"""

import logging
import os
from typing import Any

from pydantic_ai.models.openai import OpenAIModel

logger = logging.getLogger(__name__)


def get_llm_model(
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> OpenAIModel:
    """
    Get LLM model instance with standard configuration.
    
    Args:
        provider: LLM provider (ollama, openai, anthropic). Defaults to env LLM_PROVIDER.
        model: Model name. Defaults to env LLM_MODEL.
        base_url: API base URL. Defaults to env LLM_BASE_URL.
        api_key: API key. Defaults to env LLM_API_KEY.
        **kwargs: Additional model parameters
        
    Returns:
        Configured OpenAI model instance
        
    Examples:
        >>> # Use defaults from environment
        >>> model = get_llm_model()
        
        >>> # Override specific settings
        >>> model = get_llm_model(model="gpt-4", temperature=0.7)
        
        >>> # Use for specific capability
        >>> model = get_llm_model(provider="ollama", model="llama3.2")
    """
    # Get configuration from environment or parameters
    provider = provider or os.getenv("LLM_PROVIDER", "ollama")
    model = model or os.getenv("LLM_MODEL", "llama3.2")
    base_url = base_url or os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")
    api_key = api_key or os.getenv("LLM_API_KEY", "not-needed")
    
    logger.debug(
        f"Creating LLM model: provider={provider}, model={model}, base_url={base_url}"
    )
    
    # Create OpenAI-compatible model
    # Note: This works with Ollama, vLLM, and other OpenAI-compatible endpoints
    return OpenAIModel(
        model,
        base_url=base_url,
        api_key=api_key,
        **kwargs,
    )


def get_agent_model(capability_name: str, **kwargs: Any) -> OpenAIModel:
    """
    Get LLM model for a specific capability with optional overrides.
    
    This is a convenience wrapper that:
    1. Checks for capability-specific env vars (e.g., RAG_MODEL)
    2. Falls back to global LLM settings
    3. Applies any additional kwargs
    
    Args:
        capability_name: Capability name (e.g., "RAG", "N8N_WORKFLOW")
        **kwargs: Additional model parameters to override
        
    Returns:
        Configured model instance
        
    Examples:
        >>> # Get model for RAG capability
        >>> model = get_agent_model("RAG")
        
        >>> # Override temperature for specific use
        >>> model = get_agent_model("N8N_WORKFLOW", temperature=0.9)
    """
    capability_name = capability_name.upper().replace("-", "_")
    
    # Check for capability-specific overrides
    model = os.getenv(f"{capability_name}_MODEL") or os.getenv("LLM_MODEL", "llama3.2")
    provider = os.getenv(f"{capability_name}_PROVIDER") or os.getenv("LLM_PROVIDER", "ollama")
    base_url = os.getenv(f"{capability_name}_BASE_URL") or os.getenv(
        "LLM_BASE_URL", "http://ollama:11434/v1"
    )
    
    return get_llm_model(provider=provider, model=model, base_url=base_url, **kwargs)
