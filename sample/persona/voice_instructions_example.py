#!/usr/bin/env python3
"""Voice instructions example using Persona project.

This example demonstrates how the Persona project generates dynamic
voice instructions based on current persona state (mood, relationship, context).

Voice instructions guide how a persona should respond based on:
- Current emotional state
- Relationship with the user
- Conversation context

Prerequisites:
- MongoDB running
- Ollama or OpenAI configured
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, etc.)
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging

from server.projects.persona.agent import get_persona_voice_instructions_tool
from server.projects.persona.dependencies import PersonaDeps
from server.projects.shared.context_helpers import create_run_context

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate voice instructions generation."""
    # Example user and persona IDs
    user_id = "user_123"
    persona_id = "persona_456"

    print("=" * 80)
    print("Persona - Voice Instructions Example")
    print("=" * 80)
    print()
    print("This example demonstrates voice instructions generation:")
    print("  - Generates dynamic style instructions from persona state")
    print("  - Incorporates current mood, relationship, and context")
    print("  - Guides persona response style and tone")
    print()
    print(f"User ID: {user_id}")
    print(f"Persona ID: {persona_id}")
    print()

    # Initialize dependencies
    deps = PersonaDeps.from_settings()
    await deps.initialize()

    try:
        # Create run context for tools
        ctx = create_run_context(deps)

        # Get voice instructions
        print("🔍 Generating voice instructions...")
        logger.info(f"Getting voice instructions for user: {user_id}, persona: {persona_id}")

        voice_instructions = await get_persona_voice_instructions_tool(
            ctx=ctx, user_id=user_id, persona_id=persona_id
        )

        # Display voice instructions
        print("\n" + "=" * 80)
        print("VOICE INSTRUCTIONS")
        print("=" * 80)
        print(voice_instructions)
        print("=" * 80)
        print()
        print("✅ Voice instructions generated!")
        print()
        print("These instructions guide the persona's response style based on:")
        print("  - Current emotional state (mood)")
        print("  - Relationship with the user (affection, trust)")
        print("  - Conversation context (topics, mode)")
        print("=" * 80)

    except Exception as e:
        logger.exception(f"❌ Error generating voice instructions: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
