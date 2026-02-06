"""Circle.so-specific content extractors.

This module provides extractors for Circle.so community platform content,
including posts tables and article content.
"""

import logging
import re
from dataclasses import dataclass, field

from app.workflows.ingestion.crawl4ai_rag.services.extractors.base import (
    ArticleContent,
    ArticleExtractor,
    TableExtractor,
    TableRow,
)

logger = logging.getLogger(__name__)


@dataclass
class CirclePost(TableRow):
    """Data class for a Circle.so post from the admin posts table."""

    title: str = ""
    url: str = ""
    status: str = ""
    author: str = ""
    author_url: str = ""
    space: str = ""
    likes: int = 0
    comments: int = 0
    updated: str = ""

    # Content fields (populated when article is fetched)
    content_markdown: str = ""
    content_html: str = ""
    author_tags: list[str] = field(default_factory=list)
    author_credentials: str = ""
    cover_image_url: str = ""
    published_date: str = ""


class CircleTableExtractor(TableExtractor[CirclePost]):
    """
    Extractor for Circle.so admin posts table (/settings/posts).

    Extracts post metadata from the paginated table in the Circle.so
    admin interface.
    """

    def extract_rows_from_html(self, html: str) -> list[CirclePost]:
        """Extract posts from Circle.so settings/posts table HTML."""
        posts = []

        # Find the tbody content
        tbody_match = re.search(
            r'<tbody[^>]*class="bg-primary divide-primary divide-y"[^>]*>(.*?)</tbody>',
            html,
            re.DOTALL,
        )

        if not tbody_match:
            logger.warning("Could not find tbody in HTML")
            return posts

        tbody_html = tbody_match.group(1)

        # Split by rows
        rows = re.findall(
            r'<tr[^>]*class="cursor-default[^"]*"[^>]*>(.*?)</tr>',
            tbody_html,
            re.DOTALL,
        )

        for row_html in rows:
            try:
                post = self._parse_row(row_html)
                if post:
                    posts.append(post)
            except Exception as e:
                logger.warning(f"Failed to parse row: {e}")
                continue

        return posts

    def _parse_row(self, row_html: str) -> CirclePost | None:
        """Parse a single table row into a CirclePost."""
        # Extract title and URL
        title_match = re.search(
            r'<a href="([^"]+)"[^>]*><span[^>]*>([^<]+)</span></a>',
            row_html,
        )
        if not title_match:
            return None

        url = title_match.group(1)
        title = title_match.group(2).strip()

        # Extract status
        status_match = re.search(
            r'data-testid="status-badge">([^<]+)</span>',
            row_html,
        )
        status = status_match.group(1).strip() if status_match else ""

        # Extract author URL
        author_url_match = re.search(
            r'<a href="(/u/[^"]+)"[^>]*aria-label="View user profile"',
            row_html,
        )
        author_url = author_url_match.group(1) if author_url_match else ""

        # Extract author name
        author_match = re.search(
            r'</div></div></div><span[^>]*class="[^"]*text-dark[^"]*"[^>]*>([^<]+)</span>',
            row_html,
        )
        author = author_match.group(1).strip() if author_match else ""

        # Extract space
        space_match = re.search(
            r'aria-hidden="true"[^>]*>[^<]*</span><span>([^<]+)</span>',
            row_html,
        )
        space = space_match.group(1).strip() if space_match else ""

        # Extract likes and comments
        numeric_cells = re.findall(
            r"<td[^>]*whitespace-nowrap[^>]*>(\d+)</td>",
            row_html,
        )
        likes = int(numeric_cells[0]) if len(numeric_cells) > 0 else 0
        comments = int(numeric_cells[1]) if len(numeric_cells) > 1 else 0

        # Extract updated date
        date_match = re.search(
            r"<td[^>]*whitespace-nowrap[^>]*>([A-Z][a-z]{2} \d{1,2}, \d{4} at \d{2}:\d{2} [AP]M)</td>",
            row_html,
        )
        updated = date_match.group(1).strip() if date_match else ""

        return CirclePost(
            title=title,
            url=url,
            status=status,
            author=author,
            author_url=author_url,
            space=space,
            likes=likes,
            comments=comments,
            updated=updated,
        )

    def get_row_key(self, row: CirclePost) -> str:
        """Get unique key for a post (URL)."""
        return row.url

    def get_pagination_total(self, html: str) -> tuple[int, int]:
        """
        Extract pagination info from the page.

        Args:
            html: Page HTML

        Returns:
            Tuple of (total_items, total_pages)
        """
        # Look for "of <span...>123</span>"
        total_match = re.search(r"of\s*<span[^>]*>(\d+)</span>", html)
        total_items = int(total_match.group(1)) if total_match else 0
        total_pages = (total_items + 9) // 10  # 10 items per page
        return total_items, total_pages


