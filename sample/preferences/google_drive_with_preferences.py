"""Sample script demonstrating preference-aware Google Drive search.

This script shows how preferences enable seamless Google Drive searches
without requiring the user to specify folder_id on every request.

The flow:
1. User sets their preferred Google Drive folder via preferences API
2. Application code reads user's preference (or falls back to system default)
3. User performs searches without explicitly passing folder_id

Usage:
    python sample/preferences/google_drive_with_preferences.py
"""

import asyncio

# Use shared auth helpers
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.auth_helpers import get_api_base_url, get_auth_headers


def set_user_folder_preference(folder_id: str) -> bool:
    """Set user's preferred Google Drive folder.

    Args:
        folder_id: Google Drive folder ID

    Returns:
        True if successful
    """
    api_base_url = get_api_base_url()
    headers = get_auth_headers()

    response = requests.put(
        f"{api_base_url}/api/v1/preferences/google_drive.default_folder_id",
        json={"value": folder_id},
        headers=headers,
    )

    if response.status_code == 200:
        print(f"✓ Set default Google Drive folder to: {folder_id}")
        return True
    print(f"✗ Failed to set folder preference: {response.text}")
    return False


def get_user_folder_preference() -> str | None:
    """Get user's preferred Google Drive folder.

    Returns:
        Folder ID or None
    """
    api_base_url = get_api_base_url()
    headers = get_auth_headers()

    response = requests.get(
        f"{api_base_url}/api/v1/preferences/google_drive.default_folder_id", headers=headers
    )

    if response.status_code == 200:
        pref = response.json()
        print(f"Current default folder: {pref['value']} (source: {pref['source']})")
        return pref["value"]
    print(f"Could not retrieve folder preference: {response.text}")
    return None


async def main():
    """Main function demonstrating preference-aware Google Drive usage."""
    print("=" * 80)
    print("Preference-Aware Google Drive Search Demo")
    print("=" * 80)
    print()

    # Example: User workflow
    print("Step 1: Check current default folder preference")
    current_folder = get_user_folder_preference()
    print()

    print("Step 2: Update preference to custom folder")
    # In real usage, this would be a folder the user owns/has access to
    custom_folder_id = "my_work_folder_abc123"
    set_user_folder_preference(custom_folder_id)
    print()

    print("Step 3: Verify preference was updated")
    updated_folder = get_user_folder_preference()
    print()

    print("Step 4: Application code can now use user's preferred folder")
    print("When implementing Google Drive search endpoints, they would:")
    print("  1. Check if folder_id parameter was explicitly provided")
    print("  2. If not, fetch user's preference using PreferencesService")
    print("  3. Use preference value for the search")
    print()

    print("Example implementation in FastAPI route:")
    print("-" * 80)
    print(
        """
@router.post("/api/v1/google-drive/search")
async def search_files(
    folder_id: str | None = None,
    user: User = Depends(get_current_user),
    prefs: PreferencesService = Depends(get_preferences_service)
):
    # Resolve folder: explicit param → user pref → system default
    resolved_folder_id = folder_id or await prefs.get(
        user.id,
        "google_drive.default_folder_id",
        default="root"
    )

    # Use resolved folder for search
    google_drive = GoogleDrive(authenticator)
    files = await google_drive.search_files(folder_id=resolved_folder_id)
    return files
    """
    )
    print("-" * 80)
    print()

    print("Step 5: Reset to system default (optional)")
    api_base_url = get_api_base_url()
    headers = get_auth_headers()

    response = requests.delete(
        f"{api_base_url}/api/v1/preferences/google_drive.default_folder_id", headers=headers
    )
    if response.status_code == 200:
        print("✓ Deleted user preference, now using system default")

    print()
    print("=" * 80)
    print("Demo complete!")
    print()
    print("Key Benefits:")
    print("- Users don't need to specify folder_id on every API call")
    print("- Preferences persist across sessions")
    print("- Easy to override with explicit parameters when needed")
    print("- Falls back gracefully to system defaults")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
