"""RAG project configuration."""

from app.core.config import settings as global_settings


class RAGConfig:
    """RAG-specific configuration derived from global settings."""

    # MongoDB
    mongodb_uri = global_settings.mongodb_uri
    mongodb_database = global_settings.mongodb_database
    mongodb_collection_documents = "documents"
    mongodb_collection_chunks = "chunks"
    mongodb_vector_index = "vector_index"
    mongodb_text_index = "text_index"

    # LLM
    llm_provider = global_settings.llm_provider
    llm_model = global_settings.llm_model
    llm_base_url = global_settings.llm_base_url
    llm_api_key = global_settings.llm_api_key

    # Embeddings
    embedding_provider = global_settings.embedding_provider
    embedding_model = global_settings.embedding_model
    embedding_base_url = global_settings.embedding_base_url
    embedding_api_key = global_settings.embedding_api_key
    embedding_dimension = global_settings.embedding_dimension

    # Search
    default_match_count = 10
    max_match_count = 50
    default_text_weight = 0.3

    # Advanced RAG Strategies
    use_contextual_embeddings = global_settings.use_contextual_embeddings
    use_agentic_rag = global_settings.use_agentic_rag
    use_reranking = global_settings.use_reranking
    use_knowledge_graph = global_settings.use_knowledge_graph

    # Entity extraction
    enable_entity_extraction = global_settings.enable_entity_extraction
    entity_extractor_type = global_settings.entity_extractor_type
    entity_llm_threshold = global_settings.entity_llm_threshold
    ner_model = global_settings.ner_model

    # Neo4j (for graph operations)
    neo4j_uri = global_settings.neo4j_uri
    neo4j_username = global_settings.neo4j_user
    neo4j_password = global_settings.neo4j_password
    neo4j_database = global_settings.neo4j_database


config = RAGConfig()
