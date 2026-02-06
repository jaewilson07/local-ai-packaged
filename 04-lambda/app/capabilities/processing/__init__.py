"""Processing capability - Content classification and structuring."""

from .ai import (
    ProcessingDeps,
    ProcessingState,
    classify_conversation_topics,
    topic_classification_agent,
)
from .processing_workflow import classify_topics_workflow
from .router import get_processing_deps, router
from .schemas import TopicClassificationRequest, TopicClassificationResponse

__all__ = [
    # Router
    "router",
    "get_processing_deps",
    # Workflow
    "classify_topics_workflow",
    # AI
    "ProcessingDeps",
    "ProcessingState",
    "topic_classification_agent",
    "classify_conversation_topics",
    # Schemas
    "TopicClassificationRequest",
    "TopicClassificationResponse",
]
