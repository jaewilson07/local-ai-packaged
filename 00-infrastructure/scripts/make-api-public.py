#!/usr/bin/env python3
"""
Make api.datacrew.space publicly accessible by creating a Service Auth policy.
"""

import requests
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Configuration
ACCOUNT_ID = "7552371386451b222f527fa794562a37"
EMAIL = os.getenv("CLOUDFLARE_EMAIL", "")
API_KEY = os.getenv("CLOUDFLARE_GLOBAL_API_KEY", "")


def get_auth_headers():
    """Get authentication headers."""
    return {
        "X-Auth-Email": EMAIL.strip(),
        "X-Auth-Key": API_KEY.strip(),
        "Content-Type": "application/json",
    }


def create_public_api_application():
    """Create a self-hosted application for api.datacrew.space with public access."""
    
    # Check if application already exists
    list_url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/access/apps"
    response = requests.get(list_url, headers=get_auth_headers(), timeout=30)
    
    if response.status_code == 200:
        apps = response.json().get("result", [])
        for app in apps:
            if app.get("domain") == "api.datacrew.space":
                app_id = app["id"]
                print(f"✅ Found existing application: api.datacrew.space (ID: {app_id})")
                
                # Update to bypass policy
                update_payload = {
                    "name": "API - Lambda Server (Public)",
                    "domain": "api.datacrew.space",
                    "type": "self_hosted",
                    "session_duration": "24h",
                    "policies": [
                        {
                            "name": "Public Access",
                            "decision": "bypass",
                            "include": [
                                {"everyone": {}}
                            ]
                        }
                    ]
                }
                
                update_url = f"{list_url}/{app_id}"
                update_response = requests.put(update_url, json=update_payload, headers=get_auth_headers(), timeout=30)
                
                if update_response.status_code == 200:
                    print(f"✅ Updated api.datacrew.space to PUBLIC (bypass) access")
                    return True
                else:
                    print(f"❌ Failed to update: {update_response.text[:300]}")
                    return False
    
    # Create new application
    print("Creating new public API application...")
    payload = {
        "name": "API - Lambda Server (Public)",
        "domain": "api.datacrew.space",
        "type": "self_hosted",
        "session_duration": "24h",
        "policies": [
            {
                "name": "Public Access",
                "decision": "bypass",
                "include": [
                    {"everyone": {}}
                ]
            }
        ]
    }
    
    create_response = requests.post(list_url, json=payload, headers=get_auth_headers(), timeout=30)
    
    if create_response.status_code == 200:
        result = create_response.json().get("result", {})
        print(f"✅ Created public API application: {result.get('id')}")
        return True
    else:
        print(f"❌ Failed to create application: {create_response.text[:300]}")
        return False


def main():
    print("=" * 70)
    print("Making api.datacrew.space Publicly Accessible")
    print("=" * 70)
    
    if create_public_api_application():
        print("\n✅ Success! api.datacrew.space is now publicly accessible")
        print("\nTest it:")
        print("  curl https://api.datacrew.space/health")
    else:
        print("\n❌ Failed to configure public access")
        sys.exit(1)


if __name__ == "__main__":
    main()

