"""Validation CLI script for Discord bot configuration and connectivity.

Usage:
    python scripts/validate.py config      # Validate configuration
    python scripts/validate.py immich      # Test Immich connection
    python scripts/validate.py discord    # Test Discord connection
    python scripts/validate.py database   # Check database schema
    python scripts/validate.py mcp        # Test MCP server
    python scripts/validate.py all        # Run all validations
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add bot directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import config
from bot.database import Database


def validate_config():
    """Validate configuration values."""
    print("=" * 60)
    print("Validating Configuration")
    print("=" * 60)

    errors = config.validate()

    if errors:
        print("❌ Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("✅ All required configuration values are set")
    print()
    print("Configuration values:")
    print(f"  DISCORD_BOT_TOKEN: {'✓ Set' if config.DISCORD_BOT_TOKEN else '✗ Missing'}")
    print(
        f"  DISCORD_UPLOAD_CHANNEL_ID: {'✓ Set' if config.DISCORD_UPLOAD_CHANNEL_ID else '✗ Missing'}"
    )
    print(f"  IMMICH_API_KEY: {'✓ Set' if config.IMMICH_API_KEY else '✗ Missing'}")
    print(f"  IMMICH_SERVER_URL: {config.IMMICH_SERVER_URL}")
    print(f"  BOT_DB_PATH: {config.BOT_DB_PATH}")
    print(f"  NOTIFICATION_POLL_INTERVAL: {config.NOTIFICATION_POLL_INTERVAL}s")
    print(f"  MCP_ENABLED: {config.MCP_ENABLED}")
    if config.MCP_ENABLED:
        print(f"  MCP_HOST: {config.MCP_HOST}")
        print(f"  MCP_PORT: {config.MCP_PORT}")

    return True


async def validate_immich():
    """Validate Immich connection."""
    print("=" * 60)
    print("Validating Immich Connection")
    print("=" * 60)

    try:
        from bot.immich_client import ImmichClient

        client = ImmichClient()

        # Test connection with a simple API call
        print("Testing Immich API connection...")
        people = await client.search_people("")
        print("✅ Immich connection successful!")
        print(f"  Server: {config.IMMICH_SERVER_URL}")
        print(f"  Found {len(people)} people in database")
        return True

    except Exception as e:
        print(f"❌ Immich connection failed: {type(e).__name__}: {e!s}")
        print()
        print("Troubleshooting:")
        print("1. Verify IMMICH_SERVER_URL is correct")
        print("2. Verify IMMICH_API_KEY is valid")
        print("3. Check if Immich server is running")
        return False


async def validate_discord():
    """Validate Discord connection."""
    print("=" * 60)
    print("Validating Discord Connection")
    print("=" * 60)

    try:
        import discord

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        client = discord.Client(intents=intents)
        connected = False

        @client.event
        async def on_ready():
            nonlocal connected
            connected = True

        try:
            # Try to connect with timeout
            asyncio.create_task(client.start(config.DISCORD_BOT_TOKEN))
            await asyncio.sleep(3)  # Wait for connection

            if connected:
                print("✅ Discord connection successful!")
                print(f"  Bot: {client.user.name} (ID: {client.user.id})")
                print(f"  Servers: {len(client.guilds)}")
                await client.close()
                return True
            print("❌ Failed to connect to Discord (timeout)")
            await client.close()
            return False

        except discord.LoginFailure:
            print("❌ Invalid Discord bot token")
            return False
        except Exception as e:
            print(f"❌ Discord connection failed: {type(e).__name__}: {e!s}")
            if not client.is_closed():
                await client.close()
            return False

    except ImportError:
        print("❌ discord.py not installed")
        return False


async def validate_database():
    """Validate database schema."""
    print("=" * 60)
    print("Validating Database")
    print("=" * 60)

    try:
        db = Database()
        await db.initialize()

        print("✅ Database initialized successfully")
        print(f"  Path: {db.db_path}")

        # Check if tables exist
        import aiosqlite

        async with aiosqlite.connect(db.db_path) as conn:
            async with conn.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
                tables = [row[0] for row in await cursor.fetchall()]
                print(f"  Tables: {', '.join(tables)}")

                if "users" in tables and "last_check" in tables:
                    print("✅ All required tables exist")
                    return True
                print("❌ Missing required tables")
                return False

    except Exception as e:
        print(f"❌ Database validation failed: {type(e).__name__}: {e!s}")
        return False


async def validate_mcp():
    """Validate MCP server."""
    print("=" * 60)
    print("Validating MCP Server")
    print("=" * 60)

    if not config.MCP_ENABLED:
        print("⚠ MCP server is disabled")
        print("Set MCP_ENABLED=true to enable MCP server")
        return True  # Not an error, just disabled

    try:
        import httpx

        base_url = f"http://{config.MCP_HOST}:{config.MCP_PORT}"

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(f"{base_url}/mcp/tools/list", json={})
            response.raise_for_status()

            print("✅ MCP server is accessible")
            print(f"  URL: {base_url}")
            tools = response.json()
            print(f"  Tools available: {len(tools.get('tools', []))}")
            return True

    except httpx.ConnectError:
        print(f"❌ MCP server not accessible at {base_url}")
        print("Make sure the Discord bot is running with MCP_ENABLED=true")
        return False
    except Exception as e:
        print(f"❌ MCP server validation failed: {type(e).__name__}: {e!s}")
        return False


async def validate_all():
    """Run all validations."""
    print()
    results = {}

    results["config"] = validate_config()
    print()

    results["immich"] = await validate_immich()
    print()

    results["discord"] = await validate_discord()
    print()

    results["database"] = await validate_database()
    print()

    results["mcp"] = await validate_mcp()
    print()

    # Summary
    print("=" * 60)
    print("Validation Summary")
    print("=" * 60)
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name:12} {status}")
    print()

    all_passed = all(results.values())
    if all_passed:
        print("✅ All validations passed!")
    else:
        print("❌ Some validations failed")

    return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Discord bot configuration and connectivity"
    )
    parser.add_argument(
        "command",
        choices=["config", "immich", "discord", "database", "mcp", "all"],
        help="Validation command to run",
    )

    args = parser.parse_args()

    if args.command == "config":
        success = validate_config()
    elif args.command == "immich":
        success = asyncio.run(validate_immich())
    elif args.command == "discord":
        success = asyncio.run(validate_discord())
    elif args.command == "database":
        success = asyncio.run(validate_database())
    elif args.command == "mcp":
        success = asyncio.run(validate_mcp())
    elif args.command == "all":
        success = asyncio.run(validate_all())

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
