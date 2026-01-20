"""Tests for Open WebUI export tools."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from server.projects.openwebui_export.dependencies import OpenWebUIExportDeps
from server.projects.openwebui_export.models import ConversationExportRequest, ConversationMessage
from server.projects.openwebui_export.tools import (
    export_conversation,
    get_conversations,
)

from tests.conftest import MockRunContext


@pytest.fixture
def mock_openwebui_deps():
    """Create mock OpenWebUIExportDeps."""
    deps = OpenWebUIExportDeps()
    # Setup MongoDB mocks - need proper async mocks
    mock_collection = AsyncMock()
    mock_collection.insert_one = AsyncMock(return_value=Mock(inserted_id="doc_123"))
    mock_collection.insert_many = AsyncMock(return_value=Mock(inserted_ids=["chunk_1", "chunk_2"]))

    mock_db = Mock()
    mock_db.__getitem__ = Mock(return_value=mock_collection)

    deps.mongo_client = Mock()
    deps.mongo_client.__getitem__ = Mock(return_value=mock_db)
    deps.mongodb_database = "test_db"
    # Override the db property by setting it directly
    deps._db = mock_db
    deps.http_client = AsyncMock()
    return deps


@pytest.mark.asyncio
async def test_export_conversation_success(mock_openwebui_deps):
    """Test exporting a conversation successfully."""
    # Setup
    ctx = MockRunContext(mock_openwebui_deps)

    # Mock chunker and embedder creation
    with (
        patch("server.projects.openwebui_export.tools.create_chunker") as mock_chunker_create,
        patch("server.projects.openwebui_export.tools.create_embedder") as mock_embedder_create,
    ):
        # Create proper mock chunks with required attributes
        from types import SimpleNamespace

        mock_chunk1 = SimpleNamespace(content="Chunk 1", start_char=0, end_char=10, metadata={})
        mock_chunk2 = SimpleNamespace(content="Chunk 2", start_char=10, end_char=20, metadata={})

        mock_chunker = AsyncMock()
        mock_chunker.chunk_document = AsyncMock(return_value=[mock_chunk1, mock_chunk2])
        mock_chunker_create.return_value = mock_chunker

        mock_embedder = AsyncMock()
        mock_embedder.embed_batch = AsyncMock(return_value=[[0.1] * 384, [0.2] * 384])
        mock_embedder_create.return_value = mock_embedder

        request = ConversationExportRequest(
            conversation_id="conv_123",
            user_id="user1",
            title="Test Conversation",
            messages=[
                ConversationMessage(role="user", content="Hello"),
                ConversationMessage(role="assistant", content="Hi there!"),
            ],
        )

        # Execute
        result = await export_conversation(ctx, request)

        # Assert
        assert result["success"] is True
        assert "document_id" in result
        assert "chunks_created" in result


@pytest.mark.asyncio
async def test_get_conversations_success(mock_openwebui_deps):
    """Test getting conversations successfully."""
    # Setup
    ctx = MockRunContext(mock_openwebui_deps)
    mock_openwebui_deps.openwebui_api_url = "http://localhost:3000"

    mock_conversations = {
        "items": [
            {"id": "conv_1", "title": "Conversation 1"},
            {"id": "conv_2", "title": "Conversation 2"},
        ]
    }
    mock_response = Mock()
    mock_response.json = Mock(return_value=mock_conversations)
    mock_response.raise_for_status = Mock()
    mock_openwebui_deps.http_client.get = AsyncMock(return_value=mock_response)

    # Execute
    result = await get_conversations(ctx, user_id="user1", limit=10, offset=0)

    # Assert
    assert isinstance(result, dict)
    # The function returns the response directly, so check for the structure
    assert "conversations" in result or "total" in result
    if "conversations" in result:
        assert len(result["conversations"]) == 2
    if "total" in result:
        assert result["total"] == 2
