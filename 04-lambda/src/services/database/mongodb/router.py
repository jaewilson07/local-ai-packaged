from fastapi import APIRouter, HTTPException

from .client import MongoDBClient

router = APIRouter(prefix="/mongodb", tags=["Infrastructure"])


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
