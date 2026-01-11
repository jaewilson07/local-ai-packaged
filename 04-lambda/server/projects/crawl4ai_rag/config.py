"""Crawl4AI RAG project configuration."""

from server.config import settings as global_settings


class Crawl4AIConfig:
    """Crawl4AI-specific configuration derived from global settings."""

    # MongoDB (reuse from global)
    mongodb_uri = global_settings.mongodb_uri
    mongodb_database = global_settings.mongodb_database
    mongodb_collection_documents = "documents"
    mongodb_collection_chunks = "chunks"

    # Embeddings (reuse from global)
    embedding_provider = global_settings.embedding_provider
    embedding_model = global_settings.embedding_model
    embedding_base_url = global_settings.embedding_base_url
    embedding_api_key = global_settings.embedding_api_key
    embedding_dimension = global_settings.embedding_dimension

    # Crawl4AI-specific settings
    max_concurrent_sessions: int = 10
    default_chunk_size: int = 1000
    default_chunk_overlap: int = 200
    browser_headless: bool = True


config = Crawl4AIConfig()
