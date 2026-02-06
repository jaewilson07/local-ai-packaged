"""Pagination utilities for Crawl4AI.

This module provides helpers for handling JavaScript-rendered paginated content
by accessing Playwright pages directly through Crawl4AI's browser manager.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

logger = logging.getLogger(__name__)


@dataclass
class PaginationResult:
    """Result from paginated extraction."""

    pages_extracted: int
    total_items: int
    items: list[Any]
    errors: list[str]


class PaginationHelper:
    """
    Helper class for extracting data from JavaScript-rendered paginated content.

    This class uses direct Playwright page manipulation to click through pagination
    controls while maintaining browser state, which is necessary for SPAs that
    don't use URL-based pagination.

    Example:
        ```python
        async with AsyncWebCrawler(config=browser_config) as crawler:
            helper = PaginationHelper(
                crawler=crawler,
                next_button_selector='button:has-text("Next"):not([disabled])',
                extract_fn=my_extract_function,
            )
            result = await helper.extract_all_pages(
                url="https://example.com/table",
                max_pages=20,
            )
        ```
    """

    def __init__(
        self,
        crawler: AsyncWebCrawler,
        next_button_selector: str,
        extract_fn: Callable[[str], list[Any]],
        get_item_key: Callable[[Any], str] | None = None,
        page_load_delay: float = 1.5,
    ):
        """
        Initialize pagination helper.

        Args:
            crawler: AsyncWebCrawler instance (must be entered via __aenter__)
            next_button_selector: CSS selector for the "Next" button
            extract_fn: Function that extracts items from HTML string
            get_item_key: Optional function to get unique key from item (for deduplication)
            page_load_delay: Seconds to wait after clicking Next (default: 1.5)
        """
        self.crawler = crawler
        self.next_button_selector = next_button_selector
        self.extract_fn = extract_fn
        self.get_item_key = get_item_key
        self.page_load_delay = page_load_delay

    async def extract_all_pages(
        self,
        url: str,
        max_pages: int = 100,
        session_id: str = "pagination_session",
        wait_until: str = "networkidle",
        page_timeout: int = 60000,
    ) -> PaginationResult:
        """
        Extract data from all pages by clicking through pagination.

        Args:
            url: Starting URL
            max_pages: Maximum number of pages to extract (safety limit)
            session_id: Session ID for maintaining browser state
            wait_until: Playwright wait condition (default: "networkidle")
            page_timeout: Page load timeout in milliseconds (default: 60000)

        Returns:
            PaginationResult with all extracted items
        """
        all_items: list[Any] = []
        seen_keys: set[str] = set()
        errors: list[str] = []
        pages_extracted = 0

        # Initial page load with session
        config = CrawlerRunConfig(
            wait_until=wait_until,
            page_timeout=page_timeout,
            session_id=session_id,
        )

        logger.info(f"Loading initial page: {url}")
        result = await self.crawler.arun(url=url, config=config)

        if not result.success:
            error_msg = f"Failed to load initial page: {result.error_message}"
            logger.error(error_msg)
            return PaginationResult(
                pages_extracted=0,
                total_items=0,
                items=[],
                errors=[error_msg],
            )

        # Extract from first page
        page_items = self.extract_fn(result.html)
        new_items = self._deduplicate_items(page_items, seen_keys)
        all_items.extend(new_items)
        pages_extracted = 1
        logger.info(f"Page 1: Extracted {len(new_items)} items")

        # Get Playwright page for direct manipulation
        try:
            page = await self._get_playwright_page(config)
            if not page:
                logger.warning("Could not access Playwright page, returning first page only")
                return PaginationResult(
                    pages_extracted=pages_extracted,
                    total_items=len(all_items),
                    items=all_items,
                    errors=errors,
                )

            # Click through remaining pages
            for page_num in range(2, max_pages + 1):
                try:
                    # Find and click Next button
                    next_button = await page.query_selector(self.next_button_selector)
                    if not next_button:
                        logger.info(
                            f"No more pages - Next button not found after page {page_num - 1}"
                        )
                        break

                    await next_button.click()
                    await page.wait_for_load_state(wait_until)
                    await asyncio.sleep(self.page_load_delay)

                    # Extract from updated page
                    html = await page.content()
                    page_items = self.extract_fn(html)
                    new_items = self._deduplicate_items(page_items, seen_keys)

                    if len(new_items) == 0:
                        logger.info(f"Page {page_num}: No new items found, stopping")
                        break

                    all_items.extend(new_items)
                    pages_extracted = page_num
                    logger.info(
                        f"Page {page_num}: Extracted {len(new_items)} new items (total: {len(all_items)})"
                    )

                except Exception as e:
                    error_msg = f"Error on page {page_num}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    break

        except Exception as e:
            error_msg = f"Error accessing Playwright page: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)

        return PaginationResult(
            pages_extracted=pages_extracted,
            total_items=len(all_items),
            items=all_items,
            errors=errors,
        )

    async def _get_playwright_page(self, config: CrawlerRunConfig):
        """Get the Playwright page from the browser manager."""
        try:
            crawler_strategy = self.crawler.crawler_strategy
            browser_manager = crawler_strategy.browser_manager
            page_result = await browser_manager.get_page(config)

            if isinstance(page_result, tuple):
                return page_result[0]
            return page_result
        except Exception as e:
            logger.warning(f"Could not get Playwright page: {e}")
            return None

    def _deduplicate_items(self, items: list[Any], seen_keys: set[str]) -> list[Any]:
        """Remove duplicate items based on get_item_key function."""
        if not self.get_item_key:
            return items

        new_items = []
        for item in items:
            key = self.get_item_key(item)
            if key not in seen_keys:
                seen_keys.add(key)
                new_items.append(item)
        return new_items


async def extract_with_pagination(
    crawler: AsyncWebCrawler,
    url: str,
    next_button_selector: str,
    extract_fn: Callable[[str], list[Any]],
    get_item_key: Callable[[Any], str] | None = None,
    max_pages: int = 100,
    page_load_delay: float = 1.5,
) -> PaginationResult:
    """
    Convenience function for paginated extraction.

    This is a simpler API for one-off extractions without creating
    a PaginationHelper instance.

    Args:
        crawler: AsyncWebCrawler instance (must be entered)
        url: Starting URL
        next_button_selector: CSS selector for Next button
        extract_fn: Function to extract items from HTML
        get_item_key: Optional function to get unique key for deduplication
        max_pages: Maximum pages to extract (default: 100)
        page_load_delay: Delay after clicking Next (default: 1.5s)

    Returns:
        PaginationResult with extracted items
    """
    helper = PaginationHelper(
        crawler=crawler,
        next_button_selector=next_button_selector,
        extract_fn=extract_fn,
        get_item_key=get_item_key,
        page_load_delay=page_load_delay,
    )
    return await helper.extract_all_pages(url=url, max_pages=max_pages)
