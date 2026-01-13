#!/usr/bin/env python3
"""Memory tools example using MongoDB RAG.

This example demonstrates how to use MongoDB RAG's memory tools to:
- Store and retrieve conversation messages
- Store and search facts
- Store web content for later retrieval
- Get context windows for conversations

Memory tools enable persistent conversation context and knowledge storage.

Prerequisites:
- MongoDB running
- Environment variables configured (MONGODB_URI, etc.)
"""

import asyncio
import os
import sys
from pathlib import Path

# Set environment variables for host execution (not Docker)
# These override defaults that use Docker hostnames
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
# MongoDB with authentication (default credentials: admin/admin123)
os.environ.setdefault(
    "MONGODB_URI",
    "mongodb://admin:admin123@localhost:27017/?directConnection=true&authSource=admin",
)

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from server.projects.mongo_rag.dependencies import AgentDependencies  # noqa: E402
from server.projects.mongo_rag.memory_tools import MemoryTools  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate memory tools functionality."""
    # Example user and persona IDs
    user_id = "user_123"
    persona_id = "persona_456"

    print("=" * 80)
    print("MongoDB RAG - Memory Tools Example")
    print("=" * 80)
    print()
    print("This example demonstrates memory tools for:")
    print("  - Storing and retrieving conversation messages")
    print("  - Storing and searching facts")
    print("  - Storing web content")
    print("  - Getting context windows")
    print()
    print(f"User ID: {user_id}")
    print(f"Persona ID: {persona_id}")
    print()

    # Initialize dependencies with user context (for RLS)
    # In production, these would come from authenticated user session
    from uuid import uuid4

    deps_user_id = str(uuid4())  # Simulated user ID for dependencies
    deps_user_email = "demo@example.com"  # Simulated user email

    deps = AgentDependencies.from_settings(
        user_id=deps_user_id, user_email=deps_user_email, is_admin=False, user_groups=[]
    )
    await deps.initialize()

    try:
        # Create memory tools instance
        memory_tools = MemoryTools(deps=deps)

        # 1. Store conversation messages
        print("=" * 80)
        print("1. STORING CONVERSATION MESSAGES")
        print("=" * 80)

        messages = [
            ("user", "Hello! I'm interested in learning about vector databases."),
            (
                "assistant",
                "Great! Vector databases are designed to store and search high-dimensional vectors efficiently.",
            ),
            ("user", "How do they compare to traditional databases?"),
            (
                "assistant",
                "Traditional databases excel at exact matches, while vector databases use similarity search for semantic matching.",
            ),
        ]

        for role, content in messages:
            memory_tools.record_message(
                user_id=user_id, persona_id=persona_id, content=content, role=role
            )
            print(f"  ✅ Stored {role} message: {content[:50]}...")

        print()

        # 2. Retrieve context window
        print("=" * 80)
        print("2. RETRIEVING CONTEXT WINDOW")
        print("=" * 80)

        context_messages = memory_tools.get_context_window(
            user_id=user_id, persona_id=persona_id, limit=10
        )

        print(f"Retrieved {len(context_messages)} messages:")
        for msg in context_messages:
            print(f"  [{msg.role}]: {msg.content[:80]}...")
        print()

        # 3. Store facts
        print("=" * 80)
        print("3. STORING FACTS")
        print("=" * 80)

        facts = [
            "User prefers technical explanations with examples",
            "User is interested in database technologies",
            "User works in software development",
        ]

        for fact in facts:
            memory_tools.store_fact(
                user_id=user_id, persona_id=persona_id, fact=fact, tags=["preference", "interest"]
            )
            print(f"  ✅ Stored fact: {fact}")
        print()

        # 4. Search facts
        print("=" * 80)
        print("4. SEARCHING FACTS")
        print("=" * 80)

        found_facts = memory_tools.search_facts(
            user_id=user_id, persona_id=persona_id, query="database technologies", limit=5
        )

        print(f"Found {len(found_facts)} facts matching 'database technologies':")
        for fact in found_facts:
            print(f"  - {fact.fact}")
            if fact.tags:
                print(f"    Tags: {', '.join(fact.tags)}")
        print()

        # 5. Store web content
        print("=" * 80)
        print("5. STORING WEB CONTENT")
        print("=" * 80)

        web_content = """
        Vector databases are a type of database designed to store and query high-dimensional vectors.
        They use approximate nearest neighbor (ANN) algorithms to find similar vectors efficiently.
        Common use cases include semantic search, recommendation systems, and similarity matching.
        """

        memory_tools.store_web_content(
            user_id=user_id,
            persona_id=persona_id,
            content=web_content,
            source_url="https://example.com/vector-databases",
            source_title="Introduction to Vector Databases",
            source_description="A comprehensive guide to vector databases",
            source_domain="example.com",
            tags=["vector-databases", "tutorial"],
        )

        print("  ✅ Stored web content from: https://example.com/vector-databases")
        print()

        # 6. Search web content
        print("=" * 80)
        print("6. SEARCHING WEB CONTENT")
        print("=" * 80)

        web_results = memory_tools.search_web_content(
            user_id=user_id, persona_id=persona_id, query="ANN algorithms", limit=5
        )

        print(f"Found {len(web_results)} web content items matching 'ANN algorithms':")
        for item in web_results:
            print(f"  - {item.source_title}")
            print(f"    URL: {item.source_url}")
            print(f"    Content: {item.content[:100]}...")
        print()

        print("=" * 80)
        print("✅ Memory tools demonstration completed!")
        print("=" * 80)
        print()
        print("All stored data persists in MongoDB and can be retrieved across sessions.")
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
            collection="memory_messages",
            expected_count_min=1,
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
