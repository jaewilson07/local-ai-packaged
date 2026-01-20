"""
ControlNet skeleton management service
"""

import logging
from datetime import datetime, timedelta
from io import BytesIO
from uuid import UUID

import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from PIL import Image
from server.projects.auth.models import User
from server.projects.controlnet_skeleton.config import get_controlnet_config
from server.projects.controlnet_skeleton.models import (
    ControlNetSkeleton,
    ControlNetSkeletonCreate,
    ControlNetSkeletonUpdate,
    PreprocessorType,
    SkeletonMetadata,
    SkeletonSearchRequest,
    SkeletonSearchResult,
    SkeletonSearchResponse,
    VisionAnalysisResult,
)
from server.projects.controlnet_skeleton.vision_service import VisionAnalysisService
from services.storage.minio import MinIOClient
from supabase import Client as SupabaseClient

logger = logging.getLogger(__name__)


class ControlNetSkeletonService:
    """Service for managing ControlNet skeletons"""

    def __init__(
        self,
        supabase: SupabaseClient,
        minio: MinIOClient,
        mongo_client: AsyncIOMotorClient,
    ):
        self.supabase = supabase
        self.minio = minio
        self.mongo = mongo_client
        self.config = get_controlnet_config()
        self.vision_service = VisionAnalysisService()

        # MongoDB collection
        self.db = self.mongo[self.config.mongodb_database]
        self.collection = self.db[self.config.skeleton_collection]

    async def download_image_from_url(self, url: str) -> bytes:
        """Download image from URL"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def create_skeleton_from_url(
        self,
        user: User,
        image_url: str,
        name: str,
        preprocessor_type: PreprocessorType,
        description: str | None = None,
        auto_analyze: bool = True,
        is_public: bool = True,
    ) -> ControlNetSkeleton:
        """
        Create a skeleton from an image URL

        Args:
            user: Current user
            image_url: URL of the source image
            name: Name for the skeleton
            preprocessor_type: Type of preprocessor to use
            description: Optional description (auto-generated if None and auto_analyze=True)
            auto_analyze: Whether to auto-analyze image with vision model
            is_public: Whether skeleton is public

        Returns:
            Created skeleton
        """
        logger.info(f"Creating skeleton from URL: {image_url}")

        # Download image
        image_data = await self.download_image_from_url(image_url)

        # Auto-analyze if requested
        vision_analysis = None
        if auto_analyze:
            logger.info("Running vision analysis...")
            vision_analysis = await self.vision_service.analyze_image(image_data, context=name)

            # Use vision-generated description if none provided
            if not description and vision_analysis.description:
                description = vision_analysis.description

        # Process image with ControlNet preprocessor
        logger.info(f"Processing with {preprocessor_type.value} preprocessor...")
        processed_image_data = await self._run_preprocessor(image_data, preprocessor_type)

        # Get image dimensions
        dimensions = self.vision_service.get_image_dimensions(processed_image_data)

        # Upload to MinIO
        object_key = f"{self.config.skeleton_path_prefix}/{name.replace(' ', '_')}-{preprocessor_type.value}.png"
        minio_path = await self.minio.upload_file(
            user_id=user.uid,
            file_data=processed_image_data,
            object_key=object_key,
            content_type="image/png",
            metadata={
                "type": "controlnet_skeleton",
                "preprocessor": preprocessor_type.value,
                "source_url": image_url,
            },
        )
        logger.info(f"Uploaded to MinIO: {minio_path}")

        # Build metadata
        metadata = SkeletonMetadata(
            image_dimensions=dimensions,
            original_image_url=image_url,
            vision_analysis=vision_analysis.model_dump() if vision_analysis else None,
        )

        # Extract tags from vision analysis
        tags = vision_analysis.tags if vision_analysis else []
        tags.append(preprocessor_type.value)  # Add preprocessor as tag

        # Generate embedding from description
        embedding_id = None
        if description:
            embedding_id = await self._create_mongodb_document(
                user=user,
                description=description,
                tags=tags,
                preprocessor_type=preprocessor_type,
                minio_path=minio_path,
                metadata=metadata,
            )

        # Create Supabase record
        skeleton_data = {
            "user_id": str(user.uid),
            "name": name,
            "description": description,
            "minio_path": minio_path,
            "preprocessor_type": preprocessor_type.value,
            "tags": tags,
            "embedding_id": embedding_id,
            "is_public": is_public,
            "metadata": metadata.model_dump(),
        }

        result = self.supabase.table("comfyui_controlnet_skeletons").insert(skeleton_data).execute()

        if not result.data:
            raise Exception("Failed to create skeleton in database")

        logger.info(f"Created skeleton: {result.data[0]['id']}")
        return ControlNetSkeleton.model_validate(result.data[0])

    async def _run_preprocessor(
        self, image_data: bytes, preprocessor_type: PreprocessorType
    ) -> bytes:
        """
        Run ControlNet preprocessor on image

        For now, this is a placeholder that returns the original image.
        In production, this should call ComfyUI API to run the actual preprocessor.

        TODO: Implement ComfyUI preprocessor workflow execution
        """
        logger.warning(
            f"Preprocessor {preprocessor_type.value} not yet implemented - returning original image"
        )

        # Convert to PNG if needed
        try:
            image = Image.open(BytesIO(image_data))
            output = BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
        except Exception as e:
            logger.error(f"Image conversion failed: {e}")
            return image_data

    async def _create_mongodb_document(
        self,
        user: User,
        description: str,
        tags: list[str],
        preprocessor_type: PreprocessorType,
        minio_path: str,
        metadata: SkeletonMetadata,
    ) -> str:
        """Create MongoDB document with embedding"""
        from capabilities.retrieval.mongo_rag.ingestion.embedder import EmbeddingGenerator

        # Generate embedding
        embedder = EmbeddingGenerator(model=self.config.embedding_model)
        embedding = await embedder.generate_embedding(description)

        # Insert into MongoDB
        doc = {
            "user_id": str(user.uid),
            "user_email": user.email,
            "description": description,
            "tags": tags,
            "preprocessor_type": preprocessor_type.value,
            "embedding": embedding,
            "minio_path": minio_path,
            "metadata": metadata.model_dump(),
            "is_public": True,
            "created_at": datetime.utcnow(),
        }

        result = await self.collection.insert_one(doc)
        logger.info(f"Created MongoDB document: {result.inserted_id}")
        return str(result.inserted_id)

    async def search_skeletons(
        self, user: User, search_request: SkeletonSearchRequest
    ) -> SkeletonSearchResponse:
        """
        Search for skeletons using semantic or hybrid search

        Args:
            user: Current user
            search_request: Search parameters

        Returns:
            Search results with similarity scores
        """
        from capabilities.retrieval.mongo_rag.ingestion.embedder import EmbeddingGenerator

        # Generate query embedding
        embedder = EmbeddingGenerator(model=self.config.embedding_model)
        query_embedding = await embedder.generate_embedding(search_request.query)

        # Build search pipeline based on search type
        if search_request.search_type == "semantic":
            pipeline = await self._build_vector_search_pipeline(
                query_embedding, search_request, user
            )
        elif search_request.search_type == "text":
            pipeline = await self._build_text_search_pipeline(search_request, user)
        else:  # hybrid
            pipeline = await self._build_hybrid_search_pipeline(
                query_embedding, search_request, user
            )

        # Execute search
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=search_request.match_count)

        # Convert to response objects
        search_results = []
        for result in results:
            # Get Supabase skeleton data
            skeleton_response = (
                self.supabase.table("comfyui_controlnet_skeletons")
                .select("*")
                .eq("embedding_id", str(result["_id"]))
                .execute()
            )

            if skeleton_response.data:
                skeleton = ControlNetSkeleton.model_validate(skeleton_response.data[0])

                # Generate presigned URL for preview
                preview_url = await self._get_preview_url(skeleton.minio_path, user.uid)

                search_results.append(
                    SkeletonSearchResult(
                        skeleton=skeleton,
                        similarity_score=result.get("score", 0.0),
                        preview_url=preview_url,
                    )
                )

        return SkeletonSearchResponse(
            results=search_results,
            total_count=len(search_results),
            query=search_request.query,
            search_type=search_request.search_type,
        )

    async def _build_vector_search_pipeline(
        self, query_embedding: list[float], search_request: SkeletonSearchRequest, user: User
    ) -> list[dict]:
        """Build MongoDB vector search pipeline"""
        match_filter = {"is_public": True}

        # Add user's private skeletons if requested
        if search_request.include_private:
            match_filter = {
                "$or": [{"is_public": True}, {"user_id": str(user.uid)}]
            }

        # Add preprocessor filter
        if search_request.preprocessor_type:
            match_filter["preprocessor_type"] = search_request.preprocessor_type.value

        return [
            {
                "$vectorSearch": {
                    "index": "skeleton_vector_index",
                    "queryVector": query_embedding,
                    "path": "embedding",
                    "numCandidates": search_request.match_count * 10,
                    "limit": search_request.match_count,
                    "filter": match_filter,
                }
            },
            {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
            {
                "$project": {
                    "_id": 1,
                    "description": 1,
                    "tags": 1,
                    "preprocessor_type": 1,
                    "score": 1,
                }
            },
        ]

    async def _build_text_search_pipeline(
        self, search_request: SkeletonSearchRequest, user: User
    ) -> list[dict]:
        """Build MongoDB text search pipeline"""
        match_filter = {"is_public": True}

        if search_request.include_private:
            match_filter = {
                "$or": [{"is_public": True}, {"user_id": str(user.uid)}]
            }

        if search_request.preprocessor_type:
            match_filter["preprocessor_type"] = search_request.preprocessor_type.value

        return [
            {
                "$search": {
                    "index": "skeleton_text_index",
                    "text": {"query": search_request.query, "path": ["description", "tags"]},
                }
            },
            {"$match": match_filter},
            {"$addFields": {"score": {"$meta": "searchScore"}}},
            {"$limit": search_request.match_count},
            {
                "$project": {
                    "_id": 1,
                    "description": 1,
                    "tags": 1,
                    "preprocessor_type": 1,
                    "score": 1,
                }
            },
        ]

    async def _build_hybrid_search_pipeline(
        self, query_embedding: list[float], search_request: SkeletonSearchRequest, user: User
    ) -> list[dict]:
        """Build MongoDB hybrid search pipeline with RRF"""
        # For simplicity, use vector search with higher candidate count
        # True hybrid search would require running both pipelines and merging results
        return await self._build_vector_search_pipeline(query_embedding, search_request, user)

    async def _get_preview_url(self, minio_path: str, user_id: UUID) -> str | None:
        """Generate presigned URL for skeleton preview"""
        try:
            # Extract object key from minio_path
            # Format: user-{uuid}/{object_key}
            parts = minio_path.split("/", 1)
            if len(parts) == 2:
                object_key = parts[1]
                url = await self.minio.get_presigned_url(
                    user_id=user_id,
                    object_key=object_key,
                    expiry=timedelta(hours=1),
                )
                return url
        except Exception as e:
            logger.error(f"Failed to generate preview URL: {e}")

        return None

    async def get_skeleton(self, skeleton_id: UUID, user: User) -> ControlNetSkeleton | None:
        """Get a skeleton by ID"""
        response = (
            self.supabase.table("comfyui_controlnet_skeletons")
            .select("*")
            .eq("id", str(skeleton_id))
            .execute()
        )

        if not response.data:
            return None

        skeleton = ControlNetSkeleton.model_validate(response.data[0])

        # Check access (own skeleton or public)
        if skeleton.user_id != user.uid and not skeleton.is_public:
            return None

        return skeleton

    async def list_skeletons(
        self,
        user: User,
        preprocessor_type: PreprocessorType | None = None,
        include_public: bool = True,
        limit: int = 50,
    ) -> list[ControlNetSkeleton]:
        """List skeletons for a user"""
        query = self.supabase.table("comfyui_controlnet_skeletons").select("*")

        # Filter by visibility
        if include_public:
            query = query.or_(f"user_id.eq.{user.uid},is_public.eq.true")
        else:
            query = query.eq("user_id", str(user.uid))

        # Filter by preprocessor type
        if preprocessor_type:
            query = query.eq("preprocessor_type", preprocessor_type.value)

        # Order and limit
        query = query.order("created_at", desc=True).limit(limit)

        response = query.execute()
        return [ControlNetSkeleton.model_validate(item) for item in response.data]

    async def delete_skeleton(self, skeleton_id: UUID, user: User) -> bool:
        """Delete a skeleton (user must own it)"""
        # Get skeleton first
        skeleton = await self.get_skeleton(skeleton_id, user)
        if not skeleton or skeleton.user_id != user.uid:
            return False

        # Delete from MongoDB if embedding exists
        if skeleton.embedding_id:
            try:
                from bson import ObjectId

                await self.collection.delete_one({"_id": ObjectId(skeleton.embedding_id)})
            except Exception as e:
                logger.error(f"Failed to delete MongoDB document: {e}")

        # Delete from MinIO
        try:
            parts = skeleton.minio_path.split("/", 1)
            if len(parts) == 2:
                await self.minio.delete_file(user_id=user.uid, object_key=parts[1])
        except Exception as e:
            logger.error(f"Failed to delete MinIO file: {e}")

        # Delete from Supabase
        self.supabase.table("comfyui_controlnet_skeletons").delete().eq(
            "id", str(skeleton_id)
        ).execute()

        logger.info(f"Deleted skeleton: {skeleton_id}")
        return True
