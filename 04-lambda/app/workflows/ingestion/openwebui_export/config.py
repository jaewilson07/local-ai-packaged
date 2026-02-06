"""OpenWebUI export configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings


class OpenWebUIExportConfig(BaseSettings):
    """Configuration for OpenWebUI export service."""

    # Open WebUI API
    openwebui_url: str = Field("http://open-webui:8080", env="OPENWEBUI_URL")
    openwebui_api_key: str | None = Field(None, env="OPENWEBUI_API_KEY")

    # MongoDB settings (for export destination)
    mongodb_uri: str = Field("mongodb://mongodb:27017", env="MONGODB_URI")
    mongodb_database: str = Field("local_ai", env="MONGODB_DATABASE")
    mongodb_collection_exports: str = Field("openwebui_exports", env="MONGODB_COLLECTION_EXPORTS")

    class Config:
        env_prefix = ""
        extra = "ignore"


config = OpenWebUIExportConfig()

__all__ = ["OpenWebUIExportConfig", "config"]
