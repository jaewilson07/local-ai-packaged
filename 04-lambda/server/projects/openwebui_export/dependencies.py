"""Dependencies for Open WebUI Export Agent."""

from dataclasses import dataclass, field
from typing import Optional
import logging
import httpx
from pymongo import AsyncMongoClient

from server.projects.shared.dependencies import BaseDependencies, MongoDBMixin
from server.projects.openwebui_export.config import config

logger = logging.getLogger(__name__)


@dataclass
class OpenWebUIExportDeps(BaseDependencies, MongoDBMixin):
    """Infrastructure dependencies for Open WebUI export operations."""
    
    # MongoDB client for RAG storage
    mongo_client: Optional[AsyncMongoClient] = None
    
    # HTTP client for Open WebUI API
    http_client: Optional[httpx.AsyncClient] = None
    
    # Configuration
    mongodb_uri: str = field(default_factory=lambda: config.mongodb_uri)
    mongodb_database: str = field(default_factory=lambda: config.mongodb_database)
    openwebui_api_url: str = field(default_factory=lambda: config.openwebui_api_url)
    openwebui_api_key: Optional[str] = field(default_factory=lambda: config.openwebui_api_key)
    
    async def initialize(self) -> None:
        """
        Initialize all infrastructure connections.
        
        Raises:
            Exception: If connection initialization fails
        """
        # Initialize MongoDB using mixin
        await self.initialize_mongodb(
            mongodb_uri=self.mongodb_uri,
            mongodb_database=self.mongodb_database
        )
        logger.info(
            "mongodb_client_initialized",
            extra={
                "database": self.mongodb_database,
                "uri": self.mongodb_uri.split("@")[-1] if "@" in self.mongodb_uri else "***"
            }
        )
        
        # Initialize HTTP client for Open WebUI API
        if not self.http_client:
            headers = {"Content-Type": "application/json"}
            if self.openwebui_api_key:
                headers["Authorization"] = f"Bearer {self.openwebui_api_key}"
            
            self.http_client = httpx.AsyncClient(
                base_url=self.openwebui_api_url,
                headers=headers,
                timeout=30.0
            )
            logger.info(
                "openwebui_client_initialized",
                extra={
                    "api_url": self.openwebui_api_url,
                    "has_api_key": bool(self.openwebui_api_key)
                }
            )
    
    async def cleanup(self) -> None:
        """Clean up all infrastructure connections."""
        # Cleanup MongoDB using mixin
        await self.cleanup_mongodb()
        
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
            logger.info("openwebui_client_closed")
    
    @property
    def db(self):
        """Get MongoDB database instance."""
        if not self.mongo_client:
            raise RuntimeError("MongoDB client not initialized. Call initialize() first.")
        return self.mongo_client[self.mongodb_database]
    
    @classmethod
    def from_settings(
        cls,
        mongo_client: Optional[AsyncMongoClient] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        mongodb_uri: Optional[str] = None,
        mongodb_database: Optional[str] = None,
        openwebui_api_url: Optional[str] = None,
        openwebui_api_key: Optional[str] = None
    ) -> "OpenWebUIExportDeps":
        """
        Factory method to create dependencies from settings.
        
        Args:
            mongo_client: Optional pre-initialized MongoDB client
            http_client: Optional pre-initialized HTTP client
            mongodb_uri: Optional override for MongoDB URI
            mongodb_database: Optional override for MongoDB database
            openwebui_api_url: Optional override for Open WebUI API URL
            openwebui_api_key: Optional override for Open WebUI API key
        
        Returns:
            OpenWebUIExportDeps instance
        """
        return cls(
            mongo_client=mongo_client,
            http_client=http_client,
            mongodb_uri=mongodb_uri or config.mongodb_uri,
            mongodb_database=mongodb_database or config.mongodb_database,
            openwebui_api_url=openwebui_api_url or config.openwebui_api_url,
            openwebui_api_key=openwebui_api_key or config.openwebui_api_key
        )