class CircleArticleExtractor(ArticleExtractor):
    """
    Extractor for Circle.so article/post content.

    Extracts full article content from Circle.so post pages.
    """

    def __init__(self, base_url: str = "https://datacrew.circle.so"):
        """
        Initialize extractor.

        Args:
            base_url: Base URL for the Circle.so community
        """
        self.base_url = base_url

    def extract_content_from_html(self, html: str, url: str = "") -> ArticleContent:
        """Extract article content from Circle.so post page HTML."""
        article = ArticleContent(url=url)

        try:
            # Extract title
            title_match = re.search(
                r'data-testid="post-title"[^>]*>.*?<a[^>]*>([^<]+)</a>',
                html,
                re.DOTALL,
            )
            if title_match:
                article.title = title_match.group(1).strip()

            # Extract published date
            date_match = re.search(
                r'class="author__time[^"]*"[^>]*>.*?<span[^>]*>([^<]+)</span>',
                html,
                re.DOTALL,
            )
            if date_match:
                article.published_date = date_match.group(1).strip()

            # Extract author
            author_match = re.search(
                r'data-testid="post-avatar"[^>]*>([^<]+)</a>',
                html,
            )
            if author_match:
                article.author = author_match.group(1).strip()

            # Extract author tags
            tags = re.findall(
                r'data-testid="member-tag-label">([^<]+)</span>',
                html,
            )
            if tags:
                article.tags = list(set(t.strip() for t in tags))  # Dedupe

            # Extract cover image
            cover_match = re.search(
                r'class="post__cover[^"]*"[^>]*>.*?<img[^>]*src="([^"]+)"',
                html,
                re.DOTALL,
            )
            if cover_match:
                article.cover_image_url = cover_match.group(1)

            # Extract extra metadata
            creds_match = re.search(
                r'class="author__credentials[^"]*"[^>]*>.*?<span[^>]*>([^<]+)</span>',
                html,
                re.DOTALL,
            )
            if creds_match:
                article.extra["author_credentials"] = creds_match.group(1).strip()

            # Extract main content from trix-content div
            content_html = self._extract_trix_content(html)
            if content_html:
                article.content_html = content_html
                article.content_markdown = self.html_to_markdown(content_html)

        except Exception as e:
            logger.warning(f"Error extracting article content: {e}")

        return article

    def _extract_trix_content(self, html: str) -> str:
        """Extract the main content from trix-content div."""
        # Try several patterns
        patterns = [
            r'<div[^>]*class="[^"]*trix-content[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>\s*<button',
            r'<div class="trix-content">(.*?)</div>\s*</div>',
            r'class="react-trix-content[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                return match.group(1)

        return ""

    def extract_from_post(self, post: CirclePost, html: str) -> CirclePost:
        """
        Extract article content and update a CirclePost in-place.

        This is a convenience method that extracts content from HTML
        and updates the post object with the extracted data.

        Args:
            post: CirclePost to update
            html: HTML of the article page

        Returns:
            Updated CirclePost
        """
        article = self.extract_content_from_html(html, url=post.url)

        # Update post with extracted content
        post.content_markdown = article.content_markdown
        post.content_html = article.content_html
        post.published_date = article.published_date or post.updated
        post.cover_image_url = article.cover_image_url
        post.author_tags = article.tags

        if "author_credentials" in article.extra:
            post.author_credentials = article.extra["author_credentials"]

        return post

    def post_to_article_content(self, post: CirclePost) -> ArticleContent:
        """
        Convert a CirclePost to ArticleContent.

        Args:
            post: CirclePost with content already extracted

        Returns:
            ArticleContent instance
        """
        return ArticleContent(
            title=post.title,
            url=post.url,
            author=post.author,
            author_url=post.author_url,
            published_date=post.published_date,
            updated_date=post.updated,
            content_markdown=post.content_markdown,
            content_html=post.content_html,
            tags=post.author_tags,
            categories=[post.space] if post.space else [],
            cover_image_url=post.cover_image_url,
            likes=post.likes,
            comments=post.comments,
            extra={
                "status": post.status,
                "author_credentials": post.author_credentials,
            },
        )


# Constants for Circle.so pagination
CIRCLE_NEXT_BUTTON_SELECTOR = 'button:has-text("Next"):not([disabled])'
CIRCLE_POSTS_PER_PAGE = 10
