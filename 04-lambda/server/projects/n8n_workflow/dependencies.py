"""Dependencies for N8n Workflow Agent."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging
import httpx
from server.projects.shared.dependencies import BaseDependencies
from server.projects.n8n_workflow.config import config

logger = logging.getLogger(__name__)


@dataclass
class N8nWorkflowDeps(BaseDependencies):
    """Dependencies injected into the N8n workflow agent context."""
    
    # HTTP client for N8n API calls
    http_client: Optional[httpx.AsyncClient] = None
    
    # N8n API configuration
    n8n_api_url: str = field(default_factory=lambda: config.n8n_api_url)
    n8n_api_key: Optional[str] = field(default_factory=lambda: config.n8n_api_key)
    
    # Session context
    session_id: Optional[str] = None
    
    async def initialize(self) -> None:
        """
        Initialize HTTP client for N8n API calls.
        
        Raises:
            Exception: If HTTP client initialization fails
        """
        if not self.http_client:
            headers = {}
            if self.n8n_api_key:
                headers["X-N8N-API-KEY"] = self.n8n_api_key
            
            self.http_client = httpx.AsyncClient(
                base_url=self.n8n_api_url,
                headers=headers,
                timeout=30.0
            )
            logger.info(
                "n8n_client_initialized",
                extra={
                    "api_url": self.n8n_api_url,
                    "has_api_key": bool(self.n8n_api_key)
                }
            )
    
    async def cleanup(self) -> None:
        """Clean up HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
            logger.info("n8n_client_closed")
    
    @classmethod
    def from_settings(
        cls,
        http_client: Optional[httpx.AsyncClient] = None,
        n8n_api_url: Optional[str] = None,
        n8n_api_key: Optional[str] = None
    ) -> "N8nWorkflowDeps":
        """
        Create dependencies from application settings.
        
        Args:
            http_client: Optional pre-initialized HTTP client
            n8n_api_url: Optional override for N8n API URL
            n8n_api_key: Optional override for N8n API key
        
        Returns:
            N8nWorkflowDeps instance
        """
        return cls(
            http_client=http_client,
            n8n_api_url=n8n_api_url or config.n8n_api_url,
            n8n_api_key=n8n_api_key or config.n8n_api_key
        )

