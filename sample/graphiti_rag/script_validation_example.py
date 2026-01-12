#!/usr/bin/env python3
"""Script validation example using Graphiti RAG.

This example demonstrates how to validate AI-generated Python scripts
against a knowledge graph to detect hallucinations (incorrect API usage,
non-existent methods, etc.).

The validator checks:
- Import statements (are modules/classes imported correctly?)
- Method calls (do methods exist in the classes?)
- Class instantiations (are classes used correctly?)
- Function calls (do functions exist with correct signatures?)

Prerequisites:
- Neo4j running with knowledge graph populated (use repository_parsing_example.py)
- Python script to validate (or create a test script)
- Environment variables configured (NEO4J_URI, LLM_BASE_URL, etc.)
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
from server.projects.graphiti_rag.tools import validate_ai_script
from server.projects.shared.context_helpers import create_run_context

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Validate an AI-generated script against the knowledge graph."""
    # Create a test script to validate
    # In practice, this would be an AI-generated script
    test_script_path = Path("test_script_to_validate.py")

    # Example script with potential issues
    test_script_content = """# Example AI-generated script
from pydantic_ai import Agent, RunContext

# Create an agent
agent = Agent(
    model="gpt-4",
    system_prompt="You are a helpful assistant"
)

# Use the agent (this might have issues if the API changed)
@agent.tool
async def my_tool(ctx: RunContext, query: str) -> str:
    return f"Processed: {query}"

# Call a method that might not exist
result = await agent.run("test query")
"""

    print("=" * 80)
    print("Graphiti RAG - Script Validation Example")
    print("=" * 80)
    print()
    print("This example validates an AI-generated Python script against")
    print("the knowledge graph to detect hallucinations.")
    print()
    print("The validator checks:")
    print("  - Import statements (correct modules/classes?)")
    print("  - Method calls (do methods exist?)")
    print("  - Class instantiations (correct usage?)")
    print("  - Function calls (correct signatures?)")
    print()

    # Write test script
    print(f"📝 Creating test script: {test_script_path}")
    test_script_path.write_text(test_script_content)
    print("✅ Test script created")
    print()

    # Initialize dependencies
    deps = GraphitiRAGDeps.from_settings()
    await deps.initialize()

    try:
        # Create run context for tools
        ctx = create_run_context(deps)

        # Validate script
        print("🔍 Validating script against knowledge graph...")
        logger.info(f"Validating script: {test_script_path}")

        # Use absolute path
        abs_script_path = str(test_script_path.absolute())

        result = await validate_ai_script(ctx=ctx, script_path=abs_script_path)

        # Display results
        print("\n" + "=" * 80)
        print("VALIDATION RESULTS")
        print("=" * 80)

        if result.get("success"):
            print("✅ Script validation completed!")
            print()

            validation = result.get("validation", {})

            # Display import validation
            imports = validation.get("imports", {})
            print(f"Imports checked: {imports.get('total', 0)}")
            print(f"  Valid: {imports.get('valid', 0)}")
            print(f"  Invalid: {imports.get('invalid', 0)}")
            if imports.get("invalid_imports"):
                print("  Invalid imports:")
                for imp in imports["invalid_imports"]:
                    print(f"    - {imp}")
            print()

            # Display method validation
            methods = validation.get("methods", {})
            print(f"Methods checked: {methods.get('total', 0)}")
            print(f"  Valid: {methods.get('valid', 0)}")
            print(f"  Invalid: {methods.get('invalid', 0)}")
            if methods.get("invalid_methods"):
                print("  Invalid methods:")
                for method in methods["invalid_methods"]:
                    print(f"    - {method}")
            print()

            # Display hallucination report
            report = result.get("report", "")
            if report:
                print("Hallucination Report:")
                print(report)
        else:
            print("❌ Script validation failed!")
            print(f"   Error: {result.get('message', 'Unknown error')}")
            if result.get("error"):
                print(f"   Details: {result['error']}")

        print("=" * 80)

        # Verify via API
        if result.get("success"):
            try:
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
                    print("\n⚠️  Verification failed (nodes may need time to sync)")
                    sys.exit(1)
            except Exception as e:
                logger.warning(f"Verification error: {e}")
                print(f"\n⚠️  Verification error: {e}")
                sys.exit(1)
        else:
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ Error during script validation: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        # Remove test script
        if test_script_path.exists():
            test_script_path.unlink()
            logger.info("🧹 Test script removed")
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
