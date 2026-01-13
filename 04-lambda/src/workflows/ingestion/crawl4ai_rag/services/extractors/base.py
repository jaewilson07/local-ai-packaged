"""Base classes for site-specific content extractors."""

from __future__ import annotations

import csv
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, TypeVar

from workflows.ingestion.crawl4ai_rag.utils.filename import (
    generate_unique_filepath,
    sanitize_filename,
)
from workflows.ingestion.crawl4ai_rag.utils.html_converter import html_to_markdown

logger = logging.getLogger(__name__)


@dataclass
class TableRow:
    """
    Base class for table row data.

    Subclass this for site-specific table schemas.
    All fields should be serializable for JSON/CSV export.
    """


@dataclass
class ArticleContent:
    """
    Container for extracted article content.

    This is a generic structure for article/post content that can be
    extended for site-specific needs.
    """

    title: str = ""
    url: str = ""
    author: str = ""
    author_url: str = ""
    published_date: str = ""
    updated_date: str = ""

    # Content
    content_markdown: str = ""
    content_html: str = ""

    # Optional metadata
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    cover_image_url: str = ""

    # Engagement metrics
    likes: int = 0
    comments: int = 0
    views: int = 0

    # Extra fields for site-specific data
    extra: dict[str, Any] = field(default_factory=dict)


T = TypeVar("T", bound=TableRow)


