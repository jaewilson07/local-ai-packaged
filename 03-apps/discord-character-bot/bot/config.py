"""Configuration management for Discord character bot."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration from environment variables."""

    # Discord configuration
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")

    # Lambda API configuration
    LAMBDA_API_URL: str = os.getenv("LAMBDA_API_URL", "http://lambda:8000")
    LAMBDA_API_KEY: str | None = os.getenv("LAMBDA_API_KEY")

    # Character settings
    MAX_CHARACTERS_PER_CHANNEL: int = int(os.getenv("MAX_CHARACTERS_PER_CHANNEL", "5"))
    ENGAGEMENT_PROBABILITY: float = float(os.getenv("ENGAGEMENT_PROBABILITY", "0.15"))
    CONTEXT_MESSAGE_LIMIT: int = int(os.getenv("CONTEXT_MESSAGE_LIMIT", "20"))

    # Engagement task settings
    ENGAGEMENT_CHECK_INTERVAL: int = int(os.getenv("ENGAGEMENT_CHECK_INTERVAL", "60"))  # seconds

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration values."""
        errors = []
        if not cls.DISCORD_BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN is required")
        if not cls.LAMBDA_API_URL:
            errors.append("LAMBDA_API_URL is required")
        return errors


config = Config()
