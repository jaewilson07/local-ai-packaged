#!/usr/bin/env python3
"""Create N8N workflow example using N8N Workflow project.

This example demonstrates how to create an N8N workflow using the
N8N Workflow project, which includes RAG-enhanced workflow creation
by searching the knowledge base for best practices and examples.

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
lambda_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from workflows.automation.n8n_workflow.ai.agent import create_workflow_tool  # noqa: E402
from workflows.automation.n8n_workflow.ai.dependencies import N8nWorkflowDeps  # noqa: E402

from shared.context_helpers import create_run_context  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Create an N8N workflow."""
    # Example workflow configuration
    workflow_name = "Example Webhook Workflow"
    nodes = [
        {
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1,
            "position": [250, 300],
            "parameters": {"path": "example-webhook", "httpMethod": "POST"},
        },
        {
            "name": "Respond to Webhook",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1,
            "position": [450, 300],
            "parameters": {"options": {}},
        },
    ]
    connections = {
        "Webhook": {"main": [[{"node": "Respond to Webhook", "type": "main", "index": 0}]]}
    }

    print("=" * 80)
    print("N8N Workflow - Create Workflow Example")
    print("=" * 80)
    print()
    print("This example demonstrates creating an N8N workflow:")
    print("  - Creates a workflow with nodes and connections")
    print("  - Uses RAG-enhanced workflow creation (searches knowledge base)")
    print("  - Discovers available nodes via N8N API")
    print()
    print(f"Workflow Name: {workflow_name}")
    print(f"Nodes: {len(nodes)}")
    print()

    # Initialize dependencies
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()

    try:
        # Create run context for tools
        ctx = create_run_context(deps)

        # Create workflow
        print("🚀 Creating workflow...")
        logger.info(f"Creating workflow: {workflow_name}")

        result = await create_workflow_tool(
            ctx=ctx, name=workflow_name, nodes=nodes, connections=connections, active=False
        )

        # Display result
        print("\n" + "=" * 80)
        print("WORKFLOW CREATION RESULT")
        print("=" * 80)
        print(result)
        print("=" * 80)
        print()
        print("✅ Workflow creation completed!")
        print()
        print("Note: The N8N Workflow agent automatically searches the")
        print("      knowledge base for best practices before creating workflows.")
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
            expected_workflows_min=1,
        )
        print(message)

        if success:
            print("\n✅ Verification passed!")
            sys.exit(0)
        else:
            print("\n❌ Verification failed (workflow may need time to sync)")
            sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
