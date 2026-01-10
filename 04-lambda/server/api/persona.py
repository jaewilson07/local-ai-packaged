"""Persona project REST API."""

from fastapi import APIRouter, HTTPException
import logging

from server.projects.persona.models import (
    GetVoiceInstructionsRequest,
    RecordInteractionRequest,
    GetPersonaStateRequest,
    UpdateMoodRequest,
    VoiceInstructionsResponse,
    PersonaStateResponse,
)
from server.projects.persona.dependencies import PersonaDeps
from server.core.api_utils import with_dependencies
from server.projects.persona.tools import get_voice_instructions, record_interaction

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/get-voice", response_model=VoiceInstructionsResponse)
@with_dependencies(PersonaDeps)
async def get_voice_instructions_endpoint(
    request: GetVoiceInstructionsRequest,
    deps: PersonaDeps
):
    """
    Generate dynamic style instructions based on current persona state.
    
    Returns prompt injection with current emotional state, relationship context,
    and conversation mode to guide persona responses.
    """
    instructions = await get_voice_instructions(
        deps, request.user_id, request.persona_id
    )
    return VoiceInstructionsResponse(
        success=True,
        voice_instructions=instructions
    )


@router.post("/record-interaction")
@with_dependencies(PersonaDeps)
async def record_interaction_endpoint(
    request: RecordInteractionRequest,
    deps: PersonaDeps
):
    """
    Record an interaction to update persona state.
    
    Automatically analyzes the interaction and updates:
    - Mood state based on emotional tone
    - Relationship state based on sentiment
    - Conversation context based on mode and topic
    """
    result = await record_interaction(
        deps,
        request.user_id,
        request.persona_id,
        request.user_message,
        request.bot_response
    )
    return {
        "success": True,
        "mood": result.get("mood"),
        "relationship": result.get("relationship"),
        "context": result.get("context"),
    }


@router.get("/state", response_model=PersonaStateResponse)
@with_dependencies(PersonaDeps)
async def get_persona_state_endpoint(
    user_id: str,
    persona_id: str,
    deps: PersonaDeps
):
    """
    Get current persona state including mood, relationship, and context.
    """
    try:
        if not deps.persona_store:
            raise HTTPException(status_code=500, detail="Persona store not initialized")
        
        # Get all state components
        personality = deps.persona_store.get_personality(persona_id)
        mood = deps.persona_store.get_mood(user_id, persona_id)
        relationship = deps.persona_store.get_relationship(user_id, persona_id)
        context = deps.persona_store.get_conversation_context(user_id, persona_id)
        
        if not personality:
            raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")
        
        if not mood:
            # Create default mood
            from server.projects.persona.models import MoodState
            mood = MoodState(primary_emotion="neutral", intensity=0.5)
        
        if not relationship:
            # Create default relationship
            from server.projects.persona.models import RelationshipState
            relationship = RelationshipState(
                user_id=user_id,
                persona_id=persona_id,
                affection_score=0.0,
                trust_level=0.5,
                interaction_count=0
            )
        
        if not context:
            # Create default context
            from server.projects.persona.models import ConversationContext
            context = ConversationContext(mode="balanced", depth_level=3)
        
        from server.projects.persona.models import PersonaState
        persona_state = PersonaState(
            base_profile=personality,
            current_mood=mood,
            relationships={user_id: relationship},
            current_context=context,
            learned_preferences={}
        )
        
        return PersonaStateResponse(
            success=True,
            persona_state=persona_state
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting persona state: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await deps.cleanup()


@router.post("/update-mood")
@with_dependencies(PersonaDeps)
async def update_mood_endpoint(
    request: UpdateMoodRequest,
    deps: PersonaDeps
):
    """
    Update persona mood state.
    
    Manually set the persona's current emotional state.
    """
    try:
        if not deps.persona_store:
            raise HTTPException(status_code=500, detail="Persona store not initialized")
        
        from server.projects.persona.models import MoodState
        from datetime import datetime
        
        mood = MoodState(
            primary_emotion=request.primary_emotion,
            intensity=request.intensity,
            timestamp=datetime.now()
        )
        
        deps.persona_store.update_mood(request.user_id, request.persona_id, mood)
        return {
            "success": True,
            "mood": mood.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating mood: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await deps.cleanup()
