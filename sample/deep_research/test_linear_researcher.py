"""Test script for Linear Researcher agent (Phase 3).

This script tests the end-to-end flow of the Linear Researcher agent.
"""

import asyncio
import os
import sys

# Set minimal environment variables before imports
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/test")
os.environ.setdefault("MONGODB_DATABASE", "test_db")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("EMBEDDING_API_KEY", "test-key")
os.environ.setdefault("SEARXNG_URL", "http://localhost:8081")

# Add the lambda directory to the path
lambda_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../04-lambda"))
sys.path.insert(0, lambda_dir)


async def test_linear_researcher():
    """Test the Linear Researcher agent."""
    from server.projects.deep_research.workflow import run_linear_research

    print("=" * 80)
    print("Testing Linear Researcher Agent (Phase 3)")
    print("=" * 80)
    print()

    # Test query
    query = "Who is the CEO of Anthropic?"
    print(f"Query: {query}")
    print()

    try:
        # Run the agent
        print("Running agent...")
        result = await run_linear_research(query)

        # Display results
        print()
        print("=" * 80)
        print("Results")
        print("=" * 80)
        print()
        print("Answer:")
        print(result.data.answer)
        print()
        print(f"Sources ({len(result.data.sources)}):")
        for i, source in enumerate(result.data.sources, 1):
            print(f"  [{i}] {source}")
        print()
        print(f"Citations: {result.data.citations}")
        print()
        print(f"Session ID: {result.data.session_id}")
        print()

        # Check if answer is reasonable
        if len(result.data.answer) > 50:
            print("✅ Test passed: Agent produced a substantial answer")

            # Verify via API if research ingested data
            try:
                from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
                from sample.shared.verification_helpers import verify_rag_data

                api_base_url = get_api_base_url()
                headers = get_auth_headers()

                print("\n" + "=" * 80)
                print("Verification")
                print("=" * 80)

                # Verify that sources were ingested (if applicable)
                success, message = verify_rag_data(
                    api_base_url=api_base_url,
                    headers=headers,
                    expected_documents_min=1 if result.data.sources else None,
                )
                print(message)
            except Exception as e:
                print(f"\n⚠️  Verification skipped: {e}")

            return True
        print("⚠️  Warning: Answer seems too short")
        return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_linear_researcher())
    sys.exit(0 if success else 1)
