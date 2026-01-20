"""FastAPI dependencies for authentication."""

import ipaddress
import logging
import os
import uuid

import asyncpg
from fastapi import Header, HTTPException, Request
from services.auth.config import config
from services.auth.jwt import JWTService
from services.auth.models import User
from services.auth.services.minio_service import MinIOService
from services.auth.services.token_service import TokenService
from services.database.mongodb import MongoDBClient
from services.database.neo4j import Neo4jClient
from services.database.supabase import SupabaseClient, SupabaseConfig

logger = logging.getLogger(__name__)

# Environment variable to enable development mode (bypasses auth for internal networks)
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
DEV_USER_EMAIL = os.getenv("DEV_USER_EMAIL", os.getenv("CLOUDFLARE_EMAIL", "dev@localhost"))

# Internal network CIDR ranges (Docker networks, localhost)
INTERNAL_NETWORK_RANGES = [
    "172.16.0.0/12",  # Docker default bridge
    "10.0.0.0/8",  # Docker overlay networks
    "192.168.0.0/16",  # Local networks
    "127.0.0.0/8",  # Localhost
]

# Database connection pool for token validation (lazy initialized)
_db_pool: asyncpg.Pool | None = None


async def _get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool."""
    global _db_pool
    if _db_pool is None:
        supabase_config = SupabaseConfig()
        _db_pool = await asyncpg.create_pool(
            dsn=supabase_config.db_url,
            min_size=1,
            max_size=5,
        )
    return _db_pool


def _is_internal_request(request: Request) -> bool:
    """
    Check if request is from internal Docker network.

    Args:
        request: FastAPI request object

    Returns:
        True if request is from an internal network
    """
    if not request or not request.client:
        return False

    client_ip = request.client.host

    # Check if IP is in any internal range
    try:
        ip = ipaddress.ip_address(client_ip)
        for cidr in INTERNAL_NETWORK_RANGES:
            network = ipaddress.ip_network(cidr)
            if ip in network:
                return True
    except ValueError:
        # Invalid IP address
        pass

    return False


async def _validate_api_token(token: str) -> User | None:
    """
    Validate an API token and return user.

    Args:
        token: Bearer token (with or without 'lat_' prefix)

    Returns:
        User object if valid, None otherwise
    """
    pool = await _get_db_pool()
    token_service = TokenService(pool)

    user_info = await token_service.validate_token(token)
    if not user_info:
        return None

    # Build User object from token validation result
    user = User(
        id=user_info["id"],
        email=user_info["email"],
        role=user_info.get("role", "user"),
        tier=user_info.get("tier", "free"),
    )

    # Add extra attributes
    user.__dict__["mongodb_username"] = user_info.get("mongodb_username")
    user.__dict__["mongodb_password"] = user_info.get("mongodb_password")
    user.__dict__["immich_user_id"] = user_info.get("immich_user_id")
    user.__dict__["immich_api_key"] = user_info.get("immich_api_key")
    user.__dict__["discord_user_id"] = user_info.get("discord_user_id")

    # Add token-specific info if from named token
    if "token_name" in user_info:
        user.__dict__["token_name"] = user_info["token_name"]
        user.__dict__["token_scopes"] = user_info.get("token_scopes", [])

    return user


async def _get_user_by_email(email: str) -> User:
    """
    Get or provision user by email (for internal network requests).

    Args:
        email: User email

    Returns:
        User object
    """
    supabase_config = SupabaseConfig()
    supabase_service = SupabaseClient(supabase_config)

    try:
        user = await supabase_service.get_or_provision_user(email)
        return user
    except Exception as e:
        logger.warning(f"User lookup failed for {email}: {e}")
        # Return a minimal user object
        return User(
            id=uuid.uuid4(),
            email=email,
            role="user",
            tier="free",
        )


async def _validate_cloudflare_jwt(cf_jwt: str) -> User:
    """
    Validate Cloudflare Access JWT and return user with JIT provisioning.

    Args:
        cf_jwt: Cloudflare Access JWT

    Returns:
        User object

    Raises:
        HTTPException: If validation fails
    """
    # Validate JWT and extract email
    jwt_service = JWTService(config)
    email = await jwt_service.validate_and_extract_email(cf_jwt)

    # Check if user exists in Supabase, provision if not
    supabase_config = SupabaseConfig()
    supabase_service = SupabaseClient(supabase_config)

    # Get or provision user (ensures table exists and creates user if needed)
    user = await supabase_service.get_or_provision_user(email)

    # Check if this is a new user by checking if MongoDB credentials exist
    is_new_user = not hasattr(user, "__dict__") or user.__dict__.get("mongodb_username") is None

    # Provision in Neo4j, MinIO, and MongoDB if this is a new user
    if is_new_user:
        await _provision_new_user(user, email, supabase_service)

    return user


async def _provision_new_user(user: User, email: str, supabase_service: SupabaseClient) -> None:
    """
    Provision a new user across all services.

    Args:
        user: User object
        email: User email
        supabase_service: Supabase client for credential storage
    """
    # Import here to avoid circular imports
    from services.external.immich import ImmichService

    try:
        neo4j_client = Neo4jClient()
        await neo4j_client.provision_user(email)
    except Exception as e:
        logger.warning(f"Neo4j provisioning failed for {email}: {e}")
    finally:
        try:
            await neo4j_client.close()
        except Exception:
            pass

    try:
        minio_service = MinIOService(config)
        await minio_service.provision_user(user.id, email)
    except Exception as e:
        logger.warning(f"MinIO provisioning failed for {email}: {e}")

    try:
        mongodb_client = MongoDBClient()
        creds = await mongodb_client.provision_user(email, str(user.id))
        await supabase_service.update_mongodb_credentials(email, creds.username, creds.password)
    except Exception as e:
        logger.warning(f"MongoDB provisioning failed for {email}: {e}")

    try:
        immich_service = ImmichService(config)
        immich_user_id, immich_api_key = await immich_service.provision_user(email, str(user.id))
        await supabase_service.update_immich_credentials(email, immich_user_id, immich_api_key)
    except Exception as e:
        logger.warning(f"Immich provisioning failed for {email}: {e}")


async def get_current_user(
    request: Request,
    cf_jwt: str = Header(alias="Cf-Access-Jwt-Assertion", default=None),
    authorization: str = Header(alias="Authorization", default=None),
    x_user_email: str = Header(alias="X-User-Email", default=None),
) -> User:
    """
    FastAPI dependency to authenticate users via multiple methods.

    Authentication methods (in priority order):
    1. Cloudflare Access JWT (Cf-Access-Jwt-Assertion header) - browser access
    2. Bearer token (Authorization header) - API token for automation
    3. Internal network + X-User-Email header - Docker service communication
    4. DEV_MODE bypass - development without authentication

    Args:
        request: FastAPI request object
        cf_jwt: Cloudflare Access JWT from header
        authorization: Authorization header (Bearer token)
        x_user_email: User email header for internal network requests

    Returns:
        User object with UUID, email, role, tier

    Raises:
        HTTPException: 403 if no valid auth, 401 if token invalid
    """
    # Priority 1: Cloudflare Access JWT (browser access via Cloudflare)
    if cf_jwt:
        try:
            return await _validate_cloudflare_jwt(cf_jwt)
        except HTTPException:
            raise
        except Exception as e:
            error_msg = str(e)
            logger.exception("Cloudflare JWT validation failed")

            if "does not exist" in error_msg.lower() or "relation" in error_msg.lower():
                raise HTTPException(
                    status_code=500,
                    detail=f"Database schema error: {error_msg}",
                ) from e

            if (
                "jwt" in error_msg.lower()
                or "token" in error_msg.lower()
                or "signature" in error_msg.lower()
            ):
                raise HTTPException(status_code=401, detail=f"Invalid JWT: {error_msg}") from e

            raise HTTPException(status_code=500, detail=f"Authentication error: {error_msg}") from e

    # Priority 2: Bearer token (API token for automation)
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user = await _validate_api_token(token)
        if user:
            logger.debug(f"API token authenticated: {user.email}")
            return user
        raise HTTPException(
            status_code=401,
            detail="Invalid API token. Generate a new token via POST /api/me/token",
        )

    # Priority 3: Internal network with user email header
    if _is_internal_request(request) and x_user_email:
        logger.debug(f"Internal network auth: {x_user_email}")
        return await _get_user_by_email(x_user_email)

    # Priority 4: DEV_MODE bypass (development only)
    if DEV_MODE:
        email = x_user_email or DEV_USER_EMAIL
        logger.info(f"DEV_MODE: Using email {email} without authentication")
        return await _get_user_by_email(email)

    # No valid authentication method found
    raise HTTPException(
        status_code=403,
        detail=(
            "Authentication required. Supported methods: "
            "(1) Cf-Access-Jwt-Assertion header for Cloudflare Access, "
            "(2) Authorization: Bearer <token> for API tokens, "
            "(3) X-User-Email header from internal Docker network. "
            "For local development, set DEV_MODE=true in environment."
        ),
    )


async def get_optional_user(
    request: Request,
    cf_jwt: str = Header(alias="Cf-Access-Jwt-Assertion", default=None),
    authorization: str = Header(alias="Authorization", default=None),
    x_user_email: str = Header(alias="X-User-Email", default=None),
) -> User | None:
    """
    Optional authentication - returns None instead of raising exception.

    Useful for endpoints that have different behavior for authenticated vs anonymous users.
    """
    try:
        return await get_current_user(request, cf_jwt, authorization, x_user_email)
    except HTTPException:
        return None
