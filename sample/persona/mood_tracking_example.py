#!/usr/bin/env python3
"""Mood tracking example using Persona project.

This example demonstrates how the Persona project tracks and analyzes
mood state from conversations using LLM-based analysis.

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

from server.projects.persona.actions.track_mood import analyze_mood_from_interaction
from server.projects.persona.dependencies import PersonaDeps

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate mood tracking."""
    # Example user and persona IDs
    user_id = "user_123"
    persona_id = "persona_456"

    # Example interactions with different emotional tones
    interactions = [
        {
            "user_message": "I'm so excited about this new project!",
            "bot_response": "That's wonderful! I'm glad you're excited. What aspects are you most looking forward to?",
        },
        {
            "user_message": "I'm feeling a bit overwhelmed with all these tasks.",
            "bot_response": "I understand that can be stressful. Let's break it down into smaller steps.",
        },
        {
            "user_message": "This is frustrating. Nothing seems to be working.",
            "bot_response": "I hear your frustration. Let's troubleshoot this together step by step.",
        },
    ]

    print("=" * 80)
    print("Persona - Mood Tracking Example")
    print("=" * 80)
    print()
    print("This example demonstrates mood tracking from conversations:")
    print("  - Analyzes user and bot messages for emotional content")
    print("  - Uses LLM to identify primary emotion and intensity")
    print("  - Updates persona mood state in MongoDB")
    print()
    print(f"User ID: {user_id}")
    print(f"Persona ID: {persona_id}")
    print()

    # Initialize dependencies
    deps = PersonaDeps.from_settings()
    await deps.initialize()

    try:
        # Process each interaction
        for i, interaction in enumerate(interactions, 1):
            print(f"\n{'=' * 80}")
            print(f"Interaction {i}")
            print("=" * 80)
            print(f"User: {interaction['user_message']}")
            print(f"Bot: {interaction['bot_response']}")
            print()

            logger.info(f"Analyzing mood for interaction {i}...")

            # Analyze mood from interaction
            mood = analyze_mood_from_interaction(
                user_message=interaction["user_message"],
                bot_response=interaction["bot_response"],
                persona_store=deps.persona_store,
                user_id=user_id,
                persona_id=persona_id,
                llm_client=deps.openai_client,
            )

            # Display mood analysis
            print("✅ Mood Analysis:")
            print(f"   Primary Emotion: {mood.primary_emotion}")
            print(f"   Intensity: {mood.intensity:.2f}")
            print(f"   Timestamp: {mood.timestamp}")
            print()

            # Get current mood from store
            current_mood = deps.persona_store.get_mood(user_id, persona_id)
            if current_mood:
                print("Current Mood State:")
                print(f"   Primary Emotion: {current_mood.primary_emotion}")
                print(f"   Intensity: {current_mood.intensity:.2f}")
                print(f"   Timestamp: {current_mood.timestamp}")

        print("=" * 80)
        print("✅ Mood tracking demonstration completed!")
        print("=" * 80)
        print()
        print("Mood state is stored in MongoDB and persists across sessions.")
        print("The persona can use this mood state to adjust its voice")
        print("and response style to match the user's emotional state.")
        print("=" * 80)

        # Verify via API
        try:
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
                collection="persona_moods",
                expected_count_min=len(interactions),
            )
            print(message)

            if success:
                print("\n✅ Verification passed!")
                sys.exit(0)
            else:
                print("\n⚠️  Verification failed (data may need time to propagate)")
                sys.exit(1)
        except Exception as e:
            logger.warning(f"Verification error: {e}")
            print(f"\n⚠️  Verification error: {e}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ Error during mood tracking: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
