"""Main entry point for Discord bot."""

import asyncio
import logging
import sys

import discord
from discord import app_commands

from bot.config import config
from bot.database import Database
from bot.handlers.command_handler import setup_claim_face_command
from bot.handlers.notification_task import NotificationTask
from bot.handlers.upload_handler import handle_upload
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

# Create Discord client with intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.members = True  # Required for user lookups

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    """Called when bot is ready."""
    logger.info(f"Bot logged in as {client.user}")

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
    except Exception as e:
        logger.exception(f"Failed to initialize database: {e}")
        await client.close()
        sys.exit(1)

    # Setup commands
    try:
        await setup_claim_face_command(tree, immich_client, database)
        synced = await tree.sync()
        logger.info(f"Commands registered and synced: {len(synced)} commands")
    except Exception as e:
        logger.exception(f"Failed to setup commands: {e}")

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
        from bot.agents.supabase_event_agent import SupabaseEventAgent
        from bot.agents.tumblr_agent import TumblrAgent

        agent_manager = get_agent_manager()
        agent_manager.set_discord_client(client)

        # Get Discord communication layer
        discord_comm = agent_manager.get_discord_comm()

        # Register Bluesky agent (if configured)
        if config.BLUESKY_HANDLE and config.BLUESKY_PASSWORD:
            bluesky_agent = BlueskyAgent(
                discord_channel_id=config.DISCORD_UPLOAD_CHANNEL_ID,  # Use upload channel or configure separately
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

        logger.info("Agent manager initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize agent manager: {e}")

    # Start notification task
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

    # Handle file uploads
    await handle_upload(message, immich_client)


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
    except Exception as e:
        logger.exception(f"Fatal error in Discord bot: {e}")
    finally:
        # Cleanup
        if notification_task:
            await notification_task.stop()
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
    except Exception as e:
        logger.exception(f"Fatal error in MCP server: {e}")


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
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        # Cleanup
        if notification_task:
            await notification_task.stop()
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
