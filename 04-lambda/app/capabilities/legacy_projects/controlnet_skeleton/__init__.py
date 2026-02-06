"""
ControlNet skeleton management project

Provides endpoints for:
- Creating ControlNet skeletons from images
- Vision-based image analysis and auto-tagging
- Semantic search for skeletons
- Skeleton library management
"""

from app.capabilities.legacy_projects.controlnet_skeleton.router import router

__all__ = ["router"]
