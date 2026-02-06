"""Neo4j administrative endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from .client import Neo4jClient

router = APIRouter(prefix="/api/v1/data/neo4j", tags=["data", "neo4j"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """Check Neo4j connectivity and driver status."""
    client = Neo4jClient()
    try:
        status = await client.ping()
        if status.status == "healthy":
            return status.model_dump()
        raise HTTPException(status_code=503, detail=f"Neo4j unhealthy: {status.message}")
    finally:
        await client.close()
