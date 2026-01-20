"""Authentication and identity API endpoints."""

import logging
from datetime import datetime
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure
from server.config import settings
from services.auth.config import config
from services.auth.dependencies import get_current_user
from services.auth.models import (
    CalendarSummary,
    DataSummary,
    ImmichSummary,
    LoRASummary,
    RAGSummary,
    User,
    UserProfile,
)
from services.auth.services.auth_service import AuthService
from services.auth.services.token_service import TokenService
from services.database.supabase import SupabaseClient, SupabaseConfig
from services.external.immich import ImmichService
from services.storage.minio import MinIOClient, MinIOConfig

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = logging.getLogger(__name__)


# Pydantic models for token endpoints
class TokenCreateResponse(BaseModel):
    """Response when creating a new API token."""

    token: str = Field(
        ..., description="The API token. Store this securely - it cannot be retrieved again!"
    )
    created_at: str = Field(..., description="ISO timestamp when the token was created")
    message: str = Field(default="Token created successfully. Store it securely!")


class TokenInfoResponse(BaseModel):
    """Response for token info (without the actual token)."""

    has_token: bool = Field(..., description="Whether the user has an API token")
    created_at: str | None = Field(None, description="ISO timestamp when the token was created")
    token_prefix: str = Field(default="lat_", description="Token prefix for identification")


class TokenRevokeResponse(BaseModel):
    """Response when revoking a token."""

    revoked: bool = Field(..., description="Whether a token was revoked")
    message: str


class NamedTokenCreateRequest(BaseModel):
    """Request to create a named API token."""

    name: str = Field(..., description="Name for the token (must be unique per user)")
    scopes: list[str] = Field(
        default_factory=list, description="Optional list of scopes/permissions"
    )
    expires_in_days: int | None = Field(None, description="Optional expiration in days from now")


class NamedTokenResponse(BaseModel):
    """Response for a named token (without the actual token value)."""

    id: str
    name: str
    scopes: list[str]
    expires_at: str | None
    last_used_at: str | None
    created_at: str | None


class NamedTokenListResponse(BaseModel):
    """Response listing all named tokens."""

    tokens: list[NamedTokenResponse]
    total: int


# Helper to get database pool for token service
async def get_token_service() -> TokenService:
    """Get TokenService instance with database pool."""
    supabase_config = SupabaseConfig()
    pool = await asyncpg.create_pool(
        dsn=supabase_config.db_url,
        min_size=1,
        max_size=5,
    )
    return TokenService(pool)


# Helper functions for data summaries
async def get_mongodb_client() -> AsyncMongoClient | None:
    """Get MongoDB client instance."""
    try:
        client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        return client
    except (ConnectionFailure, Exception) as e:
        logger.warning(f"Failed to connect to MongoDB: {e}")
        return None


