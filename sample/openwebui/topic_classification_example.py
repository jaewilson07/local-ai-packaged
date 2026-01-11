#!/usr/bin/env python3
"""Topic classification example using Open WebUI Topics project.

This example demonstrates how to classify topics for a conversation
using LLM-based analysis to identify main themes.

Prerequisites:
- Ollama or OpenAI configured
- Environment variables configured (LLM_BASE_URL, LLM_MODEL, etc.)
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging

from server.projects.openwebui_topics.agent import classify_topics_tool
from server.projects.openwebui_topics.dependencies import OpenWebUITopicsDeps
from server.projects.shared.context_helpers import create_run_context

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Classify topics for a conversation."""
    # Example conversation
    conversation_id = "conv_123"
    title = "Database Discussion"
    messages = [
        {"role": "user", "content": "What is MongoDB?"},
        {"role": "assistant", "content": "MongoDB is a NoSQL document database."},
        {"role": "user", "content": "How does it compare to PostgreSQL?"},
        {
            "role": "assistant",
            "content": "MongoDB is document-based while PostgreSQL is relational.",
        },
        {"role": "user", "content": "What about vector search capabilities?"},
        {
            "role": "assistant",
            "content": "MongoDB Atlas supports vector search for semantic queries.",
        },
    ]

    print("=" * 80)
    print("Open WebUI - Topic Classification Example")
    print("=" * 80)
    print()
    print("This example demonstrates topic classification:")
    print("  - Analyzes conversation content using LLM")
    print("  - Identifies 3-5 main topics")
    print("  - Provides reasoning for classification")
    print()
    print(f"Conversation ID: {conversation_id}")
    print(f"Title: {title}")
    print(f"Messages: {len(messages)}")
    print()

    # Initialize dependencies
    deps = OpenWebUITopicsDeps.from_settings()
    await deps.initialize()

    try:
        # Create run context for tools
        ctx = create_run_context(deps)

        # Classify topics
        print("🔍 Classifying topics...")
        logger.info(f"Classifying topics for conversation: {conversation_id}")

        result = await classify_topics_tool(
            ctx=ctx, conversation_id=conversation_id, messages=messages, title=title
        )

        # Display result
        print("\n" + "=" * 80)
        print("TOPIC CLASSIFICATION RESULT")
        print("=" * 80)
        print(result)
        print("=" * 80)
        print()
        print("✅ Topic classification completed!")
        print()
        print("Topics can be used for:")
        print("  - Organizing conversations")
        print("  - Filtering and searching")
        print("  - Building knowledge bases")
        print("=" * 80)

    except Exception as e:
        logger.exception(f"❌ Error classifying topics: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
