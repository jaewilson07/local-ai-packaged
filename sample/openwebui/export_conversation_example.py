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
import os
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

from server.projects.openwebui_export.dependencies import OpenWebUIExportDeps
from server.projects.openwebui_export.agent import export_conversation_tool
from server.projects.shared.context_helpers import create_run_context
from server.projects.openwebui_export.models import ConversationMessage
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        ConversationMessage(role="assistant", content="A vector database is designed to store and query high-dimensional vectors efficiently."),
        ConversationMessage(role="user", content="How does it differ from traditional databases?"),
        ConversationMessage(role="assistant", content="Traditional databases excel at exact matches, while vector databases use similarity search for semantic matching."),
    ]
    topics = ["vector-databases", "database-comparison"]
    
    print("="*80)
    print("Open WebUI - Export Conversation Example")
    print("="*80)
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
            topics=topics
        )
        
        # Display result
        print("\n" + "="*80)
        print("EXPORT RESULT")
        print("="*80)
        print(result)
        print("="*80)
        print()
        print("✅ Conversation export completed!")
        print()
        print("The conversation is now searchable via MongoDB RAG.")
        print("Run semantic_search_example.py to search for it.")
        print("="*80)
        
    except Exception as e:
        logger.exception(f"❌ Error exporting conversation: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