async def get_rag_summary(user: User, is_admin: bool) -> RAGSummary:
    """Get RAG data summary from MongoDB and Supabase."""
    mongodb_documents = 0
    mongodb_chunks = 0
    mongodb_sources = 0
    supabase_items = 0
    supabase_workflows = 0

    # MongoDB summary
    mongo_client = await get_mongodb_client()
    if mongo_client:
        try:
            db = mongo_client[settings.mongodb_database]
            documents_collection = db["documents"]
            chunks_collection = db["chunks"]
            sources_collection = db["sources"]

            # Build query filters for user-scoped data
            document_filter = {} if is_admin else {"user_email": user.email}

            # Count documents
            mongodb_documents = await documents_collection.count_documents(document_filter)

            # Count chunks - need to filter by user's documents
            if is_admin:
                mongodb_chunks = await chunks_collection.count_documents({})
            else:
                # Get all document IDs for this user
                user_document_ids = await documents_collection.find(
                    {"user_email": user.email}, {"_id": 1}
                ).to_list(length=None)
                user_doc_ids = [doc["_id"] for doc in user_document_ids]

                if user_doc_ids:
                    # Count chunks that belong to user's documents
                    mongodb_chunks = await chunks_collection.count_documents(
                        {"document_id": {"$in": user_doc_ids}}
                    )
                else:
                    mongodb_chunks = 0

            # Count sources - sources are aggregated from documents, so count unique sources from user's documents
            if is_admin:
                mongodb_sources = await sources_collection.count_documents({})
            else:
                # Get unique sources from user's documents
                pipeline = [
                    {"$match": {"user_email": user.email}},
                    {"$group": {"_id": "$source"}},
                    {"$count": "total"},
                ]
                result = await documents_collection.aggregate(pipeline).to_list(length=1)
                mongodb_sources = result[0]["total"] if result and result[0] else 0

            await mongo_client.close()
        except (ConnectionFailure, Exception) as e:
            logger.warning(f"Failed to get MongoDB summary: {e}")

    # Supabase summary
    try:
        supabase_service = SupabaseClient(SupabaseConfig())
        pool = await supabase_service._get_pool()

        async with pool.acquire() as conn:
            # Count items
            try:
                if is_admin:
                    row = await conn.fetchrow("SELECT COUNT(*) as count FROM items")
                else:
                    row = await conn.fetchrow(
                        "SELECT COUNT(*) as count FROM items WHERE owner_email = $1", user.email
                    )
                supabase_items = row["count"] if row else 0
            except (asyncpg.PostgresError, asyncpg.UndefinedTableError):
                # Table might not exist
                supabase_items = 0

            # Count workflows
            try:
                if is_admin:
                    row = await conn.fetchrow("SELECT COUNT(*) as count FROM comfyui_workflows")
                else:
                    user_id = user.id
                    row = await conn.fetchrow(
                        "SELECT COUNT(*) as count FROM comfyui_workflows WHERE user_id = $1",
                        user_id,
                    )
                supabase_workflows = row["count"] if row else 0
            except (asyncpg.PostgresError, asyncpg.UndefinedTableError):
                # Table might not exist
                supabase_workflows = 0

            # Count workflow runs
            try:
                if is_admin:
                    row = await conn.fetchrow("SELECT COUNT(*) as count FROM comfyui_workflow_runs")
                else:
                    user_id = user.id
                    row = await conn.fetchrow(
                        "SELECT COUNT(*) as count FROM comfyui_workflow_runs WHERE user_id = $1",
                        user_id,
                    )
                supabase_workflow_runs = row["count"] if row else 0
            except (asyncpg.PostgresError, asyncpg.UndefinedTableError):
                # Table might not exist
                supabase_workflow_runs = 0
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as e:
        logger.warning(f"Failed to get Supabase summary: {e}")
        supabase_workflow_runs = 0

    total_data_points = (
        mongodb_documents
        + mongodb_chunks
        + supabase_items
        + supabase_workflows
        + supabase_workflow_runs
    )

    return RAGSummary(
        mongodb_documents=mongodb_documents,
        mongodb_chunks=mongodb_chunks,
        mongodb_sources=mongodb_sources,
        supabase_items=supabase_items,
        supabase_workflows=supabase_workflows,
        supabase_workflow_runs=supabase_workflow_runs,
        total_data_points=total_data_points,
    )


async def get_immich_summary(user: User) -> ImmichSummary:
    """Get Immich data summary from user's account."""
    # Get user's Immich API key from their profile
    immich_api_key = user.__dict__.get("immich_api_key")

    if not immich_api_key:
        return ImmichSummary(
            total_photos=0,
            total_videos=0,
            total_albums=0,
            total_size_bytes=0,
            message="Immich account not linked. Log into datacrew.space to provision your account.",
        )

    try:
        immich_service = ImmichService(config)
        stats = await immich_service.get_user_statistics(immich_api_key)
        await immich_service.close()

        if stats is None:
            return ImmichSummary(
                total_photos=0,
                total_videos=0,
                total_albums=0,
                total_size_bytes=0,
                message="Failed to retrieve Immich statistics. Server may be unavailable.",
            )

        return ImmichSummary(
            total_photos=stats.get("total_photos", 0),
            total_videos=stats.get("total_videos", 0),
            total_albums=stats.get("total_albums", 0),
            total_size_bytes=stats.get("total_size_bytes", 0),
            message=None,
        )

    except Exception as e:
        logger.warning(f"Failed to get Immich summary for {user.email}: {e}")
        return ImmichSummary(
            total_photos=0,
            total_videos=0,
            total_albums=0,
            total_size_bytes=0,
            message=f"Error retrieving Immich statistics: {e!s}",
        )


