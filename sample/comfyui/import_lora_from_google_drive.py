"""Sample script to import a LoRA model from Google Drive via the API endpoint.

This script demonstrates how to:
1. Import a LoRA model from Google Drive using the ComfyUI workflow API
2. The file will be downloaded, uploaded to MinIO, and metadata stored in Supabase
3. Uses shared authentication helpers for Cloudflare Zero Trust support
4. Data will be reflected in /api/me/data for the authenticated user
"""

import json
import sys

import requests

from sample.shared.auth_helpers import (
    get_api_base_url,
    get_auth_headers,
    require_cloudflare_email,
)
from sample.shared.verification_helpers import verify_loras_data


def import_lora_from_google_drive(
    api_base_url: str,
    headers: dict[str, str],
    google_drive_file_id: str,
    lora_name: str,
    description: str | None = None,
    tags: list | None = None,
    character_name: str | None = None,
):
    """
    Import a LoRA model from Google Drive using the API endpoint.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers (from get_auth_headers())
        google_drive_file_id: Google Drive file ID
        lora_name: Name for the LoRA model
        description: Optional description
        tags: Optional list of tags
        character_name: Optional character name for character-based LoRA selection

    Returns:
        Response data or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/loras/import-from-google-drive"

    # Add Content-Type to headers
    headers = {**headers, "Content-Type": "application/json"}

    payload = {
        "google_drive_file_id": google_drive_file_id,
        "name": lora_name,
    }

    if description:
        payload["description"] = description

    if tags:
        payload["tags"] = tags

    if character_name:
        payload["character_name"] = character_name

    print("Importing LoRA from Google Drive...")
    print(f"  URL: {url}")
    print(f"  File ID: {google_drive_file_id}")
    print(f"  Name: {lora_name}")
    if character_name:
        print(f"  Character Name: {character_name}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        print("\n✅ Successfully imported LoRA!")
        print(f"   - LoRA ID: {result.get('id')}")
        print(f"   - Name: {result.get('name')}")
        print(f"   - Filename: {result.get('filename')}")
        print(f"   - MinIO Path: {result.get('minio_path')}")
        if result.get("character_name"):
            print(f"   - Character Name: {result.get('character_name')}")

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
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
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
        print("\nTip: For local development, use internal network URL:")
        print("  export API_BASE_URL=http://lambda-server:8000")
        print("  (or http://localhost:8000 if running outside Docker)")
        return

    # Google Drive file ID from the URL
    google_drive_file_id = "1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7"

    # LoRA name
    lora_name = "jw_sample_lora"

    print("=" * 60)
    print("Import LoRA from Google Drive")
    print("=" * 60)
    print(f"API Base URL: {api_base_url}")
    print(f"User Email: {cloudflare_email}")
    if headers:
        print("Authentication: Using Cloudflare Access JWT")
    else:
        print("Authentication: Internal network (no auth required)")
    print(f"Google Drive File ID: {google_drive_file_id}")
    print(f"LoRA Name: {lora_name}")
    print("=" * 60)

    # Import the LoRA
    result = import_lora_from_google_drive(
        api_base_url=api_base_url,
        headers=headers,
        google_drive_file_id=google_drive_file_id,
        lora_name=lora_name,
        description="Sample LoRA imported from Google Drive",
        tags=["sample", "imported"],
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
        print("Import failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
