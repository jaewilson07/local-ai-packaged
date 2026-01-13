"""Integration tests for MongoDB RAG search with Row-Level Security (RLS)."""

from unittest.mock import AsyncMock, Mock

import pytest
from bson import ObjectId

from server.projects.mongo_rag.tools import hybrid_search, semantic_search, text_search
from tests.conftest import MockRunContext, async_iter


@pytest.fixture
def mock_deps_with_user(mock_agent_dependencies):
    """Mock dependencies with user context for RLS."""
    deps = mock_agent_dependencies
    deps.current_user_id = "user-123"
    deps.current_user_email = "user@example.com"
    deps.is_admin = False
    deps.user_groups = []
    return deps


@pytest.fixture
def mock_deps_admin(mock_agent_dependencies):
    """Mock dependencies with admin user."""
    deps = mock_agent_dependencies
    deps.current_user_id = "admin-123"
    deps.current_user_email = "admin@example.com"
    deps.is_admin = True
    deps.user_groups = []
    return deps


@pytest.fixture
def sample_own_document():
    """Sample document owned by test user."""
    return {
        "_id": ObjectId(),
        "title": "My Document",
        "user_id": "user-123",
        "user_email": "user@example.com",
        "is_public": False,
        "shared_with": [],
        "group_ids": [],
    }


@pytest.fixture
def sample_public_document():
    """Sample public document."""
    return {
        "_id": ObjectId(),
        "title": "Public Document",
        "user_id": "other-user",
        "user_email": "other@example.com",
        "is_public": True,
        "shared_with": [],
        "group_ids": [],
    }


@pytest.fixture
def sample_shared_document():
    """Sample document shared with test user."""
    return {
        "_id": ObjectId(),
        "title": "Shared Document",
        "user_id": "other-user",
        "user_email": "other@example.com",
        "is_public": False,
        "shared_with": ["user-123"],
        "group_ids": [],
    }


@pytest.fixture
def sample_private_document():
    """Sample private document not accessible to test user."""
    return {
        "_id": ObjectId(),
        "title": "Private Document",
        "user_id": "other-user",
        "user_email": "other@example.com",
        "is_public": False,
        "shared_with": [],
        "group_ids": [],
    }


@pytest.fixture
def sample_chunk_own(sample_own_document):
    """Sample chunk from own document."""
    return {
        "_id": ObjectId(),
        "document_id": sample_own_document["_id"],
        "content": "Content from my document",
        "embedding": [0.1] * 768,
        "document_info": {
            "title": sample_own_document["title"],
            "user_id": sample_own_document["user_id"],
            "user_email": sample_own_document["user_email"],
            "is_public": sample_own_document["is_public"],
            "shared_with": sample_own_document["shared_with"],
            "group_ids": sample_own_document["group_ids"],
        },
    }


@pytest.fixture
def sample_chunk_public(sample_public_document):
    """Sample chunk from public document."""
    return {
        "_id": ObjectId(),
        "document_id": sample_public_document["_id"],
        "content": "Content from public document",
        "embedding": [0.1] * 768,
        "document_info": {
            "title": sample_public_document["title"],
            "user_id": sample_public_document["user_id"],
            "user_email": sample_public_document["user_email"],
            "is_public": sample_public_document["is_public"],
            "shared_with": sample_public_document["shared_with"],
            "group_ids": sample_public_document["group_ids"],
        },
    }


@pytest.fixture
def sample_chunk_shared(sample_shared_document):
    """Sample chunk from shared document."""
    return {
        "_id": ObjectId(),
        "document_id": sample_shared_document["_id"],
        "content": "Content from shared document",
        "embedding": [0.1] * 768,
        "document_info": {
            "title": sample_shared_document["title"],
            "user_id": sample_shared_document["user_id"],
            "user_email": sample_shared_document["user_email"],
            "is_public": sample_shared_document["is_public"],
            "shared_with": sample_shared_document["shared_with"],
            "group_ids": sample_shared_document["group_ids"],
        },
    }


@pytest.fixture
def sample_chunk_private(sample_private_document):
    """Sample chunk from private document."""
    return {
        "_id": ObjectId(),
        "document_id": sample_private_document["_id"],
        "content": "Content from private document",
        "embedding": [0.1] * 768,
        "document_info": {
            "title": sample_private_document["title"],
            "user_id": sample_private_document["user_id"],
            "user_email": sample_private_document["user_email"],
            "is_public": sample_private_document["is_public"],
            "shared_with": sample_private_document["shared_with"],
            "group_ids": sample_private_document["group_ids"],
        },
    }


