#!/usr/bin/env python3
"""
Add DNS records for api.datacrew.space and postman.datacrew.space
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
ZONE_ID = "77d3277e791671bfe46f0bac478a6f5b"  # datacrew.space zone
TUNNEL_HOSTNAME = "bff69fdf-293d-4511-b318-7e55e0ca22de.cfargotunnel.com"

# Get API Token
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
EMAIL = os.getenv("CLOUDFLARE_EMAIL", "")
API_KEY = os.getenv("CLOUDFLARE_GLOBAL_API_KEY", "")


def get_auth_headers():
    """Get authentication headers for Cloudflare API."""
    # Prefer Email + Global API Key for DNS operations (API Token often lacks DNS permissions)
    if EMAIL and EMAIL.strip() and API_KEY and API_KEY.strip():
        print(f"🔑 Using Email + Global API Key authentication")
        return {
            "X-Auth-Email": EMAIL.strip(),
            "X-Auth-Key": API_KEY.strip(),
            "Content-Type": "application/json",
        }
    elif API_TOKEN and API_TOKEN.strip():
        print(f"🔑 Using API Token authentication")
        return {
            "Authorization": f"Bearer {API_TOKEN.strip()}",
            "Content-Type": "application/json",
        }
    else:
        print("❌ Error: No valid Cloudflare credentials found")
        print("   Set either (CLOUDFLARE_EMAIL + CLOUDFLARE_GLOBAL_API_KEY) or CLOUDFLARE_API_TOKEN")
        sys.exit(1)


def create_dns_record(name: str, comment: str):
    """Create a CNAME DNS record."""
    url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records"
    
    payload = {
        "type": "CNAME",
        "name": name,
        "content": TUNNEL_HOSTNAME,
        "ttl": 1,  # Auto
        "proxied": True,
        "comment": comment,
    }
    
    print(f"Creating DNS record: {name}.datacrew.space → {TUNNEL_HOSTNAME}")
    
    try:
        response = requests.post(url, json=payload, headers=get_auth_headers(), timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("success"):
            record = result.get("result", {})
            print(f"✅ Successfully created: {record.get('name')} (ID: {record.get('id')})")
            return True
        else:
            errors = result.get("errors", [])
            # Check if record already exists
            if any("already exists" in str(err).lower() for err in errors):
                print(f"⚠️  Record already exists: {name}.datacrew.space")
                return True
            else:
                print(f"❌ Failed to create record: {errors}")
                return False
                
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return False


def main():
    """Create DNS records for api and postman subdomains."""
    print("=" * 60)
    print("Adding DNS Records to Cloudflare")
    print("=" * 60)
    
    records = [
        ("api", "Lambda Server API"),
        ("postman", "Postman Documentation Redirect"),
    ]
    
    success_count = 0
    for name, comment in records:
        if create_dns_record(name, comment):
            success_count += 1
        print()
    
    print("=" * 60)
    print(f"✅ Successfully configured {success_count}/{len(records)} DNS records")
    print("=" * 60)
    
    if success_count == len(records):
        print("\n🎉 All DNS records are configured!")
        print("\nYour subdomains:")
        print("  • https://api.datacrew.space → Lambda Server")
        print("  • https://postman.datacrew.space → Postman Docs")
        print("\nDNS propagation is usually instant with Cloudflare proxy.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

