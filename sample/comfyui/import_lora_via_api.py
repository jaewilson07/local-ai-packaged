"""Sample script to import a LoRA model from Google Drive via the API endpoint.

This script uses the REST API to import a LoRA, which handles authentication
through the FastAPI auth system.
"""

import os
import sys
import requests
import json
from pathlib import Path


def import_lora_via_api(
    api_base_url: str,
    auth_token: str,
    google_drive_file_id: str,
    lora_name: str,
    description: str = None,
    tags: list = None
):
    """
    Import a LoRA model from Google Drive using the API endpoint.
    
    Args:
        api_base_url: Base URL of the API (e.g., "http://localhost:8000")
        auth_token: JWT authentication token
        google_drive_file_id: Google Drive file ID
        lora_name: Name for the LoRA model
        description: Optional description
        tags: Optional list of tags
    
    Returns:
        Response data or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/loras/import-from-google-drive"
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "google_drive_file_id": google_drive_file_id,
        "name": lora_name,
    }
    
    if description:
        payload["description"] = description
    
    if tags:
        payload["tags"] = tags
    
    print(f"Importing LoRA from Google Drive...")
    print(f"  URL: {url}")
    print(f"  File ID: {google_drive_file_id}")
    print(f"  Name: {lora_name}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"\n✅ Successfully imported LoRA!")
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


def list_loras(api_base_url: str, auth_token: str, limit: int = 100, offset: int = 0):
    """
    List all LoRA models available to the authenticated user.
    
    Args:
        api_base_url: Base URL of the API
        auth_token: JWT authentication token
        limit: Maximum number of results
        offset: Pagination offset
    
    Returns:
        List of LoRA models or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/loras"
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
    }
    
    params = {
        "limit": limit,
        "offset": offset
    }
    
    print(f"Listing LoRA models...")
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
            print(f"  Size: {model.get('file_size', 0):,} bytes" if model.get('file_size') else "  Size: Unknown")
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
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    auth_token = os.getenv("AUTH_TOKEN")
    
    if not auth_token:
        print("Error: AUTH_TOKEN environment variable not set")
        print("Get your JWT token from your auth system and set it with:")
        print("  export AUTH_TOKEN=your-jwt-token")
        return
    
    # Google Drive file ID
    google_drive_file_id = "1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7"
    lora_name = "jw_sample_lora"
    
    print("=" * 60)
    print("ComfyUI LoRA Import via API")
    print("=" * 60)
    print(f"API Base URL: {api_base_url}")
    print(f"Google Drive File ID: {google_drive_file_id}")
    print(f"LoRA Name: {lora_name}")
    print("=" * 60)
    
    # Import the LoRA
    result = import_lora_via_api(
        api_base_url=api_base_url,
        auth_token=auth_token,
        google_drive_file_id=google_drive_file_id,
        lora_name=lora_name,
        description="Sample LoRA imported from Google Drive",
        tags=["sample", "imported"]
    )
    
    if result:
        print("\n" + "=" * 60)
        print("Import completed successfully!")
        print("=" * 60)
        
        # List all LoRAs
        print("\n")
        list_loras(api_base_url, auth_token)
    else:
        print("\n" + "=" * 60)
        print("Import failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
