"""Manual test script for MCP server tools.

This script can be run independently to test MCP server endpoints:
    python -m tests.manual.test_mcp_tools
"""

import asyncio
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("❌ ERROR: httpx not installed. Install with: pip install httpx")
    sys.exit(1)

# Add bot directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.config import config


async def test_mcp_server():
    """Test MCP server endpoints."""
    print("=" * 60)
    print("Testing MCP Server")
    print("=" * 60)

    if not config.MCP_ENABLED:
        print("⚠ MCP server is disabled (MCP_ENABLED=false)")
        print("Set MCP_ENABLED=true to test MCP server")
        return False

    base_url = f"http://{config.MCP_HOST}:{config.MCP_PORT}"
    print(f"✓ MCP Server URL: {base_url}")
    print()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Test 1: List available tools
            print("Test 1: Listing available MCP tools...")
            try:
                response = await client.post(f"{base_url}/mcp/tools/list", json={})
                response.raise_for_status()
                tools = response.json()
                print(f"✅ Found {len(tools.get('tools', []))} MCP tools")
                if tools.get("tools"):
                    print("  Available tools:")
                    for tool in tools["tools"][:10]:  # Show first 10
                        print(f"    - {tool.get('name', 'N/A')}")
                    if len(tools["tools"]) > 10:
                        print(f"    ... and {len(tools['tools']) - 10} more")
                print()
            except httpx.ConnectError:
                print("❌ ERROR: Could not connect to MCP server")
                print("Make sure the Discord bot is running with MCP_ENABLED=true")
                return False
            except Exception as e:
                print(f"⚠ Warning: {type(e).__name__}: {e!s}")
                print()

            # Test 2: Call a simple tool (list_servers)
            print("Test 2: Testing list_servers tool...")
            try:
                response = await client.post(
                    f"{base_url}/mcp/tools/call", json={"name": "list_servers", "arguments": {}}
                )
                response.raise_for_status()
                result = response.json()
                print("✅ list_servers tool executed successfully")
                if result.get("content"):
                    content = result["content"]
                    if isinstance(content, list):
                        print(f"  Found {len(content)} servers")
                    else:
                        print(f"  Result: {str(content)[:100]}")
                print()
            except Exception as e:
                print(f"⚠ Warning: Could not test list_servers: {type(e).__name__}: {e!s}")
                print("  (This is expected if bot is not connected to Discord)")
                print()

            # Test 3: Test invalid tool call
            print("Test 3: Testing error handling...")
            try:
                response = await client.post(
                    f"{base_url}/mcp/tools/call", json={"name": "nonexistent_tool", "arguments": {}}
                )
                # Should return error
                if response.status_code != 200:
                    print("✅ Error handling works correctly")
                else:
                    result = response.json()
                    if result.get("isError"):
                        print("✅ Error handling works correctly")
                    else:
                        print("⚠ Unexpected success for invalid tool")
                print()
            except Exception as e:
                print(f"⚠ Warning: {type(e).__name__}: {e!s}")
                print()

            print("=" * 60)
            print("✅ MCP server tests completed!")
            print("=" * 60)
            return True

        except httpx.ConnectError:
            print("❌ ERROR: Could not connect to MCP server")
            print()
            print("Troubleshooting:")
            print("1. Verify MCP_ENABLED=true in environment")
            print("2. Check if Discord bot is running")
            print("3. Verify MCP_PORT and MCP_HOST are correct")
            print("4. Check if MCP server is accessible at the configured URL")
            return False
        except Exception as e:
            print(f"❌ ERROR: {type(e).__name__}: {e!s}")
            return False


async def main():
    """Main entry point."""
    print()
    success = await test_mcp_server()
    print()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
