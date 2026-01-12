#!/usr/bin/env python3
"""Enhanced RAG example using MongoDB RAG.

This example demonstrates advanced RAG capabilities including:
- Query decomposition: Breaking complex queries into sub-queries
- Document grading: Filtering irrelevant documents using LLM
- Citation extraction: Identifying and formatting citations
- Result synthesis: Combining results from multiple sub-queries

Enhanced RAG provides better answers for complex, multi-part questions.

Prerequisites:
- MongoDB running with documents ingested
- LLM available (Ollama or OpenAI) for decomposition and grading
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, etc.)
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

import logging

from server.projects.mongo_rag.agent import rag_agent
from server.projects.mongo_rag.dependencies import AgentDependencies

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate enhanced RAG capabilities."""
    # Example queries of varying complexity
    simple_query = "What is authentication?"
    complex_query = (
        "What is authentication and how does it differ from authorization? Also explain OAuth2."
    )

    print("=" * 80)
    print("MongoDB RAG - Enhanced RAG Example")
    print("=" * 80)
    print()
    print("This example demonstrates advanced RAG features:")
    print("  - Query decomposition: Breaks complex queries into sub-queries")
    print("  - Document grading: Filters irrelevant documents using LLM")
    print("  - Citation extraction: Identifies sources for answers")
    print("  - Result synthesis: Combines results from multiple queries")
    print()

    # Initialize dependencies with user context (for RLS)
    # In production, these would come from authenticated user session
    from uuid import uuid4

    user_id = str(uuid4())  # Simulated user ID
    user_email = "demo@example.com"  # Simulated user email

    deps = AgentDependencies.from_settings(
        user_id=user_id, user_email=user_email, is_admin=False, user_groups=[]
    )
    await deps.initialize()

    try:
        # 1. Simple query (no decomposition needed)
        print("=" * 80)
        print("1. SIMPLE QUERY (No Decomposition)")
        print("=" * 80)
        print(f"Query: {simple_query}")
        print()

        logger.info("🔍 Performing enhanced search for simple query...")
        simple_result = await rag_agent.run(simple_query, deps=deps)

        print("Result:")
        print(simple_result.data)
        print()

        # 2. Complex query (will be decomposed)
        print("=" * 80)
        print("2. COMPLEX QUERY (With Decomposition)")
        print("=" * 80)
        print(f"Query: {complex_query}")
        print()
        print("This query will be decomposed into multiple sub-queries:")
        print("  - What is authentication?")
        print("  - How does authentication differ from authorization?")
        print("  - Explain OAuth2")
        print()

        logger.info("🔍 Performing enhanced search for complex query...")
        complex_result = await rag_agent.run(complex_query, deps=deps)

        print("Result:")
        print(complex_result.data)
        print()

        # 3. Enhanced search with query rewriting
        print("=" * 80)
        print("3. ENHANCED SEARCH WITH QUERY REWRITING")
        print("=" * 80)
        print("Query: 'auth stuff'")
        print("(This will be rewritten to a better query)")
        print()

        logger.info("🔍 Performing enhanced search with query rewriting...")
        rewritten_result = await rag_agent.run("auth stuff", deps=deps)

        print("Result:")
        print(rewritten_result.data)
        print()

        print("=" * 80)
        print("✅ Enhanced RAG demonstration completed!")
        print("=" * 80)
        print()
        print("Key benefits of enhanced RAG:")
        print("  - Better handling of complex, multi-part questions")
        print("  - Automatic filtering of irrelevant documents")
        print("  - Clear citations for source tracking")
        print("  - Synthesized answers from multiple sources")
        print("=" * 80)

        # Verify via API
        try:
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
                print("\n⚠️  Verification failed (data may need time to propagate)")
                sys.exit(1)
        except Exception as e:
            logger.warning(f"Verification error: {e}")
            print(f"\n⚠️  Verification error: {e}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ Error during enhanced RAG demo: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
