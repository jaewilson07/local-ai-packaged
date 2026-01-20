"""Crawl4AI service client for web crawling operations.

This module provides a unified interface for crawling web pages using Crawl4AI,
supporting both single-page and deep crawling with configurable parameters.
"""

import logging
from typing import Any

from .crawler import crawl_deep, crawl_single_page

logger = logging.getLogger(__name__)


class Crawl4AIClient:
    """Client for Crawl4AI web crawling service."""

    async def crawl_single_page(
        self,
        url: str,
        word_count_threshold: int = 10,
        remove_overlay_elements: bool = True,
        remove_base64_images: bool = True,
        cache_mode: str = "BYPASS",
        browser_type: str = "chromium",
        timeout: int = 30,
        cookies: str | dict[str, str] | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """
        Crawl a single web page and extract content.

        Args:
            url: The URL to crawl
            word_count_threshold: Minimum word count for a block to be included
            remove_overlay_elements: Remove overlay elements from the page
            remove_base64_images: Remove base64 encoded images
            cache_mode: Cache mode for crawling (BYPASS, CACHED, or WRITE)
            browser_type: Browser type to use (chromium or firefox)
            timeout: Request timeout in seconds
            cookies: Optional cookies as string or dict
            user_agent: Optional custom user agent

        Returns:
            Dictionary containing crawled content and metadata
        """
        result = await crawl_single_page(
            url=url,
            word_count_threshold=word_count_threshold,
            remove_overlay_elements=remove_overlay_elements,
            remove_base64_images=remove_base64_images,
            cache_mode=cache_mode,
            browser_type=browser_type,
            timeout=timeout,
            cookies=cookies,
            user_agent=user_agent,
        )
        return result

    async def crawl_deep(
        self,
        start_url: str,
        max_depth: int = 2,
        allowed_domains: list[str] | None = None,
        allowed_subdomains: list[str] | None = None,
        exclude_external_links: bool = False,
        remove_overlay_elements: bool = True,
        remove_base64_images: bool = True,
        word_count_threshold: int = 10,
        cache_mode: str = "BYPASS",
        browser_type: str = "chromium",
        timeout: int = 30,
        cookies: str | dict[str, str] | None = None,
        user_agent: str | None = None,
        visited_urls: set[str] | None = None,
        current_depth: int = 0,
    ) -> dict[str, Any]:
        """
        Perform a deep crawl of a website.

        Args:
            start_url: The starting URL for the crawl
            max_depth: Maximum depth to crawl
            allowed_domains: List of allowed domains (None = same domain as start_url)
            allowed_subdomains: List of allowed subdomains
            exclude_external_links: Exclude external links from crawl
            remove_overlay_elements: Remove overlay elements from pages
            remove_base64_images: Remove base64 encoded images
            word_count_threshold: Minimum word count for a block to be included
            cache_mode: Cache mode for crawling
            browser_type: Browser type to use
            timeout: Request timeout in seconds
            cookies: Optional cookies
            user_agent: Optional custom user agent
            visited_urls: Set of already visited URLs (internal use)
            current_depth: Current crawl depth (internal use)

        Returns:
            Dictionary containing crawled content from all pages and metadata
        """
        result = await crawl_deep(
            start_url=start_url,
            max_depth=max_depth,
            allowed_domains=allowed_domains,
            allowed_subdomains=allowed_subdomains,
            exclude_external_links=exclude_external_links,
            remove_overlay_elements=remove_overlay_elements,
            remove_base64_images=remove_base64_images,
            word_count_threshold=word_count_threshold,
            cache_mode=cache_mode,
            browser_type=browser_type,
            timeout=timeout,
            cookies=cookies,
            user_agent=user_agent,
            visited_urls=visited_urls,
            current_depth=current_depth,
        )
        return result
