#!/usr/bin/env python3
"""Ingest exported Circle.so articles into MongoDB RAG via the centralized API.

This script reads markdown files from EXPORTS/articles/ and ingests them
into the MongoDB RAG system using the /api/v1/rag/ingest/content endpoint.

Features:
- Uses centralized ContentIngestionService via REST API
- Parses YAML frontmatter for Circle.so metadata (author, tags, dates, etc.)
- Deduplication via skip_duplicates option
- Dry run mode to preview without ingesting
- Supports both internal (Docker) and external (authenticated) access

Prerequisites:
- Lambda server running (either locally or via Docker)
- Articles exported to EXPORTS/articles/ (run extract_table_data.py first)

Usage:
    # Ingest all articles (internal network - no auth)
    python sample/crawl4ai_rag/ingest_articles_to_rag.py

    # Ingest with external API (requires auth)
    python sample/crawl4ai_rag/ingest_articles_to_rag.py --external

    # Dry run to see what would be ingested
    python sample/crawl4ai_rag/ingest_articles_to_rag.py --dry-run

    # Skip duplicates (default behavior)
    python sample/crawl4ai_rag/ingest_articles_to_rag.py --skip-duplicates

    # Force re-ingest even if exists
    python sample/crawl4ai_rag/ingest_articles_to_rag.py --no-skip-duplicates
"""

