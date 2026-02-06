"""MinIO configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MinIOConfig(BaseSettings):
    """Configuration for MinIO storage.

    Environment variables:
        MINIO_ENDPOINT: MinIO server URL (e.g., http://minio:9000)
        MINIO_ACCESS_KEY: Access key ID (falls back to MINIO_ROOT_USER)
        MINIO_SECRET_KEY: Secret access key (falls back to MINIO_ROOT_PASSWORD)
        MINIO_BUCKET_NAME: Bucket for user data (default: user-data)
        MINIO_USE_SSL: Use SSL for connections (default: false)
    """

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
        validation_alias="MINIO_ACCESS_KEY",
        description="MinIO access key ID",
    )
    secret_key: str = Field(
        ...,
        validation_alias="MINIO_SECRET_KEY",
        description="MinIO secret access key",
    )
    bucket_name: str = Field(
        default="user-data",
        validation_alias="MINIO_BUCKET_NAME",
        description="Default bucket name for user data",
    )
    use_ssl: bool = Field(
        default=False,
        validation_alias="MINIO_USE_SSL",
        description="Use SSL for MinIO connections",
    )
