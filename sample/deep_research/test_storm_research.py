"""Test script for STORM-based Deep Research Agent (Phase 4-6).

This script tests the full LangGraph orchestrator with:
- Planner node (STORM pattern)
- Executor node (Hunter pattern)
- Auditor node (Validation - Phase 5)
- Writer node (Synthesis)
- Graph-enhanced reasoning (Phase 6)
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


async def test_storm_research():
    """Test the STORM-based deep research workflow."""
    from server.projects.deep_research.storm_workflow import run_storm_research

    print("=" * 80)
    print("Testing STORM-based Deep Research Agent (Phase 4-6)")
    print("=" * 80)
    print()

    # Test query
    query = "Comprehensive report on the history of potential superconductor LK-99"
    print(f"Query: {query}")
    print()

    try:
        # Run the STORM research workflow
        print("Running STORM research workflow...")
        print("This includes:")
        print("  - Planner: Generating research outline")
        print("  - Executor: Searching, fetching, parsing, ingesting")
        print("  - Auditor: Validating data (Phase 5)")
        print("  - Writer: Synthesizing final report")
        print()

        result = await run_storm_research(query, max_iterations=10)

        # Display results
        print()
        print("=" * 80)
        print("Results")
        print("=" * 80)
        print()

        print(f"Outline ({len(result.get('outline', []))} sections):")
        for i, section in enumerate(result.get("outline", []), 1):
            print(f"  {i}. {section}")
        print()

        print(f"Research Vectors ({len(result.get('vectors', []))}):")
        for vector in result.get("vectors", []):
            status_icon = (
                "✅"
                if vector.status == "verified"
                else "⏳"
                if vector.status == "ingesting"
                else "❌"
            )
            print(f"  {status_icon} {vector.id}: {vector.topic} ({vector.status})")
        print()

        if result.get("final_report"):
            print("Final Report:")
            print("-" * 80)
            print(result["final_report"])
            print("-" * 80)
        else:
            print("⚠️  No final report generated")

        if result.get("errors"):
            print()
            print("Errors:")
            for error in result["errors"]:
                print(f"  - {error}")

        print()
        print(f"Session ID: {result.get('knowledge_graph_session_id')}")
        print()

        # Check if report was generated
        if result.get("final_report") and len(result["final_report"]) > 100:
            print("✅ Test passed: STORM research workflow completed successfully")
            return True
        else:
            print("⚠️  Warning: Report seems incomplete or missing")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_storm_research())
    sys.exit(0 if success else 1)
