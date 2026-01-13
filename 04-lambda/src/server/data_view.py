"""Data viewing API endpoints for all storage layers."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from pymongo import AsyncMongoClient
from services.auth.config import config
from services.auth.dependencies import User, get_current_user
from src.services.auth.services.auth_service import AuthService
from src.services.database.neo4j import Neo4jClient
from src.services.database.supabase import SupabaseClient, SupabaseConfig
from src.services.storage.minio import MinIOClient, MinIOConfig

from server.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


# Response Models
class StorageFileResponse(BaseModel):
    """Response model for storage file metadata."""

    key: str
    filename: str
    size: int
    last_modified: str
    etag: str


class StorageDataResponse(BaseModel):
    """Response model for storage endpoint."""

    files: list[StorageFileResponse]
    count: int
    prefix: str | None = None
    user_id: str


class SupabaseItemResponse(BaseModel):
    """Response model for Supabase item."""

    id: str
    owner_email: str
    name: str
    data: dict[str, Any] | None = None
    created_at: str


class SupabaseDataResponse(BaseModel):
    """Response model for Supabase endpoint."""

    table: str
    items: list[SupabaseItemResponse]
    count: int
    page: int = 1
    per_page: int = 100


class Neo4jNodeResponse(BaseModel):
    """Response model for Neo4j node."""

    id: str
    labels: list[str]
    properties: dict[str, Any]


class Neo4jRelationshipResponse(BaseModel):
    """Response model for Neo4j relationship."""

    id: str
    type: str
    start_node_id: str
    end_node_id: str
    properties: dict[str, Any]


class Neo4jDataResponse(BaseModel):
    """Response model for Neo4j endpoint."""

    nodes: list[Neo4jNodeResponse]
    relationships: list[Neo4jRelationshipResponse]
    node_count: int
    relationship_count: int
    node_type: str | None = None


class MongoDBDocumentResponse(BaseModel):
    """Response model for MongoDB document."""

    id: str
    collection: str
    data: dict[str, Any]


class MongoDBDataResponse(BaseModel):
    """Response model for MongoDB endpoint."""

    collection: str
    documents: list[MongoDBDocumentResponse]
    count: int
    page: int = 1
    per_page: int = 100


# Helper Functions
async def get_auth_service() -> AuthService:
    """Get AuthService instance."""
    return AuthService(config)


async def get_supabase_service() -> SupabaseClient:
    """Get SupabaseClient instance."""
    config = SupabaseConfig()
    return SupabaseClient(config)


async def get_neo4j_service() -> Neo4jClient:
    """Get Neo4jClient instance."""
    return Neo4jClient()


async def get_minio_service() -> MinIOClient:
    """Get MinIOClient instance."""
    minio_config = MinIOConfig()
    return MinIOClient(minio_config)


async def get_mongodb_client() -> AsyncMongoClient:
    """Get MongoDB client instance."""
    return AsyncMongoClient(settings.mongodb_uri)


# Endpoints
@router.get("/storage", response_model=StorageDataResponse)
async def view_storage_data(
    prefix: str | None = Query(None, description="Prefix to filter files (e.g., 'loras/')"),
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    minio_service: MinIOService = Depends(get_minio_service),
):
    """
    View MinIO/blob storage files for the authenticated user.

    **Query Parameters:**
    - `prefix` (optional): Filter files by prefix (e.g., "loras/" for LoRA models)

    **Response:**
    Returns list of files with metadata. Admin users see all files from all users.

    **Example Usage:**
    ```bash
    # List all files
    curl http://localhost:8000/api/v1/data/storage

    # List files with prefix
    curl "http://localhost:8000/api/v1/data/storage?prefix=loras/"
    ```
    """
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    is_admin = await auth_service.is_admin(user.email)

    try:
        if is_admin:
            # Admin users: list all files from all user folders
            # We need to list all objects and filter by user prefix pattern
            s3_client = minio_service._get_s3_client()
            bucket_name = "user-data"

            import asyncio

            loop = asyncio.get_event_loop()

            def list_all_objects():
                response = s3_client.list_objects_v2(
                    Bucket=bucket_name, Prefix=prefix if prefix else "", MaxKeys=1000
                )
                return response.get("Contents", [])

            objects = await loop.run_in_executor(None, list_all_objects)

            # Filter out .keep files
            files = []
            for obj in objects:
                if obj["Key"].endswith("/.keep"):
                    continue

                # Extract user_id from key (format: user-{uuid}/...)
                key_parts = obj["Key"].split("/")
                if len(key_parts) > 0 and key_parts[0].startswith("user-"):
                    key_parts[0][5:]  # Remove 'user-' prefix
                    filename = "/".join(key_parts[1:]) if len(key_parts) > 1 else key_parts[0]
                else:
                    continue

                files.append(
                    StorageFileResponse(
                        key=obj["Key"],
                        filename=filename,
                        size=obj["Size"],
                        last_modified=obj["LastModified"].isoformat(),
                        etag=obj["ETag"].strip('"'),
                    )
                )
        else:
            # Regular users: list only their files
            files_data = await minio_service.list_files(user_id=user_id, prefix=prefix)
            files = [
                StorageFileResponse(
                    key=file_dict["key"],
                    filename=file_dict["filename"],
                    size=file_dict["size"],
                    last_modified=file_dict["last_modified"],
                    etag=file_dict["etag"],
                )
                for file_dict in files_data
            ]

        return StorageDataResponse(
            files=files, count=len(files), prefix=prefix, user_id=str(user_id)
        )
    except Exception as e:
        logger.exception("Failed to list storage files")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {e!s}") from e


@router.get("/supabase", response_model=SupabaseDataResponse)
async def view_supabase_data(
    table: str = Query("items", description="Table name to query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=1000, description="Items per page"),
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    supabase_service: SupabaseService = Depends(get_supabase_service),
):
    """
    View Supabase table data for the authenticated user.

    **Query Parameters:**
    - `table` (default: "items"): Table name to query
    - `page` (default: 1): Page number (1-indexed)
    - `per_page` (default: 100, max: 1000): Items per page

    **Response:**
    Returns paginated items from the specified table. Admin users see all rows.

    **Example Usage:**
    ```bash
    # List items from default table
    curl http://localhost:8000/api/v1/data/supabase

    # List items from specific table with pagination
    curl "http://localhost:8000/api/v1/data/supabase?table=items&page=1&per_page=50"
    ```
    """
    is_admin = await auth_service.is_admin(user.email)
    pool = await supabase_service._get_pool()

    try:
        async with pool.acquire() as conn:
            # Ensure table exists (for items table)
            if table == "items":
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS items (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        owner_email TEXT NOT NULL,
                        name TEXT NOT NULL,
                        data JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """
                )

                await conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_items_owner_email ON items(owner_email)
                """
                )

            # Build query based on admin status
            offset = (page - 1) * per_page

            if is_admin:
                # Admin: see all rows
                rows = await conn.fetch(
                    f"""
                    SELECT id, owner_email, name, data, created_at
                    FROM {table}
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                """,
                    per_page,
                    offset,
                )

                # Get total count
                count_row = await conn.fetchrow(
                    f"""
                    SELECT COUNT(*) as count FROM {table}
                """
                )
                total_count = count_row["count"] if count_row else 0
            else:
                # Regular user: filter by owner_email
                rows = await conn.fetch(
                    f"""
                    SELECT id, owner_email, name, data, created_at
                    FROM {table}
                    WHERE owner_email = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                """,
                    user.email,
                    per_page,
                    offset,
                )

                # Get total count for user
                count_row = await conn.fetchrow(
                    f"""
                    SELECT COUNT(*) as count FROM {table} WHERE owner_email = $1
                """,
                    user.email,
                )
                total_count = count_row["count"] if count_row else 0

            items = [
                SupabaseItemResponse(
                    id=str(row["id"]),
                    owner_email=row["owner_email"],
                    name=row["name"],
                    data=dict(row["data"]) if row["data"] else None,
                    created_at=row["created_at"].isoformat() if row["created_at"] else "",
                )
                for row in rows
            ]

            return SupabaseDataResponse(
                table=table, items=items, count=total_count, page=page, per_page=per_page
            )
    except Exception as e:
        logger.exception("Failed to fetch Supabase data")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e!s}") from e


@router.get("/neo4j", response_model=Neo4jDataResponse)
async def view_neo4j_data(
    node_type: str | None = Query(None, description="Filter by node type/label (e.g., 'Document')"),
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    neo4j_service: Neo4jClient = Depends(get_neo4j_service),
):
    """
    View Neo4j nodes and relationships for the authenticated user.

    **Query Parameters:**
    - `node_type` (optional): Filter by node type/label (e.g., "Document", "User")

    **Response:**
    Returns nodes and relationships. Admin users see all nodes.

    **Example Usage:**
    ```bash
    # List all user's nodes
    curl http://localhost:8000/api/v1/data/neo4j

    # Filter by node type
    curl "http://localhost:8000/api/v1/data/neo4j?node_type=Document"
    ```
    """
    is_admin = await auth_service.is_admin(user.email)
    driver = await neo4j_service._get_driver()

    try:
        async with driver.session() as session:
            # Build query based on admin status and node type filter
            if is_admin:
                if node_type:
                    query = f"""
                        MATCH (n:{node_type})
                        OPTIONAL MATCH (n)-[r]->(m)
                        RETURN n, labels(n) as labels, r, startNode(r) as start_node, endNode(r) as end_node
                        LIMIT 1000
                    """
                else:
                    query = """
                        MATCH (n)
                        OPTIONAL MATCH (n)-[r]->(m)
                        RETURN n, labels(n) as labels, r, startNode(r) as start_node, endNode(r) as end_node
                        LIMIT 1000
                    """
            # Regular user: anchor to user node
            elif node_type:
                query = f"""
                        MATCH (u:User {{email: $email}})
                        OPTIONAL MATCH (u)-[*0..2]-(n:{node_type})
                        OPTIONAL MATCH (n)-[r]->(m)
                        WHERE n IS NOT NULL
                        RETURN DISTINCT n, labels(n) as labels, r, startNode(r) as start_node, endNode(r) as end_node
                        LIMIT 1000
                    """
            else:
                query = """
                        MATCH (u:User {email: $email})
                        OPTIONAL MATCH (u)-[*0..2]-(n)
                        OPTIONAL MATCH (n)-[r]->(m)
                        WHERE n IS NOT NULL
                        RETURN DISTINCT n, labels(n) as labels, r, startNode(r) as start_node, endNode(r) as end_node
                        LIMIT 1000
                    """

            result = await session.run(query, email=user.email)
            records = await result.values()

            nodes = []
            relationships = []
            seen_node_ids = set()
            seen_rel_ids = set()

            for record in records:
                node = record[0]
                labels = record[1] if len(record) > 1 else []
                rel = record[2] if len(record) > 2 else None
                start_node = record[3] if len(record) > 3 else None
                end_node = record[4] if len(record) > 4 else None

                # Process node
                if node and node.id not in seen_node_ids:
                    seen_node_ids.add(node.id)
                    nodes.append(
                        Neo4jNodeResponse(
                            id=str(node.id),
                            labels=list(labels) if labels else [],
                            properties=dict(node) if node else {},
                        )
                    )

                # Process relationship
                if rel and rel.id not in seen_rel_ids:
                    seen_rel_ids.add(rel.id)
                    relationships.append(
                        Neo4jRelationshipResponse(
                            id=str(rel.id),
                            type=rel.type if hasattr(rel, "type") else "",
                            start_node_id=str(start_node.id) if start_node else "",
                            end_node_id=str(end_node.id) if end_node else "",
                            properties=dict(rel) if rel else {},
                        )
                    )

            return Neo4jDataResponse(
                nodes=nodes,
                relationships=relationships,
                node_count=len(nodes),
                relationship_count=len(relationships),
                node_type=node_type,
            )
    except Exception as e:
        logger.exception("Failed to fetch Neo4j data")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e!s}") from e


@router.get("/mongodb", response_model=MongoDBDataResponse)
async def view_mongodb_data(
    collection: str = Query("documents", description="Collection name to query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=1000, description="Documents per page"),
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    mongo_client: AsyncMongoClient = Depends(get_mongodb_client),
):
    """
    View MongoDB collection data for the authenticated user.

    **Query Parameters:**
    - `collection` (default: "documents"): Collection name to query
    - `page` (default: 1): Page number (1-indexed)
    - `per_page` (default: 100, max: 1000): Documents per page

    **Response:**
    Returns paginated documents from the specified collection.
    Filters by user_id or user_email fields if present. Admin users see all documents.

    **Example Usage:**
    ```bash
    # List documents from default collection
    curl http://localhost:8000/api/v1/data/mongodb

    # List documents from specific collection with pagination
    curl "http://localhost:8000/api/v1/data/mongodb?collection=memory_messages&page=1&per_page=50"
    ```
    """
    is_admin = await auth_service.is_admin(user.email)
    db = mongo_client[settings.mongodb_database]
    coll = db[collection]

    try:
        # Build query filter based on admin status
        if is_admin:
            query_filter = {}
        else:
            # Regular user: filter by user_id or user_email
            # Try user_id first (UUID string), then user_email
            query_filter = {
                "$or": [
                    {"user_id": str(user.id)},
                    {"user_email": user.email},
                    {"metadata.user_id": str(user.id)},
                    {"metadata.user_email": user.email},
                ]
            }

        # Calculate skip
        skip = (page - 1) * per_page

        # Query documents
        cursor = coll.find(query_filter).skip(skip).limit(per_page).sort("_id", -1)
        documents = await cursor.to_list(length=per_page)

        # Get total count
        total_count = await coll.count_documents(query_filter)

        # Format documents
        formatted_docs = []
        for doc in documents:
            doc_id = str(doc.pop("_id", ""))
            formatted_docs.append(
                MongoDBDocumentResponse(id=doc_id, collection=collection, data=doc)
            )

        return MongoDBDataResponse(
            collection=collection,
            documents=formatted_docs,
            count=total_count,
            page=page,
            per_page=per_page,
        )
    except Exception as e:
        logger.exception("Failed to fetch MongoDB data")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e!s}") from e