class TableExtractor(ABC, Generic[T]):
    """
    Abstract base class for extracting tabular data from web pages.

    Implement this class for site-specific table extraction logic.
    Provides common utilities for parsing, deduplication, and export.

    Example:
        ```python
        class MyTableExtractor(TableExtractor[MyRowType]):
            def extract_rows_from_html(self, html: str) -> list[MyRowType]:
                # Parse HTML and return rows
                ...

            def get_row_key(self, row: MyRowType) -> str:
                return row.id  # Or whatever makes rows unique
        ```
    """

    @abstractmethod
    def extract_rows_from_html(self, html: str) -> list[T]:
        """
        Extract table rows from HTML content.

        Args:
            html: HTML string containing the table

        Returns:
            List of TableRow subclass instances
        """

    @abstractmethod
    def get_row_key(self, row: T) -> str:
        """
        Get a unique key for a row (used for deduplication).

        Args:
            row: Table row instance

        Returns:
            Unique string identifier for the row
        """

    def deduplicate_rows(self, new_rows: list[T], existing_rows: list[T]) -> list[T]:
        """
        Remove rows that already exist in the existing set.

        Args:
            new_rows: Newly extracted rows
            existing_rows: Previously extracted rows

        Returns:
            List of rows not in existing_rows
        """
        existing_keys = {self.get_row_key(row) for row in existing_rows}
        return [row for row in new_rows if self.get_row_key(row) not in existing_keys]

    def save_to_json(
        self,
        rows: list[T],
        output_path: Path,
        indent: int = 2,
    ) -> Path:
        """
        Save rows to a JSON file.

        Args:
            rows: List of rows to save
            output_path: Output file path
            indent: JSON indentation (default: 2)

        Returns:
            Path to saved file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(row) for row in rows]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=str)

        logger.info(f"Saved {len(rows)} rows to {output_path}")
        return output_path

    def save_to_csv(
        self,
        rows: list[T],
        output_path: Path,
        fields: list[str] | None = None,
    ) -> Path:
        """
        Save rows to a CSV file.

        Args:
            rows: List of rows to save
            output_path: Output file path
            fields: Optional list of fields to include (default: all)

        Returns:
            Path to saved file
        """
        if not rows:
            logger.warning("No rows to save to CSV")
            return output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get all fields from first row if not specified
        first_row_dict = asdict(rows[0])
        if fields is None:
            fields = list(first_row_dict.keys())

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                row_dict = asdict(row)
                # Convert non-string values to strings for CSV
                csv_row = {}
                for field_name in fields:
                    value = row_dict.get(field_name, "")
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                    csv_row[field_name] = value
                writer.writerow(csv_row)

        logger.info(f"Saved {len(rows)} rows to {output_path}")
        return output_path


class ArticleExtractor(ABC):
    """
    Abstract base class for extracting article/post content.

    Implement this class for site-specific article extraction logic.
    """

    @abstractmethod
    def extract_content_from_html(self, html: str, url: str = "") -> ArticleContent:
        """
        Extract article content from HTML.

        Args:
            html: HTML string containing the article
            url: Original URL of the article

        Returns:
            ArticleContent instance with extracted data
        """

    def html_to_markdown(self, html: str) -> str:
        """
        Convert HTML to markdown.

        Override this method to customize HTML-to-markdown conversion.

        Args:
            html: HTML string

        Returns:
            Markdown string
        """
        return html_to_markdown(html)

    def save_as_markdown(
        self,
        article: ArticleContent,
        output_dir: Path,
        include_frontmatter: bool = True,
    ) -> Path:
        """
        Save article as a markdown file with optional YAML frontmatter.

        Args:
            article: Article content to save
            output_dir: Directory to save file in
            include_frontmatter: Whether to include YAML frontmatter (default: True)

        Returns:
            Path to saved file
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename from title
        filename = sanitize_filename(article.title, max_length=100) + ".md"
        filepath = generate_unique_filepath(output_dir, filename)

        # Build content
        content_parts = []

        if include_frontmatter:
            frontmatter = self._build_frontmatter(article)
            content_parts.append(f"---\n{frontmatter}---\n")

        # Title
        content_parts.append(f"# {article.title}\n")

        # Metadata section
        if article.author:
            content_parts.append(f"**Author:** {article.author}\n")
        if article.published_date:
            content_parts.append(f"**Published:** {article.published_date}\n")
        if article.tags:
            content_parts.append(f"**Tags:** {', '.join(article.tags)}\n")
        if article.categories:
            content_parts.append(f"**Categories:** {', '.join(article.categories)}\n")

        # Cover image
        if article.cover_image_url:
            content_parts.append(f"\n![Cover Image]({article.cover_image_url})\n")

        # Main content
        content_parts.append("\n---\n\n")
        content_parts.append(article.content_markdown)
        content_parts.append("\n")

        # Write file
        filepath.write_text("".join(content_parts), encoding="utf-8")
        logger.debug(f"Saved article: {filepath}")

        return filepath

    def _build_frontmatter(self, article: ArticleContent) -> str:
        """Build YAML frontmatter for article."""
        lines = []

        # Escape quotes in title
        safe_title = article.title.replace('"', '\\"')
        lines.append(f'title: "{safe_title}"')

        if article.url:
            lines.append(f"url: {article.url}")
        if article.author:
            lines.append(f"author: {article.author}")
        if article.published_date:
            lines.append(f"published_date: {article.published_date}")
        if article.updated_date:
            lines.append(f"updated_date: {article.updated_date}")
        if article.tags:
            lines.append(f"tags: {article.tags}")
        if article.categories:
            lines.append(f"categories: {article.categories}")
        if article.likes:
            lines.append(f"likes: {article.likes}")
        if article.comments:
            lines.append(f"comments: {article.comments}")

        return "\n".join(lines) + "\n"

    def save_batch_as_markdown(
        self,
        articles: list[ArticleContent],
        output_dir: Path,
        include_frontmatter: bool = True,
    ) -> list[Path]:
        """
        Save multiple articles as markdown files.

        Args:
            articles: List of articles to save
            output_dir: Directory to save files in
            include_frontmatter: Whether to include YAML frontmatter

        Returns:
            List of paths to saved files
        """
        saved_paths = []
        for article in articles:
            if article.content_markdown:
                path = self.save_as_markdown(article, output_dir, include_frontmatter)
                saved_paths.append(path)

        logger.info(f"Saved {len(saved_paths)} markdown files to {output_dir}")
        return saved_paths


def create_timestamped_filename(prefix: str, extension: str = ".json") -> str:
    """
    Create a filename with timestamp.

    Args:
        prefix: Filename prefix
        extension: File extension (default: ".json")

    Returns:
        Filename like "prefix_20240115_143022.json"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}{extension}"
