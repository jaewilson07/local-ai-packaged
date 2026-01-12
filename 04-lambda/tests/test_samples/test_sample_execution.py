"""Tests to validate that sample files can execute (with mocked dependencies)."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Sample files that have a main() function to execute
EXECUTABLE_SAMPLES = [
    # MongoDB RAG - all have main()
    ("mongo_rag", "semantic_search_example.py"),
    ("mongo_rag", "hybrid_search_example.py"),
    ("mongo_rag", "document_ingestion_example.py"),
    ("mongo_rag", "memory_tools_example.py"),
    ("mongo_rag", "enhanced_rag_example.py"),
    # Graphiti RAG - all have main()
    ("graphiti_rag", "knowledge_graph_search_example.py"),
    ("graphiti_rag", "repository_parsing_example.py"),
    ("graphiti_rag", "script_validation_example.py"),
    ("graphiti_rag", "cypher_query_example.py"),
    # Crawl4AI RAG - all have main()
    ("crawl4ai_rag", "single_page_crawl_example.py"),
    ("crawl4ai_rag", "deep_crawl_example.py"),
    ("crawl4ai_rag", "adaptive_crawl_example.py"),
    # Calendar - all have main()
    ("calendar", "create_event_example.py"),
    ("calendar", "list_events_example.py"),
    ("calendar", "sync_state_example.py"),
    # Conversation - all have main()
    ("conversation", "orchestration_example.py"),
    ("conversation", "multi_agent_example.py"),
    # Persona - all have main()
    ("persona", "mood_tracking_example.py"),
    ("persona", "voice_instructions_example.py"),
    ("persona", "relationship_management_example.py"),
    # N8N Workflow - all have main()
    ("n8n_workflow", "create_workflow_example.py"),
    ("n8n_workflow", "execute_workflow_example.py"),
    ("n8n_workflow", "rag_enhanced_workflow_example.py"),
    # Open WebUI - all have main()
    ("openwebui", "export_conversation_example.py"),
    ("openwebui", "topic_classification_example.py"),
    # Neo4j - all have main()
    ("neo4j", "basic_cypher_example.py"),
    ("neo4j", "knowledge_graph_example.py"),
    # Deep Research - all have main() or async test functions
    ("deep_research", "test_linear_researcher.py"),
    ("deep_research", "test_storm_research.py"),
    ("deep_research", "test_searxng_simple.py"),
]


async def execute_sample_main(service_dir: str, filename: str, mocks: dict) -> tuple[bool, str]:
    """
    Attempt to execute the main() function of a sample file with mocked dependencies.

    Args:
        service_dir: Service directory name
        filename: Sample filename
        mocks: Dictionary of mocks to apply

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    # Get sample base path and lambda path
    project_root = Path(__file__).parent.parent.parent.parent
    sample_base = project_root / "sample"
    lambda_path = project_root / "04-lambda"
    sample_path = sample_base / service_dir / filename

    if not sample_path.exists():
        return False, f"File not found: {sample_path}"

    # Add lambda path to sys.path
    lambda_str = str(lambda_path)
    if lambda_str not in sys.path:
        sys.path.insert(0, lambda_str)

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            f"{service_dir}.{filename.replace('.py', '')}", sample_path
        )
        if spec is None or spec.loader is None:
            return False, "Failed to create module spec"

        module = importlib.util.module_from_spec(spec)

        # Apply mocks before loading
        with (
            patch.multiple(
                "server.projects.mongo_rag.dependencies",
                AsyncMongoClient=mocks.get("mongodb_client", AsyncMock),
            ),
            patch.multiple(
                "server.projects.crawl4ai_rag.dependencies",
                AsyncMongoClient=mocks.get("mongodb_client", AsyncMock),
                AsyncWebCrawler=mocks.get("crawler", AsyncMock),
            ),
            patch.multiple(
                "server.projects.graphiti_rag.dependencies",
                Graphiti=mocks.get("graphiti", Mock),
            ),
            patch.multiple(
                "server.projects.calendar.dependencies",
                AsyncMongoClient=mocks.get("mongodb_client", AsyncMock),
            ),
            patch.multiple(
                "server.projects.persona.dependencies",
                AsyncMongoClient=mocks.get("mongodb_client", AsyncMock),
            ),
            patch("openai.AsyncOpenAI", mocks.get("openai", Mock())),
            patch.multiple(
                "server.projects.openwebui_export.dependencies",
                AsyncMongoClient=mocks.get("mongodb_client", AsyncMock),
                httpx=mocks.get("httpx", Mock()),
            ),
            patch.multiple(
                "server.projects.n8n_workflow.dependencies", httpx=mocks.get("httpx", Mock())
            ),
        ):
            # Load the module
            spec.loader.exec_module(module)

            # Check if main() exists
            if not hasattr(module, "main"):
                return False, "Module does not have a main() function"

            # Execute main() with timeout
            try:
                await asyncio.wait_for(module.main(), timeout=5.0)
                return True, ""
            except asyncio.TimeoutError:
                return False, "main() execution timed out"
            except Exception as e:
                return False, f"Error executing main(): {e!s}"

    except Exception as e:
        return False, f"Error loading/executing module: {e!s}"

    finally:
        # Clean up
        if lambda_str in sys.path:
            sys.path.remove(lambda_str)


@pytest.mark.asyncio
@pytest.mark.parametrize("service_dir,filename", EXECUTABLE_SAMPLES)
async def test_sample_execution(
    service_dir: str,
    filename: str,
    sample_base_path,
    lambda_path,
    mock_mongodb,
    mock_neo4j,
    mock_openai_client,
    mock_httpx_client,
    mock_crawl4ai_crawler,
    mock_graphiti,
    mock_google_calendar_service,
):
    """
    Test that a sample file's main() function can execute with mocked dependencies.

    This test validates:
    - The file can be imported
    - The main() function exists
    - The main() function can execute without crashing (with mocks)
    """
    sample_path = sample_base_path / service_dir / filename

    # Check file exists
    assert sample_path.exists(), f"Sample file not found: {sample_path}"

    # Prepare mocks
    mongo_client, _mongo_db = mock_mongodb
    mocks = {
        "mongodb_client": mongo_client,
        "openai": Mock(AsyncOpenAI=Mock(return_value=mock_openai_client)),
        "httpx": Mock(AsyncClient=Mock(return_value=mock_httpx_client)),
        "crawler": Mock(return_value=mock_crawl4ai_crawler),
        "graphiti": Mock(return_value=mock_graphiti),
    }

    # Execute with mocks
    success, error_msg = await execute_sample_main(service_dir, filename, mocks)

    assert success, (
        f"Failed to execute {service_dir}/{filename}: {error_msg}. "
        "Check that the main() function is properly defined and dependencies are mocked."
    )
