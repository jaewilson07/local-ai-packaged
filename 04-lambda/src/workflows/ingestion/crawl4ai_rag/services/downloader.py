"""Download service for Crawl4AI - downloads pages as markdown without MongoDB ingestion."""

import csv
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler
from services.compute.crawl4ai import crawl_deep, crawl_single_page

from ..utils.filename import (
    sanitize_filename,
)

logger = logging.getLogger(__name__)


# Re-export for backwards compatibility
__all__ = [
    "create_timestamped_path",
    "download_page_as_markdown",
    "download_pages_as_markdown",
    "generate_filename_from_url",
    "sanitize_filename",
    "save_data_to_csv",
    "save_data_to_json",
    "save_markdown_file",
]


def generate_filename_from_url(url: str, output_dir: Path | None = None) -> Path:
    """
    Generate a safe filename from a URL.

    Args:
        url: URL to generate filename from
        output_dir: Optional output directory (defaults to current directory)

    Returns:
        Path object for the output file
    """
    parsed = urlparse(url)
    # Build filename from domain and path
    domain = parsed.netloc.replace(":", "-")  # Replace port colon with dash
    path = parsed.path.strip("/") or "index"

    # Combine domain and path
    if path == "index":
        filename = f"{domain}.md"
    else:
        # Replace path separators with dashes
        path_clean = path.replace("/", "-")
        filename = f"{domain}-{path_clean}.md"

    # Sanitize the filename
    filename = sanitize_filename(filename)

    # Ensure .md extension
    if not filename.endswith(".md"):
        filename += ".md"

    if output_dir:
        return output_dir / filename
    return Path(filename)


def save_markdown_file(url: str, markdown: str, output_path: str | Path | None = None) -> Path:
    """
    Save markdown content to a file.

    Args:
        url: Source URL (used to generate filename if output_path not provided)
        markdown: Markdown content to save
        output_path: Optional explicit output path (file or directory)

    Returns:
        Path to the saved file
    """
    if output_path:
        output_path = Path(output_path)
        # If it's a directory, generate filename from URL
        if output_path.is_dir() or (not output_path.exists() and output_path.suffix != ".md"):
            output_path = generate_filename_from_url(url, output_path)
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Generate filename from URL in current directory
        output_path = generate_filename_from_url(url)

    # Handle duplicate filenames
    original_path = output_path
    counter = 1
    while output_path.exists():
        stem = original_path.stem
        suffix = original_path.suffix
        output_path = original_path.parent / f"{stem}-{counter}{suffix}"
        counter += 1

    # Write markdown to file
    output_path.write_text(markdown, encoding="utf-8")
    logger.info(f"Saved markdown to {output_path}")

    return output_path


async def download_page_as_markdown(
    crawler: AsyncWebCrawler,
    url: str,
    save_to_file: bool = False,
    output_path: str | Path | None = None,
    cookies: str | dict | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Download a single page as markdown.

    Returns markdown content without MongoDB ingestion.
    Optionally saves to file.

    Args:
        crawler: AsyncWebCrawler instance
        url: URL to download
        save_to_file: Whether to save markdown to a file
        output_path: Optional output path (file or directory)
        cookies: Optional cookies for authentication
        headers: Optional custom HTTP headers for authentication

    Returns:
        Dictionary with success status, url, markdown, metadata, and optionally file_path
    """
    # Use existing crawl_single_page() with auth support
    result = await crawl_single_page(crawler, url, cookies=cookies, headers=headers)

    if not result:
        return {"success": False, "error": "Failed to crawl page", "url": url}

    file_path = None
    if save_to_file:
        try:
            file_path = save_markdown_file(url, result["markdown"], output_path)
        except Exception as e:
            logger.exception("Error saving markdown file")
            return {
                "success": False,
                "error": f"Failed to save file: {e!s}",
                "url": url,
                "markdown": result["markdown"],
                "metadata": result["metadata"],
            }

    return {
        "success": True,
        "url": result["url"],
        "markdown": result["markdown"],
        "metadata": result["metadata"],
        "file_path": str(file_path) if file_path else None,
    }


async def download_pages_as_markdown(
    crawler: AsyncWebCrawler,
    start_url: str,
    max_depth: int,
    allowed_domains: list[str] | None = None,
    allowed_subdomains: list[str] | None = None,
    save_to_files: bool = False,
    output_directory: str | Path | None = None,
    cookies: str | dict | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Download multiple pages as markdown (deep crawl).

    Returns markdown content for all pages without MongoDB ingestion.
    Optionally saves to files.

    Args:
        crawler: AsyncWebCrawler instance
        start_url: Starting URL for crawl
        max_depth: Maximum crawl depth
        allowed_domains: Optional list of allowed domains
        allowed_subdomains: Optional list of allowed subdomains
        save_to_files: Whether to save markdown to files
        output_directory: Optional output directory for files
        cookies: Optional cookies for authentication
        headers: Optional custom HTTP headers for authentication

    Returns:
        Dictionary with success status, pages array, total_pages, and optionally file_paths
    """
    # Use existing crawl_deep() with auth support
    crawled_pages = await crawl_deep(
        crawler=crawler,
        start_url=start_url,
        max_depth=max_depth,
        allowed_domains=allowed_domains,
        allowed_subdomains=allowed_subdomains,
        cookies=cookies,
        headers=headers,
    )

    if not crawled_pages:
        return {
            "success": False,
            "error": f"No pages crawled from {start_url}",
            "url": start_url,
            "pages": [],
            "total_pages": 0,
        }

    pages = []
    file_paths = []

    output_dir = None
    if save_to_files and output_directory:
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)

    for page in crawled_pages:
        page_data = {
            "url": page["url"],
            "markdown": page["markdown"],
            "metadata": page.get("metadata", {}),
        }

        if save_to_files:
            try:
                file_path = save_markdown_file(
                    page["url"], page["markdown"], output_dir or output_directory
                )
                page_data["file_path"] = str(file_path)
                file_paths.append(str(file_path))
            except Exception as e:
                logger.warning(f"Failed to save file for {page['url']}: {e}")
                page_data["file_path"] = None

        pages.append(page_data)

    return {
        "success": True,
        "url": start_url,
        "pages": pages,
        "total_pages": len(pages),
        "file_paths": file_paths if save_to_files else None,
    }


