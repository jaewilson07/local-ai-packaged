#!/usr/bin/env python3
"""Extract paginated table data and article content from Circle.so.

This script demonstrates using the Crawl4AI RAG library components:
- PaginationHelper for clicking through paginated tables
- CircleTableExtractor for parsing Circle.so posts table
- CircleArticleExtractor for extracting article content
- Export utilities for saving to JSON, CSV, and Markdown

Features:
- **Caching**: Uses Crawl4AI's CacheMode.ENABLED to avoid re-fetching pages
- **Incremental Saving**: Saves each article immediately after extraction
- **Resume Support**: Skips already-scraped articles when using --resume
- **Checkpointing**: Table data saved immediately to preserve progress

Prerequisites:
- Dependencies installed: Run `uv pip install -e ".[test]"` in `04-lambda/` directory
- Browser profile created: Run extract_and_crawl.py first to create an authenticated profile

Usage:
    # Extract table data only
    python sample/crawl4ai_rag/extract_table_data.py --table-only

    # Extract table data and all article content (default)
    python sample/crawl4ai_rag/extract_table_data.py

    # Extract specific number of articles (for testing)
    python sample/crawl4ai_rag/extract_table_data.py --limit 5

    # Resume from previous run (skips already-scraped articles)
    python sample/crawl4ai_rag/extract_table_data.py --resume

    # Force re-scrape all articles (ignore cache)
    python sample/crawl4ai_rag/extract_table_data.py --no-cache
"""

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urljoin

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_path))

try:
    from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
except ImportError:
    print("ERROR: crawl4ai not installed. Install with: pip install crawl4ai")
    sys.exit(1)

# Import library components
from workflows.ingestion.crawl4ai_rag.ai.dependencies import (  # noqa: E402
    create_browser_config_with_profile,
    get_profile_path,
)
from workflows.ingestion.crawl4ai_rag.services.downloader import (  # noqa: E402
    create_timestamped_path,
    save_data_to_csv,
    save_data_to_json,
)
from workflows.ingestion.crawl4ai_rag.services.extractors.circle import (  # noqa: E402
    CIRCLE_NEXT_BUTTON_SELECTOR,
    CircleArticleExtractor,
    CirclePost,
    CircleTableExtractor,
)
from workflows.ingestion.crawl4ai_rag.services.pagination import PaginationHelper  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "https://datacrew.circle.so"
TARGET_URL = f"{BASE_URL}/settings/posts"
PROFILE_NAME = "datacrew-circle"
EXPORTS_DIR = project_root / "EXPORTS"
ARTICLES_DIR = EXPORTS_DIR / "articles"
CHECKPOINT_FILE = EXPORTS_DIR / ".table_checkpoint.json"


def get_existing_article_urls(articles_dir: Path) -> set[str]:
    """
    Scan existing markdown files to find already-scraped article URLs.

    Args:
        articles_dir: Directory containing markdown files

    Returns:
        Set of URLs that have already been scraped
    """
    existing_urls = set()

    if not articles_dir.exists():
        return existing_urls

    for md_file in articles_dir.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            # Look for URL in frontmatter
            if content.startswith("---"):
                end_idx = content.find("---", 3)
                if end_idx > 0:
                    frontmatter = content[3:end_idx]
                    for line in frontmatter.split("\n"):
                        if line.startswith("url:"):
                            url = line[4:].strip().strip('"').strip("'")
                            if url:
                                existing_urls.add(url)
                                break
        except Exception as e:
            logger.debug(f"Could not read {md_file}: {e}")
            continue

    return existing_urls


