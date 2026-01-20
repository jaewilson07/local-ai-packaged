"""Discord Characters agent implementation."""

import logging

from capabilities.persona.discord_characters.dependencies import DiscordCharactersDeps
from pydantic import Field
from pydantic_ai import Agent, RunContext

from shared.llm import get_llm_model

logger = logging.getLogger(__name__)


DISCORD_CHARACTERS_SYSTEM_PROMPT = """You are a Discord character management assistant.

You help manage AI characters in Discord channels, including:
- Adding and removing characters from channels
- Generating character responses to user messages
- Managing conversation history
- Determining when characters should engage in conversations

Characters have distinct personalities and should respond in character.
"""


discord_characters_agent = Agent(
    get_llm_model(), deps_type=DiscordCharactersDeps, system_prompt=DISCORD_CHARACTERS_SYSTEM_PROMPT
)


@discord_characters_agent.tool
async def generate_character_response_tool(
    ctx: RunContext[DiscordCharactersDeps],
    channel_id: str = Field(..., description="Discord channel ID"),
    character_id: str = Field(..., description="Character identifier"),
    user_id: str = Field(..., description="Discord user ID"),
    message: str = Field(..., description="User message content"),
) -> str:
    """
    Generate a character response to a user message.

    Uses the character's personality and conversation history to generate
    an appropriate response in character.
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    # Get character from channel
    character = await deps.character_manager.get_character(channel_id, character_id)
    if not character:
        return f"Character '{character_id}' is not active in this channel."

    # Get conversation context
    context_messages = await deps.character_manager.get_conversation_context(
        channel_id, character_id, limit=20
    )

    # Build conversation history string
    history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in context_messages])
    history_str += f"\nuser: {message}"

    # Call conversation service to generate response
    # For now, we'll use a simple approach - in production, would call conversation API
    # or use the conversation orchestrator directly
    from capabilities.persona.persona_state.dependencies import PersonaDeps
    from capabilities.persona.persona_state.tools import get_voice_instructions
    from workflows.chat.conversation.services.orchestrator import ConversationOrchestrator

    persona_deps = PersonaDeps.from_settings()
    await persona_deps.initialize()

    try:
        # Get voice instructions for the character
        voice_instructions = await get_voice_instructions(
            persona_deps, user_id, character.persona_id
        )

        # Create orchestrator
        orchestrator = ConversationOrchestrator(llm_client=persona_deps.openai_client)

        # Plan and generate response
        available_tools = []  # No tools for Discord characters for now
        plan = await orchestrator.plan_response(message, voice_instructions, available_tools)

        tool_results = {}
        response = await orchestrator.generate_response(
            message, voice_instructions, tool_results, plan
        )

        # Record the messages
        from datetime import datetime

        from capabilities.persona.discord_characters.services_legacy.models import CharacterMessage

        user_msg = CharacterMessage(
            channel_id=channel_id,
            character_id=character_id,
            user_id=user_id,
            content=message,
            role="user",
            timestamp=datetime.utcnow(),
        )
        await deps.character_manager.record_message(user_msg)

        assistant_msg = CharacterMessage(
            channel_id=channel_id,
            character_id=character_id,
            user_id=user_id,
            content=response,
            role="assistant",
            timestamp=datetime.utcnow(),
        )
        await deps.character_manager.record_message(assistant_msg)

        return response

    except Exception as e:
        logger.exception("Error generating character response")
        return f"Error: {e!s}"
    finally:
        await persona_deps.cleanup()
