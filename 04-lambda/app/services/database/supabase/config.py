"""Supabase configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SupabaseConfig(BaseSettings):
    """Configuration for Supabase database connection."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_url: str = Field(
        ...,
        alias="SUPABASE_DB_URL",
        description="PostgreSQL connection URL for Supabase",
    )
    min_pool_size: int = Field(default=1, description="Minimum connection pool size")
    max_pool_size: int = Field(default=5, description="Maximum connection pool size")
    command_timeout: int = Field(default=10, description="Command timeout in seconds")
