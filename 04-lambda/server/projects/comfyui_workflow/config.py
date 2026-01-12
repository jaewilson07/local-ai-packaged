"""Configuration for ComfyUI Workflow project."""

import os
from dataclasses import dataclass


@dataclass
class ComfyUIWorkflowConfig:
    """Configuration for ComfyUI Workflow project."""

    comfyui_url: str = os.getenv("COMFYUI_URL", "http://comfyui:8188")
    comfyui_web_user: str = os.getenv("COMFYUI_WEB_USER", "user")
    comfyui_web_password: str = os.getenv("COMFYUI_WEB_PASSWORD", "password")


config = ComfyUIWorkflowConfig()