async def get_loras_summary(user: User, is_admin: bool) -> LoRASummary:
    """Get LoRA models summary."""
    total_models = 0
    total_size_bytes = 0
    models = []

    try:
        supabase_service = SupabaseClient(SupabaseConfig())
        pool = await supabase_service._get_pool()

        async with pool.acquire() as conn:
            try:
                if is_admin:
                    rows = await conn.fetch(
                        """
                        SELECT id, name, filename, file_size, description, tags, created_at
                        FROM comfyui_lora_models
                        ORDER BY created_at DESC
                    """
                    )
                else:
                    user_id = user.id
                    rows = await conn.fetch(
                        """
                        SELECT id, name, filename, file_size, description, tags, created_at
                        FROM comfyui_lora_models
                        WHERE user_id = $1
                        ORDER BY created_at DESC
                    """,
                        user_id,
                    )

                total_models = len(rows)
                for row in rows:
                    file_size = row.get("file_size") or 0
                    total_size_bytes += file_size
                    models.append(
                        {
                            "id": str(row["id"]),
                            "name": row.get("name"),
                            "filename": row.get("filename"),
                            "file_size": file_size,
                            "description": row.get("description"),
                            "tags": row.get("tags", []),
                            "created_at": (
                                row.get("created_at").isoformat() if row.get("created_at") else None
                            ),
                        }
                    )
            except Exception as e:
                # Table might not exist
                logger.warning(f"Failed to get LoRA models: {e}")
    except Exception as e:
        logger.warning(f"Failed to get LoRA summary: {e}")

    return LoRASummary(total_models=total_models, total_size_bytes=total_size_bytes, models=models)


