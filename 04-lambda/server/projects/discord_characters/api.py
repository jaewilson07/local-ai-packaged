"""Discord Characters REST API endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Annotated, AsyncGenerator
import logging

from server.projects.discord_characters.dependencies import DiscordCharactersDeps
from server.projects.discord_characters.models import (
    AddCharacterRequest,
    RemoveCharacterRequest,
    ListCharactersRequest,
    ClearHistoryRequest,
    ChatRequest,
    EngageRequest,
    CharacterResponse,
    ChatResponse,
    EngageResponse,
)
from server.projects.persona.dependencies import PersonaDeps

router = APIRouter()
logger = logging.getLogger(__name__)


# FastAPI dependency function with yield pattern for resource cleanup
async def get_discord_characters_deps() -> AsyncGenerator[DiscordCharactersDeps, None]:
    """FastAPI dependency that yields DiscordCharactersDeps."""
    deps = DiscordCharactersDeps.from_settings()
    await deps.initialize()
    try:
        yield deps
    finally:
        await deps.cleanup()


@router.post("/add", response_model=dict)
async def add_character_endpoint(
    request: AddCharacterRequest,
    deps: Annotated[DiscordCharactersDeps, Depends(get_discord_characters_deps)]
):
    """Add a character to a Discord channel."""
    try:
        # Validate character exists in persona service
        persona_deps = PersonaDeps.from_settings()
        await persona_deps.initialize()
        
        try:
            # Get personality from persona store
            personality = persona_deps.persona_store.get_personality(request.character_id)
            
            if not personality:
                raise HTTPException(
                    status_code=404,
                    detail=f"Character '{request.character_id}' not found in persona service"
                )
            
            # Add character to channel
            success, message = await deps.character_manager.add_character(
                request.channel_id,
                request.character_id,
                request.persona_id or request.character_id
            )
            
            if not success:
                raise HTTPException(status_code=400, detail=message)
            
            return {
                "success": True,
                "message": message,
                "character": {
                    "channel_id": request.channel_id,
                    "character_id": request.character_id,
                    "persona_id": request.persona_id or request.character_id,
                    "name": personality.name,
                    "byline": personality.byline,
                    "profile_image": personality.profile_image
                }
            }
        finally:
            await persona_deps.cleanup()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error adding character: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remove", response_model=dict)
async def remove_character_endpoint(
    request: RemoveCharacterRequest,
    deps: Annotated[DiscordCharactersDeps, Depends(get_discord_characters_deps)]
):
    """Remove a character from a Discord channel."""
    try:
        success, message = await deps.character_manager.remove_character(
            request.channel_id,
            request.character_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=message)
        
        return {
            "success": True,
            "message": message
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error removing character: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=List[CharacterResponse])
async def list_characters_endpoint(
    channel_id: str,
    deps: Annotated[DiscordCharactersDeps, Depends(get_discord_characters_deps)]
):
    """List all characters in a Discord channel."""
    try:
        characters = await deps.character_manager.list_characters(channel_id)
        
        # Get personality info for each character
        persona_deps = PersonaDeps.from_settings()
        await persona_deps.initialize()
        
        try:
            # Get personalities from persona store
            responses = []
            
            for char in characters:
                personality = personality_manager.get(char.character_id)
                responses.append(CharacterResponse(
                    channel_id=char.channel_id,
                    character_id=char.character_id,
                    persona_id=char.persona_id,
                    name=personality.name if personality else None,
                    byline=personality.byline if personality else None,
                    profile_image=personality.profile_image if personality else None
                ))
            
            return responses
        finally:
            await persona_deps.cleanup()
    
    except Exception as e:
        logger.exception(f"Error listing characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-history", response_model=dict)
async def clear_history_endpoint(
    request: ClearHistoryRequest,
    deps: Annotated[DiscordCharactersDeps, Depends(get_discord_characters_deps)]
):
    """Clear conversation history for a channel (optionally for a specific character)."""
    try:
        success, message = await deps.character_manager.clear_history(
            request.channel_id,
            request.character_id
        )
        
        return {
            "success": success,
            "message": message
        }
    
    except Exception as e:
        logger.exception(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    deps: Annotated[DiscordCharactersDeps, Depends(get_discord_characters_deps)]
):
    """Generate a character response to a user message."""
    try:
        # Get character
        character = await deps.character_manager.get_character(
            request.channel_id,
            request.character_id
        )
        
        if not character:
            raise HTTPException(
                status_code=404,
                detail=f"Character '{request.character_id}' is not active in this channel"
            )
        
        # Get conversation context
        context_messages = await deps.character_manager.get_conversation_context(
            request.channel_id, request.character_id, limit=20
        )
        
        # Call conversation service
        from server.projects.conversation.services.orchestrator import ConversationOrchestrator
        from server.projects.persona.tools import get_voice_instructions
        
        persona_deps = PersonaDeps.from_settings()
        await persona_deps.initialize()
        
        try:
            # Get voice instructions
            voice_instructions = await get_voice_instructions(
                persona_deps, request.user_id, character.persona_id
            )
            
            # Create orchestrator
            orchestrator = ConversationOrchestrator(llm_client=persona_deps.openai_client)
            
            # Plan and generate response
            available_tools = []
            plan = await orchestrator.plan_response(
                request.message, voice_instructions, available_tools
            )
            
            tool_results = {}
            response = await orchestrator.generate_response(
                request.message, voice_instructions, tool_results, plan
            )
            
            # Record messages
            from server.services.discord_characters.models import CharacterMessage
            from datetime import datetime
            
            user_msg = CharacterMessage(
                channel_id=request.channel_id,
                character_id=request.character_id,
                user_id=request.user_id,
                content=request.message,
                role="user",
                timestamp=datetime.utcnow(),
                message_id=request.message_id
            )
            await deps.character_manager.record_message(user_msg)
            
            assistant_msg = CharacterMessage(
                channel_id=request.channel_id,
                character_id=request.character_id,
                user_id=request.user_id,
                content=response,
                role="assistant",
                timestamp=datetime.utcnow()
            )
            await deps.character_manager.record_message(assistant_msg)
            
            # Get character name from persona store
            persona_deps = PersonaDeps.from_settings()
            await persona_deps.initialize()
            try:
                personality = persona_deps.persona_store.get_personality(request.character_id)
                character_name = personality.name if personality else None
            finally:
                await persona_deps.cleanup()
            
            return ChatResponse(
                success=True,
                response=response,
                character_id=request.character_id,
                character_name=character_name
            )
        finally:
            await persona_deps.cleanup()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating chat response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/engage", response_model=EngageResponse)
async def engage_endpoint(
    request: EngageRequest,
    deps: Annotated[DiscordCharactersDeps, Depends(get_discord_characters_deps)]
):
    """Check if a character should engage in a conversation."""
    try:
        # Get character
        character = await deps.character_manager.get_character(
            request.channel_id,
            request.character_id
        )
        
        if not character:
            raise HTTPException(
                status_code=404,
                detail=f"Character '{request.character_id}' is not active in this channel"
            )
        
        # Simple engagement logic: 15% chance
        import random
        from server.projects.discord_characters.config import config
        
        should_engage = random.random() < config.ENGAGEMENT_PROBABILITY
        
        if not should_engage:
            return EngageResponse(
                should_engage=False,
                character_id=request.character_id
            )
        
        # Generate response based on recent messages
        recent_context = "\n".join(request.recent_messages[-5:])  # Last 5 messages
        
        from server.projects.conversation.services.orchestrator import ConversationOrchestrator
        from server.projects.persona.tools import get_voice_instructions
        
        persona_deps = PersonaDeps.from_settings()
        await persona_deps.initialize()
        
        try:
            # Get voice instructions
            voice_instructions = await get_voice_instructions(
                persona_deps, "discord_channel", character.persona_id
            )
            
            # Create orchestrator
            orchestrator = ConversationOrchestrator(llm_client=persona_deps.openai_client)
            
            # Generate engagement message
            engagement_prompt = f"Based on this conversation context, generate a brief, natural response that fits your character:\n\n{recent_context}\n\nKeep it short and conversational."
            
            plan = await orchestrator.plan_response(
                engagement_prompt, voice_instructions, []
            )
            
            response = await orchestrator.generate_response(
                engagement_prompt, voice_instructions, {}, plan
            )
            
            return EngageResponse(
                should_engage=True,
                response=response,
                character_id=request.character_id
            )
        finally:
            await persona_deps.cleanup()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error checking engagement: {e}")
        raise HTTPException(status_code=500, detail=str(e))
