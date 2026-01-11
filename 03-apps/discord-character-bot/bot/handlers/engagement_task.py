"""Background task for character engagement."""

import asyncio
import logging
import discord
from typing import List, Optional
from bot.api_client import APIClient
from bot.config import Config

logger = logging.getLogger(__name__)


class EngagementTask:
    """Background task that monitors channels for engagement opportunities."""
    
    def __init__(self, client: discord.Client, api_client: APIClient):
        """
        Initialize engagement task.
        
        Args:
            client: Discord client
            api_client: API client for Lambda services
        """
        self.client = client
        self.api_client = api_client
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    def start(self):
        """Start the engagement task."""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("Engagement task started")
    
    def stop(self):
        """Stop the engagement task."""
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("Engagement task stopped")
    
    async def _run(self):
        """Main engagement loop."""
        while self.running:
            try:
                await self._check_channels()
                await asyncio.sleep(Config.ENGAGEMENT_CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in engagement task: {e}")
                await asyncio.sleep(Config.ENGAGEMENT_CHECK_INTERVAL)
    
    async def _check_channels(self):
        """Check all channels with active characters for engagement opportunities."""
        try:
            # Get all channels with characters
            # This would require an API endpoint to list all channels
            # For now, we'll iterate through bot's known channels
            
            for guild in self.client.guilds:
                for channel in guild.text_channels:
                    if not isinstance(channel, discord.TextChannel):
                        continue
                    
                    try:
                        # Get active characters in channel
                        characters = await self.api_client.list_characters(str(channel.id))
                        
                        if not characters:
                            continue
                        
                        # Get recent messages
                        recent_messages = []
                        async for message in channel.history(limit=20):
                            if not message.author.bot and message.content:
                                recent_messages.append(message.content)
                        
                        if len(recent_messages) < 3:
                            continue  # Need at least 3 messages for context
                        
                        # Check each character for engagement
                        for char in characters:
                            try:
                                result = await self.api_client.check_engagement(
                                    channel_id=str(channel.id),
                                    character_id=char.get("character_id"),
                                    recent_messages=recent_messages[-10:]  # Last 10 messages
                                )
                                
                                if result.get("should_engage") and result.get("response"):
                                    # Send engagement response
                                    embed = discord.Embed(
                                        description=result["response"],
                                        color=discord.Color.green()
                                    )
                                    character_name = char.get("name") or char.get("character_id", "Character")
                                    embed.set_author(
                                        name=character_name,
                                        icon_url=char.get("profile_image")
                                    )
                                    
                                    await channel.send(embed=embed)
                                    logger.info(
                                        f"Character {char.get('character_id')} engaged in channel {channel.id}"
                                    )
                            
                            except Exception as e:
                                logger.warning(f"Error checking engagement for character: {e}")
                                continue
                    
                    except discord.Forbidden:
                        # Bot doesn't have permission to read this channel
                        continue
                    except Exception as e:
                        logger.warning(f"Error checking channel {channel.id}: {e}")
                        continue
        
        except Exception as e:
            logger.exception(f"Error in _check_channels: {e}")
