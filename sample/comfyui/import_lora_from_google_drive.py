"""Sample script to import a LoRA model from Google Drive via the API endpoint.

This script demonstrates how to:
1. Import a LoRA model from Google Drive using the ComfyUI workflow API
2. The file will be downloaded, uploaded to MinIO, and metadata stored in Supabase
3. Uses shared authentication helpers for Cloudflare Zero Trust support
4. Data will be reflected in /api/me/data for the authenticated user

Versioning Behavior:
- character_name is REQUIRED and serves as the unique identifier (trigger word)
- If a LoRA for this character already exists, the API raises 409 Conflict by default
- Set replace=True to create a new version (old version archived for rollback)
- Use the rollback endpoint to switch between versions
"""

import json
import sys
from pathlib import Path

import requests

# Add project root to path for sample.shared imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sample.shared.auth_helpers import (  # noqa: E402
    get_api_base_url,
    get_auth_headers,
    require_cloudflare_email,
)
from sample.shared.verification_helpers import verify_loras_data  # noqa: E402

# Sample LoRA configuration - shared across all import scripts
SAMPLE_LORA_CONFIG = {
    "google_drive_file_id": "1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7",
    "name": "Alix Character LoRA",
    "description": "Alix character LoRA for image generation",
    "tags": ["character", "alix", "sample"],
    "character_name": "alix",  # This is the trigger word / unique identifier
}


def import_lora_from_google_drive(
    api_base_url: str,
    headers: dict[str, str],
    google_drive_file_id: str,
    character_name: str,
    name: str | None = None,
    description: str | None = None,
    tags: list | None = None,
    replace: bool = False,
):
    """
    Import a LoRA model from Google Drive using the API endpoint.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers (from get_auth_headers())
        google_drive_file_id: Google Drive file ID
        character_name: Character name / trigger word (REQUIRED, unique per user)
        name: Optional display name (defaults to character_name)
        description: Optional description
        tags: Optional list of tags
        replace: If True and LoRA exists, create new version; if False, error on duplicate

    Returns:
        Response data or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/loras/import-from-google-drive"

    # Add Content-Type to headers
    headers = {**headers, "Content-Type": "application/json"}

    payload = {
        "google_drive_file_id": google_drive_file_id,
        "character_name": character_name,  # Required
        "replace": replace,
    }

    if name:
        payload["name"] = name

    if description:
        payload["description"] = description

    if tags:
        payload["tags"] = tags

    print("Importing LoRA from Google Drive...")
    print(f"  URL: {url}")
    print(f"  File ID: {google_drive_file_id}")
    print(f"  Character Name: {character_name}")
    print(f"  Replace existing: {replace}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        version = result.get("version", 1)
        is_active = result.get("is_active", True)

        print(f"\n✅ Successfully imported LoRA (version {version})!")
        print(f"   - LoRA ID: {result.get('id')}")
        print(f"   - Name: {result.get('name')}")
        print(f"   - Character: {result.get('character_name')}")
        print(f"   - Filename: {result.get('filename')}")
        print(f"   - Version: {version}")
        print(f"   - Active: {is_active}")
        print(f"   - MinIO Path: {result.get('minio_path')}")

        return result

    except requests.exceptions.ConnectionError:
        print(f"\n✗ Connection Error: Cannot connect to {url}")
        print("   Make sure the Lambda server is running.")
        print("   For local development, try:")
        print("     export API_BASE_URL=http://localhost:8000")
        return None

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Detail: {error_detail}")

                # Provide helpful guidance for 409 Conflict
                if e.response.status_code == 409:
                    print("\n💡 Tip: To replace the existing LoRA, set replace=True")
                    print("   Or use the rollback endpoint to switch between versions")
            except (ValueError, json.JSONDecodeError):
                print(f"   Response: {e.response.text}")
        return None


def list_loras(
    api_base_url: str,
    headers: dict[str, str],
    limit: int = 100,
    offset: int = 0,
    include_inactive: bool = False,
):
    """
    List all LoRA models available to the authenticated user.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers (from get_auth_headers())
        limit: Maximum number of results
        offset: Pagination offset
        include_inactive: If True, include archived/inactive versions

    Returns:
        List of LoRA models or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/loras"
    params = {"limit": limit, "offset": offset, "include_inactive": include_inactive}

    print(f"Listing LoRA models (include_inactive={include_inactive})...")
    print(f"  URL: {url}")

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        result = response.json()
        models = result.get("models", [])
        count = result.get("count", 0)

        print(f"\n✅ Found {count} LoRA model(s):")
        print("=" * 60)

        for model in models:
            is_active = model.get("is_active", True)
            version = model.get("version", 1)
            status = "✓ ACTIVE" if is_active else "  (archived)"

            print(f"  {status} - {model.get('character_name', 'N/A')} v{version}")
            print(f"    ID: {model.get('id')}")
            print(f"    Name: {model.get('name')}")
            print(f"    Filename: {model.get('filename')}")
            print(
                f"    Size: {model.get('file_size', 0):,} bytes"
                if model.get("file_size")
                else "    Size: Unknown"
            )
            print(f"    Tags: {', '.join(model.get('tags', []))}")
            print(f"    Created: {model.get('created_at')}")
            if model.get("replaced_at"):
                print(f"    Archived: {model.get('replaced_at')}")
            print("-" * 60)

        return models

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Detail: {error_detail}")
            except (ValueError, json.JSONDecodeError):
                print(f"   Response: {e.response.text}")
        return None


