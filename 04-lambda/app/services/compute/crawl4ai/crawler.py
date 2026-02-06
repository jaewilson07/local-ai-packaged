"""Core crawler functions for Crawl4AI web crawling operations.

This module provides the actual crawling implementation using Crawl4AI,
supporting both single-page and deep crawling with authentication support.
"""

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

logger = logging.getLogger(__name__)


def _parse_cookies(cookies: str | dict[str, str] | None, url: str) -> list[dict[str, Any]] | None:
    """
    Parse cookies from string or dict format into Playwright cookie format.

    Args:
        cookies: Cookies as string (e.g., "sessionid=abc123; csrftoken=xyz")
                 or dict (e.g., {"sessionid": "abc123", "csrftoken": "xyz"})
        url: URL to extract domain for cookie assignment

    Returns:
        List of Playwright-compatible cookie dicts, or None if no cookies
    """
    if not cookies:
        return None

    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    # Remove www. prefix for broader cookie scope
    if domain.startswith("www."):
        domain = domain[4:]

    cookie_list = []

    if isinstance(cookies, str):
        # Parse string format: "name1=value1; name2=value2"
        for cookie in cookies.split(";"):
            cookie = cookie.strip()
            if "=" in cookie:
                name, value = cookie.split("=", 1)
                cookie_list.append(
                    {
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": f".{domain}",  # Prefix with . for subdomain matching
                        "path": "/",
                    }
                )
    elif isinstance(cookies, dict):
        # Parse dict format
        for name, value in cookies.items():
            cookie_list.append(
                {
                    "name": name,
                    "value": value,
                    "domain": f".{domain}",
                    "path": "/",
                }
            )

    return cookie_list if cookie_list else None


def _build_crawler_config(
    url: str,
    cookies: str | dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    word_count_threshold: int = 10,
    remove_overlay_elements: bool = True,
    cache_mode: str = "BYPASS",
) -> CrawlerRunConfig:
    """
    Build a CrawlerRunConfig with authentication support.

    Args:
        url: URL being crawled (used for cookie domain)
        cookies: Optional cookies for authentication
        headers: Optional HTTP headers for authentication
        word_count_threshold: Minimum word count for content blocks
        remove_overlay_elements: Whether to remove overlay elements
        cache_mode: Cache mode string (BYPASS, CACHED, or WRITE)

    Returns:
        Configured CrawlerRunConfig instance
    """
    # Parse cache mode
    cache_mode_enum = CacheMode.BYPASS
    if cache_mode.upper() == "CACHED":
        cache_mode_enum = CacheMode.READ_ONLY
    elif cache_mode.upper() == "WRITE":
        cache_mode_enum = CacheMode.WRITE_ONLY

    config_kwargs = {
        "word_count_threshold": word_count_threshold,
        "remove_overlay_elements": remove_overlay_elements,
        "cache_mode": cache_mode_enum,
    }

    # Add cookies if provided
    parsed_cookies = _parse_cookies(cookies, url)
    if parsed_cookies:
        config_kwargs["cookies"] = parsed_cookies
        logger.debug(f"Added {len(parsed_cookies)} cookies for domain extraction from {url}")

    # Add headers if provided
    if headers:
        config_kwargs["headers"] = headers
        logger.debug(f"Added {len(headers)} custom headers")

    return CrawlerRunConfig(**config_kwargs)


async def crawl_single_page(
    crawler: AsyncWebCrawler,
    url: str,
    cookies: str | dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    word_count_threshold: int = 10,
    remove_overlay_elements: bool = True,
    remove_base64_images: bool = True,
    cache_mode: str = "BYPASS",
    **kwargs,  # Accept additional kwargs for forward compatibility
) -> dict[str, Any] | None:
    """
    Crawl a single web page and extract content.

    Args:
        crawler: AsyncWebCrawler instance (must be entered via __aenter__)
        url: The URL to crawl
        cookies: Optional authentication cookies as string or dict
        headers: Optional custom HTTP headers as dict
        word_count_threshold: Minimum word count for a block to be included
        remove_overlay_elements: Remove overlay elements from the page
        remove_base64_images: Remove base64 encoded images
        cache_mode: Cache mode for crawling (BYPASS, CACHED, or WRITE)

    Returns:
        Dictionary containing crawled content and metadata, or None if failed:
        - url: The crawled URL (may differ from input due to redirects)
        - markdown: Page content as markdown
        - html: Raw HTML content
        - metadata: Extracted metadata (title, description, etc.)
        - links: Internal and external links found
    """
    try:
        config = _build_crawler_config(
            url=url,
            cookies=cookies,
            headers=headers,
            word_count_threshold=word_count_threshold,
            remove_overlay_elements=remove_overlay_elements,
            cache_mode=cache_mode,
        )

        logger.info(f"Crawling single page: {url}")
        result = await crawler.arun(url=url, config=config)

        if not result.success:
            logger.warning(f"Failed to crawl {url}: {result.error_message}")
            return None

        # Extract metadata from the result
        metadata = {
            "page_title": getattr(result, "title", None),
            "status_code": getattr(result, "status_code", None),
            "crawl_timestamp": getattr(result, "crawl_timestamp", None),
        }

        # Add any additional metadata from result.metadata if available
        if hasattr(result, "metadata") and result.metadata:
            metadata.update(result.metadata)

        # Extract links if available
        links = []
        if hasattr(result, "links") and result.links:
            # Handle both internal and external links
            if isinstance(result.links, dict):
                links = list(result.links.get("internal", [])) + list(
                    result.links.get("external", [])
                )
            elif isinstance(result.links, list):
                links = result.links

        return {
            "url": result.url or url,
            "markdown": result.markdown or "",
            "html": result.html or "",
            "metadata": metadata,
            "links": links,
        }

    except Exception as e:
        logger.exception(f"Error crawling {url}: {e}")
        return None


