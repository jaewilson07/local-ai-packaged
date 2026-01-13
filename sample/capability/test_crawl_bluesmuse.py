#!/usr/bin/env python3
"""Test script to crawl https://www.bluesmuse.dance/ using crawl4ai.

This is a sample capability test demonstrating how to use crawl4ai
to crawl a single webpage and extract its content.
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
server_path = project_root / "04-lambda" / "server"
sys.path.insert(0, str(server_path))

import logging  # noqa: E402

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def crawl_bluesmuse():
    """Crawl the Blues Muse Dance website."""
    url = "https://www.bluesmuse.dance/"

    logger.info(f"🚀 Starting crawl of {url}")

    # Configure browser
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        text_mode=True,  # Disable images for faster crawling
    )

    # Create crawler
    crawler = AsyncWebCrawler(config=browser_config)

    try:
        # Initialize crawler
        await crawler.__aenter__()
        logger.info("✅ Crawler initialized")

        # Configure crawl run
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            stream=False,
            wait_until="domcontentloaded",
            page_timeout=30000,  # 30 second timeout
            wait_for_images=False,
            exclude_external_links=True,
            exclude_external_images=True,
            word_count_threshold=50,
            remove_overlay_elements=True,
            magic=True,
        )

        # Perform crawl
        logger.info(f"📥 Crawling {url}...")
        result = await crawler.arun(url=url, config=run_config)

        if result.success:
            logger.info("✅ Crawl successful!")

            # Display results
            print("\n" + "=" * 80)
            print("CRAWL RESULTS")
            print("=" * 80)
            print(f"URL: {result.url}")
            print(f"Success: {result.success}")

            if result.markdown:
                markdown_length = len(result.markdown)
                print(f"Markdown length: {markdown_length} characters")
                print("\nFirst 500 characters of markdown:")
                print("-" * 80)
                print(result.markdown[:500])
                print("-" * 80)

            # Display metadata if available
            if hasattr(result, "metadata") and result.metadata:
                print("\nMetadata:")
                print("-" * 80)
                metadata = result.metadata
                if isinstance(metadata, dict):
                    for key, value in metadata.items():
                        if value:
                            print(f"  {key}: {value}")

            # Display links if available
            if hasattr(result, "links") and result.links:
                links = result.links
                if isinstance(links, dict):
                    internal = links.get("internal", [])
                    external = links.get("external", [])
                    print("\nLinks found:")
                    print(f"  Internal: {len(internal)}")
                    print(f"  External: {len(external)}")
                    if internal:
                        print("\n  First 5 internal links:")
                        for link in internal[:5]:
                            href = link.get("href", "") if isinstance(link, dict) else str(link)
                            print(f"    - {href}")

            print("\n" + "=" * 80)
            return True
        logger.error(f"❌ Crawl failed: {result.error_message}")
        return False

    except Exception:
        logger.exception("❌ Error during crawl")
        return False
    finally:
        # Cleanup
        await crawler.__aexit__(None, None, None)
        logger.info("🧹 Crawler cleaned up")


async def main():
    """Main entry point."""
    print("=" * 80)
    print("Crawl4AI Test - Blues Muse Dance Website")
    print("=" * 80)
    print()

    success = await crawl_bluesmuse()

    if success:
        print("\n✅ Test completed successfully!")

        # Verify via API
        from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
        from sample.shared.verification_helpers import verify_rag_data

        api_base_url = get_api_base_url()
        headers = get_auth_headers()

        print("\n" + "=" * 80)
        print("Verification")
        print("=" * 80)

        success_verify, message = verify_rag_data(
            api_base_url=api_base_url,
            headers=headers,
            expected_documents_min=1,
        )
        print(message)

        if success_verify:
            print("\n✅ Verification passed!")
            sys.exit(0)
        else:
            print("\n❌ Verification failed (data may need time to propagate)")
            sys.exit(1)
    else:
        print("\n❌ Test failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