def load_checkpoint(checkpoint_file: Path) -> list[dict] | None:
    """
    Load table data checkpoint if it exists.

    Args:
        checkpoint_file: Path to checkpoint file

    Returns:
        List of post dicts or None if no checkpoint
    """
    if not checkpoint_file.exists():
        return None

    try:
        with open(checkpoint_file, encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Loaded checkpoint with {len(data)} posts")
            return data
    except Exception as e:
        logger.warning(f"Failed to load checkpoint: {e}")
        return None


def save_checkpoint(posts: list[CirclePost], checkpoint_file: Path) -> None:
    """
    Save table data checkpoint.

    Args:
        posts: List of CirclePost objects
        checkpoint_file: Path to checkpoint file
    """
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

    data = [asdict(post) for post in posts]
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"Saved checkpoint with {len(posts)} posts to {checkpoint_file}")


def posts_from_checkpoint(data: list[dict]) -> list[CirclePost]:
    """
    Convert checkpoint data back to CirclePost objects.

    Args:
        data: List of post dicts from checkpoint

    Returns:
        List of CirclePost objects
    """
    posts = []
    for item in data:
        # Handle default_factory fields
        if "author_tags" not in item or item["author_tags"] is None:
            item["author_tags"] = []
        posts.append(CirclePost(**item))
    return posts


async def extract_table_data(crawler: AsyncWebCrawler) -> list[CirclePost]:
    """Extract all posts from the paginated table."""
    table_extractor = CircleTableExtractor()

    # Create pagination helper with Circle.so settings
    pagination = PaginationHelper(
        crawler=crawler,
        next_button_selector=CIRCLE_NEXT_BUTTON_SELECTOR,
        extract_fn=table_extractor.extract_rows_from_html,
        get_item_key=table_extractor.get_row_key,
        page_load_delay=1.5,
    )

    # Extract all pages
    result = await pagination.extract_all_pages(
        url=TARGET_URL,
        max_pages=20,
        session_id="circle_table_extraction",
    )

    if result.errors:
        for error in result.errors:
            logger.warning(f"Pagination error: {error}")

    print(f"\n✅ Total extracted: {result.total_items} posts from {result.pages_extracted} pages")
    return result.items


async def extract_article_content(
    crawler: AsyncWebCrawler,
    posts: list[CirclePost],
    limit: int | None = None,
    use_cache: bool = True,
    resume: bool = False,
    articles_dir: Path = ARTICLES_DIR,
) -> list[CirclePost]:
    """
    Extract full content for each article with incremental saving.

    Args:
        crawler: AsyncWebCrawler instance
        posts: List of posts to process
        limit: Optional limit on number of articles to process
        use_cache: Whether to use Crawl4AI's cache (default: True)
        resume: Whether to skip already-scraped articles (default: False)
        articles_dir: Directory for saving markdown files

    Returns:
        List of processed posts
    """
    article_extractor = CircleArticleExtractor(base_url=BASE_URL)

    # Get already-scraped URLs if resuming
    existing_urls = set()
    if resume:
        existing_urls = get_existing_article_urls(articles_dir)
        if existing_urls:
            print(f"📋 Found {len(existing_urls)} already-scraped articles")

    posts_to_process = posts[:limit] if limit else posts
    total = len(posts_to_process)
    skipped = 0
    extracted = 0
    failed = 0

    print(f"\n📚 Processing {total} articles...")
    print(f"   Cache: {'ENABLED' if use_cache else 'BYPASS'}")
    print(f"   Resume: {'YES' if resume else 'NO'}")
    print("-" * 40)

    # Ensure articles directory exists
    articles_dir.mkdir(parents=True, exist_ok=True)

    # Configure cache mode
    cache_mode = CacheMode.ENABLED if use_cache else CacheMode.BYPASS

    for i, post in enumerate(posts_to_process, 1):
        # Check if already scraped
        full_url = urljoin(BASE_URL, post.url)
        if resume and full_url in existing_urls:
            print(f"[{i}/{total}] ⏭️  Skipping (already scraped): {post.title[:50]}...")
            skipped += 1
            continue

        print(f"[{i}/{total}] {post.title[:60]}...")

        config = CrawlerRunConfig(
            wait_until="networkidle",
            page_timeout=60000,
            cache_mode=cache_mode,
        )

        try:
            result = await crawler.arun(url=full_url, config=config)

            if result.success:
                article_extractor.extract_from_post(post, result.html)

                # Fallback to Crawl4AI markdown if our extraction failed
                if not post.content_markdown and result.markdown:
                    post.content_markdown = str(result.markdown)

                # Save immediately after extraction
                if post.content_markdown:
                    article = article_extractor.post_to_article_content(post)
                    article_extractor.save_as_markdown(article, articles_dir)
                    extracted += 1
                    logger.info(f"  ✓ Extracted and saved {len(post.content_markdown)} chars")
                else:
                    logger.warning("  ⚠️ No content extracted")
                    failed += 1
            else:
                logger.warning(f"  ✗ Failed: {result.error_message}")
                failed += 1

        except Exception as e:
            logger.exception(f"  ✗ Error processing {post.url}: {e}")
            failed += 1

        # Small delay between requests (only if not using cache hit)
        await asyncio.sleep(0.5)

    print("-" * 40)
    print("✅ Processing complete:")
    print(f"   Extracted: {extracted}")
    print(f"   Skipped (already done): {skipped}")
    print(f"   Failed: {failed}")

    return posts_to_process


