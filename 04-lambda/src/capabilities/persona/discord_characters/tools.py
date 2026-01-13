"""MCP tools for Discord character management."""

import logging

from capabilities.persona.discord_characters.dependencies import DiscordCharactersDeps

logger = logging.getLogger(__name__)


# MCP tool definitions (these would be registered with the MCP server)
# For now, we'll create the tool functions that can be called


async def add_discord_character_tool(
    channel_id: str, character_id: str, persona_id: str | None = None
) -> dict:
    """
    Add a character to a Discord channel.

    Args:
        channel_id: Discord channel ID
        character_id: Character identifier
        persona_id: Optional persona ID (defaults to character_id)

    Returns:
        Result dictionary with success status and message
    """
    deps = DiscordCharactersDeps.from_settings()
    await deps.initialize()

    try:
        success, message = await deps.character_manager.add_character(
            channel_id, character_id, persona_id or character_id
        )
        return {"success": success, "message": message}
    finally:
        await deps.cleanup()


async def remove_discord_character_tool(channel_id: str, character_id: str) -> dict:
    """
    Remove a character from a Discord channel.

    Args:
        channel_id: Discord channel ID
        character_id: Character identifier

    Returns:
        Result dictionary with success status and message
    """
    deps = DiscordCharactersDeps.from_settings()
    await deps.initialize()

    try:
        success, message = await deps.character_manager.remove_character(channel_id, character_id)
        return {"success": success, "message": message}
    finally:
        await deps.cleanup()


async def list_discord_characters_tool(channel_id: str) -> list:
    """
    List all characters in a Discord channel.

    Args:
        channel_id: Discord channel ID

    Returns:
        List of character dictionaries
    """
    deps = DiscordCharactersDeps.from_settings()
    await deps.initialize()

    try:
        characters = await deps.character_manager.list_characters(channel_id)
        return [
            {
                "channel_id": char.channel_id,
                "character_id": char.character_id,
                "persona_id": char.persona_id,
                "added_at": char.added_at.isoformat(),
                "message_count": char.message_count,
            }
            for char in characters
        ]
    finally:
        await deps.cleanup()


async def clear_discord_history_tool(channel_id: str, character_id: str | None = None) -> dict:
    """
    Clear conversation history for a Discord channel.

    Args:
        channel_id: Discord channel ID
        character_id: Optional character ID to clear specific character history

    Returns:
        Result dictionary with success status and message
    """
    deps = DiscordCharactersDeps.from_settings()
    await deps.initialize()

    try:
        success, message = await deps.character_manager.clear_history(channel_id, character_id)
        return {"success": success, "message": message}
    finally:
        await deps.cleanup()


async def chat_with_discord_character_tool(
    channel_id: str, character_id: str, user_id: str, message: str
) -> dict:
    """
    Generate a character response to a message.

    Args:
        channel_id: Discord channel ID
        character_id: Character identifier
        user_id: Discord user ID
        message: User message content

    Returns:
        Result dictionary with response text
    """
    deps = DiscordCharactersDeps.from_settings()
    await deps.initialize()

    try:
        # Get character
        character = await deps.character_manager.get_character(channel_id, character_id)
        if not character:
            return {
                "success": False,
                "error": f"Character '{character_id}' is not active in this channel",
            }

        # Get conversation context
        await deps.character_manager.get_conversation_context(channel_id, character_id, limit=20)

        # Call conversation service
        from capabilities.persona.persona_state.dependencies import PersonaDeps
        from capabilities.persona.persona_state.tools import get_voice_instructions
        from workflows.chat.conversation.services.orchestrator import ConversationOrchestrator

        persona_deps = PersonaDeps.from_settings()
        await persona_deps.initialize()

        try:
            # Get voice instructions
            voice_instructions = await get_voice_instructions(
                persona_deps, user_id, character.persona_id
            )

            # Create orchestrator
            orchestrator = ConversationOrchestrator(llm_client=persona_deps.openai_client)

            # Plan and generate response
            plan = await orchestrator.plan_response(message, voice_instructions, [])
            response = await orchestrator.generate_response(message, voice_instructions, {}, plan)

            # Record messages
            from datetime import datetime

            from server.services.discord_characters.models import CharacterMessage

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

            return {"success": True, "response": response, "character_id": character_id}
        finally:
            await persona_deps.cleanup()

    finally:
        await deps.cleanup()
