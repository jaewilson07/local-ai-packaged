"""Manual test script for Discord bot connectivity.

This script can be run independently to test Discord bot connection:
    python -m tests.manual.test_discord_connection
"""

import asyncio
import sys
import os
from pathlib import Path

# Add bot directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import discord
from bot.config import config


async def test_discord_connection():
    """Test Discord bot connection."""
    print("=" * 60)
    print("Testing Discord Bot Connection")
    print("=" * 60)
    
    # Check configuration
    if not config.DISCORD_BOT_TOKEN:
        print("❌ ERROR: DISCORD_BOT_TOKEN not set in environment")
        return False
    
    print(f"✓ Bot Token: {config.DISCORD_BOT_TOKEN[:10]}...")
    print()
    
    # Create client with intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    client = discord.Client(intents=intents)
    
    connected = False
    error_message = None
    
    @client.event
    async def on_ready():
        nonlocal connected
        connected = True
        print(f"✅ Bot connected successfully!")
        print(f"  Bot Name: {client.user.name}")
        print(f"  Bot ID: {client.user.id}")
        print()
    
    @client.event
    async def on_error(event, *args, **kwargs):
        nonlocal error_message
        import traceback
        error_message = traceback.format_exc()
    
    try:
        print("Connecting to Discord...")
        # Start connection with timeout
        task = asyncio.create_task(client.start(config.DISCORD_BOT_TOKEN))
        
        # Wait for connection or timeout
        try:
            await asyncio.wait_for(asyncio.sleep(5), timeout=10)
        except asyncio.TimeoutError:
            pass
        
        if connected:
            # Test channel access
            print("Test 1: Checking channel access...")
            if config.DISCORD_UPLOAD_CHANNEL_ID:
                try:
                    channel = client.get_channel(int(config.DISCORD_UPLOAD_CHANNEL_ID))
                    if channel:
                        print(f"✓ Upload channel found: #{channel.name}")
                    else:
                        print(f"⚠ Upload channel {config.DISCORD_UPLOAD_CHANNEL_ID} not found")
                except Exception as e:
                    print(f"⚠ Error accessing channel: {e}")
            else:
                print("⚠ DISCORD_UPLOAD_CHANNEL_ID not set")
            print()
            
            # Test guild access
            print("Test 2: Checking server access...")
            guilds = list(client.guilds)
            print(f"✓ Bot is in {len(guilds)} server(s)")
            for guild in guilds[:5]:  # Show first 5
                print(f"  - {guild.name} (ID: {guild.id})")
            if len(guilds) > 5:
                print(f"  ... and {len(guilds) - 5} more")
            print()
            
            # Test permissions
            print("Test 3: Checking bot permissions...")
            if guilds:
                guild = guilds[0]
                bot_member = guild.get_member(client.user.id)
                if bot_member:
                    perms = bot_member.guild_permissions
                    print(f"✓ Bot permissions in {guild.name}:")
                    print(f"  - Send Messages: {perms.send_messages}")
                    print(f"  - Read Messages: {perms.read_messages}")
                    print(f"  - Attach Files: {perms.attach_files}")
                    print(f"  - Use Slash Commands: {perms.use_slash_commands}")
            print()
            
            await client.close()
            print("=" * 60)
            print("✅ All Discord connection tests passed!")
            print("=" * 60)
            return True
        else:
            print("❌ Failed to connect to Discord")
            if error_message:
                print(f"Error: {error_message}")
            return False
            
    except discord.LoginFailure:
        print("❌ ERROR: Invalid bot token")
        print("Please check your DISCORD_BOT_TOKEN")
        return False
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
        print()
        print("Troubleshooting:")
        print("1. Verify DISCORD_BOT_TOKEN is correct")
        print("2. Check if bot has required intents enabled in Discord Developer Portal")
        print("3. Verify bot is invited to at least one server")
        return False
    finally:
        if not client.is_closed():
            await client.close()


async def main():
    """Main entry point."""
    print()
    success = await test_discord_connection()
    print()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
