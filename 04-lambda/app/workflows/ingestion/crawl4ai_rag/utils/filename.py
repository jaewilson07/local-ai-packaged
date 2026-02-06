"""Filename sanitization utilities."""

import re
from pathlib import Path
from urllib.parse import urlparse


def sanitize_filename(
    filename: str,
    max_length: int = 200,
    replacement: str = "-",
    lowercase: bool = True,
) -> str:
    """
    Sanitize a string to be safe for use as a filename.

    Removes or replaces characters that are invalid in filenames across
    different operating systems (Windows, macOS, Linux).

    Args:
        filename: Original filename or string to sanitize
        max_length: Maximum length for the filename (default: 200)
        replacement: Character to use when replacing invalid chars (default: "-")
        lowercase: Whether to convert to lowercase (default: True)

    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "untitled"

    # Characters not allowed in filenames on various OS
    # Windows: < > : " / \ | ? *
    # macOS/Linux: / and null byte
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'

    # Replace invalid characters
    sanitized = re.sub(invalid_chars, replacement, filename)

    # Replace whitespace with the replacement character
    sanitized = re.sub(r"\s+", replacement, sanitized)

    # Collapse multiple replacement characters
    if replacement:
        sanitized = re.sub(f"{re.escape(replacement)}+", replacement, sanitized)

    # Remove leading/trailing dots, spaces, and replacement chars
    sanitized = sanitized.strip(f". {replacement}")

    # Convert to lowercase if requested
    if lowercase:
        sanitized = sanitized.lower()

    # Truncate if too long, preserving extension if present
    if len(sanitized) > max_length:
        if "." in sanitized:
            name, ext = sanitized.rsplit(".", 1)
            max_name_length = max_length - len(ext) - 1
            if max_name_length > 0:
                sanitized = f"{name[:max_name_length]}.{ext}"
            else:
                sanitized = sanitized[:max_length]
        else:
            sanitized = sanitized[:max_length]

    # Ensure we have something
    if not sanitized:
        return "untitled"

    return sanitized


def generate_filename_from_url(
    url: str,
    extension: str = ".md",
    include_domain: bool = True,
    max_length: int = 200,
) -> str:
    """
    Generate a safe filename from a URL.

    Args:
        url: URL to generate filename from
        extension: File extension to use (default: ".md")
        include_domain: Whether to include domain in filename (default: True)
        max_length: Maximum length for the filename (default: 200)

    Returns:
        Sanitized filename derived from the URL
    """
    parsed = urlparse(url)

    # Get domain (replace port colon with dash)
    domain = parsed.netloc.replace(":", "-")

    # Get path, defaulting to "index" if empty
    path = parsed.path.strip("/") or "index"

    # Replace path separators with dashes
    path_clean = path.replace("/", "-")

    # Build filename
    if include_domain:
        if path_clean == "index":
            filename = domain
        else:
            filename = f"{domain}-{path_clean}"
    else:
        filename = path_clean if path_clean != "index" else domain

    # Sanitize
    filename = sanitize_filename(filename, max_length=max_length - len(extension))

    # Add extension
    if extension and not filename.endswith(extension):
        filename += extension

    return filename


def generate_unique_filepath(
    base_path: Path,
    filename: str,
    max_attempts: int = 1000,
) -> Path:
    """
    Generate a unique filepath, adding a counter suffix if file exists.

    Args:
        base_path: Directory to create file in
        filename: Desired filename
        max_attempts: Maximum number of attempts to find unique name

    Returns:
        Path object for unique filepath

    Raises:
        ValueError: If unable to find unique filename within max_attempts
    """
    filepath = base_path / filename

    if not filepath.exists():
        return filepath

    # Split filename and extension
    if "." in filename:
        stem, suffix = filename.rsplit(".", 1)
        suffix = f".{suffix}"
    else:
        stem = filename
        suffix = ""

    # Try adding counter
    for i in range(1, max_attempts + 1):
        new_filename = f"{stem}-{i}{suffix}"
        filepath = base_path / new_filename
        if not filepath.exists():
            return filepath

    raise ValueError(f"Could not find unique filename after {max_attempts} attempts")
