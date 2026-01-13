"""Configuration for Knowledge Base project."""

import os
from dataclasses import dataclass


@dataclass
class KnowledgeBaseConfig:
    """Configuration for Knowledge Base project."""

    # MongoDB settings
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "knowledge_base")
    articles_collection: str = os.getenv("KB_ARTICLES_COLLECTION", "articles")
    proposals_collection: str = os.getenv("KB_PROPOSALS_COLLECTION", "proposals")

    # Embedding settings (same as mongo_rag)
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    embedding_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")

    # LLM settings for chat
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_api_key: str = os.getenv("OPENAI_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

    # SearXNG for web search
    searxng_url: str = os.getenv("SEARXNG_URL", "http://searxng:8080")

    # Crawl4AI for URL fetching
    crawl4ai_url: str = os.getenv("CRAWL4AI_URL", "http://crawl4ai:8000")


config = KnowledgeBaseConfig()
