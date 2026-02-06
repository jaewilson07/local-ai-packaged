"""Backwards compatibility module - re-exports from persona_state/tools.

Prefer importing directly from:
    from capabilities.persona.persona_state.tools import get_voice_instructions
"""

from app.capabilities.persona.persona_state.tools import get_voice_instructions

__all__ = ["get_voice_instructions"]
