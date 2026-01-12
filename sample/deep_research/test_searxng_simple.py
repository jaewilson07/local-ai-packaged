"""
Simple test of SearXNG search API directly.

This validates that SearXNG is working and can search for "blues muse".
"""

import asyncio
import os
import sys

import httpx

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8081")


async def test_searxng_search():
    """Test SearXNG search directly."""
    print("=" * 80)
    print("Testing SearXNG Search for 'blues muse'")
    print("=" * 80)
    print()
    print(f"SearXNG URL: {SEARXNG_URL}")
    print()

    try:
        # Build SearXNG API request
        params = {"q": "blues muse", "format": "json", "pageno": 1}

        # Make request to SearXNG
        print("Making request to SearXNG...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{SEARXNG_URL}/search", params=params)
            response.raise_for_status()
            data = response.json()

        # Parse results
        results = data.get("results", [])
        print("✓ Search completed!")
        print(f"  Total results: {len(results)}")
        print()

        if results:
            print("Top 3 results:")
            for i, item in enumerate(results[:3], 1):
                print(f"  {i}. {item.get('title', 'N/A')}")
                print(f"     URL: {item.get('url', 'N/A')}")
                print(f"     Engine: {item.get('engine', 'N/A')}")
                print(f"     Score: {item.get('score', 'N/A')}")
                print()

            # Verify results
            try:
                from sample.shared.verification_helpers import verify_search_results

                print("\n" + "=" * 80)
                print("Verification")
                print("=" * 80)

                success, message = verify_search_results(results, expected_min=1)
                print(message)

                if success:
                    print("\n✅ Verification passed!")
                else:
                    print("\n⚠️  Verification failed")
            except Exception as e:
                print(f"\n⚠️  Verification error: {e}")

            return True
        else:
            print("  ⚠ No results returned")
            return False

    except httpx.TimeoutException:
        print("✗ Request timed out")
        return False
    except httpx.HTTPStatusError as e:
        print(f"✗ HTTP error: {e.response.status_code}")
        print(f"  Response: {e.response.text[:200]}")
        return False
    except httpx.RequestError as e:
        print(f"✗ Connection error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_searxng_search())
    sys.exit(0 if success else 1)
