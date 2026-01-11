"""Test the Linear Researcher agent via the Lambda server API.

This script tests the agent by calling it through the server's REST API,
avoiding the Settings validation issues with direct imports.
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime

# Base URL for the Lambda server
BASE_URL = os.getenv("LAMBDA_SERVER_URL", "http://localhost:8000")
AGENT_ENDPOINT = f"{BASE_URL}/api/v1/deep-research/query"  # We'll need to create this endpoint


async def test_search_web():
    """Test the search_web tool via API."""
    print("=" * 80)
    print("Testing search_web via API")
    print("=" * 80)
    print()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/mcp/tools/call",
                json={
                    "name": "search_web",
                    "arguments": {
                        "query": "blues muse",
                        "result_count": 3
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ Search successful!")
            print(f"Result: {json.dumps(result, indent=2)}")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            if hasattr(e, 'response'):
                print(f"Response: {e.response.text}")
            return False


async def test_agent_workflow():
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
    
    return await test_search_web()


async def main():
    """Main test function."""
    print("Testing Deep Research Agent via Lambda Server API")
    print(f"Server URL: {BASE_URL}")
    print()
    
    # Test server connectivity
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BASE_URL}/")
            if response.status_code == 200:
                print("✅ Server is accessible")
            else:
                print(f"⚠️  Server returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print(f"   Make sure the Lambda server is running at {BASE_URL}")
        return False
    
    print()
    
    # Test search_web tool
    success = await test_search_web()
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
