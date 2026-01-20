"""Sample script demonstrating user preferences management.

This script shows how to:
1. List all available preference categories
2. Get all preferences (system defaults + user overrides)
3. Update user-specific preferences
4. Delete user preferences (revert to system defaults)

Usage:
    python sample/preferences/manage_preferences.py
"""

import asyncio

# Use shared auth helpers for consistent authentication
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.auth_helpers import get_api_base_url, get_auth_headers


async def main():
    """Main function to demonstrate preferences API."""
    api_base_url = get_api_base_url()
    headers = get_auth_headers()

    print("=" * 80)
    print("User Preferences Management Demo")
    print("=" * 80)
    print()

    # 1. List all available categories
    print("1. Getting available preference categories...")
    response = requests.get(f"{api_base_url}/api/v1/preferences/categories", headers=headers)
    if response.status_code == 200:
        categories = response.json()["categories"]
        print(f"   Available categories: {', '.join(categories)}")
    else:
        print(f"   Error: {response.status_code} - {response.text}")
        return

    print()

    # 2. Get all preferences for a specific category
    print("2. Getting Google Drive preferences...")
    response = requests.get(
        f"{api_base_url}/api/v1/preferences", params={"category": "google_drive"}, headers=headers
    )
    if response.status_code == 200:
        prefs = response.json()["preferences"]
        print("   Current Google Drive preferences:")
        for key, value in prefs.items():
            print(f"     - {key}: {value}")
    else:
        print(f"   Error: {response.status_code} - {response.text}")

    print()

    # 3. Get preference definitions (to see what's configurable)
    print("3. Getting preference definitions for 'llm' category...")
    response = requests.get(
        f"{api_base_url}/api/v1/preferences/definitions",
        params={"category": "llm"},
        headers=headers,
    )
    if response.status_code == 200:
        definitions = response.json()
        print("   Available LLM preferences:")
        for defn in definitions:
            print(f"     - {defn['key']}: {defn['description']}")
            print(f"       Type: {defn['data_type']}, Default: {defn['default_value']}")
    else:
        print(f"   Error: {response.status_code} - {response.text}")

    print()

    # 4. Update a preference
    print("4. Updating Google Drive default folder preference...")
    response = requests.put(
        f"{api_base_url}/api/v1/preferences/google_drive.default_folder_id",
        json={"value": "my_custom_folder_id"},
        headers=headers,
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Updated: {result['key']} = {result['value']}")
    else:
        print(f"   Error: {response.status_code} - {response.text}")

    print()

    # 5. Get specific preference with source tracking
    print("5. Getting updated preference to verify source...")
    response = requests.get(
        f"{api_base_url}/api/v1/preferences/google_drive.default_folder_id", headers=headers
    )
    if response.status_code == 200:
        pref = response.json()
        print(f"   Key: {pref['key']}")
        print(f"   Value: {pref['value']}")
        print(f"   Source: {pref['source']} (user override is active)")
    else:
        print(f"   Error: {response.status_code} - {response.text}")

    print()

    # 6. Update multiple preferences (LLM settings)
    print("6. Updating multiple LLM preferences...")
    llm_prefs = {
        "llm.default_model": "llama3.1:70b",
        "llm.temperature": 0.8,
        "llm.max_tokens": 4096,
    }
    for key, value in llm_prefs.items():
        response = requests.put(
            f"{api_base_url}/api/v1/preferences/{key}", json={"value": value}, headers=headers
        )
        if response.status_code == 200:
            print(f"   ✓ Updated: {key} = {value}")
        else:
            print(f"   ✗ Failed to update {key}: {response.text}")

    print()

    # 7. Get all preferences to see changes
    print("7. Getting all current preferences...")
    response = requests.get(f"{api_base_url}/api/v1/preferences", headers=headers)
    if response.status_code == 200:
        all_prefs = response.json()["preferences"]
        print(f"   Total preferences: {len(all_prefs)}")
        print("   Sample (first 5):")
        for key, value in list(all_prefs.items())[:5]:
            print(f"     - {key}: {value}")
    else:
        print(f"   Error: {response.status_code} - {response.text}")

    print()

    # 8. Delete a preference (revert to default)
    print("8. Deleting Google Drive preference (revert to system default)...")
    response = requests.delete(
        f"{api_base_url}/api/v1/preferences/google_drive.default_folder_id", headers=headers
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Deleted: {result['key']}")
        print("   User will now use system default ('root')")
    else:
        print(f"   Error: {response.status_code} - {response.text}")

    print()

    # 9. Verify deletion
    print("9. Verifying preference reverted to system default...")
    response = requests.get(
        f"{api_base_url}/api/v1/preferences/google_drive.default_folder_id", headers=headers
    )
    if response.status_code == 200:
        pref = response.json()
        print(f"   Value: {pref['value']}")
        print(f"   Source: {pref['source']} (using system default)")
    else:
        print(f"   Error: {response.status_code} - {response.text}")

    print()
    print("=" * 80)
    print("Demo complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
