"""
Sample: Deep Research Agent - Search for "blues muse"

This sample demonstrates the Phase 1-2 integration:
1. Search the web for "blues muse"
2. Fetch the top result page
3. Parse the document into chunks
4. Ingest into MongoDB and Graphiti
5. Query the knowledge base

Run this after starting the Lambda server:
    python start_services.py --stack lambda

Then run:
    python sample/deep_research/search_blues_muse.py
"""

import asyncio
from typing import Any

import httpx

BASE_URL = "http://localhost:8000"
MCP_TOOLS_ENDPOINT = f"{BASE_URL}/api/v1/mcp/tools/call"


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call an MCP tool via the REST API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            MCP_TOOLS_ENDPOINT, json={"name": tool_name, "arguments": arguments}
        )
        response.raise_for_status()
        return response.json()


async def main():
    """Run the full deep research flow for 'blues muse'."""
    print("=" * 80)
    print("Deep Research Agent - Search for 'blues muse'")
    print("=" * 80)
    print()

    session_id = "sample-blues-muse-001"

    # Step 1: Search the web
    print("Step 1: Searching the web for 'blues muse'...")
    try:
        search_result = await call_mcp_tool(
            "search_web", {"query": "blues muse", "result_count": 5}
        )

        print(f"✓ Found {search_result.get('count', 0)} results")
        if search_result.get("results"):
            print(f"  Top result: {search_result['results'][0].get('title', 'N/A')}")
            print(f"  URL: {search_result['results'][0].get('url', 'N/A')}")
            top_url = search_result["results"][0].get("url")
        else:
            print("  No results found")
            return
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return

    print()

    # Step 2: Fetch the top result page
    print(f"Step 2: Fetching page: {top_url}")
    try:
        fetch_result = await call_mcp_tool("fetch_page", {"url": top_url})

        if fetch_result.get("success"):
            print("✓ Fetched page successfully")
            print(f"  Content length: {len(fetch_result.get('content', ''))} characters")
            content = fetch_result.get("content", "")
            content_type = fetch_result.get("content_type", "html")
        else:
            print(f"✗ Fetch failed: {fetch_result.get('error', 'Unknown error')}")
            return
    except Exception as e:
        print(f"✗ Fetch failed: {e}")
        return

    print()

    # Step 3: Parse the document
    print("Step 3: Parsing document into chunks...")
    try:
        parse_result = await call_mcp_tool(
            "parse_document", {"content": content, "content_type": content_type}
        )

        if parse_result.get("success"):
            chunks = parse_result.get("chunks", [])
            print(f"✓ Parsed into {len(chunks)} chunks")
            if chunks:
                print(f"  First chunk preview: {chunks[0].get('content', '')[:100]}...")
        else:
            print(f"✗ Parse failed: {parse_result.get('error', 'Unknown error')}")
            return
    except Exception as e:
        print(f"✗ Parse failed: {e}")
        return

    print()

    # Step 4: Ingest into knowledge base
    print("Step 4: Ingesting into MongoDB and Graphiti...")
    try:
        ingest_result = await call_mcp_tool(
            "ingest_knowledge",
            {
                "chunks": chunks,
                "session_id": session_id,
                "source_url": top_url,
                "title": search_result["results"][0].get("title", "Blues Muse"),
            },
        )

        if ingest_result.get("success"):
            print("✓ Ingested successfully")
            print(f"  Document ID: {ingest_result.get('document_id', 'N/A')}")
            print(f"  Chunks created: {ingest_result.get('chunks_created', 0)}")
            print(f"  Facts added: {ingest_result.get('facts_added', 0)}")
        else:
            print(f"✗ Ingest failed: {ingest_result.get('error', 'Unknown error')}")
            return
    except Exception as e:
        print(f"✗ Ingest failed: {e}")
        return

    print()

    # Step 5: Query the knowledge base
    print("Step 5: Querying the knowledge base...")
    try:
        query_result = await call_mcp_tool(
            "query_knowledge",
            {
                "question": "What is blues muse?",
                "session_id": session_id,
                "match_count": 3,
                "search_type": "hybrid",
            },
        )

        if query_result.get("success"):
            matches = query_result.get("matches", [])
            print(f"✓ Found {len(matches)} matches")
            for i, match in enumerate(matches[:3], 1):
                print(f"  Match {i}:")
                print(f"    Content: {match.get('content', '')[:150]}...")
                print(f"    Source: {match.get('source_url', 'N/A')}")
                print(f"    Similarity: {match.get('similarity', 0):.3f}")
        else:
            print(f"✗ Query failed: {query_result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"✗ Query failed: {e}")

    print()
    print("=" * 80)
    print("Sample completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
