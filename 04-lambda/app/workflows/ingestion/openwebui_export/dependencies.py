"""OpenWebUI export dependencies."""

import logging
from dataclasses import dataclass, field

import httpx
from app.workflows.ingestion.openwebui_export.config import config

from app.core.dependencies import BaseDependencies, MongoDBMixin

logger = logging.getLogger(__name__)


@dataclass
class OpenWebUIExportDeps(BaseDependencies, MongoDBMixin):
    """Dependencies injected into the OpenWebUI export agent context."""

    # HTTP client for Open WebUI API calls
    http_client: httpx.AsyncClient | None = None

    # Configuration
    openwebui_url: str = field(default_factory=lambda: config.openwebui_url)
    openwebui_api_key: str | None = field(default_factory=lambda: config.openwebui_api_key)

    async def initialize(self) -> None:
        """Initialize external connections."""
        # Initialize HTTP client
        if not self.http_client:
            headers = {"Content-Type": "application/json"}
            if self.openwebui_api_key:
                headers["Authorization"] = f"Bearer {self.openwebui_api_key}"

            self.http_client = httpx.AsyncClient(
                base_url=self.openwebui_url,
                headers=headers,
                timeout=30.0,
            )
            logger.info(
                "openwebui_client_initialized",
                extra={"url": self.openwebui_url, "has_api_key": bool(self.openwebui_api_key)},
            )

        # Initialize MongoDB
        await self.initialize_mongodb()

    async def cleanup(self) -> None:
        """Clean up external connections."""
        # Cleanup HTTP client
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
            logger.info("openwebui_client_closed")

        # Cleanup MongoDB
        await self.cleanup_mongodb()

    @classmethod
    def from_settings(
        cls,
        http_client: httpx.AsyncClient | None = None,
        openwebui_url: str | None = None,
        openwebui_api_key: str | None = None,
    ) -> "OpenWebUIExportDeps":
        """Create dependencies from settings."""
        return cls(
            http_client=http_client,
            openwebui_url=openwebui_url or config.openwebui_url,
            openwebui_api_key=openwebui_api_key or config.openwebui_api_key,
        )


__all__ = ["OpenWebUIExportDeps"]