async def crawl_deep(
    crawler: AsyncWebCrawler,
    start_url: str,
    max_depth: int = 2,
    allowed_domains: list[str] | None = None,
    allowed_subdomains: list[str] | None = None,
    max_concurrent: int = 10,
    cookies: str | dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    word_count_threshold: int = 10,
    remove_overlay_elements: bool = True,
    remove_base64_images: bool = True,
    cache_mode: str = "BYPASS",
    **kwargs,  # Accept additional kwargs for forward compatibility
) -> list[dict[str, Any]]:
    """
    Perform a deep crawl of a website, recursively following links.

    Args:
        crawler: AsyncWebCrawler instance (must be entered via __aenter__)
        start_url: The starting URL for the crawl
        max_depth: Maximum recursion depth (1 = start page only, 2 = start + 1 level, etc.)
        allowed_domains: List of allowed domains for exact matching
        allowed_subdomains: List of allowed subdomain prefixes
        max_concurrent: Maximum concurrent crawler sessions
        cookies: Optional authentication cookies as string or dict
        headers: Optional custom HTTP headers as dict
        word_count_threshold: Minimum word count for a block to be included
        remove_overlay_elements: Remove overlay elements from the page
        remove_base64_images: Remove base64 encoded images
        cache_mode: Cache mode for crawling

    Returns:
        List of dictionaries, each containing crawled page data:
        - url: The crawled URL
        - markdown: Page content as markdown
        - html: Raw HTML content
        - metadata: Extracted metadata
        - links: Links found on the page
    """
    max_depth = max(max_depth, 1)
    max_depth = min(max_depth, 10)

    # Parse starting URL for domain filtering
    parsed_start = urlparse(start_url)
    start_domain = parsed_start.netloc

    # Default allowed domains to starting domain if not provided
    if not allowed_domains:
        # Remove www. prefix for matching
        clean_domain = start_domain
        if clean_domain.startswith("www."):
            clean_domain = clean_domain[4:]
        allowed_domains = [clean_domain, f"www.{clean_domain}"]

    def _is_allowed_url(url: str) -> bool:
        """Check if a URL is allowed based on domain/subdomain filters."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc

            # Check allowed domains (exact match)
            domain_match = False
            for allowed in allowed_domains:
                if domain == allowed or domain.endswith(f".{allowed}"):
                    domain_match = True
                    break

            if not domain_match:
                return False

            # Check allowed subdomains (prefix match)
            if allowed_subdomains:
                for subdomain in allowed_subdomains:
                    if domain.startswith(f"{subdomain}."):
                        return True
                return False

            return True

        except Exception:
            return False

    # Track visited URLs and results
    visited_urls: set[str] = set()
    results: list[dict[str, Any]] = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _crawl_page(url: str, depth: int, parent_url: str | None = None) -> None:
        """Crawl a single page and queue its links for further crawling."""
        # Normalize URL (remove fragment, trailing slash)
        normalized_url = url.split("#")[0].rstrip("/")

        async with semaphore:
            # Skip if already visited
            if normalized_url in visited_urls:
                return
            visited_urls.add(normalized_url)

            # Skip if not allowed
            if not _is_allowed_url(normalized_url):
                logger.debug(f"Skipping disallowed URL: {normalized_url}")
                return

            # Crawl the page
            result = await crawl_single_page(
                crawler=crawler,
                url=normalized_url,
                cookies=cookies,
                headers=headers,
                word_count_threshold=word_count_threshold,
                remove_overlay_elements=remove_overlay_elements,
                remove_base64_images=remove_base64_images,
                cache_mode=cache_mode,
            )

            if not result:
                logger.warning(f"Failed to crawl {normalized_url} at depth {depth}")
                return

            # Add crawl metadata
            result["metadata"]["crawl_depth"] = depth
            result["metadata"]["parent_url"] = parent_url

            results.append(result)
            logger.info(f"Crawled {normalized_url} (depth={depth}, total={len(results)})")

            # Follow links if not at max depth
            if depth < max_depth and result.get("links"):
                child_urls = [link for link in result["links"] if _is_allowed_url(link)]
                if child_urls:
                    child_tasks = [
                        _crawl_page(child_url, depth + 1, normalized_url)
                        for child_url in child_urls[:50]  # Limit links per page
                    ]
                    await asyncio.gather(*child_tasks, return_exceptions=True)

    # Start crawling from the initial URL
    logger.info(
        f"Starting deep crawl from {start_url} (max_depth={max_depth}, "
        f"allowed_domains={allowed_domains})"
    )

    await _crawl_page(start_url, depth=1)

    logger.info(f"Deep crawl complete: {len(results)} pages crawled")
    return results


__all__ = ["crawl_deep", "crawl_single_page"]
