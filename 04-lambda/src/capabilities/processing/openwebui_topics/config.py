"""Open WebUI topic classification configuration."""

from server.config import settings as global_settings


class TopicClassificationConfig:
    """Topic classification configuration."""

    # LLM for topic classification
    llm_provider = global_settings.llm_provider
    llm_model = global_settings.llm_model
    llm_base_url = global_settings.llm_base_url
    llm_api_key = global_settings.llm_api_key

    # Classification settings
    max_topics: int = 5
    min_topic_confidence: float = 0.7


config = TopicClassificationConfig()
