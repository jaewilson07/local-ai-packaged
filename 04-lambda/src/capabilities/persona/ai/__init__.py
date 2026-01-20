"""Persona AI submodule.

Exports for convenient imports.
"""

from capabilities.persona.ai.dependencies import PersonaDeps
from capabilities.persona.ai.persona_agent import PersonaAgentState, persona_agent
from capabilities.persona.ai.tools import get_voice_instructions

__all__ = [
    "PersonaAgentState",
    "PersonaDeps",
    "get_voice_instructions",
    "persona_agent",
]
