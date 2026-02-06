"""Supabase service router."""

from fastapi import APIRouter, HTTPException

from .client import SupabaseClient
from .config import SupabaseConfig
from .validation import DatabaseValidator

router = APIRouter(prefix="/api/v1/data/supabase", tags=["data", "supabase"])


@router.get("/health")
async def health_check():
    """Check Supabase database connection health."""
    try:
        config = SupabaseConfig()
        client = SupabaseClient(config)
        pool = await client._get_pool()

        # Simple health check query
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        await client.close()
        return {"status": "healthy", "service": "supabase"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e!s}")


@router.get("/validate")
async def validate_database():
    """Validate database schema and core tables."""
    try:
        config = SupabaseConfig()
        validator = DatabaseValidator(config)

        result = await validator.validate_core_tables()
        await validator.close()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {e!s}")
