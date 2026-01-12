#!/usr/bin/env python3
"""Multi-agent coordination example using Conversation project.

This example demonstrates how the Conversation project coordinates
multiple specialized agents (persona, memory, knowledge, calendar)
to deliver comprehensive, context-aware responses.

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

from pydantic_ai import RunContext, StateDeps

from server.projects.conversation.agent import ConversationState, orchestrate_conversation_tool
from server.projects.persona.dependencies import PersonaDeps

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate multi-agent coordination."""
    # Example user and persona IDs
    user_id = "user_123"
    persona_id = "persona_456"

    # Complex message requiring multiple agents
    complex_message = """
    I need help with a few things:
    1. Search for information about MongoDB vector search
    2. Check my calendar for events this week
    3. Remember that I prefer technical explanations with examples
    """

    print("=" * 80)
    print("Conversation - Multi-Agent Coordination Example")
    print("=" * 80)
    print()
    print("This example demonstrates multi-agent coordination:")
    print("  - Persona agent: Provides voice instructions")
    print("  - Memory agent: Retrieves conversation history")
    print("  - Knowledge agent: Searches knowledge base")
    print("  - Calendar agent: Accesses calendar events")
    print("  - Orchestrator: Coordinates all agents")
    print()
    print(f"User ID: {user_id}")
    print(f"Persona ID: {persona_id}")
    print()
    print("Complex message requiring multiple agents:")
    print(complex_message)
    print()

    # Initialize dependencies (conversation uses PersonaDeps)
    persona_deps = PersonaDeps.from_settings()
    await persona_deps.initialize()

    try:
        # Create state dependencies for the agent
        state_deps = StateDeps[ConversationState](deps=persona_deps, state={})

        # Create run context
        ctx = RunContext(deps=state_deps, state={}, agent=None, run_id="")

        # Orchestrate conversation with multi-agent coordination
        logger.info("Orchestrating multi-agent conversation...")

        response = await orchestrate_conversation_tool(
            ctx=ctx, user_id=user_id, persona_id=persona_id, message=complex_message
        )

        # Display response
        print("=" * 80)
        print("ORCHESTRATED RESPONSE")
        print("=" * 80)
        print(response)
        print("=" * 80)
        print()
        print("✅ Multi-agent coordination completed!")
        print()
        print("The orchestrator coordinated:")
        print("  - Persona agent for voice instructions")
        print("  - Memory agent for context retrieval")
        print("  - Knowledge agent for information search")
        print("  - Calendar agent for event access")
        print("  - Generated a comprehensive, context-aware response")
        print("=" * 80)

        # Verify that orchestration completed successfully
        try:
            from sample.shared.verification_helpers import verify_search_results

            print("\n" + "=" * 80)
            print("Verification")
            print("=" * 80)

            # Check if response was generated
            success, message = verify_search_results([response] if response else [], expected_min=1)
            print(message)

            if success:
                print("\n✅ Verification passed!")
                sys.exit(0)
            else:
                print("\n⚠️  Verification failed: No response generated")
                sys.exit(1)
        except Exception as e:
            logger.warning(f"Verification error: {e}")
            print(f"\n⚠️  Verification error: {e}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ Error during multi-agent coordination: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await persona_deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
