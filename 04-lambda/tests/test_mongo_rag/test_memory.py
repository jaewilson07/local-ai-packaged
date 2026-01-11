"""Tests for MongoDB RAG memory tools."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from server.projects.mongo_rag.memory_models import MemoryFact, MemoryMessage
from server.projects.mongo_rag.memory_tools import MemoryTools


@pytest.mark.asyncio
async def test_record_message(mock_agent_dependencies):
    """Test recording a message."""
    # Setup
    memory_tools = MemoryTools(deps=mock_agent_dependencies)

    # Mock store
    mock_store = Mock()
    mock_store.add_message = Mock()
    memory_tools._store = mock_store

    # Execute
    memory_tools.record_message(
        user_id="user1", persona_id="persona1", content="Hello, world!", role="user"
    )

    # Assert
    mock_store.add_message.assert_called_once()
    call_args = mock_store.add_message.call_args[0][0]
    assert call_args.user_id == "user1"
    assert call_args.persona_id == "persona1"
    assert call_args.content == "Hello, world!"
    assert call_args.role == "user"


@pytest.mark.asyncio
async def test_get_context_window(mock_agent_dependencies):
    """Test getting context window."""
    # Setup
    memory_tools = MemoryTools(deps=mock_agent_dependencies)

    # Mock messages
    sample_messages = [
        MemoryMessage(
            user_id="user1",
            persona_id="persona1",
            role="user",
            content="Message 1",
            created_at=datetime.now(),
        ),
        MemoryMessage(
            user_id="user1",
            persona_id="persona1",
            role="assistant",
            content="Response 1",
            created_at=datetime.now(),
        ),
    ]

    # Mock store
    mock_store = Mock()
    mock_store.get_recent_messages = Mock(return_value=sample_messages)
    memory_tools._store = mock_store

    # Execute
    messages = memory_tools.get_context_window(user_id="user1", persona_id="persona1", limit=20)

    # Assert
    assert len(messages) == 2
    assert messages[0].content == "Message 1"
    mock_store.get_recent_messages.assert_called_once_with("user1", "persona1", 20)


@pytest.mark.asyncio
async def test_store_fact(mock_agent_dependencies):
    """Test storing a fact."""
    # Setup
    memory_tools = MemoryTools(deps=mock_agent_dependencies)

    # Mock store
    mock_store = Mock()
    mock_store.add_fact = Mock()
    memory_tools._store = mock_store

    # Execute
    memory_tools.store_fact(
        user_id="user1",
        persona_id="persona1",
        fact="Python is a programming language",
        tags=["programming", "python"],
    )

    # Assert
    mock_store.add_fact.assert_called_once()
    call_args = mock_store.add_fact.call_args[0][0]
    assert call_args.fact == "Python is a programming language"
    assert "programming" in call_args.tags


@pytest.mark.asyncio
async def test_search_facts(mock_agent_dependencies):
    """Test searching facts."""
    # Setup
    memory_tools = MemoryTools(deps=mock_agent_dependencies)

    # Mock facts
    sample_facts = [
        MemoryFact(
            user_id="user1",
            persona_id="persona1",
            fact="Python is a programming language",
            tags=["programming"],
            created_at=datetime.now(),
        )
    ]

    # Mock store
    mock_store = Mock()
    mock_store.search_facts = Mock(return_value=sample_facts)
    memory_tools._store = mock_store

    # Execute
    facts = memory_tools.search_facts(
        user_id="user1", persona_id="persona1", query="programming language", limit=10
    )

    # Assert
    assert len(facts) == 1
    assert facts[0].fact == "Python is a programming language"
    mock_store.search_facts.assert_called_once_with("user1", "persona1", "programming language", 10)


@pytest.mark.asyncio
async def test_store_web_content(mock_agent_dependencies):
    """Test storing web content."""
    # Setup
    memory_tools = MemoryTools(deps=mock_agent_dependencies)

    # Mock store
    mock_store = Mock()
    mock_store.add_web_content = Mock(return_value=5)  # 5 chunks created
    memory_tools._store = mock_store

    # Execute
    chunks = memory_tools.store_web_content(
        user_id="user1",
        persona_id="persona1",
        content="<html><body><h1>Test Page</h1><p>Content here.</p></body></html>",
        source_url="https://example.com",
        source_title="Test Page",
        source_description="A test page",
        tags=["web", "test"],
    )

    # Assert
    assert chunks == 5
    mock_store.add_web_content.assert_called_once()


@pytest.mark.asyncio
async def test_get_context_window_empty(mock_agent_dependencies):
    """Test getting context window when no messages exist."""
    # Setup
    memory_tools = MemoryTools(deps=mock_agent_dependencies)

    # Mock store with empty results
    mock_store = Mock()
    mock_store.get_recent_messages = Mock(return_value=[])
    memory_tools._store = mock_store

    # Execute
    messages = memory_tools.get_context_window(user_id="user1", persona_id="persona1", limit=20)

    # Assert
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_search_facts_empty(mock_agent_dependencies):
    """Test searching facts when no facts exist."""
    # Setup
    memory_tools = MemoryTools(deps=mock_agent_dependencies)

    # Mock store with empty results
    mock_store = Mock()
    mock_store.search_facts = Mock(return_value=[])
    memory_tools._store = mock_store

    # Execute
    facts = memory_tools.search_facts(
        user_id="user1", persona_id="persona1", query="nonexistent", limit=10
    )

    # Assert
    assert len(facts) == 0
