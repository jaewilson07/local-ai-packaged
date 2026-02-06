"""Graphiti RAG project configuration."""

from app.core.config import settings as global_settings


class GraphitiRAGConfig:
    """Graphiti RAG-specific configuration derived from global settings."""

    # Neo4j / Graphiti
    neo4j_uri = global_settings.neo4j_uri
    neo4j_user = global_settings.neo4j_user
    neo4j_password = global_settings.neo4j_password
    neo4j_database = global_settings.neo4j_database

    # Feature flags
    use_graphiti = global_settings.use_graphiti
    use_knowledge_graph = global_settings.use_knowledge_graph

    # LLM for Graphiti entity extraction (uses same as main LLM)
    llm_provider = global_settings.llm_provider
    llm_model = global_settings.llm_model
    llm_base_url = global_settings.llm_base_url
    llm_api_key = global_settings.llm_api_key


config = GraphitiRAGConfig()
