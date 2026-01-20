"""Article CRUD and management service."""

import logging
import re
from datetime import datetime
from typing import Any

import openai
from bson import ObjectId
from capabilities.knowledge_graph.knowledge_base.config import config
from capabilities.knowledge_graph.knowledge_base.models import (
    Article,
    ArticleCreateRequest,
    ArticleUpdateRequest,
    ArticleVersion,
    SourceType,
)
from pymongo import AsyncMongoClient

from shared.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class ArticleService:
    """Service for managing Knowledge Base articles."""

    def __init__(
        self,
        mongo_client: AsyncMongoClient,
        openai_client: openai.AsyncOpenAI | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        """
        Initialize the article service.

        Args:
            mongo_client: MongoDB async client
            openai_client: OpenAI client for embeddings (deprecated, use embedding_service)
            embedding_service: EmbeddingService for generating embeddings
        """
        self.mongo_client = mongo_client
        self.db = mongo_client[config.mongodb_database]
        self.collection = self.db[config.articles_collection]
        self.openai_client = openai_client
        self.embedding_service = embedding_service or EmbeddingService(client=openai_client)

    @staticmethod
    def generate_slug(title: str) -> str:
        """Generate URL-friendly slug from title."""
        # Convert to lowercase
        slug = title.lower()
        # Replace spaces and special chars with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        # Limit length
        return slug[:100]

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text."""
        return await self.embedding_service.generate_embedding(text)

    async def create_article(
        self,
        request: ArticleCreateRequest,
        author_email: str,
    ) -> Article:
        """
        Create a new article.

        Args:
            request: Article creation request
            author_email: Email of the article author/owner

        Returns:
            Created article
        """
        # Generate slug if not provided
        slug = request.slug or self.generate_slug(request.title)

        # Check for duplicate slug
        existing = await self.collection.find_one({"slug": slug})
        if existing:
            # Append timestamp to make unique
            slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

        # Generate embedding
        embedding = None
        if self.openai_client:
            try:
                embedding = await self.generate_embedding(request.content)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")

        now = datetime.utcnow()
        article_data = {
            "slug": slug,
            "title": request.title,
            "content": request.content,
            "content_embedding": embedding,
            "author_email": author_email,
            "source_url": request.source_url,
            "source_type": request.source_type.value,
            "tags": request.tags,
            "version": 1,
            "version_history": [],
            "created_at": now,
            "updated_at": now,
            "reliability_score": None,
            "last_verified_at": None,
            "metadata": {},
        }

        result = await self.collection.insert_one(article_data)
        article_data["_id"] = str(result.inserted_id)

        logger.info(f"Created article: {slug} by {author_email}")
        return Article(**article_data)

    async def get_article(self, article_id: str) -> Article | None:
        """Get article by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(article_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                return Article(**doc)
        except Exception as e:
            logger.error(f"Error fetching article {article_id}: {e}")
        return None

    async def get_article_by_slug(self, slug: str) -> Article | None:
        """Get article by slug."""
        doc = await self.collection.find_one({"slug": slug})
        if doc:
            doc["_id"] = str(doc["_id"])
            return Article(**doc)
        return None

    async def update_article(
        self,
        article_id: str,
        request: ArticleUpdateRequest,
        editor_email: str,
    ) -> Article | None:
        """
        Update an article, creating a version history entry.

        Args:
            article_id: ID of article to update
            request: Update request
            editor_email: Email of person making the edit

        Returns:
            Updated article or None if not found
        """
        article = await self.get_article(article_id)
        if not article:
            return None

        # Build update dict
        update_data: dict[str, Any] = {"updated_at": datetime.utcnow()}

        # Create version history entry if content changed
        if request.content and request.content != article.content:
            version_entry = ArticleVersion(
                version=article.version,
                content=article.content,
                changed_at=article.updated_at,
                changed_by=editor_email,
                change_reason=request.change_reason,
            )

            update_data["content"] = request.content
            update_data["version"] = article.version + 1
            update_data["$push"] = {"version_history": version_entry.model_dump()}

            # Regenerate embedding
            if self.openai_client:
                try:
                    update_data["content_embedding"] = await self.generate_embedding(
                        request.content
                    )
                except Exception as e:
                    logger.warning(f"Failed to regenerate embedding: {e}")

        if request.title:
            update_data["title"] = request.title

        if request.tags is not None:
            update_data["tags"] = request.tags

        # Separate $push operation
        push_op = update_data.pop("$push", None)

        await self.collection.update_one(
            {"_id": ObjectId(article_id)},
            {"$set": update_data, **({"$push": push_op} if push_op else {})},
        )

        logger.info(f"Updated article {article_id} by {editor_email}")
        return await self.get_article(article_id)

    async def list_articles(
        self,
        page: int = 1,
        per_page: int = 20,
        source_type: str | None = None,
        tags: list[str] | None = None,
        author_email: str | None = None,
    ) -> tuple[list[Article], int]:
        """
        List articles with pagination and filtering.

        Returns:
            Tuple of (articles, total_count)
        """
        filter_dict: dict[str, Any] = {}

        if source_type:
            filter_dict["source_type"] = source_type
        if tags:
            filter_dict["tags"] = {"$in": tags}
        if author_email:
            filter_dict["author_email"] = author_email

        # Get total count
        total = await self.collection.count_documents(filter_dict)

        # Get paginated results
        skip = (page - 1) * per_page
        cursor = self.collection.find(filter_dict).sort("updated_at", -1).skip(skip).limit(per_page)

        articles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            articles.append(Article(**doc))

        return articles, total

    async def search_articles(
        self,
        query: str,
        match_count: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search articles using vector similarity.

        Args:
            query: Search query
            match_count: Number of results

        Returns:
            List of search results with similarity scores
        """
        if not self.openai_client:
            raise ValueError("OpenAI client required for semantic search")

        # Generate query embedding
        query_embedding = await self.generate_embedding(query)

        # Vector search pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "article_vector_index",
                    "path": "content_embedding",
                    "queryVector": query_embedding,
                    "numCandidates": match_count * 10,
                    "limit": match_count,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "slug": 1,
                    "title": 1,
                    "content": 1,
                    "author_email": 1,
                    "source_url": 1,
                    "source_type": 1,
                    "tags": 1,
                    "updated_at": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        results = []
        async for doc in self.collection.aggregate(pipeline):
            doc["_id"] = str(doc["_id"])
            results.append(doc)

        return results

    async def delete_article(self, article_id: str) -> bool:
        """Delete an article by ID."""
        result = await self.collection.delete_one({"_id": ObjectId(article_id)})
        return result.deleted_count > 0

    async def get_article_history(self, article_id: str) -> list[ArticleVersion]:
        """Get version history for an article."""
        article = await self.get_article(article_id)
        if not article:
            return []
        return article.version_history

    async def import_from_markdown(
        self,
        title: str,
        content: str,
        source_url: str | None = None,
        author_email: str = "system@import",
        tags: list[str] | None = None,
    ) -> Article:
        """
        Import an article from markdown content.

        Args:
            title: Article title
            content: Markdown content
            source_url: Original source URL
            author_email: Email of importer
            tags: Optional tags

        Returns:
            Created article
        """
        request = ArticleCreateRequest(
            title=title,
            content=content,
            source_url=source_url,
            source_type=SourceType.IMPORT,
            tags=tags or [],
        )
        return await self.create_article(request, author_email)
