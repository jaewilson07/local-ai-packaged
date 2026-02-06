"""Crawl4AI crawler service.

This module provides web crawling functionality using Crawl4AI.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result of a web page crawl."""

    url: str
    success: bool
    html: str = ""
    markdown: str = ""
    text: str = ""
    title: str = ""
    error: str | None = None
    metadata: dict[str, Any] | None = None


async def crawl_single_page(
    url: str,
    crawler: Any | None = None,
    http_client: Any | None = None,
    extract_markdown: bool = True,
) -> CrawlResult:
    """
    Crawl a single web page.

    Args:
        url: URL to crawl
        crawler: Optional Crawl4AI AsyncWebCrawler instance
        http_client: Optional httpx client for fallback
        extract_markdown: Whether to extract markdown content

    Returns:
        CrawlResult with crawled content
    """
    # Try Crawl4AI crawler first
    if crawler:
        try:
            result = await crawler.arun(url=url)

            if not result.success:
                return CrawlResult(
                    url=url,
                    success=False,
                    error=result.error or "Crawl failed",
                )

            return CrawlResult(
                url=url,
                success=True,
                html=result.html or "",
                markdown=result.markdown or "",
                text=result.extracted_content or "",
                title=result.metadata.get("title", "") if result.metadata else "",
                metadata=result.metadata,
            )
        except Exception as e:
            logger.warning(f"Crawl4AI failed, trying fallback: {e}")

    # Fallback to httpx
    if http_client:
        try:
            response = await http_client.get(url, follow_redirects=True)
            response.raise_for_status()

            html = response.text
            title = ""

            # Try to extract title
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html, "html.parser")
                title_tag = soup.find("title")
                if title_tag:
                    title = title_tag.get_text(strip=True)
            except ImportError:
                pass

            return CrawlResult(
                url=url,
                success=True,
                html=html,
                title=title,
            )
        except Exception as e:
            return CrawlResult(
                url=url,
                success=False,
                error=str(e),
            )

    return CrawlResult(
        url=url,
        success=False,
        error="No crawler or HTTP client available",
    )


class Crawler:
    """Web crawler service using Crawl4AI or httpx fallback."""

    def __init__(self, crawler: Any | None = None, http_client: Any | None = None):
        """
        Initialize the crawler.

        Args:
            crawler: Crawl4AI AsyncWebCrawler instance
            http_client: httpx AsyncClient for fallback
        """
        self.crawler = crawler
        self.http_client = http_client

    async def crawl(self, url: str, extract_markdown: bool = True) -> CrawlResult:
        """
        Crawl a single URL.

        Args:
            url: URL to crawl
            extract_markdown: Whether to extract markdown

        Returns:
            CrawlResult with crawled content
        """
        return await crawl_single_page(
            url=url,
            crawler=self.crawler,
            http_client=self.http_client,
            extract_markdown=extract_markdown,
        )

    async def crawl_multiple(
        self, urls: list[str], extract_markdown: bool = True
    ) -> list[CrawlResult]:
        """
        Crawl multiple URLs.

        Args:
            urls: List of URLs to crawl
            extract_markdown: Whether to extract markdown

        Returns:
            List of CrawlResults
        """
        results = []
        for url in urls:
            result = await self.crawl(url, extract_markdown)
            results.append(result)
        return results


__all__ = ["CrawlResult", "Crawler", "crawl_single_page"]
