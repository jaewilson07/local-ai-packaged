"""Main entry point for Discord bot."""

import asyncio
import logging
import sys

import discord
from discord import app_commands

from bot.capabilities import CapabilityRegistry
from bot.config import config
from bot.database import Database
from bot.handlers.notification_task import NotificationTask
from bot.immich_client import ImmichClient

# MCP server imports
if config.MCP_ENABLED:
    # Import tools to register them (must happen before using mcp)
    import uvicorn

    from bot.mcp import tools  # noqa: F401
    from bot.mcp.server import mcp, set_discord_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize components
database = Database()
immich_client = ImmichClient()
notification_task: NotificationTask | None = None

# Shared API client (initialized lazily when needed)
# This is created once and shared across all components that need Lambda API access
_shared_api_client = None


def get_shared_api_client():
    """
    Get or create the shared Lambda API client.

    Returns:
        APIClient instance or None if Lambda API is not configured
    """
    global _shared_api_client

    if not config.LAMBDA_API_URL:
        return None

    if _shared_api_client is None:
        from bot.api_client import APIClient

        _shared_api_client = APIClient(
            base_url=config.LAMBDA_API_URL,
            api_key=config.LAMBDA_API_KEY,
            cloudflare_client_id=config.CLOUDFLARE_ACCESS_CLIENT_ID,
            cloudflare_client_secret=config.CLOUDFLARE_ACCESS_CLIENT_SECRET,
        )
        logger.info("Shared API client created")

    return _shared_api_client


async def cleanup_shared_api_client():
    """Close the shared API client if it exists."""
    global _shared_api_client
    if _shared_api_client is not None:
        await _shared_api_client.close()
        _shared_api_client = None
        logger.info("Shared API client closed")


# Create Discord client with intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.members = True  # Required for user lookups

# Set presence at initialization (avoids issues with on_ready being called multiple times)
activity = discord.Activity(type=discord.ActivityType.listening, name="for @mentions")
client = discord.Client(intents=intents, activity=activity, status=discord.Status.online)
tree = app_commands.CommandTree(client)

# Initialize capability registry
capability_registry = CapabilityRegistry(client)


async def fetch_bot_config_from_api() -> tuple[list[str] | None, dict[str, dict]]:
    """
    Fetch bot configuration from Lambda API.

    Returns:
        Tuple of (enabled_capabilities, capability_settings)
        enabled_capabilities is None if API unavailable
        capability_settings is empty dict if not available
    """
    api_client = get_shared_api_client()
    if api_client is None:
        logger.debug("LAMBDA_API_URL not configured, skipping API config fetch")
        return None, {}

    try:
        bot_config = await api_client.get_bot_config()
        enabled = bot_config.get("enabled_capabilities", [])
        settings = bot_config.get("capability_settings", {})
        logger.info(f"Fetched capabilities from API: {enabled}")
        logger.info(f"Fetched capability settings: {list(settings.keys())}")
        return enabled, settings
    except Exception as e:
        logger.warning(f"Failed to fetch capabilities from API: {e}")
        return None, {}


