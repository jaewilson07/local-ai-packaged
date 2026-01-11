#!/usr/bin/env python3
"""Relationship management example using Persona project.

This example demonstrates how the Persona project tracks and manages
relationship state between users and personas.

Relationship state includes:
- Affection level
- Trust level
- Interaction history
- Relationship dynamics

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

from server.projects.persona.actions.track_relationship import track_relationship_action
from server.projects.persona.dependencies import PersonaDeps

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate relationship management."""
    # Example user and persona IDs
    user_id = "user_123"
    persona_id = "persona_456"

    # Example interactions showing relationship development
    interactions = [
        {
            "user_message": "Hello, nice to meet you!",
            "bot_response": "Hello! Nice to meet you too. I'm here to help.",
            "description": "Initial greeting",
        },
        {
            "user_message": "You've been really helpful. Thank you!",
            "bot_response": "I'm glad I could help! I enjoy our conversations.",
            "description": "Positive feedback",
        },
        {
            "user_message": "I trust your advice on this matter.",
            "bot_response": "Thank you for trusting me. I'll do my best to help.",
            "description": "Trust expression",
        },
    ]

    print("=" * 80)
    print("Persona - Relationship Management Example")
    print("=" * 80)
    print()
    print("This example demonstrates relationship state tracking:")
    print("  - Tracks affection and trust levels")
    print("  - Analyzes relationship dynamics from interactions")
    print("  - Updates relationship state in MongoDB")
    print()
    print(f"User ID: {user_id}")
    print(f"Persona ID: {persona_id}")
    print()

    # Initialize dependencies
    deps = PersonaDeps.from_settings()
    await deps.initialize()

    try:
        # Get initial relationship state
        initial_relationship = deps.persona_store.get_relationship(user_id, persona_id)
        if initial_relationship:
            print("Initial Relationship State:")
            print(f"  Affection: {initial_relationship.affection:.2f}")
            print(f"  Trust: {initial_relationship.trust:.2f}")
            print(f"  Timestamp: {initial_relationship.timestamp}")
        else:
            print("No existing relationship state (starting fresh)")
        print()

        # Process each interaction
        for i, interaction in enumerate(interactions, 1):
            print(f"\n{'=' * 80}")
            print(f"Interaction {i}: {interaction['description']}")
            print("=" * 80)
            print(f"User: {interaction['user_message']}")
            print(f"Bot: {interaction['bot_response']}")
            print()

            logger.info(f"Tracking relationship for interaction {i}...")

            # Track relationship
            await track_relationship_action(
                user_message=interaction["user_message"],
                bot_response=interaction["bot_response"],
                persona_store=deps.persona_store,
                user_id=user_id,
                persona_id=persona_id,
                llm_client=deps.openai_client,
            )

            # Get updated relationship state
            updated_relationship = deps.persona_store.get_relationship(user_id, persona_id)
            if updated_relationship:
                print("✅ Updated Relationship State:")
                print(f"   Affection: {updated_relationship.affection:.2f}")
                print(f"   Trust: {updated_relationship.trust:.2f}")
                print(f"   Timestamp: {updated_relationship.timestamp}")

        print("\n" + "=" * 80)
        print("✅ Relationship management demonstration completed!")
        print("=" * 80)
        print()
        print("Relationship state is stored in MongoDB and persists across sessions.")
        print("The persona can use this relationship state to adjust its")
        print("interaction style and level of intimacy with the user.")
        print("=" * 80)

    except Exception as e:
        logger.exception(f"❌ Error during relationship management: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
