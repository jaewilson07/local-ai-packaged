"""Crawl4AI RAG services package."""

# Import crawler functions from the centralized service
from services.compute.crawl4ai import crawl_deep, crawl_single_page

# Import downloader and pagination from local workflow services
from .downloader import (
    create_timestamped_path,
    download_page_as_markdown,
    download_pages_as_markdown,
    save_data_to_csv,
    save_data_to_json,
    save_markdown_file,
)
from .pagination import (
    PaginationHelper,
    PaginationResult,
    extract_with_pagination,
)

__all__ = [
    # Crawler
    "crawl_deep",
    "crawl_single_page",
    # Downloader
    "download_page_as_markdown",
    "download_pages_as_markdown",
    "save_markdown_file",
    "save_data_to_json",
    "save_data_to_csv",
    "create_timestamped_path",
    # Pagination
    "PaginationHelper",
    "PaginationResult",
    "extract_with_pagination",
]
