#!/usr/bin/env python3
"""
Sample script for ingesting the sample blog document and verifying ingestion.

This script demonstrates:
1. Document ingestion via FastAPI endpoint
2. Validation of ingestion results (chunks, documents)
3. Verification using search APIs (semantic, text, hybrid)
4. Verification using agent query API
5. Direct MongoDB verification (optional)
6. Graphiti verification (optional, if enabled)

Prerequisites:
- Lambda server running (default: http://localhost:8000)
- MongoDB running and accessible
- Sample blog file at: sample/mongo_rag/sample_data/sample_blog.md
- Environment variables configured (MONGODB_URI, etc.)

Usage:
    python sample/mongo_rag/ingest_and_verify_sample_blog.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx

# Import shared auth helpers
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.auth_helpers import get_api_base_url, get_auth_headers, get_cloudflare_email

# Try to import rich for pretty output, fallback to basic print
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

    # Create a simple console-like object for fallback
    class SimpleConsole:
        def print(self, *args, **kwargs):
            print(*args)

    Console = SimpleConsole
    Table = None
    Panel = None

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

console = Console()

# Configuration - use auth_helpers for consistent API URL and auth
API_BASE_URL = f"{get_api_base_url()}/api/v1/rag"
SAMPLE_BLOG_PATH = project_root / "sample" / "mongo_rag" / "sample_data" / "sample_blog.md"


async def ingest_document(file_path: Path, clean_before: bool = False) -> dict[str, Any]:
    """
    Ingest a document using the FastAPI endpoint.

    Args:
        file_path: Path to the document file
        clean_before: Whether to clean existing data before ingestion

    Returns:
        Ingestion response with validation information
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Sample blog not found: {file_path}")

    if HAS_RICH:
        console.print(f"\n[bold cyan]📄 Ingesting document: {file_path.name}[/bold cyan]")
    else:
        print(f"\n📄 Ingesting document: {file_path.name}")

    url = f"{API_BASE_URL}/ingest"
    params = {}
    if clean_before:
        params["clean_before"] = "true"

    # Read file content
    with file_path.open("rb") as f:
        file_content = f.read()

    # Prepare multipart form data
    files = {"files": (file_path.name, file_content, "text/markdown")}
    headers = get_auth_headers()

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(url, files=files, params=params, headers=headers)
        if response.status_code != 200:
            error_text = response.text
            try:
                error_json = response.json()
                error_text = json.dumps(error_json, indent=2)
            except (ValueError, json.JSONDecodeError):
                pass
            if HAS_RICH:
                console.print(f"\n[red]❌ HTTP Error: {response.status_code}[/red]")
                console.print(f"[red]Response: {error_text[:1000]}[/red]")
            else:
                print(f"\n❌ HTTP Error: {response.status_code}")
                print(f"Response: {error_text[:1000]}")
        response.raise_for_status()
        return response.json()


async def search_knowledge_base(
    query: str, search_type: str = "hybrid", match_count: int = 5
) -> dict[str, Any]:
    """
    Search the knowledge base using the search API.

    Args:
        query: Search query
        search_type: Type of search (semantic, text, hybrid)
        match_count: Number of results to return

    Returns:
        Search response
    """
    url = f"{API_BASE_URL}/search"
    payload = {"query": query, "search_type": search_type, "match_count": match_count}
    headers = get_auth_headers()

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


async def agent_query(query: str) -> dict[str, Any]:
    """
    Query the RAG agent using the agent API.

    Args:
        query: Question for the agent

    Returns:
        Agent response
    """
    url = f"{API_BASE_URL}/agent"
    payload = {"query": query}
    headers = get_auth_headers()

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


