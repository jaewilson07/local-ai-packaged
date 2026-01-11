"""Dependencies for ComfyUI workflow management."""

import logging
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

import httpx

from server.projects.auth.config import config as auth_config
from server.projects.auth.services.minio_service import MinIOService
from server.projects.auth.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

# Optional Google Drive service
try:
    from server.projects.google_drive.service import GoogleDriveService

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    GoogleDriveService = None


@dataclass
class ComfyUIWorkflowDeps:
    """Dependencies for ComfyUI workflow management."""

    # Services
    supabase_service: SupabaseService = field(default_factory=lambda: SupabaseService(auth_config))
    minio_service: MinIOService = field(default_factory=lambda: MinIOService(auth_config))
    google_drive_service: object = field(default=None)

    # HTTP client for ComfyUI API
    comfyui_http_client: httpx.AsyncClient = field(default=None)

    # Configuration
    comfyui_url: str = field(
        default_factory=lambda: os.getenv("COMFYUI_URL", "http://comfyui:8188")
    )
    comfyui_web_user: str = field(default_factory=lambda: os.getenv("COMFYUI_WEB_USER", "user"))
    comfyui_web_password: str = field(
        default_factory=lambda: os.getenv("COMFYUI_WEB_PASSWORD", "password")
    )

    async def initialize(self) -> None:
        """Initialize HTTP client for ComfyUI API and optional Google Drive service."""
        if not self.comfyui_http_client:
            # Use basic auth for ComfyUI
            auth = (self.comfyui_web_user, self.comfyui_web_password)

            self.comfyui_http_client = httpx.AsyncClient(
                base_url=self.comfyui_url,
                auth=auth,
                timeout=60.0,  # Longer timeout for image generation
            )
            logger.info(f"Initialized ComfyUI HTTP client for {self.comfyui_url}")

        # Initialize Google Drive service if available and credentials are set
        if GOOGLE_DRIVE_AVAILABLE and not self.google_drive_service:
            try:
                # Try JSON format first
                credentials_json = os.getenv("GDOC_CLIENT")
                token_json = os.getenv("GDOC_TOKEN")

                # Fall back to separate client_id/client_secret
                client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("CLIENT_ID_GOOGLE_LOGIN")
                client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv(
                    "CLIENT_SECRET_GOOGLE_LOGIN"
                )

                if (credentials_json and token_json) or (client_id and client_secret):
                    self.google_drive_service = GoogleDriveService(
                        credentials_json=credentials_json,
                        token_json=token_json,
                        client_id=client_id,
                        client_secret=client_secret,
                    )
                    logger.info("Initialized Google Drive service")
                else:
                    logger.debug("Google Drive credentials not found, skipping initialization")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Drive service: {e}")

    async def cleanup(self) -> None:
        """Clean up connections."""
        if self.comfyui_http_client:
            await self.comfyui_http_client.aclose()
            self.comfyui_http_client = None
            logger.info("Closed ComfyUI HTTP client")

        if self.supabase_service:
            await self.supabase_service.close()


async def get_comfyui_workflow_deps() -> AsyncGenerator[ComfyUIWorkflowDeps, None]:
    """
    FastAPI dependency that yields ComfyUIWorkflowDeps.

    Ensures proper initialization and cleanup.
    """
    deps = ComfyUIWorkflowDeps()
    await deps.initialize()
    try:
        yield deps
    finally:
        await deps.cleanup()
