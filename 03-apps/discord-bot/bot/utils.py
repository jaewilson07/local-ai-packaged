"""Utility functions."""

import re
from typing import Optional


def is_valid_media_file(filename: str) -> bool:
    """Check if filename is a valid media file extension."""
    valid_extensions = {".mp4", ".mov", ".jpg", ".jpeg", ".png"}
    return any(filename.lower().endswith(ext) for ext in valid_extensions)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_immich_gallery_url(asset_id: str, base_url: str) -> str:
    """Generate Immich gallery URL for an asset."""
    # Remove protocol and port for cleaner URL
    clean_url = base_url.replace("http://", "").replace("https://", "").replace(":2283", "")
    return f"https://{clean_url}/photos/{asset_id}" if "http" not in base_url else f"{base_url}/photos/{asset_id}"
