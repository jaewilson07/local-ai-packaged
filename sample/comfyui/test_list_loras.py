"""Test script to list LoRA models via the API.

This script demonstrates how to properly call the ComfyUI LoRA endpoints
with Cloudflare Access authentication.
"""

import os
import sys
import requests
from pathlib import Path


def list_loras(api_base_url: str, cf_jwt: str, limit: int = 100, offset: int = 0):
    """
    List all LoRA models available to the authenticated user.
    
    Args:
        api_base_url: Base URL of the API (e.g., "https://datacrew.space")
        cf_jwt: Cloudflare Access JWT token (from Cf-Access-Jwt-Assertion header)
        limit: Maximum number of results
        offset: Pagination offset
    
    Returns:
        List of LoRA models or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/loras"
    
    headers = {
        "Cf-Access-Jwt-Assertion": cf_jwt,
    }
    
    params = {
        "limit": limit,
        "offset": offset
    }
    
    print(f"Listing LoRA models...")
    print(f"  URL: {url}")
    print(f"  Using Cloudflare Access JWT")
    
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
                print(f"  Size: {model.get('file_size', 0):,} bytes" if model.get('file_size') else "  Size: Unknown")
                print(f"  Description: {model.get('description', 'N/A')}")
                print(f"  Tags: {', '.join(model.get('tags', []))}")
                print(f"  Created: {model.get('created_at')}")
                print("-" * 60)
        
        return models
        
    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        if e.response is not None:
            print(f"   Status Code: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                print(f"   Detail: {error_detail}")
            except:
                print(f"   Response: {e.response.text}")
            
            if e.response.status_code == 403:
                print("\n   ⚠️  This endpoint requires Cloudflare Access authentication.")
                print("   Make sure you're accessing through Cloudflare Access or")
                print("   include a valid Cf-Access-Jwt-Assertion header.")
        return None
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function."""
    # Configuration
    api_base_url = os.getenv("API_BASE_URL", "https://datacrew.space")
    cf_jwt = os.getenv("CF_ACCESS_JWT")
    
    if not cf_jwt:
        print("=" * 60)
        print("Error: CF_ACCESS_JWT environment variable not set")
        print("=" * 60)
        print("\nTo get your Cloudflare Access JWT:")
        print("1. Access your application through Cloudflare Access")
        print("2. Open browser DevTools (F12)")
        print("3. Go to Network tab")
        print("4. Make a request to any endpoint")
        print("5. Look for the 'Cf-Access-Jwt-Assertion' header in the request")
        print("6. Copy that value and set it as CF_ACCESS_JWT")
        print("\nOr use this script from a browser extension that can inject headers.")
        print("\nExample:")
        print("  export CF_ACCESS_JWT=your-jwt-token-here")
        print("  python sample/comfyui/test_list_loras.py")
        return
    
    print("=" * 60)
    print("ComfyUI LoRA List Test")
    print("=" * 60)
    print(f"API Base URL: {api_base_url}")
    print("=" * 60)
    
    # List LoRAs
    models = list_loras(api_base_url, cf_jwt)
    
    if models is not None:
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Test failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
