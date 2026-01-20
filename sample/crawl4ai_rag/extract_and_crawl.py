#!/usr/bin/env python3
"""Execute authenticated deep crawl using BrowserProfiler.

This script uses Crawl4AI's BrowserProfiler for identity-based crawling to perform
an authenticated deep crawl of a website and download all pages as markdown files
to the /EXPORTS directory.

Prerequisites:
- Dependencies installed: Run `uv pip install -e ".[test]"` in `04-lambda/` directory

Usage:
    # First run - creates profile and prompts for login
    python sample/crawl4ai_rag/extract_and_crawl.py

    # Subsequent runs - uses existing profile
    python sample/crawl4ai_rag/extract_and_crawl.py

The script will:
1. Attempt to load a local user profile
2. If profile exists, open a headed browser and navigate to target URL
3. Prompt user to press enter when ready to continue scraping
4. Start scraping with headless browser
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_path))

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, BrowserProfiler
except ImportError:
    print("ERROR: crawl4ai not installed. Install with: pip install crawl4ai")
    sys.exit(1)

from workflows.ingestion.crawl4ai_rag.ai.dependencies import Crawl4AIDependencies  # noqa: E402
from workflows.ingestion.crawl4ai_rag.services.downloader import (  # noqa: E402
    download_pages_as_markdown,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Target URL
TARGET_URL = "https://datacrew.circle.so/settings/posts"

# Deep crawl settings
MAX_DEPTH = 5  # Maximum crawl depth to follow links
ALLOWED_DOMAIN = "datacrew.circle.so"  # Restrict crawling to this domain
MAX_CONCURRENT = 10  # Maximum concurrent browser sessions

# Profile settings
PROFILE_NAME = "datacrew-circle"
PROFILE_BASE_DIR = Path.home() / ".crawl4ai" / "profiles"

# Output directory
EXPORTS_DIR = project_root / "EXPORTS"


def check_profile_exists(profile_name: str) -> Path | None:
    """
    Check if a browser profile exists.

    Args:
        profile_name: Name of the profile

    Returns:
        Path to the profile directory if it exists, None otherwise
    """
    profile_path = PROFILE_BASE_DIR / profile_name

    # Check if profile exists and has the Default directory (Chrome/Chromium structure)
    if profile_path.exists() and (profile_path / "Default").exists():
        # Return absolute path
        abs_path = profile_path.resolve()
        logger.info(f"Found existing profile: {abs_path}")
        logger.info(f"Profile Default directory exists: {(abs_path / 'Default').exists()}")
        # Check for storage_state.json (cookies/session data)
        storage_state = abs_path / "storage_state.json"
        if storage_state.exists():
            logger.info(f"Profile has storage_state.json: {storage_state}")
        else:
            logger.warning("Profile missing storage_state.json - session data may not be preserved")
        return abs_path

    logger.info(f"Profile not found: {profile_path}")
    return None


async def create_profile(profile_name: str) -> Path:
    """
    Create a new browser profile interactively.

    Args:
        profile_name: Name of the profile

    Returns:
        Path to the profile directory
    """
    logger.info(f"Creating new profile: {profile_name}")
    print("=" * 80)
    print("Browser Profile Setup")
    print("=" * 80)
    print()
    print("A browser window will open now.")
    print("Please complete authentication in the browser window.")
    print("Once you're logged in and can see the content:")
    print("  1. Navigate to the page you want to crawl")
    print("  2. Press 'q' in the terminal to save the profile and continue")
    print()
    print("=" * 80)
    print()

    profiler = BrowserProfiler()
    profile_path = await profiler.create_profile(profile_name=profile_name)

    # Return absolute path
    abs_path = Path(profile_path).resolve()
    logger.info(f"Profile created: {abs_path}")
    logger.info(f"Profile Default directory exists: {(abs_path / 'Default').exists()}")
    # Check for storage_state.json (cookies/session data)
    storage_state = abs_path / "storage_state.json"
    if storage_state.exists():
        logger.info(f"Profile has storage_state.json: {storage_state}")
    else:
        logger.warning("Profile missing storage_state.json - session data may not be preserved")
    print(f"✅ Profile saved to: {abs_path}")
    print()

    return abs_path


async def preview_url_with_headed_browser(profile_path: Path, url: str) -> None:
    """
    Open a headed browser with the profile and navigate to the target URL.
    Wait for user to press enter before continuing.

    Args:
        profile_path: Path to the browser profile
        url: URL to navigate to
    """
    print("=" * 80)
    print("Opening Browser Preview")
    print("=" * 80)
    print()
    print(f"Opening headed browser with profile: {profile_path}")
    print(f"Navigating to: {url}")
    print()
    print("The browser window will open now.")
    print("Please verify that you can see the content you want to scrape.")
    print("When you're ready to continue scraping, press Enter in this terminal.")
    print()
    print("=" * 80)
    print()

    # Ensure profile_path is absolute
    abs_profile_path = (
        profile_path.resolve() if isinstance(profile_path, Path) else Path(profile_path).resolve()
    )

    logger.info(f"Using profile path: {abs_profile_path}")
    logger.info(f"Profile Default directory exists: {(abs_profile_path / 'Default').exists()}")

    # Create headed browser config with managed browser
    # According to Crawl4AI docs, use_managed_browser=True with user_data_dir
    # automatically loads cookies from the Chrome profile directory
    # We also load storage_state.json if it exists (created by BrowserProfiler)
    storage_state_path = abs_profile_path / "storage_state.json"
    browser_config_kwargs = {
        "headless": False,  # Show browser window
        "verbose": True,
        "use_managed_browser": True,  # Uses Chrome profile directory for cookies
        "user_data_dir": str(abs_profile_path),
        "browser_type": "chromium",
    }

    # Load storage_state.json if it exists (Playwright storage state with cookies)
    # This works alongside use_managed_browser - storage_state takes precedence for cookies
    if storage_state_path.exists():
        logger.info(f"Loading storage_state.json from: {storage_state_path}")
        browser_config_kwargs["storage_state"] = str(storage_state_path)
        print(f"✅ Will load session from: {storage_state_path}")
    else:
        logger.info("No storage_state.json found, relying on Chrome profile cookies")
        print("ℹ️  No storage_state.json found, using Chrome profile cookies")

    browser_config = BrowserConfig(**browser_config_kwargs)

    # Create and open browser
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()

    try:
        # Navigate to target URL
        logger.info(f"Navigating to {url} in headed browser...")
        result = await crawler.arun(url=url)

        if not result.success:
            logger.warning(f"Navigation may have failed: {result.error_message}")
            print(f"⚠️  Warning: Navigation may have failed: {result.error_message}")
            print("You can still proceed if the browser shows the correct page.")
            print()

        # Wait for user to press enter
        print("Browser is now open. Press Enter when ready to continue scraping...")
        print("(Make sure you're logged in and can see the content you want to scrape)")
        input()

        logger.info("User confirmed ready to continue scraping")
        print("✅ Saving session state...")

        # Explicitly save the storage state to ensure cookies/session are preserved
        # This is critical - the storage_state.json contains cookies that will be loaded
        # by the headless crawler
        storage_state_path = abs_profile_path / "storage_state.json"
        if hasattr(crawler, "browser_context") and crawler.browser_context:
            try:
                # Save storage state (cookies, localStorage, sessionStorage)
                await crawler.browser_context.storage_state(path=str(storage_state_path))
                logger.info(f"✅ Saved storage state to: {storage_state_path}")
                print(f"✅ Session state saved to: {storage_state_path}")

                # Verify the file was created and has content
                if storage_state_path.exists():
                    import json

                    with open(storage_state_path) as f:
                        state_data = json.load(f)
                        cookies_count = len(state_data.get("cookies", []))
                        logger.info(f"Storage state contains {cookies_count} cookies")
                        print(f"   Storage state contains {cookies_count} cookies")
                        if cookies_count == 0:
                            print("   ⚠️  Warning: No cookies in storage state!")
                            print("   Make sure you're logged in before continuing.")
            except Exception as e:
                logger.warning(f"Could not save storage state: {e}")
                print(f"⚠️  Warning: Could not save storage state: {e}")
        else:
            logger.warning("Browser context not available to save storage state")
            print("⚠️  Warning: Could not access browser context to save storage state")

        print("✅ Continuing with scraping...")
        print()

    finally:
        # Close the headed browser
        await crawler.__aexit__(None, None, None)
        logger.info("Headed browser closed")

        # Small delay to ensure profile is fully saved
        await asyncio.sleep(1)
        logger.info("Waiting for profile to be fully saved...")


async def main():
    """Main function: setup profile and execute crawl."""
    print("=" * 80)
    print("Authenticated Deep Crawl with BrowserProfiler")
    print("=" * 80)
    print()
    print(f"Target URL: {TARGET_URL}")
    print(f"Max depth: {MAX_DEPTH}")
    print(f"Allowed domain: {ALLOWED_DOMAIN}")
    print(f"Output directory: {EXPORTS_DIR}")
    print()
    print("This script will:")
    print("  1. Attempt to load a local user profile")
    print("  2. If profile exists, open headed browser and navigate to target URL")
    print("  3. Prompt you to press enter when ready to continue scraping")
    print("  4. Execute authenticated deep crawl")
    print("  5. Download all discovered pages as markdown files to /EXPORTS")
    print()
    print("=" * 80)
    print()

    # Step 1: Check if profile exists
    logger.info("Step 1: Checking for existing browser profile...")
    profile_path = check_profile_exists(PROFILE_NAME)

    if not profile_path:
        # Profile doesn't exist - create one
        logger.info("Profile not found, creating new profile...")
        profile_path = await create_profile(PROFILE_NAME)

    # Step 1b: Preview URL with headed browser (for both existing and new profiles)
    logger.info("Opening headed browser for preview...")
    await preview_url_with_headed_browser(profile_path, TARGET_URL)

    # Step 2: Initialize dependencies with profile (skip MongoDB/OpenAI - we only need crawler)
    # Use headless=True for actual crawling
    logger.info("Step 2: Initializing dependencies for scraping...")

    # Ensure profile_path is absolute
    abs_profile_path = (
        profile_path.resolve() if isinstance(profile_path, Path) else Path(profile_path).resolve()
    )
    logger.info(f"Initializing crawler with profile: {abs_profile_path}")
    logger.info(f"Profile Default directory exists: {(abs_profile_path / 'Default').exists()}")

    print("Initializing Crawl4AI dependencies with browser profile (headless mode)...")
    print(f"Using profile: {abs_profile_path}")

    # Check if storage_state.json exists and can be loaded
    storage_state_path = abs_profile_path / "storage_state.json"
    if storage_state_path.exists():
        logger.info(f"Found storage_state.json: {storage_state_path}")
        print(f"✅ Found saved session state: {storage_state_path}")
    else:
        logger.warning(f"storage_state.json not found: {storage_state_path}")
        print("⚠️  Warning: No saved session state found. Make sure you logged in during preview.")

    deps = Crawl4AIDependencies(
        user_data_dir=str(abs_profile_path),
        skip_mongodb=True,  # Skip MongoDB - we're only downloading files
        skip_openai=True,  # Skip OpenAI - we're only downloading files
    )
    await deps.initialize()

    # Verify the crawler is using the profile
    if hasattr(deps.crawler, "config") and hasattr(deps.crawler.config, "user_data_dir"):
        logger.info(f"Crawler config user_data_dir: {deps.crawler.config.user_data_dir}")
        print(f"✅ Crawler initialized with profile: {deps.crawler.config.user_data_dir}")
    else:
        logger.warning("Could not verify crawler profile configuration")
        print("⚠️  Warning: Could not verify crawler profile configuration")
    print()

    # Step 2b: Test crawl to verify profile is working
    logger.info("Step 2b: Testing profile with a single page crawl...")
    print("Testing profile authentication with a single page crawl...")
    print(f"Test URL: {TARGET_URL}")

    from crawl4ai import CrawlerRunConfig

    # Use networkidle for JS-heavy sites like Circle.so that load content via AJAX
    test_config = CrawlerRunConfig(
        wait_until="networkidle",  # Wait for network to be idle (ensures AJAX-loaded content is available)
        page_timeout=60000,  # 60 second timeout for test crawl
    )

    test_result = await deps.crawler.arun(url=TARGET_URL, config=test_config)

    if test_result.success:
        # Check if we got the login page or actual content
        markdown_preview = test_result.markdown[:500] if test_result.markdown else ""
        if "google" in markdown_preview.lower() and "sign in" in markdown_preview.lower():
            logger.error("Profile test failed - got Google login page instead of content")
            print("❌ Profile test failed!")
            print("   The crawler is seeing the Google login page, which means the profile")
            print("   is not being used correctly or the session data is not preserved.")
            print()
            print("   Troubleshooting steps:")
            print("   1. Make sure you logged in during the preview step")
            print("   2. Try creating a new profile")
            print(
                "   3. Check that the profile directory has a 'Default' folder and 'storage_state.json'"
            )
            print()
            print(f"   Profile path: {abs_profile_path}")
            print(f"   Profile Default exists: {(abs_profile_path / 'Default').exists()}")
            storage_state = abs_profile_path / "storage_state.json"
            print(f"   storage_state.json exists: {storage_state.exists()}")
            print()
            sys.exit(1)
        else:
            logger.info("Profile test passed - got actual content, not login page")
            print("✅ Profile test passed - authentication is working!")
            print()
    else:
        logger.warning(f"Profile test had errors: {test_result.error_message}")
        print(f"⚠️  Profile test had errors: {test_result.error_message}")
        print("   Continuing anyway...")
        print()

    try:
        # Step 3: Execute deep crawl and download files
        logger.info(f"Step 3: Executing deep crawl for {TARGET_URL}...")
        print("=" * 80)
        print("Executing Deep Crawl")
        print("=" * 80)
        print()
        print(f"URL: {TARGET_URL}")
        print(f"Max depth: {MAX_DEPTH}")
        print(f"Allowed domain: {ALLOWED_DOMAIN}")
        print(f"Output directory: {EXPORTS_DIR}")
        print()
        print("Crawling pages and downloading markdown files...")
        print("This may take a while depending on the number of pages...")
        print()

        # Ensure exports directory exists
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # Execute deep crawl and download files
        result = await download_pages_as_markdown(
            crawler=deps.crawler,
            start_url=TARGET_URL,
            max_depth=MAX_DEPTH,
            allowed_domains=[ALLOWED_DOMAIN],
            save_to_files=True,
            output_directory=EXPORTS_DIR,
            cookies=None,  # Profile handles authentication
        )

        # Step 4: Display results
        print("\n" + "=" * 80)
        print("Crawl Results")
        print("=" * 80)
        print()

        if result.get("success"):
            total_pages = result.get("total_pages", 0)
            file_paths = result.get("file_paths", [])

            print("✅ Deep crawl completed successfully!")
            print()
            print(f"   Pages crawled: {total_pages}")
            print(f"   Files saved: {len(file_paths)}")
            print(f"   Output directory: {EXPORTS_DIR}")
            print()

            if file_paths:
                print("   First 10 files:")
                for i, file_path in enumerate(file_paths[:10], 1):
                    print(f"      {i}. {file_path}")
                if len(file_paths) > 10:
                    print(f"      ... and {len(file_paths) - 10} more files")

            print()
            print("=" * 80)
            print("✅ Success! All crawled pages have been saved to /EXPORTS directory.")
            print("=" * 80)
            print()

            sys.exit(0)
        else:
            error = result.get("error", "Unknown error")
            print("❌ Deep crawl failed!")
            print()
            print(f"   Error: {error}")
            print()
            print("=" * 80)
            print("❌ Failed to crawl and download content")
            print("=" * 80)
            print()

            sys.exit(1)

    finally:
        # Cleanup
        logger.info("Cleaning up dependencies...")
        await deps.cleanup()
        logger.info("Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
