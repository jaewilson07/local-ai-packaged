"""AI components for Crawl4AI RAG workflow.

IMPORTANT: To avoid circular imports, import directly from submodules:
    from workflows.ingestion.crawl4ai_rag.ai.dependencies import Crawl4AIDependencies
    from workflows.ingestion.crawl4ai_rag.ai.agent import crawl4ai_agent, Crawl4AIState
"""

# Only export safe items that don't cause circular imports
from workflows.ingestion.crawl4ai_rag.ai.dependencies import (
    Crawl4AIDependencies,
    create_browser_config_with_profile,
    get_profile_path,
)

__all__ = [
    "Crawl4AIDependencies",
    "create_browser_config_with_profile",
    "get_profile_path",
]
