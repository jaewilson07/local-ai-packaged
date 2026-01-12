"""Configuration for Knowledge project."""

import os
from dataclasses import dataclass


@dataclass
class KnowledgeConfig:
    """Configuration for Knowledge project."""

    # LLM configuration (optional, for LLM-based extraction)
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    use_llm_by_default: bool = False

    def __post_init__(self):
        """Load configuration from environment variables."""
        self.llm_api_key = os.getenv("LLM_API_KEY")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")
        self.use_llm_by_default = os.getenv("USE_LLM_FOR_EXTRACTION", "false").lower() == "true"


config = KnowledgeConfig()
