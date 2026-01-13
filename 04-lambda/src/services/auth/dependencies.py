"""FastAPI dependencies for authentication."""

import logging

from fastapi import Header, HTTPException
from services.auth.config import config
from services.auth.models import User
from src.services.auth.jwt import JWTService
from src.services.database.mongodb import MongoDBClient
from src.services.database.neo4j import Neo4jClient
from src.services.database.supabase import SupabaseClient, SupabaseConfig
from src.services.external.immich import ImmichService

logger = logging.getLogger(__name__)


async def get_current_user(
    cf_jwt: str = Header(alias="Cf-Access-Jwt-Assertion", default=None),
) -> User:
    """
    FastAPI dependency to extract and validate Cloudflare Access JWT.

    Performs JIT (Just-In-Time) user provisioning if user doesn't exist.

    Args:
        cf_jwt: Cloudflare Access JWT from header

    Returns:
        User object with UUID, email, role, tier

    Raises:
        HTTPException: 403 if header missing, 401 if token invalid
    """
    if not cf_jwt:
        raise HTTPException(
            status_code=403,
            detail="Missing Cf-Access-Jwt-Assertion header. This endpoint requires Cloudflare Access authentication. Make sure you're accessing through Cloudflare Access or include the JWT token in the header.",
        )

    try:
        # Validate JWT and extract email
        jwt_service = JWTService(config)
        email = await jwt_service.validate_and_extract_email(cf_jwt)

        # Check if user exists in Supabase, provision if not
        supabase_config = SupabaseConfig()
        supabase_service = SupabaseClient(supabase_config)

        # Get or provision user (ensures table exists and creates user if needed)
        user = await supabase_service.get_or_provision_user(email)

        # Check if this is a new user by checking if MongoDB credentials exist
        # (new users won't have these set until provisioning completes)
        is_new_user = not hasattr(user, "__dict__") or user.__dict__.get("mongodb_username") is None

        # Provision in Neo4j, MinIO, and MongoDB if this is a new user
        if is_new_user:
            try:
                neo4j_client = Neo4jClient()
                await neo4j_client.provision_user(email)
            except Exception as e:
                logger.warning(f"Neo4j provisioning failed for {email}: {e}")
            finally:
                await neo4j_client.close()

            try:
                minio_service = MinIOService(config)
                await minio_service.provision_user(user.id, email)
            except Exception as e:
                logger.warning(f"MinIO provisioning failed for {email}: {e}")

            try:
                mongodb_client = MongoDBClient()
                creds = await mongodb_client.provision_user(email, str(user.id))
                # Store credentials in Supabase
                await supabase_service.update_mongodb_credentials(
                    email, creds.username, creds.password
                )
            except Exception as e:
                logger.warning(f"MongoDB provisioning failed for {email}: {e}")

            try:
                immich_service = ImmichService(config)
                immich_user_id, immich_api_key = await immich_service.provision_user(
                    email, str(user.id)
                )
                await supabase_service.update_immich_credentials(
                    email, immich_user_id, immich_api_key
                )
            except Exception as e:
                logger.warning(f"Immich provisioning failed for {email}: {e}")

        return user

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.exception("Authentication failed")

        # Check if it's a database schema error
        if "does not exist" in error_msg.lower() or "relation" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail=f"Database schema error: {error_msg}. Please ensure the profiles table exists. Run the migration: 01-data/supabase/migrations/000_profiles_table.sql",
            ) from e

        # Check if it's a JWT validation error
        if (
            "jwt" in error_msg.lower()
            or "token" in error_msg.lower()
            or "signature" in error_msg.lower()
        ):
            raise HTTPException(status_code=401, detail=f"Invalid token: {error_msg}") from e

        # Generic error
        raise HTTPException(status_code=500, detail=f"Authentication error: {error_msg}") from e
