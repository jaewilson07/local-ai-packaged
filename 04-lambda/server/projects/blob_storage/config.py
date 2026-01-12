"""Configuration for Blob Storage project."""

from dataclasses import dataclass


@dataclass
class BlobStorageConfig:
    """Configuration for Blob Storage project."""

    # Uses auth config for MinIO


config = BlobStorageConfig()
