"""Health check endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from pymongo import AsyncMongoClient

from server.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health():
    """Basic health check."""
    return {"status": "healthy", "service": "lambda-server"}


@router.get("/health/mongodb")
async def mongodb_health():
    """Check MongoDB connectivity."""
    try:
        client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
        await client.close()
        return {"status": "healthy", "service": "mongodb"}
    except Exception as e:
        logger.exception("mongodb_health_check_failed")
        raise HTTPException(status_code=503, detail=f"MongoDB unhealthy: {e!s}") from e
