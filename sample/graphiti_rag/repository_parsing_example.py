#!/usr/bin/env python3
"""Repository parsing example using Graphiti RAG.

This example demonstrates how to parse a GitHub repository into the Neo4j
knowledge graph. The parser extracts:
- Classes and their methods
- Functions and their signatures
- Imports and dependencies
- Relationships between code elements

This enables hallucination detection by validating AI-generated scripts
against the actual codebase structure.

Prerequisites:
- Neo4j running and configured (USE_KNOWLEDGE_GRAPH=true)
- GitHub repository URL (must end with .git)
- Environment variables configured (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, etc.)
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps  # noqa: E402
from capabilities.retrieval.graphiti_rag.tools import parse_github_repository  # noqa: E402

from shared.context_helpers import create_run_context  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Parse a GitHub repository into Neo4j knowledge graph."""
    # Example repository (you can change this to any public GitHub repo)
    repo_url = "https://github.com/pydantic/pydantic-ai.git"

    print("=" * 80)
    print("Graphiti RAG - Repository Parsing Example")
    print("=" * 80)
    print()
    print("This example parses a GitHub repository into Neo4j knowledge graph.")
    print("The parser extracts:")
    print("  - Classes and their methods")
    print("  - Functions and their signatures")
    print("  - Imports and dependencies")
    print("  - Relationships between code elements")
    print()
    print("This enables hallucination detection by validating AI-generated")
    print("scripts against the actual codebase structure.")
    print()
    print(f"Repository: {repo_url}")
    print()

    # Initialize dependencies
    deps = GraphitiRAGDeps.from_settings()
    await deps.initialize()

    try:
        # Create run context for tools
        ctx = create_run_context(deps)

        # Parse repository
        print("🚀 Starting repository parsing...")
        logger.info(f"Parsing repository: {repo_url}")

        result = await parse_github_repository(ctx=ctx, repo_url=repo_url)

        # Display results
        print("\n" + "=" * 80)
        print("PARSING RESULTS")
        print("=" * 80)

        if result.get("success"):
            print("✅ Repository parsed successfully!")
            print(f"   Repository: {result.get('repo_url')}")
            print()
            print("The repository structure is now stored in Neo4j.")
            print("You can:")
            print("  - Query the knowledge graph using cypher_query_example.py")
            print("  - Validate AI scripts using script_validation_example.py")
            print("  - Search for code patterns using knowledge_graph_search_example.py")
        else:
            print("❌ Repository parsing failed!")
            print(f"   Error: {result.get('message', 'Unknown error')}")
            if result.get("error"):
                print(f"   Details: {result['error']}")

        print("=" * 80)

        # Verify via API
        if result.get("success"):
            from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
            from sample.shared.verification_helpers import verify_neo4j_data

            api_base_url = get_api_base_url()
            headers = get_auth_headers()

            print("\n" + "=" * 80)
            print("Verification")
            print("=" * 80)

            success, message = verify_neo4j_data(
                api_base_url=api_base_url,
                headers=headers,
                expected_nodes_min=1,
            )
            print(message)

            if success:
                print("\n✅ Verification passed!")
                sys.exit(0)
            else:
                print("\n❌ Verification failed (nodes may need time to sync)")
                sys.exit(1)
        else:
            sys.exit(1)

    except ValueError as e:
        # Handle validation errors (e.g., missing .git suffix)
        print(f"\n❌ Validation error: {e}")
        print("\nNote: Repository URL must end with .git")
        print("      Example: https://github.com/user/repo.git")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
