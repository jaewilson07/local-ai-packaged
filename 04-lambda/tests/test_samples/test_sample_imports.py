"""Tests to validate that all sample files can be imported without errors."""

import importlib.util
import sys
from pathlib import Path

import pytest

# Define all sample files to test
SAMPLE_FILES = [
    # MongoDB RAG
    ("mongo_rag", "semantic_search_example.py"),
    ("mongo_rag", "hybrid_search_example.py"),
    ("mongo_rag", "document_ingestion_example.py"),
    ("mongo_rag", "memory_tools_example.py"),
    ("mongo_rag", "enhanced_rag_example.py"),
    # Graphiti RAG
    ("graphiti_rag", "knowledge_graph_search_example.py"),
    ("graphiti_rag", "repository_parsing_example.py"),
    ("graphiti_rag", "script_validation_example.py"),
    ("graphiti_rag", "cypher_query_example.py"),
    # Crawl4AI RAG
    ("crawl4ai_rag", "single_page_crawl_example.py"),
    ("crawl4ai_rag", "deep_crawl_example.py"),
    ("crawl4ai_rag", "adaptive_crawl_example.py"),
    # Calendar
    ("calendar", "create_event_example.py"),
    ("calendar", "list_events_example.py"),
    ("calendar", "sync_state_example.py"),
    # Conversation
    ("conversation", "orchestration_example.py"),
    ("conversation", "multi_agent_example.py"),
    # Persona
    ("persona", "mood_tracking_example.py"),
    ("persona", "voice_instructions_example.py"),
    ("persona", "relationship_management_example.py"),
    # N8N Workflow
    ("n8n_workflow", "create_workflow_example.py"),
    ("n8n_workflow", "execute_workflow_example.py"),
    ("n8n_workflow", "rag_enhanced_workflow_example.py"),
    # Open WebUI
    ("openwebui", "export_conversation_example.py"),
    ("openwebui", "topic_classification_example.py"),
    # Neo4j
    ("neo4j", "basic_cypher_example.py"),
    ("neo4j", "knowledge_graph_example.py"),
]


def import_sample_file(
    service_dir: str, filename: str, sample_base_path: Path, lambda_path: Path
) -> bool:
    """
    Attempt to import a sample file.

    Args:
        service_dir: Service directory name (e.g., "mongo_rag")
        filename: Sample filename (e.g., "semantic_search_example.py")
        sample_base_path: Path to the sample directory
        lambda_path: Path to the lambda directory

    Returns:
        True if import succeeds, False otherwise
    """
    sample_path = sample_base_path / service_dir / filename

    if not sample_path.exists():
        return False

    # Add lambda path to sys.path if not already there
    lambda_str = str(lambda_path)
    if lambda_str not in sys.path:
        sys.path.insert(0, lambda_str)

    try:
        # Load the module
        spec = importlib.util.spec_from_file_location(
            f"{service_dir}.{filename.replace('.py', '')}", sample_path
        )
        if spec is None or spec.loader is None:
            return False

        module = importlib.util.module_from_spec(spec)

        # Execute the module (this will catch import errors)
        spec.loader.exec_module(module)

        return True
    except (ImportError, SyntaxError, AttributeError, TypeError):
        return False
    finally:
        # Clean up: remove lambda_path if we added it
        if lambda_str in sys.path:
            sys.path.remove(lambda_str)


@pytest.mark.parametrize("service_dir,filename", SAMPLE_FILES)
def test_sample_import(service_dir: str, filename: str, sample_base_path, lambda_path):
    """
    Test that a sample file can be imported without errors.

    This test validates:
    - The file exists
    - The file can be parsed as valid Python
    - All imports in the file can be resolved
    - Path setup works correctly
    """
    sample_path = sample_base_path / service_dir / filename

    # Check file exists
    assert sample_path.exists(), f"Sample file not found: {sample_path}"

    # Attempt to import
    success = import_sample_file(service_dir, filename, sample_base_path, lambda_path)

    assert success, (
        f"Failed to import {service_dir}/{filename}. "
        "Check that all dependencies are available and path setup is correct."
    )


def test_all_samples_accounted_for(sample_base_path):
    """Test that we're testing all sample files in the sample directory."""
    found_samples = []

    for service_dir in sample_base_path.iterdir():
        if not service_dir.is_dir() or service_dir.name.startswith("_"):
            continue

        for sample_file in service_dir.glob("*_example.py"):
            found_samples.append((service_dir.name, sample_file.name))

    # Check that all found samples are in our test list
    tested_samples = set(SAMPLE_FILES)
    found_samples_set = set(found_samples)

    missing = found_samples_set - tested_samples
    if missing:
        pytest.fail(
            f"Found {len(missing)} sample files not in test list: {missing}. "
            "Add them to SAMPLE_FILES in test_sample_imports.py"
        )

    # Check that all tested samples exist
    missing_files = []
    for service_dir, filename in tested_samples:
        sample_path = sample_base_path / service_dir / filename
        if not sample_path.exists():
            missing_files.append(f"{service_dir}/{filename}")

    if missing_files:
        pytest.fail(
            f"Test list references {len(missing_files)} files that don't exist: {missing_files}"
        )
