"""Configuration for ComfyUI Workflow project."""

import os
from dataclasses import dataclass, field


@dataclass
class ComfyUIConfig:
    """Configuration for ComfyUI workflow execution."""

    comfyui_url: str = field(
        default_factory=lambda: os.getenv("COMFYUI_URL", "http://comfyui:8188")
    )
    comfyui_access_token: str | None = field(
        default_factory=lambda: os.getenv("COMFYUI_ACCESS_TOKEN")
    )
    # Standard ComfyUI API endpoints
    submit_endpoint: str = "/prompt"
    history_endpoint: str = "/history"
    view_endpoint: str = "/view"
    queue_endpoint: str = "/queue"
    submit_timeout: int = 30
    poll_timeout: int = 600
    poll_interval: int = 5
    minio_bucket: str = "comfyui-outputs"
    minio_prefix: str = "images"

    # ComfyUI file system integration for workflow versioning
    comfyui_workflows_dir: str = field(
        default_factory=lambda: os.getenv("COMFYUI_WORKFLOWS_DIR", "/comfyui-workflows")
    )
    # Prefix for database-managed workflows in the file system
    managed_workflow_prefix: str = "db_"

    @property
    def is_remote(self) -> bool:
        return any(domain in self.comfyui_url for domain in ["datacrew.space", "https://"])


config = ComfyUIConfig()