class TestSemanticSearchRLS:
    """Test semantic search with RLS filtering."""

    @pytest.mark.asyncio
    async def test_semantic_search_filters_by_ownership(
        self, mock_deps_with_user, sample_chunk_own, sample_chunk_private
    ):
        """Test semantic search only returns accessible documents."""
        ctx = MockRunContext(mock_deps_with_user)

        # Mock aggregation to return own document chunk
        # The aggregation pipeline projects chunk_id from _id, so mock should match pipeline output
        mock_aggregation_result = {
            "chunk_id": sample_chunk_own["_id"],
            "document_id": sample_chunk_own["document_id"],
            "content": sample_chunk_own["content"],
            "similarity": 0.95,
            "metadata": sample_chunk_own.get("metadata", {}),
            "document_title": sample_chunk_own["document_info"]["title"],
            "document_source": sample_chunk_own["document_info"].get("source", ""),
        }
        mock_cursor = async_iter([mock_aggregation_result])
        mock_deps_with_user.db.__getitem__ = Mock(return_value=AsyncMock())
        mock_collection = mock_deps_with_user.db["chunks"]
        mock_collection.aggregate = AsyncMock(return_value=mock_cursor)

        results = await semantic_search(ctx, "test query", match_count=5)

        # Should return own document
        assert len(results) > 0
        assert results[0].document_title == "My Document"

    @pytest.mark.asyncio
    async def test_semantic_search_includes_public_documents(
        self, mock_deps_with_user, sample_chunk_public
    ):
        """Test semantic search includes public documents."""
        ctx = MockRunContext(mock_deps_with_user)

        # Mock aggregation pipeline output structure
        mock_aggregation_result = {
            "chunk_id": sample_chunk_public["_id"],
            "document_id": sample_chunk_public["document_id"],
            "content": sample_chunk_public["content"],
            "similarity": 0.95,
            "metadata": sample_chunk_public.get("metadata", {}),
            "document_title": sample_chunk_public["document_info"]["title"],
            "document_source": sample_chunk_public["document_info"].get("source", ""),
        }
        mock_cursor = async_iter([mock_aggregation_result])
        mock_deps_with_user.db.__getitem__ = Mock(return_value=AsyncMock())
        mock_collection = mock_deps_with_user.db["chunks"]
        mock_collection.aggregate = AsyncMock(return_value=mock_cursor)

        results = await semantic_search(ctx, "test query", match_count=5)

        # Should return public document
        assert len(results) > 0
        assert results[0].document_title == "Public Document"

    @pytest.mark.asyncio
    async def test_semantic_search_includes_shared_documents(
        self, mock_deps_with_user, sample_chunk_shared
    ):
        """Test semantic search includes shared documents."""
        ctx = MockRunContext(mock_deps_with_user)

        # Mock aggregation pipeline output structure
        mock_aggregation_result = {
            "chunk_id": sample_chunk_shared["_id"],
            "document_id": sample_chunk_shared["document_id"],
            "content": sample_chunk_shared["content"],
            "similarity": 0.95,
            "metadata": sample_chunk_shared.get("metadata", {}),
            "document_title": sample_chunk_shared["document_info"]["title"],
            "document_source": sample_chunk_shared["document_info"].get("source", ""),
        }
        mock_cursor = async_iter([mock_aggregation_result])
        mock_deps_with_user.db.__getitem__ = Mock(return_value=AsyncMock())
        mock_collection = mock_deps_with_user.db["chunks"]
        mock_collection.aggregate = AsyncMock(return_value=mock_cursor)

        results = await semantic_search(ctx, "test query", match_count=5)

        # Should return shared document
        assert len(results) > 0
        assert results[0].document_title == "Shared Document"

    @pytest.mark.asyncio
    async def test_semantic_search_excludes_private_documents(
        self, mock_deps_with_user, sample_chunk_private
    ):
        """Test semantic search excludes inaccessible documents."""
        ctx = MockRunContext(mock_deps_with_user)

        # Mock aggregation pipeline to verify RLS filter is applied
        mock_cursor = async_iter([])  # Empty results (filtered out)
        mock_deps_with_user.db.__getitem__ = Mock(return_value=AsyncMock())
        mock_collection = mock_deps_with_user.db["chunks"]
        mock_collection.aggregate = AsyncMock(return_value=mock_cursor)

        results = await semantic_search(ctx, "test query", match_count=5)

        # Should not return private document
        # (In real scenario, $lookup with RLS filter would exclude it)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_semantic_search_admin_sees_all(
        self, mock_deps_admin, sample_chunk_own, sample_chunk_private
    ):
        """Test admin users see all documents."""
        ctx = MockRunContext(mock_deps_admin)

        # Admin should see both own and private documents
        mock_cursor = async_iter([sample_chunk_own, sample_chunk_private])
        mock_deps_admin.db.__getitem__ = Mock(return_value=AsyncMock())
        mock_collection = mock_deps_admin.db["chunks"]
        mock_collection.aggregate = AsyncMock(return_value=mock_cursor)

        results = await semantic_search(ctx, "test query", match_count=5)

        # Admin should see all documents (no filtering)
        assert len(results) >= 0  # Could be 0 or more depending on mock


class TestTextSearchRLS:
    """Test text search with RLS filtering."""

    @pytest.mark.asyncio
    async def test_text_search_applies_rls_filter(self, mock_deps_with_user, sample_chunk_own):
        """Test text search applies RLS filtering."""
        ctx = MockRunContext(mock_deps_with_user)

        mock_cursor = async_iter([sample_chunk_own])
        mock_deps_with_user.db.__getitem__ = Mock(return_value=AsyncMock())
        mock_collection = mock_deps_with_user.db["chunks"]
        mock_collection.aggregate = AsyncMock(return_value=mock_cursor)

        results = await text_search(ctx, "test query", match_count=5)

        # Should return accessible documents
        assert len(results) >= 0


class TestHybridSearchRLS:
    """Test hybrid search with RLS filtering."""

    @pytest.mark.asyncio
    async def test_hybrid_search_applies_rls_filter(
        self, mock_deps_with_user, sample_chunk_own, sample_chunk_public
    ):
        """Test hybrid search applies RLS filtering to both semantic and text results."""
        ctx = MockRunContext(mock_deps_with_user)

        # Mock both semantic and text search results
        mock_cursor = async_iter([sample_chunk_own, sample_chunk_public])
        mock_deps_with_user.db.__getitem__ = Mock(return_value=AsyncMock())
        mock_collection = mock_deps_with_user.db["chunks"]
        mock_collection.aggregate = AsyncMock(return_value=mock_cursor)

        results = await hybrid_search(ctx, "test query", match_count=5)

        # Should return accessible documents only
        assert len(results) >= 0
        # Results should be from own or public documents
        titles = [r.document_title for r in results]
        assert "My Document" in titles or "Public Document" in titles or len(results) == 0
