#!/usr/bin/env python3
"""
configure_tunnel_hostnames.py

Configure Cloudflare Tunnel public hostnames via API.
"""

import requests
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

# Configuration
DOMAIN = "datacrew.space"
TUNNEL_ID = "3885d13d-2d48-47ee-811c-878920be4d69"
ZONE_ID = "77d3277e791671bfe46f0bac478a6f5b"

# For Global API Key
CLOUDFLARE_EMAIL = os.getenv("CLOUDFLARE_EMAIL", "")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "")
# For API Token
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")

# Services
SERVICES = [
    {"hostname": "n8n.datacrew.space", "service": "http://caddy:80"},
    {"hostname": "webui.datacrew.space", "service": "http://caddy:80"},
    {"hostname": "flowise.datacrew.space", "service": "http://caddy:80"},
    {"hostname": "langfuse.datacrew.space", "service": "http://caddy:80"},
    {"hostname": "supabase.datacrew.space", "service": "http://caddy:80"},
    {"hostname": "neo4j.datacrew.space", "service": "http://caddy:80"},
    {"hostname": "comfyui.datacrew.space", "service": "http://caddy:80"},
    {"hostname": "infisical.datacrew.space", "service": "http://caddy:80"},
]


def get_auth_headers():
    """Get authentication headers."""
    if API_TOKEN and API_TOKEN.strip():
        return {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
        }
    elif CLOUDFLARE_EMAIL and CLOUDFLARE_EMAIL.strip() and CLOUDFLARE_API_KEY and CLOUDFLARE_API_KEY.strip():
        return {
            "X-Auth-Email": CLOUDFLARE_EMAIL.strip(),
            "X-Auth-Key": CLOUDFLARE_API_KEY.strip(),
            "Content-Type": "application/json",
        }
    else:
        raise ValueError("Either API token or email+API key must be provided")


def get_account_id():
    """Get account ID from zone."""
    url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}"
    headers = get_auth_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        
        if response.status_code == 200 and data.get("success"):
            account_id = data["result"].get("account", {}).get("id")
            return account_id
        return None
    except Exception as e:
        print(f"[ERROR] Failed to get account ID: {e}")
        return None


def get_tunnel_config(account_id):
    """Get current tunnel configuration."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{TUNNEL_ID}/configurations"
    headers = get_auth_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        
        if response.status_code == 200 and data.get("success"):
            return data["result"].get("config", {})
        return {}
    except Exception as e:
        print(f"[ERROR] Failed to get tunnel config: {e}")
        return {}


def update_tunnel_config(account_id, config):
    """Update tunnel configuration."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{TUNNEL_ID}/configurations"
    headers = get_auth_headers()
    
    try:
        response = requests.put(url, headers=headers, json={"config": config}, timeout=30)
        data = response.json()
        
        if response.status_code == 200 and data.get("success"):
            return True
        else:
            errors = data.get("errors", [])
            if errors:
                print(f"[ERROR] {errors[0].get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to update tunnel config: {e}")
        return False


def main():
    """Main function."""
    print("=" * 60)
    print("Configure Cloudflare Tunnel Public Hostnames")
    print("=" * 60)
    print()
    
    try:
        headers = get_auth_headers()
        print("[OK] Authentication configured")
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    
    # Get account ID
    print("Getting account ID...")
    account_id = get_account_id()
    if not account_id:
        print("[ERROR] Could not get account ID")
        sys.exit(1)
    print(f"[OK] Account ID: {account_id}")
    print()
    
    # Get current config
    print("Getting current tunnel configuration...")
    config = get_tunnel_config(account_id)
    
    # Build ingress rules
    ingress = []
    
    # Add service-specific rules
    for service in SERVICES:
        ingress.append({
            "hostname": service["hostname"],
            "service": service["service"],
            "originRequest": {
                "httpHostHeader": service["hostname"]
            }
        })
    
    # Add catch-all at the end
    ingress.append({"service": "http_status:404"})
    
    config["ingress"] = ingress
    
    # Update config
    print("Updating tunnel configuration...")
    print()
    for service in SERVICES:
        print(f"  [ADD] {service['hostname']} -> {service['service']}")
    
    if update_tunnel_config(account_id, config):
        print()
        print("[OK] Tunnel configuration updated successfully!")
        print()
        print("Next steps:")
        print("1. Verify configuration in Cloudflare dashboard:")
        print("   https://one.dash.cloudflare.com/ -> Networks -> Tunnels -> datacrew-services")
        print("2. Start your services:")
        print("   python start_services.py --profile gpu-nvidia")
        print("3. Test your services:")
        for service in SERVICES:
            print(f"   https://{service['hostname']}")
    else:
        print()
        print("[WARNING] Failed to update tunnel configuration via API.")
        print("   You may need to configure public hostnames manually in the dashboard:")
        print("   https://one.dash.cloudflare.com/ -> Networks -> Tunnels -> datacrew-services -> Configure")


if __name__ == "__main__":
    main()

