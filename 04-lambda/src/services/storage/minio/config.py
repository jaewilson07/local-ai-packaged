"""MinIO configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MinIOConfig(BaseSettings):
    """Configuration for MinIO storage."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    endpoint: str = Field(
        ...,
        alias="MINIO_ENDPOINT",
        description="MinIO endpoint URL",
    )
    access_key: str = Field(
        ...,
        alias="MINIO_ROOT_USER",
        description="MinIO access key ID",
    )
    secret_key: str = Field(
        ...,
        alias="MINIO_ROOT_PASSWORD",
        description="MinIO secret access key",
    )
    bucket_name: str = Field(
        default="user-data",
        description="Default bucket name for user data",
    )
    use_ssl: bool = Field(
        default=False,
        description="Use SSL for MinIO connections",
    )
