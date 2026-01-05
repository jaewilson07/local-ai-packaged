"""RAG project configuration."""

from server.config import settings as global_settings


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
    
    # Advanced RAG Strategies
    use_contextual_embeddings = global_settings.use_contextual_embeddings
    use_agentic_rag = global_settings.use_agentic_rag
    use_reranking = global_settings.use_reranking
    use_knowledge_graph = global_settings.use_knowledge_graph


config = RAGConfig()

