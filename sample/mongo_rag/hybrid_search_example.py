#!/usr/bin/env python3
"""Hybrid search example using MongoDB RAG.

This example demonstrates hybrid search that combines semantic (vector)
and text (keyword) search using Reciprocal Rank Fusion (RRF) for optimal results.

Hybrid search provides better results than semantic-only or text-only search
by leveraging both meaning similarity and keyword matching.

Prerequisites:
- MongoDB running with vector search index configured
- Documents ingested into MongoDB (use document_ingestion_example.py)
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, EMBEDDING_BASE_URL, etc.)
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

from server.projects.mongo_rag.dependencies import AgentDependencies
from server.projects.mongo_rag.tools import hybrid_search, semantic_search, text_search
from server.projects.shared.context_helpers import create_run_context

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate hybrid search vs semantic-only and text-only."""
    query = "authentication and authorization"

    print("=" * 80)
    print("MongoDB RAG - Hybrid Search Example")
    print("=" * 80)
    print()
    print("This example compares:")
    print("  1. Semantic search (vector similarity only)")
    print("  2. Text search (keyword matching only)")
    print("  3. Hybrid search (combines both using RRF)")
    print()
    print(f"Query: {query}")
    print()

    # Initialize dependencies with user context (for RLS)
    # In production, these would come from authenticated user session
    from uuid import uuid4
    user_id = str(uuid4())  # Simulated user ID
    user_email = "demo@example.com"  # Simulated user email
    
    deps = AgentDependencies.from_settings(
        user_id=user_id,
        user_email=user_email,
        is_admin=False,
        user_groups=[]
    )
    await deps.initialize()

    try:
        # Create run context for search tools
        ctx = create_run_context(deps)

        # 1. Semantic search only
        print("=" * 80)
        print("1. SEMANTIC SEARCH (Vector Similarity)")
        print("=" * 80)
        logger.info("🔍 Performing semantic search...")
        semantic_results = await semantic_search(ctx=ctx, query=query, match_count=5)
        print(f"Found {len(semantic_results)} results")
        for i, result in enumerate(semantic_results[:3], 1):
            print(f"  {i}. [{result.similarity:.3f}] {result.document_title}")
        print()

        # 2. Text search only
        print("=" * 80)
        print("2. TEXT SEARCH (Keyword Matching)")
        print("=" * 80)
        logger.info("🔍 Performing text search...")
        text_results = await text_search(ctx=ctx, query=query, match_count=5)
        print(f"Found {len(text_results)} results")
        for i, result in enumerate(text_results[:3], 1):
            print(f"  {i}. [{result.similarity:.3f}] {result.document_title}")
        print()

        # 3. Hybrid search (combines both)
        print("=" * 80)
        print("3. HYBRID SEARCH (Semantic + Text with RRF)")
        print("=" * 80)
        logger.info("🔍 Performing hybrid search...")
        hybrid_results = await hybrid_search(ctx=ctx, query=query, match_count=5)
        print(f"Found {len(hybrid_results)} results")
        print("\nTop results (ranked by RRF score):")
        for i, result in enumerate(hybrid_results[:5], 1):
            print(f"\n  {i}. Similarity: {result.similarity:.3f}")
            print(f"     Title: {result.document_title}")
            print(f"     Source: {result.document_source}")
            print(f"     Content: {result.content[:150]}...")

        print("\n" + "=" * 80)
        print("✅ Hybrid search comparison completed!")
        print("=" * 80)
        print("\nNote: Hybrid search typically provides better results by combining")
        print("      both semantic understanding and keyword matching.")
        print("=" * 80)

    except Exception as e:
        logger.exception(f"❌ Error during hybrid search: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
