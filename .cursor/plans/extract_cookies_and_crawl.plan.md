# Plan: Extract Cookies and Execute Crawl Script

## Objective
Create a Python script that automatically extracts cookies from the user's browser and executes a crawl operation to scrape `https://community.datacrew.space/settings/posts` and ingest it into MongoDB RAG.

## Target URL
- `https://community.datacrew.space/settings/posts`

## Implementation Plan

### 1. Create Script: `sample/crawl4ai_rag/extract_and_crawl.py`

**Purpose**: Automatically extract cookies and execute authenticated crawl

**Key Components**:

1. **Cookie Extraction Function** (`extract_cookies_with_playwright`)
   - Use Playwright with persistent browser context to access existing Chrome/Chromium sessions
   - Find Chrome user data directory (platform-specific):
     - Linux: `~/.config/google-chrome` or `~/.config/chromium`
     - macOS: `~/Library/Application Support/Google/Chrome`
     - Windows: `%LOCALAPPDATA%\Google\Chrome\User Data`
   - Launch browser with `user_data_dir` parameter
   - Navigate to target URL
   - Extract cookies from browser context using `context.cookies()`
   - Format cookies as string: `"name1=value1; name2=value2"`
   - Return cookie string or None if extraction fails

2. **Manual Cookie Input Fallback** (`get_cookies_manually`)
   - Prompt user to paste cookie string
   - Validate cookie format
   - Return cookie string

3. **Main Function** (`main`)
   - Try automatic cookie extraction first
   - Fall back to manual input if automatic extraction fails
   - Initialize `Crawl4AIDependencies`
   - Create run context using `create_run_context` helper
   - Call `crawl_and_ingest_single_page` with extracted cookies
   - Display results and handle errors

**Dependencies**:
- `playwright` (for browser automation)
- `server.projects.crawl4ai_rag.dependencies.Crawl4AIDependencies`
- `server.projects.crawl4ai_rag.tools.crawl_and_ingest_single_page`
- `server.projects.shared.context_helpers.create_run_context`

**Error Handling**:
- Handle Playwright launch failures (browser not found, user data directory not accessible)
- Handle cookie extraction failures (no cookies found, navigation timeout)
- Handle crawl failures (network errors, authentication failures)
- Provide clear error messages and fallback options

**Script Structure**:
```python
#!/usr/bin/env python3
"""Extract cookies and execute authenticated crawl."""

import asyncio
import logging
import platform
from pathlib import Path
import sys

# Add server to path
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

from playwright.async_api import async_playwright
from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies
from server.projects.crawl4ai_rag.tools import crawl_and_ingest_single_page
from server.projects.shared.context_helpers import create_run_context

# Configure logging
logging.basicConfig(...)
logger = logging.getLogger(__name__)

TARGET_URL = "https://community.datacrew.space/settings/posts"

def find_chrome_user_data_dir() -> Path | None:
    """Find Chrome/Chromium user data directory."""
    # Platform-specific paths
    ...

async def extract_cookies_with_playwright(url: str) -> str | None:
    """Extract cookies using Playwright with persistent browser context."""
    # Launch browser with persistent context
    # Navigate to URL
    # Extract cookies
    # Return cookie string
    ...

def get_cookies_manually() -> str:
    """Prompt user for manual cookie input."""
    # Prompt and validate
    ...

async def main():
    """Main function: extract cookies and execute crawl."""
    # Try automatic extraction
    # Fall back to manual if needed
    # Initialize dependencies
    # Execute crawl
    # Display results
    ...

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Implementation Details

**Cookie Extraction Strategy**:
1. **Automatic (Preferred)**:
   - Use Playwright's `launch_persistent_context()` with Chrome user data directory
   - This reuses existing browser sessions and cookies
   - Navigate to target URL
   - Extract cookies using `context.cookies(url)`
   - Format as cookie string

2. **Manual (Fallback)**:
   - If automatic extraction fails, prompt user to:
     - Open browser DevTools (F12)
     - Go to Console tab
     - Run the `extract_cookies.js` script (already created)
     - Paste the cookie string

**Crawl Execution**:
- Use existing `crawl_and_ingest_single_page` function from `04-lambda/server/projects/crawl4ai_rag/tools.py`
- Pass extracted cookies as `cookies` parameter
- Use default chunk settings (chunk_size=1000, chunk_overlap=200)
- Display crawl results (success, pages crawled, chunks created, document ID)

**Error Handling**:
- **Playwright Launch Failures**: Catch `PlaywrightException`, log error, fall back to manual input
- **Cookie Extraction Failures**: Catch navigation timeouts, log error, fall back to manual input
- **Crawl Failures**: Catch exceptions from `crawl_and_ingest_single_page`, log error, exit with code 1
- **Dependency Initialization Failures**: Catch connection errors, log error, exit with code 1

### 3. File Locations

- **New Script**: `sample/crawl4ai_rag/extract_and_crawl.py`
- **Reference Files**:
  - `sample/crawl4ai_rag/single_page_crawl_example.py` (pattern to follow)
  - `04-lambda/server/projects/crawl4ai_rag/tools.py` (crawl function)
  - `sample/crawl4ai_rag/extract_cookies.js` (manual extraction script)

### 4. Testing Strategy

1. **Test Automatic Extraction**:
   - Ensure Chrome/Chromium is installed
   - Ensure user is logged into `community.datacrew.space` in Chrome
   - Run script and verify cookies are extracted

2. **Test Manual Fallback**:
   - Simulate Playwright failure (wrong user data directory)
   - Verify script prompts for manual input
   - Test with manually pasted cookies

3. **Test Crawl Execution**:
   - Verify crawl succeeds with extracted cookies
   - Verify content is ingested into MongoDB RAG
   - Verify results are displayed correctly

### 5. Success Criteria

- Script successfully extracts cookies (automatic or manual)
- Script executes crawl with extracted cookies
- Content is successfully ingested into MongoDB RAG
- Results are displayed clearly
- Error handling works for all failure scenarios
- Script follows patterns from existing sample scripts

## Notes

- Playwright persistent context requires Chrome/Chromium to be installed
- User must be logged into the target site in Chrome/Chromium for automatic extraction to work
- Manual fallback ensures script works even if automatic extraction fails
- Script uses existing crawl infrastructure, no changes needed to core crawl functions
