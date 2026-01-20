"""Simple sample: Search Google Drive and list results.

This demonstrates basic Google Drive search functionality.

Usage:
    uv run sample/external/google_drive/google_drive_simple_search.py
"""

import sys
from pathlib import Path

# Add Lambda src to path for direct imports
project_root = Path(__file__).parent.parent.parent
lambda_src = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_src))

from services.external.google_drive import GoogleDriveService


def main():
    """Search Google Drive and display results."""

    # Initialize service
    service = GoogleDriveService()

    # Search query
    query = "copilot agent"

    print(f"🔍 Searching Google Drive for: '{query}'\n")

    # Search for files
    results = service.search_files(query=query, top_n=10)

    print(f"✅ Found {results.total_results} files\n")
    print(f"{'='*80}\n")

    # Display results
    for idx, file in enumerate(results.files, 1):
        print(f"[{idx}] {file.name}")
        print(f"    Type: {file.mime_type}")
        print(f"    ID: {file.id}")
        print(f"    Modified: {file.modified_time}")
        print(f"    URL: {file.web_view_link}")
        print()


if __name__ == "__main__":
    main()
