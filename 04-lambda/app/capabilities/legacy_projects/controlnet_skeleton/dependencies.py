"""
Dependencies for ControlNet skeleton management
"""

from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient
from app.capabilities.legacy_projects.controlnet_skeleton.config import get_controlnet_config
from app.capabilities.legacy_projects.controlnet_skeleton.service import ControlNetSkeletonService
from app.services.storage.minio import MinIOClient, MinIOConfig
from supabase import create_client


@lru_cache
def get_supabase_client():
    """Get cached Supabase client"""
    import os

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

    return create_client(supabase_url, supabase_key)


@lru_cache
def get_minio_client():
    """Get cached MinIO client"""
    config = MinIOConfig()
    return MinIOClient(config)


@lru_cache
def get_mongo_client():
    """Get cached MongoDB client"""
    config = get_controlnet_config()
    return AsyncIOMotorClient(config.mongodb_uri)


def get_skeleton_service() -> ControlNetSkeletonService:
    """Get ControlNet skeleton service instance"""
    return ControlNetSkeletonService(
        supabase=get_supabase_client(),
        minio=get_minio_client(),
        mongo_client=get_mongo_client(),
    )
