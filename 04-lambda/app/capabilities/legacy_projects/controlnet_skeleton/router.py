"""
ControlNet skeleton management router
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from app.capabilities.legacy_projects.auth.dependencies import get_current_user
from app.capabilities.legacy_projects.auth.models import User
from app.capabilities.legacy_projects.controlnet_skeleton.dependencies import get_skeleton_service
from app.capabilities.legacy_projects.controlnet_skeleton.models import (
    ControlNetSkeleton,
    ControlNetSkeletonCreate,
    PreprocessorType,
    SkeletonSearchRequest,
    SkeletonSearchResponse,
    VisionAnalysisResult,
)
from app.capabilities.legacy_projects.controlnet_skeleton.service import ControlNetSkeletonService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/controlnet/skeletons", tags=["ControlNet Skeletons"])


@router.post("/create-from-url", response_model=ControlNetSkeleton, status_code=status.HTTP_201_CREATED)
async def create_skeleton_from_url(
    image_url: str,
    name: str,
    preprocessor_type: PreprocessorType,
    description: str | None = None,
    auto_analyze: bool = True,
    is_public: bool = True,
    user: User = Depends(get_current_user),
    service: ControlNetSkeletonService = Depends(get_skeleton_service),
):
    """
    Create a ControlNet skeleton from an image URL

    The image will be:
    1. Downloaded from the URL
    2. Analyzed with vision model (if auto_analyze=True)
    3. Processed with the specified ControlNet preprocessor
    4. Stored in MinIO with metadata
    5. Indexed in MongoDB for semantic search

    Args:
        image_url: URL of the source image
        name: Name for the skeleton
        preprocessor_type: Type of preprocessor (canny, depth, openpose, etc.)
        description: Optional description (auto-generated if None)
        auto_analyze: Whether to analyze image with vision model
        is_public: Whether skeleton is publicly accessible

    Returns:
        Created skeleton with metadata
    """
    try:
        return await service.create_skeleton_from_url(
            user=user,
            image_url=image_url,
            name=name,
            preprocessor_type=preprocessor_type,
            description=description,
            auto_analyze=auto_analyze,
            is_public=is_public,
        )
    except Exception as e:
        logger.error(f"Failed to create skeleton from URL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create skeleton: {str(e)}",
        )


@router.post("/analyze-image", response_model=VisionAnalysisResult)
async def analyze_image(
    image_url: str,
    context: str = "ControlNet skeleton creation",
    user: User = Depends(get_current_user),
    service: ControlNetSkeletonService = Depends(get_skeleton_service),
):
    """
    Analyze an image using vision model

    Returns description, tags, and suggested preprocessor without creating a skeleton.
    Useful for previewing what the vision model detects before creating a skeleton.

    Args:
        image_url: URL of the image to analyze
        context: Context for analysis

    Returns:
        Vision analysis result with description, tags, and suggestions
    """
    try:
        # Download image
        image_data = await service.download_image_from_url(image_url)

        # Analyze
        return await service.vision_service.analyze_image(image_data, context)
    except Exception as e:
        logger.error(f"Failed to analyze image: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze image: {str(e)}",
        )


@router.post("/search", response_model=SkeletonSearchResponse)
async def search_skeletons(
    search_request: SkeletonSearchRequest,
    user: User = Depends(get_current_user),
    service: ControlNetSkeletonService = Depends(get_skeleton_service),
):
    """
    Search for ControlNet skeletons using semantic or hybrid search

    Examples:
        - "woman in car interior, profile view"
        - "standing pose with arms raised"
        - "indoor room with depth, architectural"

    The search uses embeddings to find semantically similar skeletons.
    Results include similarity scores and preview URLs.

    Args:
        search_request: Search parameters including query and filters

    Returns:
        Ranked list of matching skeletons with similarity scores
    """
    try:
        return await service.search_skeletons(user, search_request)
    except Exception as e:
        logger.error(f"Skeleton search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.get("/", response_model=list[ControlNetSkeleton])
async def list_skeletons(
    preprocessor_type: PreprocessorType | None = None,
    include_public: bool = True,
    limit: int = 50,
    user: User = Depends(get_current_user),
    service: ControlNetSkeletonService = Depends(get_skeleton_service),
):
    """
    List available ControlNet skeletons

    Returns user's own skeletons and optionally public skeletons.

    Args:
        preprocessor_type: Filter by preprocessor type
        include_public: Include public skeletons from other users
        limit: Maximum number of results

    Returns:
        List of skeletons
    """
    try:
        return await service.list_skeletons(
            user=user,
            preprocessor_type=preprocessor_type,
            include_public=include_public,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Failed to list skeletons: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list skeletons: {str(e)}",
        )


@router.get("/{skeleton_id}", response_model=ControlNetSkeleton)
async def get_skeleton(
    skeleton_id: UUID,
    user: User = Depends(get_current_user),
    service: ControlNetSkeletonService = Depends(get_skeleton_service),
):
    """
    Get a specific skeleton by ID

    Args:
        skeleton_id: Skeleton UUID

    Returns:
        Skeleton details
    """
    skeleton = await service.get_skeleton(skeleton_id, user)
    if not skeleton:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skeleton not found or not accessible",
        )
    return skeleton


@router.delete("/{skeleton_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skeleton(
    skeleton_id: UUID,
    user: User = Depends(get_current_user),
    service: ControlNetSkeletonService = Depends(get_skeleton_service),
):
    """
    Delete a skeleton (user must own it)

    Removes the skeleton from Supabase, MongoDB, and MinIO.

    Args:
        skeleton_id: Skeleton UUID
    """
    success = await service.delete_skeleton(skeleton_id, user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skeleton not found or not owned by user",
        )