def save_data_to_json(
    data: list[Any],
    output_path: Path,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> Path:
    """
    Save data to a JSON file.

    Handles dataclass instances, dicts, and other JSON-serializable objects.

    Args:
        data: List of items to save (dataclasses, dicts, etc.)
        output_path: Output file path
        indent: JSON indentation (default: 2)
        ensure_ascii: Whether to escape non-ASCII characters (default: False)

    Returns:
        Path to saved file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert dataclass instances to dicts
    serializable_data = []
    for item in data:
        if hasattr(item, "__dataclass_fields__"):
            serializable_data.append(asdict(item))
        elif isinstance(item, dict):
            serializable_data.append(item)
        else:
            serializable_data.append(item)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serializable_data, f, indent=indent, ensure_ascii=ensure_ascii, default=str)

    logger.info(f"Saved {len(data)} items to {output_path}")
    return output_path


def save_data_to_csv(
    data: list[Any],
    output_path: Path,
    fields: list[str] | None = None,
    exclude_fields: list[str] | None = None,
) -> Path:
    """
    Save data to a CSV file.

    Args:
        data: List of items to save (dataclasses, dicts, etc.)
        output_path: Output file path
        fields: Optional list of fields to include (default: all)
        exclude_fields: Optional list of fields to exclude

    Returns:
        Path to saved file
    """
    if not data:
        logger.warning("No data to save to CSV")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert first item to dict to get fields
    first_item = data[0]
    if hasattr(first_item, "__dataclass_fields__"):
        first_dict = asdict(first_item)
    elif isinstance(first_item, dict):
        first_dict = first_item
    else:
        raise ValueError("Data items must be dataclasses or dicts")

    # Determine fields to use
    if fields is None:
        fields = list(first_dict.keys())

    # Apply exclusions
    if exclude_fields:
        fields = [f for f in fields if f not in exclude_fields]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()

        for item in data:
            if hasattr(item, "__dataclass_fields__"):
                item_dict = asdict(item)
            elif isinstance(item, dict):
                item_dict = item
            else:
                continue

            # Convert complex types to JSON strings for CSV
            csv_row = {}
            for field_name in fields:
                value = item_dict.get(field_name, "")
                if isinstance(value, (list, dict)):
                    value = json.dumps(value)
                csv_row[field_name] = value

            writer.writerow(csv_row)

    logger.info(f"Saved {len(data)} items to {output_path}")
    return output_path


def create_timestamped_path(
    output_dir: Path,
    prefix: str,
    extension: str = ".json",
) -> Path:
    """
    Create a file path with timestamp in the filename.

    Args:
        output_dir: Directory for the file
        prefix: Filename prefix
        extension: File extension (default: ".json")

    Returns:
        Path like "output_dir/prefix_20240115_143022.json"
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}{extension}"
    return output_dir / filename
