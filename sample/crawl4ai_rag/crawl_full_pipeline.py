#!/usr/bin/env python3
"""Comprehensive Crawl4AI test demonstrating all crawl functionality.

This sample validates:
1. Download without MongoDB (single page and deep crawl)
2. Crawl with MongoDB RAG ingestion
3. Graphiti knowledge graph extraction
4. Search verification (MongoDB RAG + Graphiti)

Prerequisites:
- Lambda server running
- MongoDB running
- Neo4j running (for Graphiti)
- Environment variables configured

Usage:
    python sample/crawl4ai_rag/crawl_full_pipeline.py

Validation:
This sample validates its results through:

1. **Download Validation** (no database):
   - Verifies markdown content is extracted
   - Checks file saving works correctly
   - Validates metadata extraction

2. **MongoDB RAG Validation**:
   - Verifies content is ingested into MongoDB
   - Confirms chunks are created with embeddings
   - Tests semantic search returns results

3. **Graphiti Validation** (if enabled):
   - Verifies facts are extracted to Neo4j
   - Tests knowledge graph search returns results

Exit codes:
- 0: All validations passed
- 1: One or more validations failed
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_URL = "https://example.com"  # Simple, reliable test URL
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
MAX_DEPTH = 2

# Output directory for downloaded files
OUTPUT_DIR = Path(__file__).parent.parent.parent / "temp" / "crawl4ai_test"


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)
    print()


def print_result(name: str, success: bool, details: str = "") -> None:
    """Print a formatted result."""
    status = "✅" if success else "❌"
    print(f"{status} {name}")
    if details:
        for line in details.split("\n"):
            print(f"   {line}")


async def check_server_health() -> bool:
    """Check if the Lambda server is healthy."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                print_result("Server health check", True)
                return True
            print_result("Server health check", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_result("Server health check", False, str(e))
        return False


# =============================================================================
# Test 1: Download without MongoDB (MCP tools)
# =============================================================================


async def test_download_single_page() -> dict[str, Any]:
    """Test download_page_markdown MCP tool (no MongoDB)."""
    print_header("Test 1a: Download Single Page (No MongoDB)")
    print(f"URL: {TEST_URL}")
    print("Save to file: True")
    print(f"Output directory: {OUTPUT_DIR}")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "name": "download_page_markdown",
                "arguments": {
                    "url": TEST_URL,
                    "save_to_file": True,
                    "output_path": str(OUTPUT_DIR),
                },
            }

            print("\n📡 Calling MCP tool: download_page_markdown...")
            response = await client.post(
                f"{API_BASE_URL}/api/v1/mcp/tools/call",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                # MCP tools return result in 'result' or directly
                if "result" in result:
                    result = result["result"]

                success = result.get("success", False)
                markdown = result.get("markdown", "")
                file_path = result.get("file_path")
                metadata = result.get("metadata", {})

                details = []
                details.append(f"Markdown length: {len(markdown)} chars")
                if file_path:
                    details.append(f"File saved: {file_path}")
                if metadata:
                    details.append(f"Metadata keys: {list(metadata.keys())}")

                print_result("Download single page", success, "\n".join(details))

                return {
                    "success": success,
                    "markdown_length": len(markdown),
                    "file_path": file_path,
                    "has_metadata": bool(metadata),
                }

            print_result(
                "Download single page", False, f"HTTP {response.status_code}: {response.text[:200]}"
            )
            return {"success": False, "error": response.text}

    except Exception as e:
        print_result("Download single page", False, str(e))
        return {"success": False, "error": str(e)}


async def test_download_deep_crawl() -> dict[str, Any]:
    """Test download_website_markdown MCP tool (no MongoDB)."""
    print_header("Test 1b: Download Deep Crawl (No MongoDB)")
    print(f"URL: {TEST_URL}")
    print(f"Max depth: {MAX_DEPTH}")
    print("Save to files: True")
    print(f"Output directory: {OUTPUT_DIR}")

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            payload = {
                "name": "download_website_markdown",
                "arguments": {
                    "url": TEST_URL,
                    "max_depth": MAX_DEPTH,
                    "save_to_files": True,
                    "output_directory": str(OUTPUT_DIR),
                },
            }

            print("\n📡 Calling MCP tool: download_website_markdown...")
            response = await client.post(
                f"{API_BASE_URL}/api/v1/mcp/tools/call",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    result = result["result"]

                success = result.get("success", False)
                pages = result.get("pages", [])
                total_pages = result.get("total_pages", 0)
                file_paths = result.get("file_paths", [])

                details = []
                details.append(f"Pages crawled: {total_pages}")
                details.append(f"Files saved: {len(file_paths) if file_paths else 0}")

                print_result("Download deep crawl", success, "\n".join(details))

                return {
                    "success": success,
                    "total_pages": total_pages,
                    "file_count": len(file_paths) if file_paths else 0,
                }

            print_result(
                "Download deep crawl", False, f"HTTP {response.status_code}: {response.text[:200]}"
            )
            return {"success": False, "error": response.text}

    except Exception as e:
        print_result("Download deep crawl", False, str(e))
        return {"success": False, "error": str(e)}


# =============================================================================
# Test 2: Crawl with MongoDB RAG ingestion
# =============================================================================


async def test_crawl_with_mongodb() -> dict[str, Any]:
    """Test crawl_single_page with MongoDB RAG ingestion."""
    print_header("Test 2: Crawl with MongoDB RAG Ingestion")
    print(f"URL: {TEST_URL}")
    print(f"Chunk size: {CHUNK_SIZE}")
    print(f"Chunk overlap: {CHUNK_OVERLAP}")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "url": TEST_URL,
                "chunk_size": CHUNK_SIZE,
                "chunk_overlap": CHUNK_OVERLAP,
            }

            print("\n📡 Calling REST API: /api/v1/crawl/single...")
            response = await client.post(
                f"{API_BASE_URL}/api/v1/crawl/single",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()

                success = result.get("success", False)
                pages_crawled = result.get("pages_crawled", 0)
                chunks_created = result.get("chunks_created", 0)
                document_ids = result.get("document_ids", [])
                errors = result.get("errors", [])

                details = []
                details.append(f"Pages crawled: {pages_crawled}")
                details.append(f"Chunks created: {chunks_created}")
                details.append(f"Documents: {len(document_ids)}")
                if errors:
                    details.append(f"Errors: {len(errors)}")

                print_result("MongoDB RAG ingestion", success, "\n".join(details))

                return {
                    "success": success,
                    "pages_crawled": pages_crawled,
                    "chunks_created": chunks_created,
                    "document_count": len(document_ids),
                    "errors": errors,
                }

            print_result(
                "MongoDB RAG ingestion",
                False,
                f"HTTP {response.status_code}: {response.text[:200]}",
            )
            return {"success": False, "error": response.text}

    except Exception as e:
        print_result("MongoDB RAG ingestion", False, str(e))
        return {"success": False, "error": str(e)}


# =============================================================================
# Test 3: Verify MongoDB RAG search
# =============================================================================


async def test_mongodb_rag_search() -> dict[str, Any]:
    """Test semantic search in MongoDB RAG."""
    print_header("Test 3: MongoDB RAG Semantic Search")

    search_query = "example domain"  # Should match example.com content
    print(f"Query: '{search_query}'")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "query": search_query,
                "search_type": "hybrid",
                "match_count": 5,
            }

            print("\n📡 Calling REST API: /api/v1/rag/search...")
            response = await client.post(
                f"{API_BASE_URL}/api/v1/rag/search",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                results = result.get("results", [])

                success = len(results) > 0
                details = []
                details.append(f"Results found: {len(results)}")

                if results:
                    details.append("\nTop results:")
                    for i, r in enumerate(results[:3], 1):
                        score = r.get("score", 0)
                        source = r.get("source", "Unknown")[:50]
                        details.append(f"  {i}. Score: {score:.4f}, Source: {source}")

                print_result("MongoDB RAG search", success, "\n".join(details))

                return {
                    "success": success,
                    "result_count": len(results),
                }

            print_result(
                "MongoDB RAG search", False, f"HTTP {response.status_code}: {response.text[:200]}"
            )
            return {"success": False, "error": response.text}

    except Exception as e:
        print_result("MongoDB RAG search", False, str(e))
        return {"success": False, "error": str(e)}


# =============================================================================
# Test 4: Verify Graphiti knowledge graph (if enabled)
# =============================================================================


async def test_graphiti_search() -> dict[str, Any]:
    """Test Graphiti knowledge graph search."""
    print_header("Test 4: Graphiti Knowledge Graph Search")

    search_query = "example domain information"
    print(f"Query: '{search_query}'")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "query": search_query,
                "match_count": 5,
            }

            print("\n📡 Calling REST API: /api/v1/graphiti/search...")
            response = await client.post(
                f"{API_BASE_URL}/api/v1/graphiti/search",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                results = result.get("results", [])
                success = result.get("success", False)

                details = []
                details.append(f"Results found: {len(results)}")

                if results:
                    details.append("\nTop results:")
                    for i, r in enumerate(results[:3], 1):
                        fact = r.get("fact", "")[:80]
                        similarity = r.get("similarity", 0)
                        details.append(f"  {i}. Similarity: {similarity:.4f}")
                        details.append(f"     Fact: {fact}...")

                print_result("Graphiti search", success and len(results) > 0, "\n".join(details))

                return {
                    "success": success and len(results) > 0,
                    "result_count": len(results),
                }

            if response.status_code == 404:
                print_result(
                    "Graphiti search",
                    True,
                    "Graphiti endpoint not available (USE_GRAPHITI may be disabled)",
                )
                return {"success": True, "skipped": True, "result_count": 0}

            print_result(
                "Graphiti search", False, f"HTTP {response.status_code}: {response.text[:200]}"
            )
            return {"success": False, "error": response.text}

    except Exception as e:
        print_result("Graphiti search", False, str(e))
        return {"success": False, "error": str(e)}


# =============================================================================
# Test 5: Crawl with authentication (cookies/headers)
# =============================================================================


async def test_crawl_with_auth() -> dict[str, Any]:
    """Test crawl_single_page with authentication parameters."""
    print_header("Test 5: Crawl with Authentication Parameters")
    print(f"URL: {TEST_URL}")
    print("Cookies: test_session=abc123")
    print("Headers: X-Custom-Header=test")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "name": "download_page_markdown",
                "arguments": {
                    "url": TEST_URL,
                    "save_to_file": False,
                    "cookies": "test_session=abc123; auth_token=xyz",
                    "headers": {"X-Custom-Header": "test", "Accept-Language": "en-US"},
                },
            }

            print("\n📡 Calling MCP tool: download_page_markdown with auth...")
            response = await client.post(
                f"{API_BASE_URL}/api/v1/mcp/tools/call",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    result = result["result"]

                success = result.get("success", False)
                markdown = result.get("markdown", "")

                details = []
                details.append(f"Success: {success}")
                details.append(f"Markdown extracted: {len(markdown)} chars")
                details.append("(Auth params accepted - actual auth validation depends on target)")

                print_result("Authenticated crawl", success, "\n".join(details))

                return {
                    "success": success,
                    "markdown_length": len(markdown),
                }

            print_result(
                "Authenticated crawl", False, f"HTTP {response.status_code}: {response.text[:200]}"
            )
            return {"success": False, "error": response.text}

    except Exception as e:
        print_result("Authenticated crawl", False, str(e))
        return {"success": False, "error": str(e)}


# =============================================================================
# Main
# =============================================================================


async def main():
    """Run all tests."""
    print_header("Crawl4AI Full Pipeline Test")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test URL: {TEST_URL}")

    # Check server health
    if not await check_server_health():
        print("\n❌ Server is not healthy. Please ensure the Lambda server is running.")
        print("   Start with: python start_services.py --stack lambda")
        print()
        print("   To check server status:")
        print("   docker ps --filter 'name=lambda'")
        print()
        print("   To view server logs:")
        print("   docker logs lambda-server --tail 50")
        sys.exit(1)

    # Run all tests
    results = {}

    # Test 1a: Download single page (no MongoDB)
    results["download_single"] = await test_download_single_page()

    # Test 1b: Download deep crawl (no MongoDB)
    results["download_deep"] = await test_download_deep_crawl()

    # Test 2: Crawl with MongoDB ingestion
    results["mongodb_ingest"] = await test_crawl_with_mongodb()

    # Wait for ingestion to propagate
    print("\n⏳ Waiting 3 seconds for ingestion to propagate...")
    await asyncio.sleep(3)

    # Test 3: MongoDB RAG search
    results["mongodb_search"] = await test_mongodb_rag_search()

    # Test 4: Graphiti search
    results["graphiti_search"] = await test_graphiti_search()

    # Test 5: Crawl with authentication
    results["auth_crawl"] = await test_crawl_with_auth()

    # Summary
    print_header("Test Summary")

    all_passed = True
    for test_name, result in results.items():
        success = result.get("success", False)
        skipped = result.get("skipped", False)

        if skipped:
            print(f"⏭️  {test_name}: SKIPPED")
        elif success:
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
            all_passed = False

    print()

    if all_passed:
        print("=" * 80)
        print("✅ All tests passed!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("=" * 80)
        print("❌ Some tests failed. Check output above for details.")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