def save_results(
    posts: list[CirclePost],
    output_dir: Path,
    save_markdown: bool = True,
    use_timestamp: bool = False,
) -> dict[str, Path]:
    """Save extracted posts to various formats.

    Args:
        posts: List of CirclePost objects to save
        output_dir: Directory to save files to
        save_markdown: Whether to save individual markdown files
        use_timestamp: Whether to include timestamp in filenames (default: False)

    Returns:
        Dictionary of saved file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_files = {}

    # Determine file paths (with or without timestamp)
    if use_timestamp:
        json_path = create_timestamped_path(output_dir, "circle_posts", ".json")
        csv_path = create_timestamped_path(output_dir, "circle_posts", ".csv")
    else:
        json_path = output_dir / "circle_posts.json"
        csv_path = output_dir / "circle_posts.csv"

    # Save JSON
    save_data_to_json(posts, json_path)
    saved_files["json"] = json_path

    # Save CSV (metadata only)
    save_data_to_csv(
        posts,
        csv_path,
        fields=[
            "title",
            "url",
            "status",
            "author",
            "author_url",
            "space",
            "likes",
            "comments",
            "updated",
            "published_date",
        ],
    )
    saved_files["csv"] = csv_path

    # Save individual markdown files
    if save_markdown:
        article_extractor = CircleArticleExtractor(base_url=BASE_URL)
        articles_dir = output_dir / "articles"
        articles_dir.mkdir(parents=True, exist_ok=True)

        md_count = 0
        for post in posts:
            if post.content_markdown:
                article = article_extractor.post_to_article_content(post)
                article_extractor.save_as_markdown(article, articles_dir)
                md_count += 1

        if md_count > 0:
            saved_files["markdown_dir"] = articles_dir
            logger.info(f"Saved {md_count} markdown files to {articles_dir}")

    return saved_files


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract paginated table data and article content from Circle.so"
    )
    parser.add_argument(
        "--table-only",
        action="store_true",
        help="Only extract table data, skip article content extraction",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of articles to extract (for testing)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no visible window)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous run - skip already-scraped articles",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass Crawl4AI's cache (force fresh scrape)",
    )
    parser.add_argument(
        "--use-checkpoint",
        action="store_true",
        help="Use saved table data checkpoint instead of re-scraping table",
    )
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_args()

    print("=" * 80)
    print("Extract Paginated Table Data and Articles from Circle.so")
    print("=" * 80)
    print()
    print(f"Target URL: {TARGET_URL}")
    print(f"Output directory: {EXPORTS_DIR}")
    print(f"Mode: {'Table only' if args.table_only else 'Table + Article content'}")
    if args.limit:
        print(f"Article limit: {args.limit}")
    print(f"Resume: {'YES' if args.resume else 'NO'}")
    print(f"Cache: {'DISABLED' if args.no_cache else 'ENABLED'}")
    print(f"Use checkpoint: {'YES' if args.use_checkpoint else 'NO'}")
    print()

    # Try to load from checkpoint if requested
    posts = None
    if args.use_checkpoint:
        checkpoint_data = load_checkpoint(CHECKPOINT_FILE)
        if checkpoint_data:
            posts = posts_from_checkpoint(checkpoint_data)
            print(f"✅ Loaded {len(posts)} posts from checkpoint")
            print()

    # Check for browser profile (needed for table scraping or if no checkpoint)
    if posts is None:
        profile_path = get_profile_path(PROFILE_NAME)
        if not profile_path:
            print("❌ No browser profile found!")
            print("   Please run extract_and_crawl.py first to create an authenticated profile.")
            sys.exit(1)

        print(f"✅ Found profile: {profile_path}")
        print()

        # Create browser config and crawler
        browser_config = create_browser_config_with_profile(
            profile_path,
            headless=args.headless,
            verbose=True,
            text_mode=False,  # Need full rendering for JS tables
        )
        crawler = AsyncWebCrawler(config=browser_config)

        await crawler.__aenter__()

        try:
            # Step 1: Extract table data
            posts = await extract_table_data(crawler)

            if not posts:
                print("❌ No data extracted!")
                sys.exit(1)

            # Save checkpoint immediately after table extraction
            save_checkpoint(posts, CHECKPOINT_FILE)

            # Step 2: Extract article content (unless --table-only)
            if not args.table_only:
                posts = await extract_article_content(
                    crawler,
                    posts,
                    limit=args.limit,
                    use_cache=not args.no_cache,
                    resume=args.resume,
                    articles_dir=ARTICLES_DIR,
                )

        finally:
            await crawler.__aexit__(None, None, None)
            logger.info("Browser closed")
    # Using checkpoint - still need crawler for article extraction
    elif not args.table_only:
        profile_path = get_profile_path(PROFILE_NAME)
        if not profile_path:
            print("❌ No browser profile found!")
            print("   Please run extract_and_crawl.py first to create an authenticated profile.")
            sys.exit(1)

        browser_config = create_browser_config_with_profile(
            profile_path,
            headless=args.headless,
            verbose=True,
            text_mode=False,
        )
        crawler = AsyncWebCrawler(config=browser_config)

        await crawler.__aenter__()

        try:
            posts = await extract_article_content(
                crawler,
                posts,
                limit=args.limit,
                use_cache=not args.no_cache,
                resume=args.resume,
                articles_dir=ARTICLES_DIR,
            )
        finally:
            await crawler.__aexit__(None, None, None)
            logger.info("Browser closed")

    # Save final results (JSON and CSV - markdown already saved incrementally)
    # Use fixed filenames since the posts list doesn't change frequently
    saved_files = save_results(
        posts,
        EXPORTS_DIR,
        save_markdown=False,  # Already saved incrementally
        use_timestamp=False,  # Fixed filenames for posts data
    )

    # Print summary
    print()
    print("=" * 80)
    print("Extraction Complete")
    print("=" * 80)
    print()
    print(f"✅ Extracted {len(posts)} posts")
    print(f"   JSON: {saved_files.get('json')}")
    print(f"   CSV: {saved_files.get('csv')}")
    print(f"   Markdown: {ARTICLES_DIR}")
    print(f"   Checkpoint: {CHECKPOINT_FILE}")
    print()

    # Show sample data
    print("Sample data (first 5 posts):")
    print("-" * 40)
    for post in posts[:5]:
        print(f"  Title: {post.title[:60]}{'...' if len(post.title) > 60 else ''}")
        print(f"  Author: {post.author}")
        print(f"  Space: {post.space}")
        print(f"  Likes: {post.likes}, Comments: {post.comments}")
        if post.content_markdown:
            print(f"  Content: {len(post.content_markdown)} chars")
        print("-" * 40)

    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
