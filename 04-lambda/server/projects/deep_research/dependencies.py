"""Dependencies for Deep Research Agent."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging
import httpx
from crawl4ai import AsyncWebCrawler, BrowserConfig
from docling.document_converter import DocumentConverter
from server.projects.shared.dependencies import BaseDependencies, MongoDBMixin, OpenAIClientMixin
from server.projects.deep_research.config import config
from server.projects.graphiti_rag.dependencies import GraphitiRAGDeps as GraphitiDeps
from server.projects.graphiti_rag.config import config as graphiti_config
from server.config import settings as global_settings

logger = logging.getLogger(__name__)


@dataclass
class DeepResearchDeps(BaseDependencies, MongoDBMixin, OpenAIClientMixin):
    """Dependencies injected into the deep research agent context."""

    # Core dependencies
    http_client: Optional[httpx.AsyncClient] = None
    crawler: Optional[AsyncWebCrawler] = None
    document_converter: Optional[DocumentConverter] = None
    settings: Optional[Any] = None
    
    # Graphiti dependencies (optional)
    graphiti_deps: Optional[GraphitiDeps] = None

    # Session context
    session_id: Optional[str] = None

    @classmethod
    def from_settings(
        cls,
        http_client: Optional[httpx.AsyncClient] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> "DeepResearchDeps":
        """
        Create dependencies from application settings.
        
        Args:
            http_client: Optional httpx client (will create if not provided)
            session_id: Optional session ID for tracking
            **kwargs: Additional overrides
            
        Returns:
            DeepResearchDeps instance (not yet initialized)
        """
        if http_client is None:
            http_client = httpx.AsyncClient(timeout=30.0)
        
        return cls(
            http_client=http_client,
            session_id=session_id,
            settings=config,
            **kwargs
        )

    async def initialize(self) -> None:
        """
        Initialize external connections.
        
        Raises:
            Exception: If initialization fails
        """
        if not self.settings:
            self.settings = config
            logger.info("settings_loaded", extra={"searxng_url": config.searxng_url})

        # Initialize MongoDB
        if not self.mongo_client:
            await self.initialize_mongodb()

        # Initialize OpenAI clients (for embeddings)
        if not self.embedding_client:
            await self.initialize_openai_client()

        # Initialize Crawl4AI crawler
        if not self.crawler:
            try:
                browser_config = BrowserConfig(
                    headless=config.browser_headless,
                    verbose=False,
                    text_mode=True  # Disable images for faster crawling
                )
                self.crawler = AsyncWebCrawler(config=browser_config)
                await self.crawler.__aenter__()
                logger.info("crawl4ai_crawler_initialized")
            except Exception as e:
                logger.exception("crawl4ai_initialization_failed", extra={"error": str(e)})
                raise

        # Initialize Docling document converter
        if not self.document_converter:
            try:
                self.document_converter = DocumentConverter()
                logger.info("docling_converter_initialized")
            except Exception as e:
                logger.exception("docling_initialization_failed", extra={"error": str(e)})
                raise

        # Initialize Graphiti if enabled
        if graphiti_config.use_graphiti and not self.graphiti_deps:
            try:
                self.graphiti_deps = GraphitiDeps()
                await self.graphiti_deps.initialize()
                if self.graphiti_deps.graphiti:
                    logger.info("graphiti_initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Graphiti: {e}")
                self.graphiti_deps = None

    async def cleanup(self) -> None:
        """Clean up external connections."""
        # Cleanup MongoDB
        await self.cleanup_mongodb()

        # Cleanup OpenAI clients
        await self.cleanup_openai_clients()

        # Cleanup crawler
        if self.crawler:
            try:
                await self.crawler.__aexit__(None, None, None)
                self.crawler = None
                logger.info("crawl4ai_crawler_closed")
            except Exception as e:
                logger.warning(f"Error closing crawler: {e}")

        # Cleanup HTTP client
        if self.http_client:
            try:
                await self.http_client.aclose()
                self.http_client = None
                logger.info("http_client_closed")
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")

        # Cleanup Graphiti
        if self.graphiti_deps:
            await self.graphiti_deps.cleanup()
            self.graphiti_deps = None

        # Document converter doesn't need explicit cleanup
        self.document_converter = None

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            Exception: If embedding generation fails
        """
        if not self.embedding_client:
            await self.initialize()

        response = await self.embedding_client.embeddings.create(
            model=global_settings.embedding_model, input=text
        )
        # Return as list of floats - MongoDB stores as native array
        return response.data[0].embedding
