"""User images API for listing and accessing generated images."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from app.services.auth.dependencies import get_current_user
from app.services.auth.models import User
from app.services.database.supabase import SupabaseClient, SupabaseConfig
from app.services.external.immich.client import ImmichService
from app.services.storage.minio import MinIOClient, MinIOConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/images")


class ImageMetadata(BaseModel):
    """Metadata for a single image."""

    key: str
    source: str  # "minio", "immich", "comfyui"
    size: int | None = None
    created_at: datetime | None = None
    content_type: str | None = None
    url: str | None = None
    thumbnail_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImagesListResponse(BaseModel):
    """Response for listing images."""

    images: list[ImageMetadata]
    total: int
    source: str


class CombinedImagesResponse(BaseModel):
    """Combined response from multiple sources."""

    minio: ImagesListResponse | None = None
    immich: ImagesListResponse | None = None
    comfyui: ImagesListResponse | None = None


async def _list_minio_images(user: User, prefix: str = "") -> list[ImageMetadata]:
    """List images from MinIO for the user."""
    try:
        config = MinIOConfig()
        client = MinIOClient(config)

        user_prefix = f"user-{user.uid}/{prefix}"
        objects = client.list_objects("user-data", prefix=user_prefix)

        images = []
        for obj in objects:
            if any(
                obj.object_name.lower().endswith(ext)
                for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]
            ):
                presigned_url = client.get_presigned_url("user-data", obj.object_name)
                images.append(
                    ImageMetadata(
                        key=obj.object_name,
                        source="minio",
                        size=obj.size,
                        created_at=obj.last_modified,
                        content_type=obj.content_type,
                        url=presigned_url,
                    )
                )

        return images
    except Exception as e:
        logger.warning(f"Error listing MinIO images: {e}")
        return []


async def _list_immich_images(user: User, limit: int = 100) -> list[ImageMetadata]:
    """List images from Immich for the user."""
    try:
        # Get user's Immich API key from profile
        supabase_config = SupabaseConfig()
        supabase = SupabaseClient(supabase_config)

        profile = await supabase.get_profile(user.email)
        if not profile or not profile.get("immich_api_key"):
            return []

        immich = ImmichService(api_key=profile["immich_api_key"])
        assets = await immich.get_assets(limit=limit)

        images = []
        for asset in assets:
            images.append(
                ImageMetadata(
                    key=asset.get("id", ""),
                    source="immich",
                    size=asset.get("exifInfo", {}).get("fileSizeInByte"),
                    created_at=(
                        datetime.fromisoformat(asset["createdAt"].replace("Z", "+00:00"))
                        if asset.get("createdAt")
                        else None
                    ),
                    content_type=asset.get("originalMimeType"),
                    url=f"/api/v1/images/immich/{asset['id']}",
                    thumbnail_url=(
                        await immich.get_asset_thumbnail_url(asset["id"])
                        if asset.get("id")
                        else None
                    ),
                    metadata={"type": asset.get("type"), "isFavorite": asset.get("isFavorite")},
                )
            )

        return images
    except Exception as e:
        logger.warning(f"Error listing Immich images: {e}")
        return []


@router.get("", response_model=CombinedImagesResponse)
async def list_all_images(
    include_minio: bool = Query(True),
    include_immich: bool = Query(True),
    limit: int = Query(100, ge=1, le=1000),
    user: User = Depends(get_current_user),
):
    """List images from all sources."""
    response = CombinedImagesResponse()

    if include_minio:
        minio_images = await _list_minio_images(user)
        response.minio = ImagesListResponse(
            images=minio_images[:limit],
            total=len(minio_images),
            source="minio",
        )

    if include_immich:
        immich_images = await _list_immich_images(user, limit)
        response.immich = ImagesListResponse(
            images=immich_images,
            total=len(immich_images),
            source="immich",
        )

    return response


@router.get("/minio", response_model=ImagesListResponse)
async def list_minio_images(
    prefix: str = Query(""),
    limit: int = Query(100, ge=1, le=1000),
    user: User = Depends(get_current_user),
):
    """List images from MinIO storage."""
    images = await _list_minio_images(user, prefix)
    return ImagesListResponse(
        images=images[:limit],
        total=len(images),
        source="minio",
    )


@router.get("/immich", response_model=ImagesListResponse)
async def list_immich_images(
    limit: int = Query(100, ge=1, le=1000),
    user: User = Depends(get_current_user),
):
    """List images from Immich library."""
    images = await _list_immich_images(user, limit)
    return ImagesListResponse(
        images=images,
        total=len(images),
        source="immich",
    )


@router.get("/{image_key:path}")
async def get_image_url(
    image_key: str,
    user: User = Depends(get_current_user),
):
    """Get a presigned URL for accessing an image."""
    try:
        # Ensure the key belongs to the user
        expected_prefix = f"user-{user.uid}/"
        if not image_key.startswith(expected_prefix):
            raise HTTPException(status_code=403, detail="Access denied to this image")

        config = MinIOConfig()
        client = MinIOClient(config)
        url = client.get_presigned_url("user-data", image_key)

        return {"url": url, "key": image_key}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting presigned URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate image URL")
