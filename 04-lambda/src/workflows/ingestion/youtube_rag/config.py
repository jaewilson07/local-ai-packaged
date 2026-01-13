"""Configuration for YouTube RAG project."""

import os
from dataclasses import dataclass


@dataclass
class YouTubeRAGConfig:
    """Configuration settings for YouTube RAG."""

    # MongoDB settings
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "rag")
    mongodb_collection_documents: str = os.getenv("MONGODB_COLLECTION_DOCUMENTS", "documents")
    mongodb_collection_chunks: str = os.getenv("MONGODB_COLLECTION_CHUNKS", "chunks")

    # Chunking defaults
    default_chunk_size: int = int(os.getenv("YOUTUBE_CHUNK_SIZE", "1000"))
    default_chunk_overlap: int = int(os.getenv("YOUTUBE_CHUNK_OVERLAP", "200"))

    # Transcript settings
    default_transcript_language: str = os.getenv("YOUTUBE_TRANSCRIPT_LANGUAGE", "en")
    fallback_languages: list[str] | None = None

    # LLM settings for extractors
    llm_model: str = os.getenv("YOUTUBE_LLM_MODEL", "gpt-4o-mini")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # Graphiti integration
    use_graphiti: bool = os.getenv("USE_GRAPHITI", "true").lower() == "true"

    def __post_init__(self) -> None:
        """Initialize fallback languages if not set."""
        if self.fallback_languages is None:
            fallback_env = os.getenv("YOUTUBE_FALLBACK_LANGUAGES", "en,en-US,en-GB")
            self.fallback_languages = [lang.strip() for lang in fallback_env.split(",")]


config = YouTubeRAGConfig()
