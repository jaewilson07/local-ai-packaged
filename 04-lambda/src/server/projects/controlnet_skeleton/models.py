"""
Pydantic models for ControlNet skeleton management
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PreprocessorType(str, Enum):
    """Supported ControlNet preprocessor types"""

    CANNY = "canny"
    DEPTH = "depth"
    OPENPOSE = "openpose"
    DWPOSE = "dwpose"
    LINEART = "lineart"
    SCRIBBLE = "scribble"
    TILE = "tile"


class VisionAnalysisResult(BaseModel):
    """Result from vision model image analysis"""

    description: str = Field(..., description="Generated description of the image")
    prompt: str = Field(..., description="Optimized prompt for image generation")
    tags: list[str] = Field(default_factory=list, description="Auto-detected tags")
    scene_composition: str | None = Field(None, description="Composition analysis")
    detected_elements: list[str] = Field(
        default_factory=list, description="Detected objects/elements"
    )
    suggested_preprocessor: PreprocessorType | None = Field(
        None, description="Suggested ControlNet preprocessor"
    )


class SkeletonMetadata(BaseModel):
    """Flexible metadata for skeleton images"""

    image_dimensions: dict[str, int] | None = None
    pose_keypoints: list[dict] | None = None
    edge_density: float | None = None
    depth_range: dict[str, float] | None = None
    original_image_url: str | None = None
    vision_analysis: dict[str, Any] | None = None


class ControlNetSkeleton(BaseModel):
    """ControlNet skeleton database model"""

    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    minio_path: str
    preprocessor_type: PreprocessorType
    tags: list[str] = Field(default_factory=list)
    embedding_id: str | None = None
    is_public: bool = True
    metadata: SkeletonMetadata = Field(default_factory=SkeletonMetadata)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ControlNetSkeletonCreate(BaseModel):
    """Request to create a new skeleton"""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    preprocessor_type: PreprocessorType
    tags: list[str] = Field(default_factory=list)
    is_public: bool = True
    metadata: SkeletonMetadata = Field(default_factory=SkeletonMetadata)


class ControlNetSkeletonUpdate(BaseModel):
    """Request to update an existing skeleton"""

    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    is_public: bool | None = None
    metadata: SkeletonMetadata | None = None


class SkeletonSearchRequest(BaseModel):
    """Request to search for skeletons"""

    query: str = Field(..., min_length=1, description="Search query")
    preprocessor_type: PreprocessorType | None = Field(
        None, description="Filter by preprocessor type"
    )
    match_count: int = Field(10, ge=1, le=100, description="Number of results")
    include_private: bool = Field(True, description="Include user's private skeletons in search")
    search_type: str = Field(
        "hybrid",
        description="Search type: 'semantic', 'text', or 'hybrid'",
        pattern="^(semantic|text|hybrid)$",
    )


class SkeletonSearchResult(BaseModel):
    """Single skeleton search result"""

    skeleton: ControlNetSkeleton
    similarity_score: float = Field(..., ge=0, le=1, description="Similarity score (0-1)")
    preview_url: str | None = Field(None, description="Presigned URL for preview")


class SkeletonSearchResponse(BaseModel):
    """Response from skeleton search"""

    results: list[SkeletonSearchResult]
    total_count: int
    query: str
    search_type: str
