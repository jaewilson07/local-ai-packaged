"""Persona capability - Character personality and state management.

IMPORTANT: To avoid circular imports, import specific items from submodules:
    - from capabilities.persona.ai.dependencies import PersonaDeps
    - from capabilities.persona.ai.persona_agent import persona_agent
    - from capabilities.persona.router import router
    - from capabilities.persona.schemas import PersonaState
"""

# Only export safe leaf modules that don't cause circular imports
__all__: list[str] = []
