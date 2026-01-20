from fastapi import APIRouter, HTTPException

from .client import MongoDBClient

router = APIRouter(prefix="/api/v1/data/mongodb", tags=["data", "mongodb"])


@router.get("/health")
async def health_check():
    """Check MongoDB connectivity."""
    client = MongoDBClient()
    try:
        await client.ping()
        return {"status": "healthy", "service": "mongodb"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MongoDB unhealthy: {e}")
    finally:
        await client.close()
