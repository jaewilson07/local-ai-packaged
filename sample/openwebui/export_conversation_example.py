#!/usr/bin/env python3
"""Export conversation example using Open WebUI Export project.

This example demonstrates how to export an Open WebUI conversation
to MongoDB RAG, making it searchable via semantic search.

Prerequisites:
- MongoDB running
- Ollama or OpenAI configured (for embeddings)
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, EMBEDDING_BASE_URL, etc.)
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from server.projects.openwebui_export.agent import export_conversation_tool  # noqa: E402
from server.projects.openwebui_export.dependencies import OpenWebUIExportDeps  # noqa: E402
from server.projects.openwebui_export.models import ConversationMessage  # noqa: E402
from server.projects.shared.context_helpers import create_run_context  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Export a conversation to MongoDB RAG."""
    # Example conversation
    conversation_id = "conv_123"
    user_id = "user_123"
    title = "Vector Database Discussion"
    messages = [
        ConversationMessage(role="user", content="What is a vector database?"),
        ConversationMessage(
            role="assistant",
            content="A vector database is designed to store and query high-dimensional vectors efficiently.",
        ),
        ConversationMessage(role="user", content="How does it differ from traditional databases?"),
        ConversationMessage(
            role="assistant",
            content="Traditional databases excel at exact matches, while vector databases use similarity search for semantic matching.",
        ),
    ]
    topics = ["vector-databases", "database-comparison"]

    print("=" * 80)
    print("Open WebUI - Export Conversation Example")
    print("=" * 80)
    print()
    print("This example demonstrates exporting a conversation to MongoDB RAG:")
    print("  - Exports conversation messages to MongoDB")
    print("  - Chunks conversation for semantic search")
    print("  - Generates embeddings for searchability")
    print("  - Preserves metadata (ID, title, topics)")
    print()
    print(f"Conversation ID: {conversation_id}")
    print(f"Title: {title}")
    print(f"Messages: {len(messages)}")
    print(f"Topics: {topics}")
    print()

    # Initialize dependencies
    deps = OpenWebUIExportDeps.from_settings()
    await deps.initialize()

    try:
        # Create run context for tools
        ctx = create_run_context(deps)

        # Export conversation
        print("🚀 Exporting conversation...")
        logger.info(f"Exporting conversation: {conversation_id}")

        result = await export_conversation_tool(
            ctx=ctx,
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            messages=messages,
            topics=topics,
        )

        # Display result
        print("\n" + "=" * 80)
        print("EXPORT RESULT")
        print("=" * 80)
        print(result)
        print("=" * 80)
        print()
        print("✅ Conversation export completed!")
        print()
        print("The conversation is now searchable via MongoDB RAG.")
        print("Run semantic_search_example.py to search for it.")
        print("=" * 80)

        # Verify via API
        from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
        from sample.shared.verification_helpers import verify_rag_data

        api_base_url = get_api_base_url()
        headers = get_auth_headers()

        print("\n" + "=" * 80)
        print("Verification")
        print("=" * 80)

        success, message = verify_rag_data(
            api_base_url=api_base_url,
            headers=headers,
            expected_documents_min=1,
        )
        print(message)

        if success:
            print("\n✅ Verification passed!")
            sys.exit(0)
        else:
            print("\n❌ Verification failed (data may need time to propagate)")
            sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
