"""OpenWebUI Topics models - re-exports from schemas.

Import specific items directly from this module or from capabilities.processing.schemas.
"""

from capabilities.processing.schemas import (
    TopicClassificationRequest,
    TopicClassificationResponse,
)

__all__ = ["TopicClassificationRequest", "TopicClassificationResponse"]
