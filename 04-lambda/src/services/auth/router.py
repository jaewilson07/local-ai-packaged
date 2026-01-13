"""Authentication and identity API endpoints."""

import logging

import asyncpg
from fastapi import APIRouter, Depends
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure
from src.services.auth.config import config
from src.services.auth.dependencies import get_current_user
from src.services.auth.models import (
    CalendarSummary,
    DataSummary,
    ImmichSummary,
    LoRASummary,
    RAGSummary,
    User,
    UserProfile,
)
from src.services.auth.services.auth_service import AuthService
from src.services.database.supabase import SupabaseClient, SupabaseConfig
from src.services.external.immich import ImmichService
from src.services.storage.minio import MinIOClient, MinIOConfig

from server.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


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
    """Get Immich data summary (placeholder for now)."""
    # TODO: Implement Immich API integration
    return ImmichSummary(
        total_photos=0,
        total_videos=0,
        total_albums=0,
        total_size_bytes=0,
        message="Immich API integration not yet implemented",
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


@router.get("/api/me", response_model=UserProfile)
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


@router.get("/api/me/data", response_model=DataSummary)
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


@router.get("/api/me/data/rag", response_model=RAGSummary)
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


@router.get("/api/me/data/loras", response_model=LoRASummary)
async def get_loras_data_summary(user: User = Depends(get_current_user)) -> LoRASummary:
    """
    Get LoRA models summary.

    Returns count and metadata for all LoRA models the user has access to.
    """
    auth_service = AuthService(config)
    is_admin = await auth_service.is_admin(user.email)

    return await get_loras_summary(user, is_admin)


@router.get("/api/me/data/calendar", response_model=CalendarSummary)
async def get_calendar_data_summary(user: User = Depends(get_current_user)) -> CalendarSummary:
    """
    Get calendar events summary.

    Returns count of synced calendar events grouped by calendar ID.
    Regular users see only their own events, admin users see all events.
    """
    auth_service = AuthService(config)
    is_admin = await auth_service.is_admin(user.email)

    return await get_calendar_summary(user, is_admin)


@router.get("/api/me/immich/api-key")
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


@router.post("/api/me/discord/link")
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
