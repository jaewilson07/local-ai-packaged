"""Main entry point for Discord character bot."""

import asyncio
import logging
import sys

import discord
from discord import app_commands

from bot.api_client import APIClient
from bot.config import Config
from bot.handlers.command_handler import (
    handle_add_character,
    handle_clear_history,
    handle_list_characters,
    handle_query_knowledge_store,
    handle_remove_character,
)
from bot.handlers.engagement_task import EngagementTask
from bot.handlers.message_handler import handle_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize components
api_client: APIClient | None = None
engagement_task: EngagementTask | None = None

# Create Discord client with intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.members = True  # Required for user lookups

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    """Called when bot is ready."""
    logger.info(f"Discord Character Bot logged in as {client.user}")

    # Validate configuration
    errors = Config.validate()
    if errors:
        logger.error(f"Configuration errors: {', '.join(errors)}")
        await client.close()
        sys.exit(1)

    # Initialize API client
    global api_client
    api_client = APIClient(base_url=Config.LAMBDA_API_URL, api_key=Config.LAMBDA_API_KEY)
    logger.info(f"API client initialized: {Config.LAMBDA_API_URL}")

    # Register slash commands
    @tree.command(name="add_character", description="Add an AI character to this channel")
    @app_commands.describe(name="Character name (persona ID)")
    async def add_character_command(interaction: discord.Interaction, name: str):
        await handle_add_character(interaction, name, api_client)

    @tree.command(name="remove_character", description="Remove an AI character from this channel")
    @app_commands.describe(name="Character name (persona ID)")
    async def remove_character_command(interaction: discord.Interaction, name: str):
        await handle_remove_character(interaction, name, api_client)

    @tree.command(name="list_characters", description="List all active characters in this channel")
    async def list_characters_command(interaction: discord.Interaction):
        await handle_list_characters(interaction, api_client)

    @tree.command(name="clear_history", description="Clear conversation history for this channel")
    @app_commands.describe(character="Optional: Character name to clear specific character history")
    async def clear_history_command(interaction: discord.Interaction, character: str = None):
        await handle_clear_history(interaction, character, api_client)

    @tree.command(name="query_knowledgestore", description="Query the knowledge base using RAG")
    @app_commands.describe(query="Your question about the knowledge base")
    async def query_knowledge_store_command(interaction: discord.Interaction, query: str):
        await handle_query_knowledge_store(interaction, query, api_client)

    # Sync commands
    try:
        synced = await tree.sync()
        logger.info(f"Commands registered and synced: {len(synced)} commands")
    except Exception as e:
        logger.exception(f"Failed to sync commands: {e}")

    # Start engagement task
    global engagement_task
    engagement_task = EngagementTask(client, api_client)
    engagement_task.start()
    logger.info("Engagement task started")


@client.event
async def on_message(message: discord.Message):
    """Handle incoming messages."""
    # Ignore bot messages
    if message.author.bot:
        return

    # Ignore if no API client
    if api_client is None:
        return

    # Handle message (check for character mentions, etc.)
    await handle_message(message, api_client, client)


@client.event
async def on_error(event, *args, **kwargs):
    """Handle errors."""
    logger.error(f"Error in event {event}: {args}, {kwargs}", exc_info=True)


async def main():
    """Main entry point."""
    try:
        await client.start(Config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
        if engagement_task:
            engagement_task.stop()
        if api_client:
            await api_client.close()
        await client.close()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
