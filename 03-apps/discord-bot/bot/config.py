"""Configuration management for Discord bot."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration from environment variables."""

    # Discord configuration
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_UPLOAD_CHANNEL_ID: str = os.getenv("DISCORD_UPLOAD_CHANNEL_ID", "")

    # Immich configuration
    IMMICH_SERVER_URL: str = os.getenv("IMMICH_SERVER_URL", "http://immich-server:2283")
    IMMICH_API_KEY: str = os.getenv("IMMICH_API_KEY", "")

    # Database configuration
    BOT_DB_PATH: str = os.getenv("BOT_DB_PATH", "/app/data/bot.sqlite")

    # Notification polling interval (seconds)
    NOTIFICATION_POLL_INTERVAL: int = int(os.getenv("NOTIFICATION_POLL_INTERVAL", "120"))

    # MCP Server configuration
    MCP_ENABLED: bool = os.getenv("MCP_ENABLED", "true").lower() == "true"
    MCP_PORT: int = int(os.getenv("MCP_PORT", "8001"))
    MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
    
    # Bluesky configuration
    BLUESKY_HANDLE: Optional[str] = os.getenv("BLUESKY_HANDLE")
    BLUESKY_PASSWORD: Optional[str] = os.getenv("BLUESKY_PASSWORD")
    
    # Tumblr configuration
    TUMBLR_CONSUMER_KEY: Optional[str] = os.getenv("TUMBLR_CONSUMER_KEY")
    TUMBLR_CONSUMER_SECRET: Optional[str] = os.getenv("TUMBLR_CONSUMER_SECRET")
    TUMBLR_OAUTH_TOKEN: Optional[str] = os.getenv("TUMBLR_OAUTH_TOKEN")
    TUMBLR_OAUTH_SECRET: Optional[str] = os.getenv("TUMBLR_OAUTH_SECRET")
    
    # Supabase configuration (for event agent)
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
    SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")
    SUPABASE_DB_URL: Optional[str] = os.getenv(
        "SUPABASE_DB_URL",
        f"postgresql://postgres:{os.getenv('POSTGRES_PASSWORD', '')}@supabase-db:5432/postgres"
    )

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration values."""
        errors = []
        if not cls.DISCORD_BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN is required")
        if not cls.DISCORD_UPLOAD_CHANNEL_ID:
            errors.append("DISCORD_UPLOAD_CHANNEL_ID is required")
        if not cls.IMMICH_API_KEY:
            errors.append("IMMICH_API_KEY is required")
        return errors


config = Config()
