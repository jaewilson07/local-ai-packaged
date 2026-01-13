"""Open WebUI export project configuration."""

from server.config import settings as global_settings


class OpenWebUIExportConfig:
    """Open WebUI export-specific configuration."""

    # Open WebUI API
    openwebui_api_url: str = "http://open-webui:8080"
    openwebui_api_key: str | None = None

    # MongoDB (reuse RAG config)
    mongodb_uri = global_settings.mongodb_uri
    mongodb_database = global_settings.mongodb_database
    mongodb_collection_documents = "documents"
    mongodb_collection_chunks = "chunks"

    # Embeddings (reuse RAG config)
    embedding_provider = global_settings.embedding_provider
    embedding_model = global_settings.embedding_model
    embedding_base_url = global_settings.embedding_base_url
    embedding_api_key = global_settings.embedding_api_key
    embedding_dimension = global_settings.embedding_dimension

    # Ingestion settings
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Export settings
    auto_export_enabled: bool = True
    export_interval_seconds: int = 300  # 5 minutes


config = OpenWebUIExportConfig()