def load_capabilities(
    enabled: list[str] | None = None,
    capability_settings: dict[str, dict] | None = None,
) -> None:
    """
    Load enabled capabilities based on configuration.

    Args:
        enabled: List of capability names to enable (falls back to config if None)
        capability_settings: Per-capability settings from Lambda API
    """
    if enabled is None:
        enabled = config.get_enabled_capabilities()
    if capability_settings is None:
        capability_settings = {}

    logger.info(f"Loading capabilities: {enabled}")

    # Import and register capabilities based on config
    if "echo" in enabled:
        from bot.capabilities.echo import EchoCapability

        echo_settings = capability_settings.get("echo", {})
        capability_registry.register(EchoCapability(client, settings=echo_settings))

    if "upload" in enabled:
        from bot.capabilities.upload import UploadCapability

        upload_settings = capability_settings.get("upload", {})
        capability_registry.register(
            UploadCapability(client, immich_client, database, settings=upload_settings)
        )

    if "character" in enabled:
        from bot.capabilities.character_commands import CharacterCommandsCapability
        from bot.capabilities.character_mention import CharacterMentionCapability

        # Use shared API client for character capabilities
        api_client = get_shared_api_client()
        if api_client:
            character_settings = capability_settings.get("character", {})

            # Register character commands capability (slash commands)
            capability_registry.register(
                CharacterCommandsCapability(client, api_client, settings=character_settings)
            )

            # Register character mention capability (message handling)
            capability_registry.register(
                CharacterMentionCapability(client, api_client, settings=character_settings)
            )
        else:
            logger.warning("Character capability enabled but LAMBDA_API_URL not configured")

    if "selfie_generation" in enabled:
        from bot.capabilities.selfie_generation import SelfieGenerationCapability

        # Use shared API client for selfie generation
        api_client = get_shared_api_client()
        if api_client:
            selfie_settings = capability_settings.get("selfie_generation", {})
            capability_registry.register(
                SelfieGenerationCapability(client, api_client, settings=selfie_settings)
            )
        else:
            logger.warning("Selfie generation capability enabled but LAMBDA_API_URL not configured")

    logger.info(f"Loaded {len(capability_registry.capabilities)} capabilities")

    # Validate dependencies
    dependency_errors = capability_registry.validate_dependencies()
    if dependency_errors:
        for error in dependency_errors:
            logger.warning(f"Capability dependency warning: {error}")


@client.event
async def on_ready():
    """Called when bot is ready."""
    logger.info(f"Bot logged in as {client.user}")

    # Explicitly set presence after connection to ensure Discord gateway receives it
    await client.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.listening, name="for @mentions"),
    )
    logger.info("Presence set: Online, listening for @mentions")

    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error(f"Configuration errors: {', '.join(errors)}")
        await client.close()
        sys.exit(1)

    # Initialize database
    try:
        await database.initialize()
        logger.info("Database initialized")
    except Exception:
        logger.exception("Failed to initialize database")
        await client.close()
        sys.exit(1)

    # Fetch capabilities and settings from API (falls back to env var if API unavailable)
    api_capabilities, capability_settings = await fetch_bot_config_from_api()
    load_capabilities(api_capabilities, capability_settings)

    # Initialize capabilities (let them register commands including /claim_face)
    await capability_registry.on_ready(tree)

    # Sync command tree
    try:
        synced = await tree.sync()
        logger.info(f"Commands registered and synced: {len(synced)} commands")
    except Exception:
        logger.exception("Failed to sync commands")

    # Set Discord client for MCP server
    if config.MCP_ENABLED:
        try:
            set_discord_client(client)
            logger.info("Discord client set for MCP server")
        except Exception as e:
            logger.warning(f"Failed to set Discord client for MCP: {e}")

    # Initialize agent manager and register agents
    try:
        from bot.agents import get_agent_manager
        from bot.agents.bluesky_agent import BlueskyAgent
        from bot.agents.character_engagement_agent import CharacterEngagementAgent
        from bot.agents.supabase_event_agent import SupabaseEventAgent
        from bot.agents.tumblr_agent import TumblrAgent

        agent_manager = get_agent_manager()
        agent_manager.set_discord_client(client)

        # Get Discord communication layer
        discord_comm = agent_manager.get_discord_comm()

        # Register Bluesky agent (if configured)
        if config.BLUESKY_HANDLE and config.BLUESKY_PASSWORD:
            bluesky_agent = BlueskyAgent(
                discord_channel_id=config.DISCORD_UPLOAD_CHANNEL_ID,
            )
            bluesky_agent.set_discord_comm(discord_comm)
            agent_manager.register_agent(bluesky_agent)
            await agent_manager.start_agent("bluesky")
            logger.info("Bluesky agent registered and started")

        # Register Tumblr agent (if configured)
        if all(
            [
                config.TUMBLR_CONSUMER_KEY,
                config.TUMBLR_CONSUMER_SECRET,
                config.TUMBLR_OAUTH_TOKEN,
                config.TUMBLR_OAUTH_SECRET,
            ]
        ):
            tumblr_agent = TumblrAgent(
                discord_channel_id=config.DISCORD_UPLOAD_CHANNEL_ID,
            )
            tumblr_agent.set_discord_comm(discord_comm)
            agent_manager.register_agent(tumblr_agent)
            await agent_manager.start_agent("tumblr")
            logger.info("Tumblr agent registered and started")

        # Register Supabase event agent (if configured)
        if config.SUPABASE_DB_URL:
            event_agent = SupabaseEventAgent(
                discord_channel_id=config.DISCORD_UPLOAD_CHANNEL_ID,
            )
            event_agent.set_discord_comm(discord_comm)
            agent_manager.register_agent(event_agent)
            await agent_manager.start_agent("supabase-event")
            logger.info("Supabase event agent registered and started")

        # Register Character engagement agent (if character capability is enabled)
        enabled_caps = config.get_enabled_capabilities()
        api_client = get_shared_api_client()
        if "character" in enabled_caps and api_client:
            engagement_agent = CharacterEngagementAgent(
                api_client=api_client,
                discord_channel_id=config.DISCORD_UPLOAD_CHANNEL_ID,
            )
            engagement_agent.set_discord_client(client)
            agent_manager.register_agent(engagement_agent)
            await agent_manager.start_agent("character-engagement")
            logger.info("Character engagement agent registered and started")

        logger.info("Agent manager initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize agent manager: {e}")

    # Start notification task (legacy - will be migrated to capability later)
    enabled_caps = config.get_enabled_capabilities()
    if "notification" in enabled_caps or "upload" in enabled_caps:
        global notification_task
        notification_task = NotificationTask(client, immich_client, database)
        await notification_task.start()
        logger.info("Notification task started")

    logger.info("Bot is ready!")