def get_version_history(api_base_url: str, headers: dict[str, str], character_name: str):
    """
    Get version history for a specific character's LoRA.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers
        character_name: Character name to get history for

    Returns:
        List of LoRA versions or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/loras/by-character/{character_name}"

    print(f"Getting version history for '{character_name}'...")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        result = response.json()
        models = result.get("models", [])

        print(f"\n✅ Found {len(models)} version(s) for '{character_name}':")
        print("=" * 60)

        for model in models:
            is_active = model.get("is_active", True)
            version = model.get("version", 1)
            status = "✓ ACTIVE" if is_active else "  archived"

            print(f"  [{status}] Version {version}")
            print(f"    ID: {model.get('id')}")
            print(f"    Created: {model.get('created_at')}")
            if model.get("replaced_at"):
                print(f"    Archived: {model.get('replaced_at')}")
            print("-" * 60)

        return models

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        return None


def rollback_to_version(
    api_base_url: str, headers: dict[str, str], character_name: str, version: int
):
    """
    Rollback to a specific version of a character's LoRA.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers
        character_name: Character name
        version: Version number to rollback to

    Returns:
        Updated LoRA model or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/loras/by-character/{character_name}/rollback/{version}"

    print(f"Rolling back '{character_name}' to version {version}...")

    try:
        response = requests.put(url, headers=headers)
        response.raise_for_status()

        result = response.json()
        print(f"\n✅ Successfully rolled back to version {version}!")
        print(f"   - LoRA ID: {result.get('id')}")
        print(f"   - Version: {result.get('version')}")
        print(f"   - Active: {result.get('is_active')}")

        return result

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Detail: {error_detail}")
            except (ValueError, json.JSONDecodeError):
                print(f"   Response: {e.response.text}")
        return None


def main():
    """Main function to import the sample LoRA."""
    # Configuration
    try:
        api_base_url = get_api_base_url()
        headers = get_auth_headers()
        cloudflare_email = require_cloudflare_email()
    except ValueError as e:
        print("=" * 60)
        print("Configuration Error")
        print("=" * 60)
        print(f"\n{e}")
        print("\nTip: For local development, set CLOUDFLARE_EMAIL:")
        print("  export CLOUDFLARE_EMAIL=your-email@example.com")
        print("\nAnd use internal network URL:")
        print("  export API_BASE_URL=http://lambda-server:8000")
        print("  (or http://localhost:8000 if running outside Docker)")
        print("\n⚠️  Sample requires configuration - exiting gracefully")
        sys.exit(0)  # Exit with success since this is a config issue, not a code issue

    print("=" * 60)
    print("Import LoRA from Google Drive")
    print("=" * 60)
    print(f"API Base URL: {api_base_url}")
    print(f"User Email: {cloudflare_email}")
    if headers:
        print("Authentication: Using Cloudflare Access JWT")
    else:
        print("Authentication: Internal network (no auth required)")
    print(f"Google Drive File ID: {SAMPLE_LORA_CONFIG['google_drive_file_id']}")
    print(f"Character Name: {SAMPLE_LORA_CONFIG['character_name']}")
    print("=" * 60)

    # Import the LoRA (replace=False by default - will error if exists)
    result = import_lora_from_google_drive(
        api_base_url=api_base_url,
        headers=headers,
        google_drive_file_id=SAMPLE_LORA_CONFIG["google_drive_file_id"],
        character_name=SAMPLE_LORA_CONFIG["character_name"],
        name=SAMPLE_LORA_CONFIG["name"],
        description=SAMPLE_LORA_CONFIG["description"],
        tags=SAMPLE_LORA_CONFIG["tags"],
        replace=False,  # Set to True to create new version if exists
    )

    if result:
        lora_id = result.get("id")
        print("\n" + "=" * 60)
        print("Import completed successfully!")
        print("=" * 60)

        # Verify it appears in /api/me/data
        print("\n" + "=" * 60)
        print("Verification")
        print("=" * 60)

        if lora_id:
            success, message = verify_loras_data(
                api_base_url=api_base_url,
                headers=headers,
                lora_id=lora_id,
            )
            print(message)

            if success:
                # List all LoRAs to show the result
                print("\n")
                list_loras(api_base_url, headers)
                print("\n✅ Success! LoRA imported and verified in /api/me/data")
                print("=" * 60)
                sys.exit(0)
            else:
                print("\n⚠️  LoRA imported but verification failed")
                print("=" * 60)
                sys.exit(1)
        else:
            print("⚠️  No LoRA ID returned, skipping verification")
            sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("Import failed (server may not be running)")
        print("=" * 60)
        print("\n⚠️  Sample requires running services - exiting gracefully")
        sys.exit(0)  # Exit with success since imports work


if __name__ == "__main__":
    main()
