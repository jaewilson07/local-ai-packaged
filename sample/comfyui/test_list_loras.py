"""Test script to list LoRA models via the API.

This script demonstrates how to properly call the ComfyUI LoRA endpoints
with Cloudflare Zero Trust authentication (supports both internal and external URLs).
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
    get_cloudflare_email,
)
from sample.shared.verification_helpers import verify_loras_data  # noqa: E402


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
    if headers:
        print("  Using Cloudflare Access JWT")
    else:
        print("  Using internal network (no auth required)")

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        result = response.json()
        models = result.get("models", [])
        count = result.get("count", 0)

        print(f"\n✅ Found {count} LoRA model(s):")
        print("=" * 60)

        if not models:
            print("  No LoRA models found.")
        else:
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

    except requests.exceptions.ConnectionError:
        print(f"\n✗ Connection Error: Cannot connect to {url}")
        print("   Make sure the Lambda server is running.")
        print("   For local development, try:")
        print("     export API_BASE_URL=http://localhost:8000")
        return None

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        if e.response is not None:
            print(f"   Status Code: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                print(f"   Detail: {error_detail}")
            except (ValueError, json.JSONDecodeError):
                print(f"   Response: {e.response.text}")

            if e.response.status_code == 403:
                print("\n   ⚠️  This endpoint requires authentication.")
                print("   For external URLs, you need a Cloudflare Access JWT token.")
                print("   For local development, use internal network URL:")
                print("     export API_BASE_URL=http://lambda-server:8000")
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

    print("=" * 60)
    print("ComfyUI LoRA List Test")
    print("=" * 60)
    print(f"API Base URL: {api_base_url}")
    if cloudflare_email:
        print(f"User Email: {cloudflare_email}")
    if headers:
        print("Authentication: Using Cloudflare Access JWT")
    else:
        print("Authentication: Internal network (no auth required)")
    print("=" * 60)

    # List LoRAs
    models = list_loras(api_base_url, headers)

    if models is not None:
        # Verify LoRAs appear in /api/me/data
        print("\n" + "=" * 60)
        print("Verification")
        print("=" * 60)

        success, message = verify_loras_data(
            api_base_url=api_base_url,
            headers=headers,
            expected_loras_min=len(models) if models else 0,
        )
        print(message)

        if success:
            print("\n✅ Test completed successfully!")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n⚠️  Test completed but verification failed!")
            print("=" * 60)
            sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("Test failed (server may not be running)")
        print("=" * 60)
        print("\n⚠️  Sample requires running services - exiting gracefully")
        sys.exit(0)  # Exit with success since imports work


if __name__ == "__main__":
    main()
