"""Tests for Conversation agent."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from server.projects.conversation.agent import (
    orchestrate_conversation_tool,
)
from server.projects.persona.dependencies import PersonaDeps
from tests.conftest import MockRunContext


@pytest.fixture
def mock_persona_deps():
    """Create mock PersonaDeps."""
    deps = PersonaDeps()
    deps.mongo_client = AsyncMock()
    deps.openai_client = AsyncMock()
    deps.persona_store = Mock()
    return deps


@pytest.mark.asyncio
async def test_orchestrate_conversation_tool(mock_persona_deps):
    """Test conversation orchestration tool."""
    # Setup
    with (
        patch(
            "server.projects.conversation.agent.PersonaDeps.from_settings",
            return_value=mock_persona_deps,
        ),
        patch(
            "server.projects.conversation.agent.get_voice_instructions", new_callable=AsyncMock
        ) as mock_voice,
        patch(
            "server.projects.conversation.agent.ConversationOrchestrator"
        ) as mock_orchestrator_class,
        patch("server.projects.conversation.agent.record_interaction", new_callable=AsyncMock),
    ):
        # Mock voice instructions
        mock_voice.return_value = "Be friendly and helpful"

        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.plan_response = AsyncMock(
            return_value={
                "tools": ["enhanced_search"],
                "reasoning": "Need to search for information",
            }
        )
        mock_orchestrator.generate_response = AsyncMock(
            return_value="Here's the information you requested."
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        # Create context
        ctx = MockRunContext(mock_persona_deps)
        ctx.deps = mock_persona_deps

        # Execute
        result = await orchestrate_conversation_tool(
            ctx,
            user_id="user1",
            persona_id="persona1",
            message="What is RAG?",
        )

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        mock_voice.assert_called_once()
        mock_orchestrator.plan_response.assert_called_once()
        mock_orchestrator.generate_response.assert_called_once()
