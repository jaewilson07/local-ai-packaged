#!/usr/bin/env python3
"""Semantic search example using MongoDB RAG.

This example demonstrates how to perform pure semantic (vector) search
over documents stored in MongoDB using vector similarity.

Prerequisites:
- MongoDB running with vector search index configured
- Documents ingested into MongoDB (use document_ingestion_example.py)
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, EMBEDDING_BASE_URL, etc.)
"""

import asyncio
import sys
import os
from pathlib import Path

# Set environment variables for host execution (not Docker)
# These override defaults that use Docker hostnames
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
# MongoDB with authentication (default credentials: admin/admin123)
os.environ.setdefault("MONGODB_URI", "mongodb://admin:admin123@localhost:27017/?directConnection=true&authSource=admin")

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

from server.projects.mongo_rag.dependencies import AgentDependencies
from server.projects.mongo_rag.tools import semantic_search
from server.projects.shared.context_helpers import create_run_context
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Perform semantic search over MongoDB documents."""
    # Example queries to search
    queries = [
        "What is authentication?",
        "How does vector search work?",
        "Explain document chunking strategies"
    ]
    
    print("="*80)
    print("MongoDB RAG - Semantic Search Example")
    print("="*80)
    print()
    print("This example demonstrates pure semantic (vector) search.")
    print("It uses MongoDB's $vectorSearch aggregation to find similar documents.")
    print()
    
    # Initialize dependencies
    deps = AgentDependencies()
    await deps.initialize()
    
    try:
        # Create run context for search tools
        ctx = create_run_context(deps)
        
        # Perform semantic search for each query
        for i, query in enumerate(queries, 1):
            print(f"\n{'='*80}")
            print(f"Query {i}: {query}")
            print("="*80)
            
            logger.info(f"🔍 Performing semantic search for: {query}")
            
            # Perform semantic search
            results = await semantic_search(
                ctx=ctx,
                query=query,
                match_count=5
            )
            
            # Display results
            if results:
                print(f"\nFound {len(results)} results:\n")
                for j, result in enumerate(results, 1):
                    print(f"Result {j} (similarity: {result.similarity:.3f}):")
                    print(f"  Title: {result.document_title}")
                    print(f"  Source: {result.document_source}")
                    print(f"  Content: {result.content[:200]}...")
                    print(f"  Chunk ID: {result.chunk_id}")
                    print()
            else:
                print("\n⚠️  No results found. Make sure documents are ingested.")
                print("   Run document_ingestion_example.py to ingest documents first.")
        
        print("\n" + "="*80)
        print("✅ Semantic search completed successfully!")
        print("="*80)
        
    except Exception as e:
        logger.exception(f"❌ Error during semantic search: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
