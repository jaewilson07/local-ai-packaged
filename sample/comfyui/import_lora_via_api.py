"""Sample script to import a LoRA model from Google Drive via the API endpoint.

This script uses the REST API to import a LoRA, which handles authentication
through Cloudflare Zero Trust (supports both internal and external URLs).
"""

import os
import sys

import requests

from sample.shared.auth_helpers import get_api_base_url, get_auth_headers, get_cloudflare_email


def import_lora_via_api(
    api_base_url: str,
    headers: dict[str, str],
    google_drive_file_id: str,
    lora_name: str,
    description: str | None = None,
    tags: list | None = None,
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

    print("Importing LoRA from Google Drive...")
    print(f"  URL: {url}")
    print(f"  File ID: {google_drive_file_id}")
    print(f"  Name: {lora_name}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        print("\n✅ Successfully imported LoRA!")
        print(f"   - LoRA ID: {result.get('id')}")
        print(f"   - Name: {result.get('name')}")
        print(f"   - Filename: {result.get('filename')}")
        print(f"   - MinIO Path: {result.get('minio_path')}")

        return result

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Detail: {error_detail}")
            except:
                print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None


def verify_in_me_data(api_base_url: str, headers: dict[str, str], lora_id: str) -> bool:
    """
    Verify that the imported LoRA appears in /api/me/data.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers (from get_auth_headers())
        lora_id: LoRA ID to verify

    Returns:
        True if LoRA found in /api/me/data, False otherwise
    """
    url = f"{api_base_url}/api/me/data"

    print("\nVerifying LoRA appears in /api/me/data...")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        result = response.json()
        loras_summary = result.get("loras", {})

        total_models = loras_summary.get("total_models", 0)
        models = loras_summary.get("models", [])

        print(f"  Total LoRA models: {total_models}")

        # Check if our LoRA is in the list
        for model in models:
            if model.get("id") == lora_id:
                print(f"  ✅ LoRA found in /api/me/data!")
                print(f"     - Name: {model.get('name')}")
                print(f"     - Filename: {model.get('filename')}")
                return True

        print(f"  ⚠️  LoRA not found in /api/me/data (may need to refresh)")
        return False

    except requests.exceptions.HTTPError as e:
        print(f"  ✗ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"     Detail: {error_detail}")
            except:
                print(f"     Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def list_loras(api_base_url: str, headers: dict[str, str], limit: int = 100, offset: int = 0):
    """
    List all LoRA models available to the authenticated user.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers (from get_auth_headers())
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        List of LoRA models or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/loras"

    params = {"limit": limit, "offset": offset}

    print("Listing LoRA models...")
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
            print(f"  ID: {model.get('id')}")
            print(f"  Name: {model.get('name')}")
            print(f"  Filename: {model.get('filename')}")
            print(
                f"  Size: {model.get('file_size', 0):,} bytes"
                if model.get("file_size")
                else "  Size: Unknown"
            )
            print(f"  Description: {model.get('description', 'N/A')}")
            print(f"  Tags: {', '.join(model.get('tags', []))}")
            print(f"  Created: {model.get('created_at')}")
            print("-" * 60)

        return models

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Detail: {error_detail}")
            except:
                print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None


def main():
    """Main function."""
    # Configuration
    try:
        api_base_url = get_api_base_url()
        headers = get_auth_headers()
    except ValueError as e:
        print("=" * 60)
        print("Authentication Error")
        print("=" * 60)
        print(f"\n{e}")
        print("\nTip: For local development, use internal network URL:")
        print("  export API_BASE_URL=http://lambda-server:8000")
        print("  (or http://localhost:8000 if running outside Docker)")
        return

    cloudflare_email = get_cloudflare_email()

    # Google Drive file ID
    google_drive_file_id = "1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7"
    lora_name = "jw_sample_lora"

    print("=" * 60)
    print("ComfyUI LoRA Import via API")
    print("=" * 60)
    print(f"API Base URL: {api_base_url}")
    if cloudflare_email:
        print(f"User Email: {cloudflare_email}")
    if headers:
        print("Authentication: Using Cloudflare Access JWT")
    else:
        print("Authentication: Internal network (no auth required)")
    print(f"Google Drive File ID: {google_drive_file_id}")
    print(f"LoRA Name: {lora_name}")
    print("=" * 60)

    # Import the LoRA
    result = import_lora_via_api(
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
        if lora_id:
            verify_in_me_data(api_base_url, headers, lora_id)

        # List all LoRAs
        print("\n")
        list_loras(api_base_url, headers)
    else:
        print("\n" + "=" * 60)
        print("Import failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
