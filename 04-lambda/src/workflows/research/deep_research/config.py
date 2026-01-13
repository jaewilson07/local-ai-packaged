"""Deep Research project configuration."""

from server.config import settings as global_settings


class DeepResearchConfig:
    """Deep Research-specific configuration derived from global settings."""

    # SearXNG (reuse from global)
    searxng_url = global_settings.searxng_url

    # Crawl4AI-specific settings
    browser_headless: bool = True
    max_concurrent_sessions: int = 10
    page_timeout: int = 30000  # 30 seconds

    # Docling settings
    default_chunk_size: int = 1000
    default_chunk_overlap: int = 200
    max_tokens: int = 512  # For embedding models

    # Search settings
    default_result_count: int = 5
    max_result_count: int = 20


config = DeepResearchConfig()
