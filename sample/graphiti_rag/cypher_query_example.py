#!/usr/bin/env python3
"""Cypher query example using Graphiti RAG.

This example demonstrates how to query the Neo4j knowledge graph
using Cypher queries to explore repository code structure.

Supported commands:
- 'repos': List all repositories
- 'explore <repo>': Get statistics for a repository
- 'query <cypher>': Execute a custom Cypher query

Prerequisites:
- Neo4j running with knowledge graph populated (use repository_parsing_example.py)
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
from server.projects.graphiti_rag.tools import query_knowledge_graph
from server.projects.shared.context_helpers import create_run_context

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Query the Neo4j knowledge graph using various commands."""
    print("=" * 80)
    print("Graphiti RAG - Cypher Query Example")
    print("=" * 80)
    print()
    print("This example demonstrates querying the Neo4j knowledge graph.")
    print("Supported commands:")
    print("  - 'repos': List all repositories")
    print("  - 'explore <repo>': Get statistics for a repository")
    print("  - 'query <cypher>': Execute a custom Cypher query")
    print()

    # Initialize dependencies
    deps = GraphitiRAGDeps.from_settings()
    await deps.initialize()

    try:
        # Create run context for tools
        ctx = create_run_context(deps)

        # 1. List repositories
        print("=" * 80)
        print("1. LISTING REPOSITORIES")
        print("=" * 80)
        print("Command: repos")
        print()

        logger.info("Querying repositories...")
        repos_result = await query_knowledge_graph(ctx=ctx, command="repos")

        if repos_result.get("success"):
            repos = repos_result.get("repositories", [])
            print(f"✅ Found {len(repos)} repository(ies):")
            for repo in repos:
                print(f"  - {repo}")
        else:
            print(f"⚠️  Query failed: {repos_result.get('error', 'Unknown error')}")
        print()

        # 2. Explore a repository (if available)
        if repos_result.get("success") and repos_result.get("repositories"):
            repo_name = repos_result["repositories"][0]
            print("=" * 80)
            print(f"2. EXPLORING REPOSITORY: {repo_name}")
            print("=" * 80)
            print(f"Command: explore {repo_name}")
            print()

            logger.info(f"Exploring repository: {repo_name}")
            explore_result = await query_knowledge_graph(ctx=ctx, command=f"explore {repo_name}")

            if explore_result.get("success"):
                stats = explore_result.get("statistics", {})
                print("✅ Repository statistics:")
                print(f"  Files: {stats.get('files', 0)}")
                print(f"  Classes: {stats.get('classes', 0)}")
                print(f"  Methods: {stats.get('methods', 0)}")
                print(f"  Functions: {stats.get('functions', 0)}")
            else:
                print(f"⚠️  Query failed: {explore_result.get('error', 'Unknown error')}")
            print()

        # 3. Custom Cypher query
        print("=" * 80)
        print("3. CUSTOM CYPHER QUERY")
        print("=" * 80)
        print("Query: Find all classes with their methods")
        print()

        cypher_query = """
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        RETURN c.name AS class_name, collect(m.name) AS methods
        LIMIT 10
        """

        logger.info("Executing custom Cypher query...")
        query_result = await query_knowledge_graph(ctx=ctx, command=f"query {cypher_query}")

        if query_result.get("success"):
            results = query_result.get("results", [])
            print(f"✅ Query returned {len(results)} result(s):")
            for i, row in enumerate(results[:5], 1):
                print(f"\n  Result {i}:")
                for key, value in row.items():
                    print(f"    {key}: {value}")
        else:
            print(f"⚠️  Query failed: {query_result.get('error', 'Unknown error')}")

        print("\n" + "=" * 80)
        print("✅ Cypher query examples completed!")
        print("=" * 80)
        print()
        print("You can execute any Cypher query to explore the knowledge graph.")
        print("Common queries:")
        print("  - Find all classes: MATCH (c:Class) RETURN c.name")
        print(
            "  - Find methods of a class: MATCH (c:Class)-[:HAS_METHOD]->(m:Method) WHERE c.name = 'ClassName' RETURN m.name"
        )
        print("  - Find imports: MATCH (f:File)-[:IMPORTS]->(i) RETURN f.name, i.name")
        print("=" * 80)

        # Verify query results
        try:
            from sample.shared.verification_helpers import verify_search_results

            # Collect results from the queries we ran
            all_results = []
            if repos_result.get("success") and repos_result.get("repositories"):
                all_results.extend(repos_result.get("repositories", []))
            if explore_result.get("success") and explore_result.get("statistics"):
                all_results.append(explore_result.get("statistics", {}))
            if query_result.get("success") and query_result.get("results"):
                all_results.extend(query_result.get("results", []))

            print("\n" + "=" * 80)
            print("Verification")
            print("=" * 80)

            success, message = verify_search_results(all_results, expected_min=1)
            print(message)

            if success:
                print("\n✅ Verification passed!")
                sys.exit(0)
            else:
                print("\n⚠️  Verification failed: No query results found")
                sys.exit(1)
        except Exception as e:
            logger.warning(f"Verification error: {e}")
            print(f"\n⚠️  Verification error: {e}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ Error during Cypher query: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
