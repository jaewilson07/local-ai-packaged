"""Dependencies for Crawl4AI RAG Agent."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openai
from crawl4ai import AsyncWebCrawler, BrowserConfig
from pymongo import AsyncMongoClient
from workflows.ingestion.crawl4ai_rag.config import config

# Import directly from submodules to avoid circular imports
from shared.constants import CrawlingDefaults
from shared.dependencies import BaseDependencies, MongoDBMixin, OpenAIClientMixin

logger = logging.getLogger(__name__)

# Default profile directory for Crawl4AI
DEFAULT_PROFILE_BASE_DIR = Path.home() / ".crawl4ai" / "profiles"


def get_profile_path(
    profile_name: str,
    base_dir: Path | None = None,
) -> Path | None:
    """
    Check if a browser profile exists and return its path.

    Args:
        profile_name: Name of the profile
        base_dir: Base directory for profiles (default: ~/.crawl4ai/profiles)

    Returns:
        Absolute path to profile directory if it exists, None otherwise
    """
    base_dir = base_dir or DEFAULT_PROFILE_BASE_DIR
    profile_path = base_dir / profile_name

    # Check if profile exists and has the Default directory (Chrome/Chromium structure)
    if profile_path.exists() and (profile_path / "Default").exists():
        abs_path = profile_path.resolve()
        logger.info(f"Found existing profile: {abs_path}")

        # Check for storage_state.json (session data)
        storage_state = abs_path / "storage_state.json"
        if storage_state.exists():
            logger.info(f"Profile has storage_state.json: {storage_state}")
        else:
            logger.warning("Profile missing storage_state.json - session data may not be preserved")

        return abs_path

    logger.info(f"Profile not found: {profile_path}")
    return None


def create_browser_config_with_profile(
    profile_path: Path,
    headless: bool = CrawlingDefaults.HEADLESS,
    verbose: bool = False,
    text_mode: bool = CrawlingDefaults.TEXT_MODE,
) -> BrowserConfig:
    """
    Create a BrowserConfig with an existing browser profile.

    Args:
        profile_path: Path to the browser profile directory
        headless: Whether to run in headless mode (default: True)
        verbose: Whether to enable verbose logging (default: False)
        text_mode: Whether to disable images for faster crawling (default: True)

    Returns:
        BrowserConfig instance configured with the profile
    """
    abs_profile_path = profile_path.resolve()
    storage_state_path = abs_profile_path / "storage_state.json"

    browser_config_kwargs = {
        "headless": headless,
        "verbose": verbose,
        "text_mode": text_mode,
        "use_managed_browser": True,
        "user_data_dir": str(abs_profile_path),
        "browser_type": "chromium",
    }

    # Load storage_state.json if it exists (Playwright session state)
    if storage_state_path.exists():
        logger.info(f"Loading storage_state.json from: {storage_state_path}")
        browser_config_kwargs["storage_state"] = str(storage_state_path)
    else:
        logger.info("No storage_state.json found, using Chrome profile cookies")

    return BrowserConfig(**browser_config_kwargs)


@dataclass
class Crawl4AIDependencies(BaseDependencies, MongoDBMixin, OpenAIClientMixin):
    """Dependencies injected into the crawl4ai agent context."""

    # Core dependencies
    mongo_client: AsyncMongoClient | None = None
    db: Any | None = None
    openai_client: openai.AsyncOpenAI | None = None
    crawler: AsyncWebCrawler | None = None
    settings: Any | None = None

    # Session context
    session_id: str | None = None
    user_preferences: dict[str, Any] = field(default_factory=dict)

    # Browser profile for identity-based crawling
    user_data_dir: str | None = None

    # Optional: skip MongoDB/OpenAI initialization if only using crawler
    skip_mongodb: bool = False
    skip_openai: bool = False

    async def initialize(self) -> None:
        """
        Initialize external connections.

        Raises:
            ConnectionFailure: If MongoDB connection fails
            ServerSelectionTimeoutError: If MongoDB server selection times out
            ValueError: If settings cannot be loaded
        """
        if not self.settings:
            self.settings = config
            logger.info("settings_loaded", extra={"database": config.mongodb_database})

        # Initialize MongoDB using mixin (optional)
        if not self.skip_mongodb:
            try:
                await self.initialize_mongodb(
                    mongodb_uri=config.mongodb_uri, mongodb_database=config.mongodb_database
                )
                logger.info(
                    "mongodb_connected",
                    extra={
                        "database": config.mongodb_database,
                        "collections": {
                            "documents": config.mongodb_collection_documents,
                            "chunks": config.mongodb_collection_chunks,
                        },
                    },
                )
            except Exception as e:
                logger.warning(f"MongoDB initialization skipped or failed: {e}")
        else:
            logger.info("MongoDB initialization skipped (skip_mongodb=True)")

        # Initialize OpenAI client using mixin (optional)
        if not self.skip_openai:
            try:
                await self.initialize_openai_client(
                    api_key=config.embedding_api_key,
                    base_url=config.embedding_base_url,
                    embedding_api_key=config.embedding_api_key,
                    embedding_base_url=config.embedding_base_url,
                )
                logger.info(
                    "openai_client_initialized",
                    extra={
                        "model": config.embedding_model,
                        "dimension": config.embedding_dimension,
                    },
                )
            except Exception as e:
                logger.warning(f"OpenAI initialization skipped or failed: {e}")
        else:
            logger.info("OpenAI initialization skipped (skip_openai=True)")

        # Initialize Crawl4AI crawler
        if not self.crawler:
            try:
                browser_config_kwargs = {
                    "headless": config.browser_headless,
                    "verbose": False,
                    "text_mode": True,  # Disable images for faster crawling
                }

                # Add managed browser support if user_data_dir is provided
                if self.user_data_dir:
                    browser_config_kwargs["use_managed_browser"] = True
                    browser_config_kwargs["user_data_dir"] = self.user_data_dir

                    # Check if storage_state.json exists to load session data
                    # storage_state.json (Playwright format) takes precedence over Chrome profile cookies
                    from pathlib import Path

                    profile_path = Path(self.user_data_dir)
                    storage_state_path = profile_path / "storage_state.json"
                    if storage_state_path.exists():
                        logger.info(f"Loading storage_state.json from: {storage_state_path}")
                        browser_config_kwargs["storage_state"] = str(storage_state_path)
                    else:
                        logger.info(
                            f"No storage_state.json found, using Chrome profile cookies from: {self.user_data_dir}"
                        )

                    logger.info(f"Using managed browser profile: {self.user_data_dir}")

                browser_config = BrowserConfig(**browser_config_kwargs)
                self.crawler = AsyncWebCrawler(config=browser_config)
                await self.crawler.__aenter__()
                logger.info("crawl4ai_crawler_initialized")
            except Exception as e:
                logger.exception("crawl4ai_initialization_failed", extra={"error": str(e)})
                raise

    async def cleanup(self) -> None:
        """Clean up external connections."""
        if self.crawler:
            try:
                await self.crawler.__aexit__(None, None, None)
                self.crawler = None
                logger.info("crawl4ai_crawler_closed")
            except Exception as e:
                logger.warning(f"Error closing crawler: {e}")

        # Cleanup using mixins (only if initialized)
        if not self.skip_mongodb:
            await self.cleanup_mongodb()
        if not self.skip_openai:
            await self.cleanup_openai_clients()

    @classmethod
    def from_settings(cls, **kwargs) -> "Crawl4AIDependencies":
        """
        Create dependencies from application settings.

        Args:
            **kwargs: Optional overrides for specific dependencies

        Returns:
            Initialized dependencies instance (not yet initialized, call initialize() separately)
        """
        return cls(**kwargs)

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
        if not self.embedding_service:
            await self.initialize()

        return await self.embedding_service.generate_embedding(text)

    def set_user_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference for the session.

        Args:
            key: Preference key
            value: Preference value
        """
        self.user_preferences[key] = value


__all__ = ["Crawl4AIDependencies", "create_browser_config_with_profile", "get_profile_path"]