def display_ingestion_results(result: dict[str, Any]) -> None:
    """Display ingestion validation information."""
    if HAS_RICH:
        console.print("\n[bold green]✅ Ingestion Complete[/bold green]")

        table = Table(title="Ingestion Validation", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Documents Processed", str(result.get("documents_processed", 0)))
        table.add_row("Chunks Created", str(result.get("chunks_created", 0)))

        errors = result.get("errors", [])
        if errors:
            error_count = sum(len(err) for err in errors if isinstance(err, list))
            table.add_row("Errors", f"[red]{error_count}[/red]")
            for i, error_list in enumerate(errors[:3], 1):  # Show first 3 errors
                if isinstance(error_list, list) and error_list:
                    table.add_row(
                        f"  Error {i}",
                        error_list[0][:60] + "..." if len(error_list[0]) > 60 else error_list[0],
                    )
        else:
            table.add_row("Errors", "[green]None[/green]")

        console.print(table)

        # Calculate average chunks per document
        docs = result.get("documents_processed", 0)
        chunks = result.get("chunks_created", 0)
        if docs > 0:
            avg_chunks = chunks / docs
            console.print(f"\n[dim]Average chunks per document: {avg_chunks:.1f}[/dim]")
    else:
        print("\n✅ Ingestion Complete")
        print(f"  Documents Processed: {result.get('documents_processed', 0)}")
        print(f"  Chunks Created: {result.get('chunks_created', 0)}")
        errors = result.get("errors", [])
        if errors:
            error_count = sum(len(err) for err in errors if isinstance(err, list))
            print(f"  Errors: {error_count}")
        else:
            print("  Errors: None")
        docs = result.get("documents_processed", 0)
        chunks = result.get("chunks_created", 0)
        if docs > 0:
            avg_chunks = chunks / docs
            print(f"  Average chunks per document: {avg_chunks:.1f}")


def display_search_results(result: dict[str, Any], query: str, search_type: str) -> None:
    """Display search results in a formatted table."""
    results = result.get("results", [])
    count = result.get("count", 0)

    if HAS_RICH:
        console.print(f"\n[bold cyan]🔍 Search Results ({search_type})[/bold cyan]")
        console.print(f"[dim]Query: {query}[/dim]")
        console.print(f"[dim]Found {count} results[/dim]\n")

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("Title", style="green", width=30)
        table.add_column("Similarity", style="yellow", width=12)
        table.add_column("Content Preview", style="white", width=50)

        for i, item in enumerate(results[:5], 1):  # Show top 5
            title = item.get("document_title", "Unknown")[:30]
            similarity = item.get("similarity", 0.0)
            content = item.get("content", "")[:50].replace("\n", " ")

            table.add_row(
                str(i),
                title,
                f"{similarity:.3f}",
                content + "..." if len(content) == 50 else content,
            )

        console.print(table)
    else:
        print(f"\n🔍 Search Results ({search_type})")
        print(f"Query: {query}")
        print(f"Found {count} results\n")

        if not results:
            print("No results found")
            return

        for i, item in enumerate(results[:5], 1):  # Show top 5
            title = item.get("document_title", "Unknown")
            similarity = item.get("similarity", 0.0)
            content = item.get("content", "")[:100].replace("\n", " ")
            print(f"{i}. [{similarity:.3f}] {title}")
            print(f"   {content}...")
            print()


def display_agent_response(result: dict[str, Any], query: str) -> None:
    """Display agent response."""
    response_text = result.get("response", "")

    if HAS_RICH:
        console.print("\n[bold cyan]🤖 Agent Response[/bold cyan]")
        console.print(f"[dim]Query: {query}[/dim]\n")

        panel = Panel(
            response_text, title="[bold]Response[/bold]", border_style="cyan", padding=(1, 2)
        )
        console.print(panel)
    else:
        print("\n🤖 Agent Response")
        print(f"Query: {query}\n")
        print("=" * 60)
        print(response_text)
        print("=" * 60)


async def verify_mongodb_direct(document_title: str | None = None) -> dict[str, Any] | None:
    """
    Verify MongoDB directly (optional - requires MongoDB connection).

    This is a placeholder - actual implementation would require MongoDB client.
    """
    if HAS_RICH:
        console.print(
            "\n[dim]💡 Tip: For direct MongoDB verification, use MongoDB client or Compass[/dim]"
        )
        console.print("[dim]   Query: db.documents.find({title: /bluesmas/i})[/dim]")
        console.print(
            "[dim]   Query: db.chunks.countDocuments({document_id: ObjectId('...')})[/dim]"
        )
    else:
        print("\n💡 Tip: For direct MongoDB verification, use MongoDB client or Compass")
        print("   Query: db.documents.find({title: /bluesmas/i})")
        print("   Query: db.chunks.countDocuments({document_id: ObjectId('...')})")
    return None


async def verify_graphiti(entity_name: str | None = None) -> dict[str, Any] | None:
    """
    Verify Graphiti/Neo4j (optional - requires Graphiti enabled).

    This would query Neo4j for entities and relationships extracted from the document.
    """
    if HAS_RICH:
        console.print(
            "\n[dim]💡 Tip: For Graphiti verification, use Graphiti search API or Neo4j browser[/dim]"
        )
        console.print("[dim]   API: POST /api/v1/rag/graphiti/search?query=Sugar[/dim]")
        console.print("[dim]   Neo4j: MATCH (n) WHERE n.name CONTAINS 'Sugar' RETURN n[/dim]")
    else:
        print("\n💡 Tip: For Graphiti verification, use Graphiti search API or Neo4j browser")
        print("   API: POST /api/v1/rag/graphiti/search?query=Sugar")
        print("   Neo4j: MATCH (n) WHERE n.name CONTAINS 'Sugar' RETURN n")
    return None


async def verify_me_data_api() -> dict[str, Any] | None:
    """
    Verify ingestion results via /api/me/data/rag endpoint.

    This shows user-scoped document and chunk counts.
    """
    api_base = get_api_base_url()
    url = f"{api_base}/api/me/data/rag"
    headers = get_auth_headers()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if HAS_RICH:
                console.print("\n[bold cyan]📊 Data Summary (/api/me/data/rag)[/bold cyan]")

                rag_data = data.get("rag", {})
                mongodb = rag_data.get("mongodb", {})

                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("Documents", str(mongodb.get("documents", 0)))
                table.add_row("Chunks", str(mongodb.get("chunks", 0)))
                table.add_row("Sources", str(mongodb.get("sources", 0)))

                console.print(table)

                user_email = get_cloudflare_email()
                if user_email:
                    console.print(f"\n[dim]User: {user_email}[/dim]")
            else:
                print("\n📊 Data Summary (/api/me/data/rag)")
                rag_data = data.get("rag", {})
                mongodb = rag_data.get("mongodb", {})
                print(f"  Documents: {mongodb.get('documents', 0)}")
                print(f"  Chunks: {mongodb.get('chunks', 0)}")
                print(f"  Sources: {mongodb.get('sources', 0)}")
                user_email = get_cloudflare_email()
                if user_email:
                    print(f"  User: {user_email}")

            return data
    except Exception as e:
        if HAS_RICH:
            console.print(f"[yellow]⚠️  Could not verify /api/me/data/rag: {e}[/yellow]")
        else:
            print(f"⚠️  Could not verify /api/me/data/rag: {e}")
        return None


async def main():
    """Main function to ingest and verify the sample blog."""
    if HAS_RICH:
        console.print(
            Panel.fit(
                "[bold cyan]MongoDB RAG - Sample Blog Ingestion & Verification[/bold cyan]",
                border_style="cyan",
            )
        )
    else:
        print("=" * 60)
        print("MongoDB RAG - Sample Blog Ingestion & Verification")
        print("=" * 60)

    # Check if sample blog exists
    if not SAMPLE_BLOG_PATH.exists():
        if HAS_RICH:
            console.print(f"[red]❌ Sample blog not found: {SAMPLE_BLOG_PATH}[/red]")
            console.print("[yellow]Please ensure the sample blog file exists[/yellow]")
        else:
            print(f"❌ Sample blog not found: {SAMPLE_BLOG_PATH}")
            print("Please ensure the sample blog file exists")
        sys.exit(1)

    try:
        # Step 1: Ingest the document
        if HAS_RICH:
            console.print("\n[bold]Step 1: Document Ingestion[/bold]")
        else:
            print("\nStep 1: Document Ingestion")
        print("=" * 60)

        ingestion_result = await ingest_document(SAMPLE_BLOG_PATH, clean_before=False)
        display_ingestion_results(ingestion_result)

        # Extract document IDs if available (for future verification)
        ingestion_result.get("document_ids", [])
        chunks_created = ingestion_result.get("chunks_created", 0)

        if chunks_created == 0:
            if HAS_RICH:
                console.print(
                    "\n[yellow]⚠️  Warning: No chunks were created. Check for errors above.[/yellow]"
                )
            else:
                print("\n⚠️  Warning: No chunks were created. Check for errors above.")
            return

        # Wait a moment for indexing
        if HAS_RICH:
            console.print("\n[dim]Waiting 2 seconds for indexing...[/dim]")
        else:
            print("\nWaiting 2 seconds for indexing...")
        await asyncio.sleep(2)

        # Step 2: Verify with search APIs
        if HAS_RICH:
            console.print("\n[bold]Step 2: Verification via Search APIs[/bold]")
        else:
            print("\nStep 2: Verification via Search APIs")
        print("=" * 60)

        # Test queries related to the sample blog
        test_queries = [
            ("What is bluesmas?", "hybrid"),
            ("Tell me about Sugar", "semantic"),
            ("bluesmas", "text"),
        ]

        for query, search_type in test_queries:
            try:
                search_result = await search_knowledge_base(
                    query, search_type=search_type, match_count=3
                )
                display_search_results(search_result, query, search_type)
            except Exception as e:
                if HAS_RICH:
                    console.print(f"[red]❌ Search failed for '{query}': {e}[/red]")
                else:
                    print(f"❌ Search failed for '{query}': {e}")

        # Step 3: Verify with agent query
        if HAS_RICH:
            console.print("\n[bold]Step 3: Verification via Agent Query[/bold]")
        else:
            print("\nStep 3: Verification via Agent Query")
        print("=" * 60)

        agent_queries = [
            "What is bluesmas?",
            "Tell me about Sugar and his music",
            "What does the blog say about traditional blues?",
        ]

        for query in agent_queries:
            try:
                agent_result = await agent_query(query)
                display_agent_response(agent_result, query)
                await asyncio.sleep(1)  # Brief pause between queries
            except Exception as e:
                if HAS_RICH:
                    console.print(f"[red]❌ Agent query failed for '{query}': {e}[/red]")
                else:
                    print(f"❌ Agent query failed for '{query}': {e}")

        # Step 4: Direct verification (optional)
        if HAS_RICH:
            console.print("\n[bold]Step 4: Direct Database Verification (Optional)[/bold]")
        else:
            print("\nStep 4: Direct Database Verification (Optional)")
        print("=" * 60)

        await verify_mongodb_direct(document_title="bluesmas")
        await verify_graphiti(entity_name="Sugar")

        # Step 5: Verify via /me/data API
        if HAS_RICH:
            console.print("\n[bold]Step 5: Verification via /api/me/data/rag[/bold]")
        else:
            print("\nStep 5: Verification via /api/me/data/rag")
        print("=" * 60)

        me_data_result = await verify_me_data_api()

        # Summary
        if HAS_RICH:
            console.print("\n[bold green]✅ Verification Complete![/bold green]")
            console.print("\n[bold]Summary:[/bold]")
            console.print(
                f"  • Documents processed: {ingestion_result.get('documents_processed', 0)}"
            )
            console.print(f"  • Chunks created: {chunks_created}")
            console.print(f"  • Search API: Tested with {len(test_queries)} queries")
            console.print(f"  • Agent API: Tested with {len(agent_queries)} queries")
            console.print("\n[dim]The document is now searchable via the RAG system![/dim]")
        else:
            print("\n✅ Verification Complete!")
            print("\nSummary:")
            print(f"  • Documents processed: {ingestion_result.get('documents_processed', 0)}")
            print(f"  • Chunks created: {chunks_created}")
            print(f"  • Search API: Tested with {len(test_queries)} queries")
            print(f"  • Agent API: Tested with {len(agent_queries)} queries")
            print("\nThe document is now searchable via the RAG system!")

    except httpx.HTTPStatusError as e:
        console.print(f"\n[red]❌ HTTP Error: {e.response.status_code}[/red]")
        console.print(f"[red]Response: {e.response.text}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback

        console.print(f"[red]{traceback.format_exc()}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
