#!/usr/bin/env python3
"""Test script to verify Discord bot can reach Lambda server."""

import asyncio
import sys

import aiohttp


async def test_lambda_connection():
    """Test if bot can reach Lambda server."""
    print("Testing connection to Lambda server...")

    try:
        async with aiohttp.ClientSession() as session:
            # Test health endpoint
            async with session.get(
                "http://lambda-server:8000/health", timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                status = resp.status
                text = await resp.text()
                print(f"✅ Health check: Status {status}, Response: {text}")

            # Test Discord characters endpoint (should fail with 500 but prove connectivity)
            async with session.get(
                "http://lambda-server:8000/api/v1/discord/characters/list?channel_id=test123",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                status = resp.status
                try:
                    text = await resp.text()
                    print(f"✅ Discord API endpoint: Status {status}")
                    if status == 500:
                        print("   (500 error expected - endpoint requires valid channel_id)")
                except Exception as e:
                    print(f"   Response error: {e}")

    except aiohttp.ClientConnectorError as e:
        print(f"❌ Connection failed: {e}")
        print("   Bot cannot reach Lambda server. Check network configuration.")
        return False
    except asyncio.TimeoutError:
        print("❌ Connection timeout: Lambda server not responding")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    print("\n✅ Bot CAN reach Lambda server!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_lambda_connection())
    sys.exit(0 if success else 1)
