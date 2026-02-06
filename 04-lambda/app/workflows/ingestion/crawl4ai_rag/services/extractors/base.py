"""Base extractor classes for Crawl4AI RAG.

This module provides abstract base classes for content extraction
from web pages.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TableRow:
    """Base class for table row data."""

    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArticleContent:
    """Extracted article content."""

    title: str = ""
    url: str = ""
    content: str = ""
    summary: str = ""
    author: str = ""
    published_date: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class TableExtractor(ABC):
    """Abstract base class for extracting table data from web pages."""

    @abstractmethod
    async def extract_rows(self, html: str, **kwargs) -> list[TableRow]:
        """
        Extract rows from an HTML table.

        Args:
            html: HTML content containing the table
            **kwargs: Additional extraction parameters

        Returns:
            List of extracted TableRow objects
        """

    @abstractmethod
    def parse_row(self, row_html: str) -> TableRow | None:
        """
        Parse a single table row.

        Args:
            row_html: HTML of a single table row

        Returns:
            TableRow object or None if parsing fails
        """


class ArticleExtractor(ABC):
    """Abstract base class for extracting article content from web pages."""

    @abstractmethod
    async def extract(self, html: str, url: str = "", **kwargs) -> ArticleContent:
        """
        Extract article content from HTML.

        Args:
            html: HTML content of the article page
            url: URL of the article (for metadata)
            **kwargs: Additional extraction parameters

        Returns:
            ArticleContent object with extracted data
        """

    def clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing extra whitespace.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""
        # Normalize whitespace
        import re

        text = re.sub(r"\s+", " ", text)
        return text.strip()


class BaseHTMLExtractor:
    """Base class with common HTML extraction utilities."""

    def __init__(self):
        self._soup = None

    def parse_html(self, html: str):
        """
        Parse HTML using BeautifulSoup.

        Args:
            html: HTML content to parse

        Returns:
            BeautifulSoup object
        """
        try:
            from bs4 import BeautifulSoup

            self._soup = BeautifulSoup(html, "html.parser")
            return self._soup
        except ImportError:
            logger.warning("BeautifulSoup not available, using basic parsing")
            return None

    def extract_text(self, element) -> str:
        """
        Extract text from a BeautifulSoup element.

        Args:
            element: BeautifulSoup element

        Returns:
            Extracted text
        """
        if element is None:
            return ""
        return element.get_text(strip=True)

    def find_meta_content(self, name: str, property_name: str | None = None) -> str:
        """
        Find content from a meta tag.

        Args:
            name: Name attribute to search for
            property_name: Property attribute to search for (for og: tags)

        Returns:
            Meta tag content or empty string
        """
        if not self._soup:
            return ""

        # Try name attribute
        meta = self._soup.find("meta", attrs={"name": name})
        if meta:
            return meta.get("content", "")

        # Try property attribute (for Open Graph tags)
        if property_name:
            meta = self._soup.find("meta", attrs={"property": property_name})
            if meta:
                return meta.get("content", "")

        return ""


__all__ = [
    "ArticleContent",
    "ArticleExtractor",
    "BaseHTMLExtractor",
    "TableExtractor",
    "TableRow",
]
