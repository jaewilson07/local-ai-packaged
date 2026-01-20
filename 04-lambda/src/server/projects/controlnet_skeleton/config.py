"""
Configuration for ControlNet skeleton management
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class ControlNetSkeletonConfig(BaseSettings):
    """Configuration for ControlNet skeleton service"""

    # Vision model settings
    vision_model: str = "llava:7b"
    ollama_base_url: str = "http://ollama:11434"

    # MongoDB settings
    mongodb_uri: str = os.getenv(
        "MONGODB_URI",
        "mongodb://admin:admin123@mongodb:27017/?authSource=admin",
    )
    mongodb_database: str = "rag_db"
    skeleton_collection: str = "controlnet_skeletons"

    # Embedding settings
    embedding_model: str = "qwen3-embedding:4b"
    embedding_dimensions: int = 2560

    # MinIO paths
    skeleton_path_prefix: str = "controlnet/skeletons"

    # Search settings
    default_match_count: int = 10
    max_match_count: int = 100

    # ComfyUI settings
    comfyui_base_url: str = "http://comfyui:8188"
    comfyui_input_path: str = "/comfy/mnt/input"

    # Image analysis settings
    vision_system_prompt: str = """You are an expert at analyzing images for ControlNet skeleton generation.

Analyze the provided image and provide:
1. A detailed description focusing on composition, pose, and scene elements
2. Auto-detected tags (e.g., portrait, full-body, car-interior, standing, profile-view)
3. Scene composition analysis
4. Detected elements/objects
5. Suggested ControlNet preprocessor (canny, depth, openpose, dwpose)

Focus on structural and compositional elements that would be useful for ControlNet guidance.
Be specific about poses, angles, and spatial relationships."""

    vision_prompt_template: str = """Analyze this image and provide the following in JSON format:

{
  "description": "Detailed description of the image composition and pose",
  "tags": ["tag1", "tag2", "tag3"],
  "scene_composition": "Analysis of composition, angles, perspective",
  "detected_elements": ["element1", "element2"],
  "suggested_preprocessor": "openpose|canny|depth"
}

Image context: {context}
"""

    class Config:
        env_prefix = "CONTROLNET_"
        case_sensitive = False


@lru_cache
def get_controlnet_config() -> ControlNetSkeletonConfig:
    """Get cached configuration instance"""
    return ControlNetSkeletonConfig()