import argparse
import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from project root
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Import auth helpers for API access
from sample.shared.auth_helpers import (
    get_api_base_url,
    get_auth_headers,
    get_cloudflare_email,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
EXPORTS_DIR = project_root / "EXPORTS"
ARTICLES_DIR = EXPORTS_DIR / "articles"
BASE_URL = "https://datacrew.circle.so"


@dataclass
class ArticleMetadata:
    """Parsed metadata from article frontmatter."""

    title: str
    url: str
    author: str = ""
    published_date: str = ""
    updated_date: str = ""
    tags: list[str] | None = None
    categories: list[str] | None = None
    likes: int = 0
    file_path: str = ""


@dataclass
class IngestionResult:
    """Result of article ingestion."""

    success: bool
    document_id: str
    title: str
    chunks_created: int
    processing_time_ms: float
    skipped: bool = False
    skip_reason: str = ""
    errors: list[str] | None = None


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown content including frontmatter

    Returns:
        Tuple of (metadata_dict, content_without_frontmatter)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the end of frontmatter
    end_match = re.search(r"\n---\n", content[3:])
    if not end_match:
        return {}, content

    frontmatter_end = end_match.start() + 3
    frontmatter_str = content[3:frontmatter_end]

    try:
        metadata = yaml.safe_load(frontmatter_str)
        if not isinstance(metadata, dict):
            return {}, content

        # Content starts after the closing ---
        body = content[frontmatter_end + 4 :].strip()
        return metadata, body
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse frontmatter: {e}")
        return {}, content


def extract_article_metadata(file_path: Path) -> ArticleMetadata | None:
    """
    Extract metadata from a markdown article file.

    Args:
        file_path: Path to the markdown file

    Returns:
        ArticleMetadata or None if parsing fails
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        metadata, _ = parse_frontmatter(content)

        if not metadata:
            # Try to extract title from first heading
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else file_path.stem

            return ArticleMetadata(
                title=title,
                url="",
                file_path=str(file_path),
            )

        # Parse tags - handle both string and list formats
        tags = metadata.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = eval(tags)  # Safe since it's from our own export
            except (ValueError, SyntaxError):
                tags = [tags]

        # Parse categories similarly
        categories = metadata.get("categories", [])
        if isinstance(categories, str):
            try:
                categories = eval(categories)
            except (ValueError, SyntaxError):
                categories = [categories]

        return ArticleMetadata(
            title=metadata.get("title", file_path.stem),
            url=metadata.get("url", ""),
            author=metadata.get("author", ""),
            published_date=metadata.get("published_date", ""),
            updated_date=metadata.get("updated_date", ""),
            tags=tags if tags else None,
            categories=categories if categories else None,
            likes=metadata.get("likes", 0),
            file_path=str(file_path),
        )
    except Exception as e:
        logger.warning(f"Failed to extract metadata from {file_path}: {e}")
        return None


def scan_articles_directory(articles_dir: Path) -> list[ArticleMetadata]:
    """
    Scan directory for markdown files and extract metadata.

    Args:
        articles_dir: Path to articles directory

    Returns:
        List of ArticleMetadata objects
    """
    if not articles_dir.exists():
        logger.error(f"Articles directory not found: {articles_dir}")
        return []

    articles = []
    md_files = list(articles_dir.glob("*.md"))

    logger.info(f"Found {len(md_files)} markdown files in {articles_dir}")

    for file_path in md_files:
        metadata = extract_article_metadata(file_path)
        if metadata:
            articles.append(metadata)

    return articles


class ArticleIngester:
    """Ingests articles into MongoDB RAG system via API."""

    def __init__(
        self,
        api_base_url: str,
        headers: dict[str, str],
        use_docling: bool = True,
        skip_duplicates: bool = True,
        dry_run: bool = False,
    ):
        """
        Initialize ingester.

        Args:
            api_base_url: Base URL for the API
            headers: HTTP headers (including auth if needed)
            use_docling: Whether to use Docling for chunking
            skip_duplicates: Whether to skip already-ingested articles
            dry_run: If True, don't actually ingest
        """
        self.api_base_url = api_base_url
        self.headers = headers
        self.use_docling = use_docling
        self.skip_duplicates = skip_duplicates
        self.dry_run = dry_run
        self.client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(timeout=120.0)  # 2 minute timeout
        logger.info(f"Initialized HTTP client for {self.api_base_url}")

    async def cleanup(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("HTTP client closed")

    async def ingest_article(self, article: ArticleMetadata) -> IngestionResult:
        """
        Ingest a single article via the /api/v1/rag/ingest/content endpoint.

        Args:
            article: Article metadata

        Returns:
            IngestionResult
        """
        if self.dry_run:
            return IngestionResult(
                success=True,
                document_id="dry-run",
                title=article.title,
                chunks_created=0,
                processing_time_ms=0,
                skipped=False,
                errors=[],
            )

        try:
            # Read file content
            file_path = Path(article.file_path)
            content = file_path.read_text(encoding="utf-8")

            # Parse frontmatter and get body
            _, body = parse_frontmatter(content)

            # Build full URL for source
            full_url = f"{BASE_URL}{article.url}" if article.url else article.file_path

            # Build metadata
            metadata = {
                "url": article.url,
                "full_url": full_url,
                "author": article.author,
                "published_date": article.published_date,
                "updated_date": article.updated_date,
                "tags": article.tags or [],
                "categories": article.categories or [],
                "likes": article.likes,
                "file_path": article.file_path,
                "source_type": "circle_article",
            }

            # Prepare request
            request_data = {
                "content": body,
                "title": article.title,
                "source": full_url,
                "source_type": "article",
                "metadata": metadata,
                "use_docling": self.use_docling,
                "skip_duplicates": self.skip_duplicates,
            }

            # Call the API
            response = await self.client.post(
                f"{self.api_base_url}/api/v1/rag/ingest/content",
                json=request_data,
                headers=self.headers,
            )

            if response.status_code != 200:
                error_detail = response.text
                return IngestionResult(
                    success=False,
                    document_id="",
                    title=article.title,
                    chunks_created=0,
                    processing_time_ms=0,
                    errors=[f"API error {response.status_code}: {error_detail}"],
                )

            result = response.json()

            return IngestionResult(
                success=result.get("success", False),
                document_id=result.get("document_id", ""),
                title=result.get("title", article.title),
                chunks_created=result.get("chunks_created", 0),
                processing_time_ms=result.get("processing_time_ms", 0),
                skipped=result.get("skipped", False),
                skip_reason=result.get("skip_reason", ""),
                errors=result.get("errors", []),
            )

        except httpx.TimeoutException:
            return IngestionResult(
                success=False,
                document_id="",
                title=article.title,
                chunks_created=0,
                processing_time_ms=0,
                errors=["Request timed out"],
            )
        except Exception as e:
            logger.exception(f"Error ingesting {article.title}")
            return IngestionResult(
                success=False,
                document_id="",
                title=article.title,
                chunks_created=0,
                processing_time_ms=0,
                errors=[str(e)],
            )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest exported Circle.so articles into MongoDB RAG via API"
    )
    parser.add_argument(
        "--external",
        action="store_true",
        help="Use external API (requires Cloudflare Access authentication)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="Override API base URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be ingested without actually ingesting",
    )
    parser.add_argument(
        "--skip-duplicates",
        action="store_true",
        default=True,
        help="Skip articles that already exist (default: True)",
    )
    parser.add_argument(
        "--no-skip-duplicates",
        action="store_true",
        help="Re-ingest articles even if they already exist",
    )
    parser.add_argument(
        "--no-docling",
        action="store_true",
        help="Disable Docling-based chunking (use simple fallback)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of articles to ingest (for testing)",
    )
    parser.add_argument(
        "--articles-dir",
        type=str,
        default=str(ARTICLES_DIR),
        help=f"Directory containing markdown articles (default: {ARTICLES_DIR})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine API URL
    if args.api_url:
        api_base_url = args.api_url
    elif args.external:
        api_base_url = "https://api.datacrew.space"
    else:
        api_base_url = get_api_base_url()

    # Get auth headers
    headers = get_auth_headers() if args.external else {"Content-Type": "application/json"}

    # Get user email for display
    user_email = get_cloudflare_email() or "anonymous"

    print("=" * 80)
    print("Ingest Circle.so Articles into MongoDB RAG")
    print("=" * 80)
    print()
    print(f"API URL: {api_base_url}")
    print(f"User: {user_email}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Skip duplicates: {'NO' if args.no_skip_duplicates else 'YES'}")
    print(f"Use Docling: {'NO' if args.no_docling else 'YES'}")
    print(f"Articles directory: {args.articles_dir}")
    if args.limit:
        print(f"Limit: {args.limit} articles")
    print()

    # Scan for articles
    articles_dir = Path(args.articles_dir)
    articles = scan_articles_directory(articles_dir)

    if not articles:
        print("❌ No articles found!")
        sys.exit(1)

    # Apply limit
    if args.limit:
        articles = articles[: args.limit]

    print(f"📚 Found {len(articles)} articles to process")
    print()

    # Initialize ingester
    skip_duplicates = not args.no_skip_duplicates
    use_docling = not args.no_docling

    ingester = ArticleIngester(
        api_base_url=api_base_url,
        headers=headers,
        use_docling=use_docling,
        skip_duplicates=skip_duplicates,
        dry_run=args.dry_run,
    )

    try:
        await ingester.initialize()

        print(f"📤 Ingesting {len(articles)} articles...")
        print("-" * 40)

        # Ingest articles
        results: list[IngestionResult] = []
        skipped_count = 0
        error_count = 0

        for i, article in enumerate(articles, 1):
            title_display = article.title[:50] + "..." if len(article.title) > 50 else article.title
            print(f"[{i}/{len(articles)}] {title_display}")

            result = await ingester.ingest_article(article)
            results.append(result)

            if result.skipped:
                skipped_count += 1
                logger.info(f"  ⏭️ Skipped: {result.skip_reason}")
            elif result.errors:
                error_count += 1
                for error in result.errors:
                    logger.warning(f"  ⚠️ {error}")
            elif not args.dry_run:
                logger.info(
                    f"  ✓ {result.chunks_created} chunks ({result.processing_time_ms:.0f}ms)"
                )

        print("-" * 40)

        # Summary
        total_chunks = sum(r.chunks_created for r in results)
        successful = len([r for r in results if r.success and not r.skipped])
        failed = len([r for r in results if not r.success])

        print()
        print("=" * 80)
        print("Ingestion Summary")
        print("=" * 80)
        print()
        print(f"✅ Successfully ingested: {successful} articles")
        print(f"⏭️  Skipped (already exist): {skipped_count} articles")
        if failed > 0:
            print(f"❌ Failed: {failed} articles")
        print(f"📄 Total chunks created: {total_chunks}")
        print()

    finally:
        await ingester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
