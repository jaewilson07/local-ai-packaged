#!/usr/bin/env python3
"""RAG-enhanced workflow creation example using N8N Workflow project.

This example demonstrates how the N8N Workflow project uses RAG to
enhance workflow creation by searching the knowledge base for:
- Node documentation and examples
- Workflow patterns and best practices
- Configuration examples

Prerequisites:
- N8N running and accessible
- MongoDB running (for RAG knowledge base)
- Environment variables configured (N8N_API_URL, N8N_API_KEY, MONGODB_URI, etc.)
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging

from server.projects.n8n_workflow.agent import (
    discover_n8n_nodes_tool,
    search_n8n_knowledge_base_tool,
    search_node_examples_tool,
)
from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
from server.projects.shared.context_helpers import create_run_context

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate RAG-enhanced workflow creation."""
    print("=" * 80)
    print("N8N Workflow - RAG-Enhanced Workflow Example")
    print("=" * 80)
    print()
    print("This example demonstrates RAG-enhanced workflow creation:")
    print("  1. Search knowledge base for workflow patterns")
    print("  2. Discover available nodes via N8N API")
    print("  3. Find node configuration examples")
    print("  4. Use information to create informed workflow")
    print()

    # Initialize dependencies
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()

    try:
        # Create run context for tools
        ctx = create_run_context(deps)

        # 1. Search knowledge base
        print("=" * 80)
        print("1. SEARCHING KNOWLEDGE BASE")
        print("=" * 80)
        print("Query: 'webhook workflow example'")
        print()

        knowledge_result = await search_n8n_knowledge_base_tool(
            ctx=ctx, query="webhook workflow example", match_count=5
        )

        print("Knowledge Base Results:")
        print(knowledge_result[:500] + "..." if len(knowledge_result) > 500 else knowledge_result)
        print()

        # 2. Discover nodes
        print("=" * 80)
        print("2. DISCOVERING AVAILABLE NODES")
        print("=" * 80)
        print("Category: trigger")
        print()

        nodes_result = await discover_n8n_nodes_tool(ctx=ctx, category="trigger")

        print("Available Trigger Nodes:")
        print(nodes_result[:500] + "..." if len(nodes_result) > 500 else nodes_result)
        print()

        # 3. Search node examples
        print("=" * 80)
        print("3. SEARCHING NODE EXAMPLES")
        print("=" * 80)
        print("Node Type: webhook")
        print()

        examples_result = await search_node_examples_tool(
            ctx=ctx, node_type="webhook", query="configuration", match_count=3
        )

        print("Node Examples:")
        print(examples_result[:500] + "..." if len(examples_result) > 500 else examples_result)
        print()

        print("=" * 80)
        print("✅ RAG-enhanced workflow creation demonstration completed!")
        print("=" * 80)
        print()
        print("The N8N Workflow agent uses RAG to:")
        print("  - Find relevant workflow patterns and examples")
        print("  - Discover available nodes and their capabilities")
        print("  - Get configuration examples for specific nodes")
        print("  - Create informed workflows based on best practices")
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
                expected_documents_min=1,  # RAG knowledge base should have documents
            )
            print(message)

            if success:
                print("\n✅ Verification passed!")
                sys.exit(0)
            else:
                print("\n⚠️  Verification failed (RAG data may need time to sync)")
                sys.exit(1)
        except Exception as e:
            logger.warning(f"Verification error: {e}")
            print(f"\n⚠️  Verification error: {e}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ Error during RAG-enhanced workflow demo: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
