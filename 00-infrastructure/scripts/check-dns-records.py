#!/usr/bin/env python3
"""
Check DNS records for all datacrew.space subdomains
"""

import os
import sys
import requests
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    env_file = project_root / ".env"
    load_dotenv(env_file)
except ImportError:
    pass

# Configuration
DOMAIN = "datacrew.space"
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_EMAIL = os.getenv("CLOUDFLARE_EMAIL", "")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "")

SUBDOMAINS = [
    "n8n",
    "webui",
    "flowise",
    "langfuse",
    "supabase",
    "neo4j",
    "comfyui",
    "infisical",
    "ollama",
    "api"
]

def get_auth_headers():
    """Get authentication headers for Cloudflare API."""
    if CLOUDFLARE_API_TOKEN and CLOUDFLARE_API_TOKEN.strip():
        return {
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN.strip()}",
            "Content-Type": "application/json"
        }
    elif CLOUDFLARE_EMAIL and CLOUDFLARE_API_KEY:
        return {
            "X-Auth-Email": CLOUDFLARE_EMAIL.strip(),
            "X-Auth-Key": CLOUDFLARE_API_KEY.strip(),
            "Content-Type": "application/json"
        }
    else:
        print("❌ Cloudflare credentials not found!")
        sys.exit(1)

def get_zone_id(headers):
    """Get zone ID for the domain."""
    url = f"https://api.cloudflare.com/client/v4/zones?name={DOMAIN}"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("result"):
                return data["result"][0]["id"]
    except Exception as e:
        print(f"❌ Error getting zone ID: {e}")
    return None

def check_dns_record(headers, zone_id, subdomain):
    """Check DNS record for a subdomain."""
    hostname = f"{subdomain}.{DOMAIN}"
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={hostname}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                records = data.get("result", [])
                if records:
                    for record in records:
                        record_type = record.get("type")
                        content = record.get("content")
                        proxied = record.get("proxied", False)
                        
                        print(f"  {hostname}:")
                        print(f"    Type: {record_type}")
                        print(f"    Content: {content}")
                        print(f"    Proxied (🧡 orange cloud): {'✅ YES' if proxied else '❌ NO (DNS only)'}")
                        
                        if not proxied:
                            print(f"    ⚠️  WARNING: Record should be proxied for Cloudflare Tunnel!")
                        
                        return True
                else:
                    print(f"  ❌ {hostname}: No DNS record found!")
                    return False
    except Exception as e:
        print(f"  ❌ Error checking {hostname}: {e}")
    
    return False

def main():
    print("=" * 60)
    print("DNS Records Check for datacrew.space")
    print("=" * 60)
    
    headers = get_auth_headers()
    print("✅ Cloudflare API credentials found")
    
    zone_id = get_zone_id(headers)
    if not zone_id:
        print("❌ Could not find zone ID")
        sys.exit(1)
    
    print(f"✅ Found zone ID: {zone_id}\n")
    
    print("=" * 60)
    print("Checking DNS Records")
    print("=" * 60)
    
    for subdomain in SUBDOMAINS:
        check_dns_record(headers, zone_id, subdomain)
        print()

if __name__ == "__main__":
    main()

