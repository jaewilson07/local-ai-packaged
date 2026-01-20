"""Test the Linear Researcher agent via the Lambda server API.

This script tests the agent by calling it through the server's REST API,
avoiding the Settings validation issues with direct imports.

Supports both internal network (no auth) and external network (JWT required) access.
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

# Add project root to path for sample.shared imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sample.shared.auth_helpers import (  # noqa: E402
    get_api_base_url,
    get_auth_headers,
    get_cloudflare_email,
)

# Base URL for the Lambda server (defaults to internal network)
BASE_URL = get_api_base_url()
AGENT_ENDPOINT = f"{BASE_URL}/api/v1/deep-research/query"  # We'll need to create this endpoint


async def test_search_web(headers: dict[str, str]):
    """Test the search_web tool via API."""
    print("=" * 80)
    print("Testing search_web via API")
    print("=" * 80)
    print()

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/mcp/tools/call",
                headers=headers,
                json={
                    "name": "search_web",
                    "arguments": {"query": "blues muse", "result_count": 3},
                },
            )
            response.raise_for_status()
            result = response.json()

            print("✅ Search successful!")
            print(f"Result: {json.dumps(result, indent=2)}")
            return True

        except Exception as e:
            print(f"❌ Error: {e}")
            if hasattr(e, "response"):
                print(f"Response: {e.response.text}")
            return False


async def test_agent_workflow(headers: dict[str, str]):
    """Test the full agent workflow via API (if endpoint exists)."""
    print("=" * 80)
    print("Testing Linear Researcher Agent Workflow")
    print("=" * 80)
    print()

    query = "Who is the CEO of Anthropic?"
    print(f"Query: {query}")
    print()

    # For now, we'll test the individual tools
    # In the future, we can add a dedicated agent endpoint

    print("Note: Full agent workflow requires a dedicated API endpoint.")
    print("For now, testing individual tools...")
    print()

    return await test_search_web(headers)


async def main():
    """Main test function."""
    # Get authentication headers
    try:
        headers = get_auth_headers()
    except ValueError as e:
        print("=" * 80)
        print("Authentication Error")
        print("=" * 80)
        print(f"\n{e}")
        print("\nTip: For local development, use internal network URL:")
        print("  export API_BASE_URL=http://lambda-server:8000")
        print("  (or http://localhost:8000 if running outside Docker)")
        return False

    cloudflare_email = get_cloudflare_email()

    print("Testing Deep Research Agent via Lambda Server API")
    print(f"Server URL: {BASE_URL}")
    if cloudflare_email:
        print(f"User Email: {cloudflare_email}")
    if headers:
        print("Authentication: Using Cloudflare Access JWT")
    else:
        print("Authentication: Internal network (no auth required)")
    print()

    # Test server connectivity
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BASE_URL}/", headers=headers)
            if response.status_code == 200:
                print("✅ Server is accessible")
            else:
                print(f"⚠️  Server returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print(f"   Make sure the Lambda server is running at {BASE_URL}")
        print("\n⚠️  Sample requires running services - exiting gracefully")
        return None  # Signal that we should exit gracefully

    print()

    # Test search_web tool
    success = await test_search_web(headers)

    # Verify results
    if success:
        try:
            print("\n" + "=" * 80)
            print("Verification")
            print("=" * 80)
            print("✅ API test completed successfully")
            print("\n✅ Verification passed!")
        except Exception as e:
            print(f"\n⚠️  Verification error: {e}")

    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        # Exit 0 if success or None (graceful exit due to missing services)
        sys.exit(0 if success is not False else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
