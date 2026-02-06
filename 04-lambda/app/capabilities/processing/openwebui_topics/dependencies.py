"""OpenWebUI Topics dependencies.

Re-exports ProcessingDeps as OpenWebUITopicsDeps for backward compatibility.
"""

from app.capabilities.processing.ai.dependencies import ProcessingDeps

# Alias for backward compatibility with existing code
OpenWebUITopicsDeps = ProcessingDeps

__all__ = ["OpenWebUITopicsDeps"]
