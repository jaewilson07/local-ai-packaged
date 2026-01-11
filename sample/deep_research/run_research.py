"""Run a real research query using the Linear Researcher agent.

This script demonstrates the full end-to-end workflow:
1. Search the web for information
2. Fetch and parse the top result
3. Ingest it into the knowledge base
4. Query the knowledge base
5. Generate an answer based on retrieved facts

NOTE: This script requires proper environment setup. The Settings class validation
may fail if extra environment variables are present. For best results, run this
through the Lambda server API or ensure your environment only contains the
required variables.

Example usage:
    python sample/deep_research/run_research.py "Who is the CEO of Anthropic?"
    python sample/deep_research/run_research.py "What is the latest news about LK-99 superconductor?"
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime

# CRITICAL: Patch settings BEFORE importing any server modules
from unittest.mock import MagicMock, patch

# Set minimal environment variables
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/test")
os.environ.setdefault("MONGODB_DATABASE", "test_db")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("EMBEDDING_API_KEY", "test-key")
os.environ.setdefault("SEARXNG_URL", "http://localhost:8081")

# Create a mock settings object
mock_settings = MagicMock()
mock_settings.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/test")
mock_settings.mongodb_database = os.getenv("MONGODB_DATABASE", "test_db")
mock_settings.llm_base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
mock_settings.llm_api_key = os.getenv("LLM_API_KEY", "test-key")
mock_settings.embedding_base_url = os.getenv("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
mock_settings.embedding_api_key = os.getenv("EMBEDDING_API_KEY", "test-key")
mock_settings.searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8081")
mock_settings.llm_provider = os.getenv("LLM_PROVIDER", "ollama")
mock_settings.llm_model = os.getenv("LLM_MODEL", "llama3.2")
mock_settings.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "ollama")
mock_settings.embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
mock_settings.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "768"))
mock_settings.log_level = os.getenv("LOG_LEVEL", "info")

# Add the lambda directory to the path
lambda_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../04-lambda'))
sys.path.insert(0, lambda_dir)

# Patch settings BEFORE importing server modules
with patch("server.config.settings", mock_settings):
    # Now we can safely import server modules
    from server.projects.deep_research.workflow import run_linear_research


def print_section(title: str, char: str = "="):
    """Print a formatted section header."""
    print()
    print(char * 80)
    print(f" {title}")
    print(char * 80)
    print()


def print_result(result, query: str):
    """Print the research result in a formatted way."""
    print_section("Research Results", "=")
    
    print(f"Query: {query}")
    print(f"Session ID: {result.data.session_id}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    print_section("Answer", "-")
    print(result.data.answer)
    print()
    
    if result.data.sources:
        print_section(f"Sources ({len(result.data.sources)})", "-")
        for i, source in enumerate(result.data.sources, 1):
            print(f"  [{i}] {source}")
        print()
    
    if result.data.citations:
        print_section("Citations", "-")
        for citation in result.data.citations:
            print(f"  {citation}")
        print()
    
    # Print agent run info if available
    if hasattr(result, 'usage') and result.usage:
        print_section("Usage Stats", "-")
        if hasattr(result.usage, 'input_tokens'):
            print(f"  Input tokens: {result.usage.input_tokens}")
        if hasattr(result.usage, 'output_tokens'):
            print(f"  Output tokens: {result.usage.output_tokens}")
        if hasattr(result.usage, 'total_tokens'):
            print(f"  Total tokens: {result.usage.total_tokens}")
        print()
    
    # Print tool calls if available
    if hasattr(result, 'all_messages'):
        tool_calls = [msg for msg in result.all_messages if hasattr(msg, 'tool_calls') and msg.tool_calls]
        if tool_calls:
            print_section(f"Tools Used ({len(tool_calls)})", "-")
            for msg in tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get('name', 'unknown')
                    print(f"  • {tool_name}")
            print()


async def run_research(query: str, verbose: bool = False):
    """Run the Linear Researcher agent on a query."""
    print_section("Deep Research Agent - Linear Researcher", "=")
    print(f"Query: {query}")
    print(f"Starting research workflow...")
    
    if verbose:
        print("\nThis will execute the following steps:")
        print("  1. Search the web for relevant information")
        print("  2. Fetch the top result page")
        print("  3. Parse the document into chunks")
        print("  4. Ingest knowledge into MongoDB and Graphiti")
        print("  5. Query the knowledge base")
        print("  6. Generate answer based on retrieved facts")
        print()
    
    try:
        start_time = datetime.now()
        
        # Run the agent (with settings patched)
        with patch("server.config.settings", mock_settings):
            result = await run_linear_research(query)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Print results
        print_result(result, query)
        
        print_section("Summary", "=")
        print(f"✅ Research completed successfully!")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📝 Answer length: {len(result.data.answer)} characters")
        print(f"📚 Sources: {len(result.data.sources)}")
        print(f"🔗 Citations: {len(result.data.citations)}")
        print()
        
        return result
        
    except Exception as e:
        print_section("Error", "=")
        print(f"❌ Research failed: {e}")
        print()
        
        if verbose:
            import traceback
            traceback.print_exc()
        
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run a research query using the Linear Researcher agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_research.py "Who is the CEO of Anthropic?"
  python run_research.py "What is the latest news about LK-99 superconductor?"
  python run_research.py "Explain quantum computing" --verbose
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        default="Who is the CEO of Anthropic?",
        help="Research question to answer (default: 'Who is the CEO of Anthropic?')"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output including error traces"
    )
    
    args = parser.parse_args()
    
    # Run the research
    try:
        result = asyncio.run(run_research(args.query, args.verbose))
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Research interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