@client.event
async def on_message(message: discord.Message):
    """Handle incoming messages."""
    # Ignore bot messages
    if message.author.bot:
        return

    # Route message through capability system
    # Capabilities are processed in priority order; first to return True stops chain
    handled = await capability_registry.handle_message(message)

    # If no capability handled the message, fall back to legacy behavior
    # (This will be removed once all features are migrated to capabilities)
    if not handled:
        # Legacy upload handling is now in UploadCapability
        pass


@client.event
async def on_error(event, *args, **kwargs):
    """Handle errors."""
    logger.exception(f"Error in event {event}")


async def run_discord_bot():
    """Run the Discord bot."""
    try:
        await client.start(config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception:
        logger.exception("Fatal error in Discord bot")
    finally:
        # Cleanup capabilities
        await capability_registry.cleanup()
        # Cleanup notification task
        if notification_task:
            await notification_task.stop()
        # Cleanup shared API client
        await cleanup_shared_api_client()
        await client.close()


async def run_mcp_server():
    """Run the MCP HTTP server."""
    if not config.MCP_ENABLED:
        return

    try:
        # Create ASGI app from MCP server
        mcp_app = mcp.http_app(path="/")

        # Run uvicorn server
        config_uvicorn = uvicorn.Config(
            app=mcp_app,
            host=config.MCP_HOST,
            port=config.MCP_PORT,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config_uvicorn)
        await server.serve()
    except Exception:
        logger.exception("Fatal error in MCP server")


async def main():
    """Main entry point - runs both Discord bot and MCP server concurrently."""
    # Validate configuration before starting
    errors = config.validate()
    if errors:
        logger.error(f"Configuration errors: {', '.join(errors)}")
        sys.exit(1)

    # Create tasks for both services
    tasks = [asyncio.create_task(run_discord_bot())]

    if config.MCP_ENABLED:
        tasks.append(asyncio.create_task(run_mcp_server()))
        logger.info(f"MCP server will start on {config.MCP_HOST}:{config.MCP_PORT}")

    try:
        # Run both tasks concurrently
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception:
        logger.exception("Fatal error")
    finally:
        # Cleanup capabilities
        await capability_registry.cleanup()
        # Cleanup notification task
        if notification_task:
            await notification_task.stop()
        # Cleanup shared API client
        await cleanup_shared_api_client()
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
