#!/usr/bin/env python3
"""Execute N8N workflow example using N8N Workflow project.

This example demonstrates how to execute an N8N workflow with input data.

Prerequisites:
- N8N running and accessible
- Existing workflow ID
- Environment variables configured (N8N_API_URL, N8N_API_KEY, etc.)
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from server.projects.n8n_workflow.agent import execute_workflow_tool  # noqa: E402
from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps  # noqa: E402
from server.projects.shared.context_helpers import create_run_context  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Execute an N8N workflow."""
    # Example workflow ID (replace with actual workflow ID)
    workflow_id = "your-workflow-id-here"
    input_data = {"name": "Test User", "message": "Hello from N8N workflow execution!"}

    print("=" * 80)
    print("N8N Workflow - Execute Workflow Example")
    print("=" * 80)
    print()
    print("This example demonstrates executing an N8N workflow:")
    print("  - Executes a workflow with input data")
    print("  - Returns workflow execution results")
    print()
    print(f"Workflow ID: {workflow_id}")
    print(f"Input Data: {input_data}")
    print()

    if workflow_id == "your-workflow-id-here":
        print("⚠️  Please replace 'your-workflow-id-here' with an actual workflow ID.")
        print("   You can get workflow IDs by listing workflows first.")
        sys.exit(1)

    # Initialize dependencies
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()

    try:
        # Create run context for tools
        ctx = create_run_context(deps)

        # Execute workflow
        print("🚀 Executing workflow...")
        logger.info(f"Executing workflow: {workflow_id}")

        result = await execute_workflow_tool(
            ctx=ctx, workflow_id=workflow_id, input_data=input_data
        )

        # Display result
        print("\n" + "=" * 80)
        print("WORKFLOW EXECUTION RESULT")
        print("=" * 80)
        print(result)
        print("=" * 80)
        print()
        print("✅ Workflow execution completed!")
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
            expected_workflow_runs_min=1,
        )
        print(message)

        if success:
            print("\n✅ Verification passed!")
            sys.exit(0)
        else:
            print("\n❌ Verification failed (workflow run may need time to sync)")
            sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
