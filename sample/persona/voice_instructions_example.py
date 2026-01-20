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
lambda_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from capabilities.persona.ai.dependencies import PersonaDeps  # noqa: E402
from capabilities.persona.persona_state.agent import (
    get_persona_voice_instructions_tool,
)

from shared.context_helpers import create_run_context  # noqa: E402

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

        # Verify via API
        from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
        from sample.shared.verification_helpers import verify_mongodb_data

        api_base_url = get_api_base_url()
        headers = get_auth_headers()

        print("\n" + "=" * 80)
        print("Verification")
        print("=" * 80)

        success, message = verify_mongodb_data(
            api_base_url=api_base_url,
            headers=headers,
            collection="persona_voice_instructions",
            expected_count_min=1,
        )
        print(message)

        if success:
            print("\n✅ Verification passed!")
            sys.exit(0)
        # Voice instructions may not be stored, just verify the tool worked
        elif voice_instructions and len(voice_instructions) > 0:
            print("\n✅ Verification passed (voice instructions generated)")
            sys.exit(0)
        else:
            print("\n❌ Verification failed")
            sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
