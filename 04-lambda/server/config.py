"""Global server configuration."""

from typing import Literal

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Server configuration from environment variables."""

    model_config = ConfigDict(
        extra="ignore",  # Ignore extra env vars for sample scripts
        env_file=".env",
        case_sensitive=False,
    )

    # Server
    log_level: Literal["debug", "info", "warning", "error"] = "info"

    # MongoDB (Docker internal)
    # Note: Replica set (rs0) is required for Atlas Search
    # For host connections, use directConnection=true to bypass replica set requirement
    # For container connections, use mongodb://mongodb:27017/?replicaSet=rs0
    # Default credentials: admin/admin123 (can be overridden via env vars)
    mongodb_uri: str = Field(
        default="mongodb://admin:admin123@localhost:27017/?directConnection=true&authSource=admin",
        env="MONGODB_URI",
    )
    mongodb_database: str = "rag_db"

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2"
    llm_base_url: str = "http://ollama:11434/v1"
    llm_api_key: str = "not-needed"

    # Embeddings
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_base_url: str = "http://ollama:11434/v1"
    embedding_api_key: str = "not-needed"
    embedding_dimension: int = 768

    # Neo4j / Graphiti
    neo4j_uri: str = Field("bolt://neo4j:7687", env="NEO4J_URI")
    neo4j_user: str = Field("neo4j", env="NEO4J_USER")
    neo4j_password: str = Field("password", env="NEO4J_PASSWORD")
    neo4j_database: str = Field("neo4j", env="NEO4J_DATABASE")

    # Graphiti-specific
    # Enabled by default for crawl4ai RAG flow and other RAG operations
    # Set USE_GRAPHITI=false to disable
    use_graphiti: bool = Field(True, env="USE_GRAPHITI")

    # Advanced RAG Strategies
    use_contextual_embeddings: bool = Field(False, env="USE_CONTEXTUAL_EMBEDDINGS")
    use_agentic_rag: bool = Field(False, env="USE_AGENTIC_RAG")
    use_reranking: bool = Field(False, env="USE_RERANKING")
    use_knowledge_graph: bool = Field(False, env="USE_KNOWLEDGE_GRAPH")

    # Entity extraction configuration
    enable_entity_extraction: bool = Field(False, env="ENABLE_ENTITY_EXTRACTION")
    entity_extractor_type: str = Field("hybrid", env="ENTITY_EXTRACTOR_TYPE")
    entity_llm_threshold: float = Field(0.7, env="ENTITY_LLM_THRESHOLD")
    ner_model: str = Field("Jean-Baptiste/roberta-large-ner-english", env="NER_MODEL")

    # Jira configuration
    jira_server: str | None = Field(None, env="JIRA_SERVER")
    jira_email: str | None = Field(None, env="JIRA_EMAIL")
    jira_api_token: str | None = Field(None, env="JIRA_API_TOKEN")

    # Confluence configuration
    confluence_url: str | None = Field(None, env="CONFLUENCE_URL")
    confluence_email: str | None = Field(None, env="CONFLUENCE_EMAIL")
    confluence_api_token: str | None = Field(None, env="CONFLUENCE_API_TOKEN")

    # Google Drive configuration
    google_drive_credentials_path: str | None = Field(None, env="GOOGLE_DRIVE_CREDENTIALS_PATH")
    google_drive_token_path: str | None = Field(None, env="GOOGLE_DRIVE_TOKEN_PATH")

    # Google Calendar configuration
    google_calendar_credentials: str | None = Field(None, env="GOOGLE_CALENDAR_CREDENTIALS")
    google_calendar_token: str | None = Field(None, env="GOOGLE_CALENDAR_TOKEN")
    google_calendar_credentials_path: str | None = Field(
        None, env="GOOGLE_CALENDAR_CREDENTIALS_PATH"
    )
    google_calendar_token_path: str | None = Field(None, env="GOOGLE_CALENDAR_TOKEN_PATH")
    google_calendar_id: str = Field("primary", env="GOOGLE_CALENDAR_ID")

    # N8n Workflow Management
    n8n_api_url: str = Field("http://n8n:5678/api/v1", env="N8N_API_URL")
    n8n_api_key: str | None = Field(None, env="N8N_API_KEY")

    # SearXNG Web Search
    searxng_url: str = Field("http://searxng:8080", env="SEARXNG_URL")

    # Cloudflare Access Authentication
    cloudflare_auth_domain: str = Field("", env="CLOUDFLARE_AUTH_DOMAIN")
    cloudflare_aud_tag: str = Field("", env="CLOUDFLARE_AUD_TAG")

    # Supabase (for auth and data)
    supabase_db_url: str = Field("", env="SUPABASE_DB_URL")
    supabase_service_key: str | None = Field(None, env="SUPABASE_SERVICE_KEY")

    # MinIO (Supabase Storage)
    minio_endpoint: str = Field("http://supabase-minio:9020", env="MINIO_ENDPOINT")
    minio_access_key: str = Field("supa-storage", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field("secret1234", env="MINIO_SECRET_KEY")


settings = Settings()
