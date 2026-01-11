"""FastAPI dependencies for authentication."""

import logging

from fastapi import Header, HTTPException

from server.projects.auth.config import config
from server.projects.auth.models import User
from server.projects.auth.services.jwt_service import JWTService
from server.projects.auth.services.minio_service import MinIOService
from server.projects.auth.services.mongodb_service import MongoDBService
from server.projects.auth.services.neo4j_service import Neo4jService
from server.projects.auth.services.supabase_service import SupabaseService

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
        supabase_service = SupabaseService(config)

        # Check if user already exists
        existing_user = await supabase_service.get_user_by_email(email)
        is_new_user = existing_user is None

        # Get or provision user
        user = await supabase_service.get_or_provision_user(email)

        # Provision in Neo4j, MinIO, and MongoDB if this is a new user
        if is_new_user:
            try:
                neo4j_service = Neo4jService(config)
                await neo4j_service.provision_user(email)
            except Exception as e:
                logger.warning(f"Neo4j provisioning failed for {email}: {e}")

            try:
                minio_service = MinIOService(config)
                await minio_service.provision_user(user.id, email)
            except Exception as e:
                logger.warning(f"MinIO provisioning failed for {email}: {e}")

            try:
                mongodb_service = MongoDBService(config)
                mongodb_username, mongodb_password = await mongodb_service.provision_user(
                    email, str(user.id)
                )
                # Store credentials in Supabase
                await supabase_service.update_mongodb_credentials(
                    email, mongodb_username, mongodb_password
                )
            except Exception as e:
                logger.warning(f"MongoDB provisioning failed for {email}: {e}")

        return user

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Authentication failed: {e}")

        # Check if it's a database schema error
        if "does not exist" in error_msg.lower() or "relation" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail=f"Database schema error: {error_msg}. Please ensure the profiles table exists. Run the migration: 01-data/supabase/migrations/000_profiles_table.sql",
            )

        # Check if it's a JWT validation error
        if (
            "jwt" in error_msg.lower()
            or "token" in error_msg.lower()
            or "signature" in error_msg.lower()
        ):
            raise HTTPException(status_code=401, detail=f"Invalid token: {error_msg}")

        # Generic error
        raise HTTPException(status_code=500, detail=f"Authentication error: {error_msg}")