async def get_calendar_summary(user: User, is_admin: bool) -> CalendarSummary:
    """Get calendar events summary from MongoDB sync state."""
    total_events = 0
    events_by_calendar = {}
    calendars_count = 0
    last_synced_at = None

    mongo_client = await get_mongodb_client()
    if mongo_client:
        try:
            db = mongo_client[settings.mongodb_database]
            sync_state_collection = db["calendar_sync_state"]

            # Build query filter
            if is_admin:
                query = {"sync_status": "synced"}
            else:
                query = {"user_id": str(user.id), "sync_status": "synced"}

            # Get total count
            total_events = await sync_state_collection.count_documents(query)

            # Get counts grouped by calendar_id
            pipeline = [
                {"$match": query},
                {
                    "$group": {
                        "_id": "$gcal_calendar_id",
                        "count": {"$sum": 1},
                        "last_sync": {"$max": "$last_synced_at"},
                    }
                },
                {"$sort": {"count": -1}},
            ]

            async for doc in sync_state_collection.aggregate(pipeline):
                calendar_id_key = doc["_id"] or "primary"
                events_by_calendar[calendar_id_key] = doc["count"]

                # Track most recent sync timestamp
                doc_last_sync = doc.get("last_sync")
                if doc_last_sync:
                    if last_synced_at is None or doc_last_sync > last_synced_at:
                        last_synced_at = doc_last_sync

            calendars_count = len(events_by_calendar)

            await mongo_client.close()
        except Exception as e:
            logger.warning(f"Failed to get calendar summary: {e}")

    return CalendarSummary(
        total_events=total_events,
        events_by_calendar=events_by_calendar,
        calendars_count=calendars_count,
        last_synced_at=last_synced_at,
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(user: User = Depends(get_current_user)) -> UserProfile:
    """
    Get current user profile.

    Returns user information including UUID, email, role, tier, and enabled services.
    """
    # Determine services enabled based on user tier/role
    services_enabled: list[str] = ["supabase"]  # All users get Supabase

    if user.tier == "pro" or user.role == "admin":
        services_enabled.extend(["immich", "n8n"])

    return UserProfile(
        uid=user.id,
        email=user.email,
        role=user.role,
        tier=user.tier,
        services_enabled=services_enabled,
    )


@router.get("/me/data", response_model=DataSummary)
async def get_data_summary(user: User = Depends(get_current_user)) -> DataSummary:
    """
    Get summary of data across all services the user has access to.

    Returns aggregated statistics from RAG (MongoDB + Supabase), Immich, and LoRA models.
    """
    auth_service = AuthService(config)
    is_admin = await auth_service.is_admin(user.email)

    # Get summaries from all services
    rag_summary = await get_rag_summary(user, is_admin)
    immich_summary = await get_immich_summary(user)
    loras_summary = await get_loras_summary(user, is_admin)
    calendar_summary = await get_calendar_summary(user, is_admin)

    return DataSummary(
        rag=rag_summary, immich=immich_summary, loras=loras_summary, calendar=calendar_summary
    )


@router.get("/me/data/rag", response_model=RAGSummary)
async def get_rag_data_summary(user: User = Depends(get_current_user)) -> RAGSummary:
    """
    Get RAG data summary across MongoDB and Supabase.

    Returns document counts, chunk counts, and source information.
    """
    auth_service = AuthService(config)
    is_admin = await auth_service.is_admin(user.email)

    return await get_rag_summary(user, is_admin)


@router.get("/api/me/data/immich", response_model=ImmichSummary)
async def get_immich_data_summary(user: User = Depends(get_current_user)) -> ImmichSummary:
    """
    Get Immich data summary.

    Returns photo/video counts and storage information.
    """
    return await get_immich_summary(user)


@router.get("/me/data/loras", response_model=LoRASummary)
async def get_loras_data_summary(user: User = Depends(get_current_user)) -> LoRASummary:
    """
    Get LoRA models summary.

    Returns count and metadata for all LoRA models the user has access to.
    """
    auth_service = AuthService(config)
    is_admin = await auth_service.is_admin(user.email)

    return await get_loras_summary(user, is_admin)


@router.get("/me/data/calendar", response_model=CalendarSummary)
async def get_calendar_data_summary(user: User = Depends(get_current_user)) -> CalendarSummary:
    """
    Get calendar events summary.

    Returns count of synced calendar events grouped by calendar ID.
    Regular users see only their own events, admin users see all events.
    """
    auth_service = AuthService(config)
    is_admin = await auth_service.is_admin(user.email)

    return await get_calendar_summary(user, is_admin)


@router.get("/me/immich/api-key")
async def get_immich_api_key(user: User = Depends(get_current_user)) -> dict[str, str | None]:
    """
    Get Immich API key for the current user.

    Returns the user's Immich API key if it exists. If it doesn't exist yet,
    attempts to provision the user and generate an API key on-demand.

    Returns:
        Dictionary with 'api_key' field (or None if provisioning fails)
    """
    supabase_service = SupabaseClient(SupabaseConfig())
    immich_user_id, immich_api_key = await supabase_service.get_immich_credentials(user.email)

    # If API key doesn't exist, try to provision on-demand
    if not immich_api_key:
        try:
            immich_service = ImmichService(config)
            immich_user_id, immich_api_key = await immich_service.provision_user(
                user.email, str(user.id)
            )
            await supabase_service.update_immich_credentials(
                user.email, immich_user_id, immich_api_key
            )
        except Exception as e:
            logger.warning(f"Failed to provision Immich user on-demand for {user.email}: {e}")
            immich_api_key = None

    return {"api_key": immich_api_key}


@router.post("/me/discord/link")
async def link_discord_account(
    discord_user_id: str, user: User = Depends(get_current_user)
) -> dict[str, str]:
    """
    Link Discord account to Cloudflare-authenticated user.

    Args:
        discord_user_id: Discord user ID to link

    Returns:
        Success message
    """
    supabase_service = SupabaseClient(SupabaseConfig())
    await supabase_service.update_discord_user_id(user.email, discord_user_id)

    return {"message": f"Discord account {discord_user_id} linked to {user.email}"}


@router.get("/user/by-discord/{discord_user_id}")
async def get_user_by_discord_id(
    discord_user_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str | None]:
    """
    Get user by Discord ID for service-to-service lookups.

    This endpoint allows the Discord bot to lookup users by their Discord ID
    to retrieve their Immich API key for user-specific uploads.

    Authentication (any of these):
    - Bearer token (LAMBDA_API_TOKEN) - for external access
    - Internal network request (X-User-Email header) - Docker internal network

    Args:
        discord_user_id: Discord user ID to lookup

    Returns:
        Dictionary with user email and immich_api_key (or None if not set)

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 404: If no user found with this Discord ID
    """
    # Authentication is handled by get_current_user dependency
    # If we reach here, the request is authenticated

    supabase_service = SupabaseClient(SupabaseConfig())
    user = await supabase_service.get_user_by_discord_id(discord_user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"No user found with Discord ID {discord_user_id}. "
            "User must link their Discord account first via /api/v1/auth/me/discord/link",
        )

    return {
        "email": user.email,
        "immich_api_key": user.__dict__.get("immich_api_key"),
    }


# ============================================================================
# API Token Management Endpoints
# ============================================================================


@router.post("/me/token", response_model=TokenCreateResponse)
async def create_api_token(
    user: User = Depends(get_current_user),
    token_service: TokenService = Depends(get_token_service),
) -> TokenCreateResponse:
    """
    Create or regenerate the primary API token for the current user.

    This creates a new API token that can be used for headless automation
    (scripts, n8n workflows, external webhooks) without requiring Cloudflare
    Access authentication.

    **Important**: The token is only returned once. Store it securely!
    If you lose it, you'll need to generate a new one (which invalidates the old one).

    Usage:
    ```
    curl -H "Authorization: Bearer lat_xxx..." https://api.example.com/api/v1/...
    ```

    Returns:
        TokenCreateResponse with the new token
    """
    token = await token_service.create_primary_token(user.id)
    created_at = datetime.utcnow().isoformat() + "Z"

    logger.info(f"Created API token for user {user.email}")

    return TokenCreateResponse(
        token=token,
        created_at=created_at,
        message="Token created successfully. Store it securely - it cannot be retrieved again!",
    )


@router.get("/me/token", response_model=TokenInfoResponse)
async def get_api_token_info(
    user: User = Depends(get_current_user),
    token_service: TokenService = Depends(get_token_service),
) -> TokenInfoResponse:
    """
    Get information about the current user's API token.

    Returns whether a token exists and when it was created.
    Does NOT return the actual token value (that's only shown on creation).
    """
    info = await token_service.get_primary_token_info(user.id)

    if info is None:
        return TokenInfoResponse(has_token=False, created_at=None)

    return TokenInfoResponse(
        has_token=info["has_token"],
        created_at=info.get("created_at"),
        token_prefix=info.get("token_prefix", "lat_"),
    )


@router.delete("/me/token", response_model=TokenRevokeResponse)
async def revoke_api_token(
    user: User = Depends(get_current_user),
    token_service: TokenService = Depends(get_token_service),
) -> TokenRevokeResponse:
    """
    Revoke the current user's API token.

    After revocation, the token can no longer be used for authentication.
    You can create a new token using POST /api/me/token.
    """
    revoked = await token_service.revoke_primary_token(user.id)

    if revoked:
        logger.info(f"Revoked API token for user {user.email}")
        return TokenRevokeResponse(revoked=True, message="Token revoked successfully")
    return TokenRevokeResponse(revoked=False, message="No token to revoke")


# ============================================================================
# Named Tokens (Multiple tokens with names/scopes)
# ============================================================================


@router.post("/me/tokens", response_model=TokenCreateResponse)
async def create_named_token(
    request: NamedTokenCreateRequest,
    user: User = Depends(get_current_user),
    token_service: TokenService = Depends(get_token_service),
) -> TokenCreateResponse:
    """
    Create a named API token with optional scopes and expiration.

    Named tokens allow you to have multiple tokens for different purposes,
    each with its own name, optional scopes, and optional expiration.

    Example use cases:
    - "n8n-production" for n8n workflow automation
    - "github-actions" for CI/CD pipelines
    - "dev-testing" for development with short expiration

    Args:
        request: Token creation request with name, scopes, and optional expiration

    Returns:
        TokenCreateResponse with the new token
    """
    from datetime import timedelta

    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    try:
        token = await token_service.create_named_token(
            user_id=user.id,
            name=request.name,
            scopes=request.scopes,
            expires_at=expires_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    created_at = datetime.utcnow().isoformat() + "Z"
    logger.info(f"Created named token '{request.name}' for user {user.email}")

    return TokenCreateResponse(
        token=token,
        created_at=created_at,
        message=f"Named token '{request.name}' created. Store it securely!",
    )


@router.get("/me/tokens", response_model=NamedTokenListResponse)
async def list_named_tokens(
    user: User = Depends(get_current_user),
    token_service: TokenService = Depends(get_token_service),
) -> NamedTokenListResponse:
    """
    List all named tokens for the current user.

    Returns token metadata (name, scopes, expiration, last used) but NOT
    the actual token values.
    """
    tokens = await token_service.list_named_tokens(user.id)

    return NamedTokenListResponse(
        tokens=[
            NamedTokenResponse(
                id=t["id"],
                name=t["name"],
                scopes=t["scopes"],
                expires_at=t["expires_at"],
                last_used_at=t["last_used_at"],
                created_at=t["created_at"],
            )
            for t in tokens
        ],
        total=len(tokens),
    )


@router.delete("/me/tokens/{token_id}", response_model=TokenRevokeResponse)
async def revoke_named_token_by_id(
    token_id: UUID,
    user: User = Depends(get_current_user),
    token_service: TokenService = Depends(get_token_service),
) -> TokenRevokeResponse:
    """
    Revoke a named token by its ID.

    Args:
        token_id: UUID of the token to revoke
    """
    revoked = await token_service.revoke_named_token(user.id, token_id)

    if revoked:
        logger.info(f"Revoked named token {token_id} for user {user.email}")
        return TokenRevokeResponse(revoked=True, message="Named token revoked successfully")
    raise HTTPException(status_code=404, detail="Token not found")


@router.delete("/me/tokens/name/{token_name}", response_model=TokenRevokeResponse)
async def revoke_named_token_by_name(
    token_name: str,
    user: User = Depends(get_current_user),
    token_service: TokenService = Depends(get_token_service),
) -> TokenRevokeResponse:
    """
    Revoke a named token by its name.

    Args:
        token_name: Name of the token to revoke
    """
    revoked = await token_service.revoke_named_token_by_name(user.id, token_name)

    if revoked:
        logger.info(f"Revoked named token '{token_name}' for user {user.email}")
        return TokenRevokeResponse(revoked=True, message=f"Named token '{token_name}' revoked")
    raise HTTPException(status_code=404, detail=f"Token '{token_name}' not found")


# ============================================================================
# Test-only endpoints for data isolation testing
# ============================================================================


@router.get("/test/my-data")
async def test_my_data(
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(lambda: AuthService(config)),
    supabase_service: SupabaseClient = Depends(lambda: SupabaseClient(SupabaseConfig())),
):
    """
    Test endpoint for data isolation - returns HTML table of user's Supabase items.

    This is a test-only endpoint used by test_data_isolation.py.
    """
    from fastapi.responses import HTMLResponse

    is_admin = await auth_service.is_admin(user.email)

    # Query Supabase items with RLS filtering
    pool = await supabase_service._get_pool()
    async with pool.acquire() as conn:
        if is_admin:
            # Admin sees all items
            rows = await conn.fetch("SELECT * FROM test_items ORDER BY name")
        else:
            # Regular users see only their own items
            rows = await conn.fetch(
                "SELECT * FROM test_items WHERE owner_email = $1 ORDER BY name",
                user.email,
            )

    # Build HTML table
    html = "<html><body><h1>My Data</h1><table border='1'><tr><th>ID</th><th>Name</th><th>Data</th><th>Owner</th></tr>"
    if rows:
        for row in rows:
            html += f"<tr><td>{row['id']}</td><td>{row['name']}</td><td>{row['data']}</td><td>{row['owner_email']}</td></tr>"
    else:
        html += "<tr><td colspan='4'>No items found</td></tr>"
    html += "</table></body></html>"

    return HTMLResponse(content=html)


@router.get("/test/my-images")
async def test_my_images(
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(lambda: AuthService(config)),
    minio_service: MinIOClient = Depends(lambda: MinIOClient(MinIOConfig())),
):
    """
    Test endpoint for image isolation - returns HTML gallery of user's images.

    This is a test-only endpoint used by test_data_isolation.py.
    """
    from fastapi.responses import HTMLResponse

    is_admin = await auth_service.is_admin(user.email)

    # Get S3 client
    s3_client = minio_service._get_s3_client()

    # List objects with user filtering
    # Use "user-data" bucket to match MinIOService
    bucket_name = "user-data"
    if is_admin:
        # Admin sees all images
        response = s3_client.list_objects_v2(Bucket=bucket_name)
    else:
        # Regular users see only their folder
        user_prefix = f"user-{user.id}/"
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=user_prefix)

    # Filter for image files only
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
    images = [
        obj
        for obj in response.get("Contents", [])
        if any(obj["Key"].lower().endswith(ext) for ext in image_extensions)
    ]

    # Generate presigned URLs
    html = "<html><body><h1>My Images</h1><div>"
    if images:
        for img in images:
            presigned_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": img["Key"]},
                ExpiresIn=3600,
            )
            html += f'<img src="{presigned_url}" alt="{img["Key"]}" style="max-width:200px; margin:10px;" />'
    else:
        html += "<p>No images found</p>"
    html += "</div></body></html>"

    return HTMLResponse(content=html)
