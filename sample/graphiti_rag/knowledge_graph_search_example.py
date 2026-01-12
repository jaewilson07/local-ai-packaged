#!/usr/bin/env python3
"""Knowledge graph search example using Graphiti RAG.

This example demonstrates how to search the Graphiti knowledge graph
for entities and relationships using hybrid search (semantic + keyword + graph traversal).

Prerequisites:
- Graphiti configured (USE_GRAPHITI=true)
- Neo4j running and configured
- Knowledge graph populated with data (use repository_parsing_example.py)
- Environment variables configured (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, etc.)
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging

from server.projects.graphiti_rag.dependencies import GraphitiRAGDeps
from server.projects.graphiti_rag.tools import search_graphiti_knowledge_graph
from server.projects.shared.context_helpers import create_run_context

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Search Graphiti knowledge graph."""
    # Example queries to search
    queries = [
        "authentication methods",
        "database connection",
        "API endpoints",
    ]

    print("=" * 80)
    print("Graphiti RAG - Knowledge Graph Search Example")
    print("=" * 80)
    print()
    print("This example demonstrates searching the Graphiti knowledge graph.")
    print("Graphiti performs hybrid search combining:")
    print("  - Semantic search (vector similarity)")
    print("  - Keyword matching")
    print("  - Graph traversal (following relationships)")
    print()

    # Initialize dependencies
    deps = GraphitiRAGDeps.from_settings()
    await deps.initialize()

    try:
        # Check if Graphiti is available
        if not deps.graphiti:
            print("⚠️  Graphiti is not initialized.")
            print("   Set USE_GRAPHITI=true in your environment variables.")
            sys.exit(1)

        # Create run context for tools
        ctx = create_run_context(deps)

        # Perform searches
        for i, query in enumerate(queries, 1):
            print(f"\n{'=' * 80}")
            print(f"Query {i}: {query}")
            print("=" * 80)

            logger.info(f"🔍 Searching Graphiti knowledge graph for: {query}")

            # Search knowledge graph
            result = await search_graphiti_knowledge_graph(ctx=ctx, query=query, match_count=10)

            # Display results
            if result.get("success"):
                print(f"\n✅ Found {result['count']} results:\n")

                for j, item in enumerate(result["results"][:5], 1):
                    print(f"Result {j} (similarity: {item['similarity']:.3f}):")
                    print(f"  Fact: {item['fact']}")
                    if item.get("metadata"):
                        print(f"  Metadata: {item['metadata']}")
                    print()

                if result["count"] > 5:
                    print(f"  ... and {result['count'] - 5} more results")
            else:
                print(f"\n⚠️  Search failed: {result.get('error', 'Unknown error')}")
                if result.get("error"):
                    print(f"   Error: {result['error']}")

        print("\n" + "=" * 80)
        print("✅ Knowledge graph search completed!")
        print("=" * 80)
        print()
        print("Note: If you see no results, make sure the knowledge graph is populated.")
        print("      Use repository_parsing_example.py to parse a GitHub repository.")
        print("=" * 80)

        # Verify search results
        try:
            from sample.shared.verification_helpers import verify_search_results

            all_results = []
            for query in queries:
                result = await search_graphiti_knowledge_graph(ctx=ctx, query=query, match_count=10)
                if result.get("success") and result.get("results"):
                    all_results.extend(result["results"])

            print("\n" + "=" * 80)
            print("Verification")
            print("=" * 80)

            success, message = verify_search_results(all_results, expected_min=1)
            print(message)

            if success:
                print("\n✅ Verification passed!")
                sys.exit(0)
            else:
                print("\n⚠️  Verification failed: No search results found")
                sys.exit(1)
        except Exception as e:
            logger.warning(f"Verification error: {e}")
            print(f"\n⚠️  Verification error: {e}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ Error during knowledge graph search: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
