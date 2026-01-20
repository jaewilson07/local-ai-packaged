"""Configuration management for Discord bot."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (works from any directory)
# Path: bot/config.py -> bot -> discord-bot -> 03-apps -> project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
else:
    # Fallback: try current directory (for Docker container)
    load_dotenv()


class Config:
    """Bot configuration from environment variables."""

    # Discord configuration
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_UPLOAD_CHANNEL_ID: str = os.getenv(
        "DISCORD_UPLOAD_CHANNEL_ID", ""
    )  # Optional: if empty, allows uploads from any channel

    # Lambda API configuration (for user-specific Immich API keys)
    LAMBDA_API_URL: str = os.getenv("LAMBDA_API_URL", "http://lambda-server:8000")
    CLOUDFLARE_EMAIL: str = os.getenv(
        "CLOUDFLARE_EMAIL", ""
    )  # User's email for internal network auth
    # Lambda API Token - preferred authentication method (Bearer token)
    # Generate via POST /api/v1/auth/me/token after authenticating via Cloudflare Access
    LAMBDA_API_TOKEN: str = os.getenv("LAMBDA_API_TOKEN", "")

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

    # Capability configuration
    # Comma-separated list of enabled capabilities
    # Available: echo, upload, notification, character, selfie_generation
    # Default: echo (simple @mention response for testing)
    ENABLED_CAPABILITIES: str = os.getenv("ENABLED_CAPABILITIES", "echo")

    @classmethod
    def get_enabled_capabilities(cls) -> list[str]:
        """Get list of enabled capability names."""
        if not cls.ENABLED_CAPABILITIES:
            return ["echo"]  # Default to echo if empty
        return [cap.strip().lower() for cap in cls.ENABLED_CAPABILITIES.split(",") if cap.strip()]

    # Character capability configuration (from discord-character-bot)
    LAMBDA_API_KEY: str = os.getenv("LAMBDA_API_KEY", "")
    CLOUDFLARE_ACCESS_CLIENT_ID: str = os.getenv("CLOUDFLARE_ACCESS_CLIENT_ID", "")
    CLOUDFLARE_ACCESS_CLIENT_SECRET: str = os.getenv("CLOUDFLARE_ACCESS_CLIENT_SECRET", "")
    MAX_CHARACTERS_PER_CHANNEL: int = int(os.getenv("MAX_CHARACTERS_PER_CHANNEL", "5"))
    ENGAGEMENT_PROBABILITY: float = float(os.getenv("ENGAGEMENT_PROBABILITY", "0.15"))
    ENGAGEMENT_CHECK_INTERVAL: int = int(os.getenv("ENGAGEMENT_CHECK_INTERVAL", "60"))

    # Bluesky configuration
    BLUESKY_HANDLE: str | None = os.getenv("BLUESKY_HANDLE")
    BLUESKY_PASSWORD: str | None = os.getenv("BLUESKY_PASSWORD")

    # Tumblr configuration
    TUMBLR_CONSUMER_KEY: str | None = os.getenv("TUMBLR_CONSUMER_KEY")
    TUMBLR_CONSUMER_SECRET: str | None = os.getenv("TUMBLR_CONSUMER_SECRET")
    TUMBLR_OAUTH_TOKEN: str | None = os.getenv("TUMBLR_OAUTH_TOKEN")
    TUMBLR_OAUTH_SECRET: str | None = os.getenv("TUMBLR_OAUTH_SECRET")

    # Supabase configuration (for event agent)
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
    SUPABASE_SERVICE_KEY: str | None = os.getenv("SUPABASE_SERVICE_KEY")
    SUPABASE_DB_URL: str | None = os.getenv(
        "SUPABASE_DB_URL",
        f"postgresql://postgres:{os.getenv('POSTGRES_PASSWORD', '')}@supabase-db:5432/postgres",
    )

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration values."""
        errors = []
        if not cls.DISCORD_BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN is required")
        # DISCORD_UPLOAD_CHANNEL_ID is now optional - if empty, allows uploads from any channel
        # IMMICH_API_KEY is now optional - bot will fetch user-specific keys from Lambda API
        return errors


config = Config()
