"""Tests for Persona tools."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from server.projects.persona.dependencies import PersonaDeps
from server.projects.persona.tools import (
    get_voice_instructions,
    record_interaction,
)


@pytest.fixture
def mock_persona_deps():
    """Create mock PersonaDeps."""
    deps = PersonaDeps()
    deps.mongo_client = AsyncMock()
    deps.openai_client = AsyncMock()
    deps.persona_store = Mock()
    return deps


@pytest.mark.asyncio
async def test_get_voice_instructions(mock_persona_deps):
    """Test getting voice instructions."""
    # Setup - create proper mock objects with required attributes
    from types import SimpleNamespace

    mock_personality = SimpleNamespace(
        name="Test Persona",
        byline="A helpful assistant",
        identity=["friendly", "helpful", "knowledgeable"],
    )
    mock_persona_deps.persona_store.get_personality = Mock(return_value=mock_personality)

    mock_mood = SimpleNamespace(primary_emotion="happy", intensity=0.8)
    mock_persona_deps.persona_store.get_mood = Mock(return_value=mock_mood)

    mock_relationship = SimpleNamespace(affection_score=0.7, trust_level=0.8, interaction_count=10)
    mock_persona_deps.persona_store.get_relationship = Mock(return_value=mock_relationship)

    mock_context = SimpleNamespace(mode="casual", topic="general", depth_level=3)
    mock_persona_deps.persona_store.get_conversation_context = Mock(return_value=mock_context)

    # Execute
    result = await get_voice_instructions(mock_persona_deps, "user1", "persona1")

    # Assert
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Test Persona" in result
    mock_persona_deps.persona_store.get_personality.assert_called_once_with("persona1")
    mock_persona_deps.persona_store.get_mood.assert_called_once_with("user1", "persona1")
    mock_persona_deps.persona_store.get_relationship.assert_called_once_with("user1", "persona1")
    mock_persona_deps.persona_store.get_conversation_context.assert_called_once_with(
        "user1", "persona1"
    )


@pytest.mark.asyncio
async def test_record_interaction(mock_persona_deps):
    """Test recording an interaction."""
    # Setup - mock the action functions
    from types import SimpleNamespace

    mock_mood_result = {
        "mood": SimpleNamespace(primary_emotion="happy", intensity=0.7, timestamp=datetime.now())
    }
    mock_relationship_result = {
        "relationship": SimpleNamespace(affection_score=0.7, trust_level=0.8, interaction_count=1)
    }
    mock_context_result = {
        "context": SimpleNamespace(mode="casual", topic="general", depth_level=1)
    }

    with (
        patch(
            "server.projects.persona.tools.track_mood_action", new_callable=AsyncMock
        ) as mock_mood_action,
        patch(
            "server.projects.persona.tools.track_relationship_action", new_callable=AsyncMock
        ) as mock_rel_action,
        patch(
            "server.projects.persona.tools.track_context_action", new_callable=AsyncMock
        ) as mock_ctx_action,
    ):
        mock_mood_action.return_value = mock_mood_result
        mock_rel_action.return_value = mock_relationship_result
        mock_ctx_action.return_value = mock_context_result

        # Execute
        result = await record_interaction(
            mock_persona_deps,
            user_id="user1",
            persona_id="persona1",
            user_message="Hello!",
            bot_response="Hi there!",
        )

        # Assert
        assert isinstance(result, dict)
        assert "mood" in result
        assert "relationship" in result
        assert "context" in result
        mock_mood_action.assert_called_once()
        mock_rel_action.assert_called_once()
        mock_ctx_action.assert_called_once()
