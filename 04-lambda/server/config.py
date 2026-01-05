"""Global server configuration."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal, Optional


class Settings(BaseSettings):
    """Server configuration from environment variables."""
    
    # Server
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    
    # MongoDB (Docker internal)
    mongodb_uri: str
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
    use_graphiti: bool = Field(False, env="USE_GRAPHITI")
    
    # Advanced RAG Strategies
    use_contextual_embeddings: bool = Field(False, env="USE_CONTEXTUAL_EMBEDDINGS")
    use_agentic_rag: bool = Field(False, env="USE_AGENTIC_RAG")
    use_reranking: bool = Field(False, env="USE_RERANKING")
    use_knowledge_graph: bool = Field(False, env="USE_KNOWLEDGE_GRAPH")
    
    # N8n Workflow Management
    n8n_api_url: str = Field("http://n8n:5678/api/v1", env="N8N_API_URL")
    n8n_api_key: Optional[str] = Field(None, env="N8N_API_KEY")
    
    # SearXNG Web Search
    searxng_url: str = Field("http://searxng:8080", env="SEARXNG_URL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

