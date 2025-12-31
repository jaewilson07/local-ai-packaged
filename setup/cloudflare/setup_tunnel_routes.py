#!/usr/bin/env python3
"""
setup_cloudflare_tunnel_routes.py

Configure Cloudflare Tunnel public hostnames via API.
This script configures routing for all services through the tunnel.
"""

import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Configuration
DOMAIN = "datacrew.space"
TUNNEL_ID = "3885d13d-2d48-47ee-811c-878920be4d69"  # From tunnel creation
ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "77d3277e791671bfe46f0bac478a6f5b")

# For Global API Key
CLOUDFLARE_EMAIL = os.getenv("CLOUDFLARE_EMAIL", "")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "")
# For API Token
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")

# Services configuration
SERVICES = {
    "n8n": {"subdomain": "n8n", "port": 5678},
    "webui": {"subdomain": "webui", "port": 8080},
    "flowise": {"subdomain": "flowise", "port": 3001},
    "langfuse": {"subdomain": "langfuse", "port": 3000},
    "supabase": {"subdomain": "supabase", "port": 8000},
    "neo4j": {"subdomain": "neo4j", "port": 7474},
    "comfyui": {"subdomain": "comfyui", "port": 8188},
    "infisical": {"subdomain": "infisical", "port": 8080},
}

CADDY_URL = "http://caddy:80"


def get_auth_headers():
    """Get authentication headers for Cloudflare API."""
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
        raise ValueError("Either API token or email+API key must be provided in .env")


def configure_public_hostname(subdomain, service_url):
    """Configure a public hostname for the tunnel."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{ZONE_ID}/cfd_tunnel/{TUNNEL_ID}/configurations"
    headers = get_auth_headers()
    
    hostname = f"{subdomain}.{DOMAIN}"
    
    # Get current config
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"[ERROR] Failed to get tunnel config: {response.status_code}")
            return False
        
        config = response.json()
        if not config.get("success"):
            print(f"[ERROR] API error: {config.get('errors', [{}])[0].get('message', 'Unknown error')}")
            return False
        
        # Get existing config or create new
        config_data = config.get("result", {}).get("config", {})
        ingress = config_data.get("ingress", [])
        
        # Check if hostname already exists
        for rule in ingress:
            if rule.get("hostname") == hostname:
                print(f"[SKIP] {hostname} already configured")
                return True
        
        # Add new hostname rule
        new_rule = {
            "hostname": hostname,
            "service": service_url
        }
        
        # Add to ingress (before catch-all)
        if ingress and ingress[-1].get("service") == "http_status:404":
            ingress.insert(-1, new_rule)
        else:
            ingress.append(new_rule)
            # Add catch-all at the end
            ingress.append({"service": "http_status:404"})
        
        # Update config
        config_data["ingress"] = ingress
        
        # Send update
        update_url = f"https://api.cloudflare.com/client/v4/accounts/{ZONE_ID}/cfd_tunnel/{TUNNEL_ID}/configurations"
        update_data = {"config": config_data}
        
        response = requests.put(update_url, headers=headers, json=update_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"[OK] Configured {hostname} -> {service_url}")
                return True
            else:
                errors = result.get("errors", [])
                if errors:
                    print(f"[ERROR] {hostname}: {errors[0].get('message', 'Unknown error')}")
                return False
        else:
            print(f"[ERROR] {hostname}: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] {hostname}: {e}")
        return False


def main():
    """Main function."""
    print("=" * 60)
    print("Cloudflare Tunnel Public Hostnames Configuration")
    print("=" * 60)
    print()
    
    try:
        headers = get_auth_headers()
        print("[OK] Authentication configured")
    except ValueError as e:
        print(f"[ERROR] {e}")
        print("   Set CLOUDFLARE_API_TOKEN or CLOUDFLARE_EMAIL + CLOUDFLARE_API_KEY in .env")
        sys.exit(1)
    
    print(f"[OK] Tunnel ID: {TUNNEL_ID}")
    print(f"[OK] Zone ID: {ZONE_ID}")
    print()
    
    print("Configuring public hostnames...")
    print("All services will route through Caddy (http://caddy:80)")
    print("Caddy will route to the correct service based on hostname")
    print()
    
    configured = 0
    failed = 0
    
    for service_name, config in SERVICES.items():
        subdomain = config["subdomain"]
        hostname = f"{subdomain}.{DOMAIN}"
        
        print(f"Configuring {hostname}...", end=" ... ")
        
        if configure_public_hostname(subdomain, CADDY_URL):
            configured += 1
        else:
            failed += 1
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"[OK] Configured: {configured}")
    print(f"[ERROR] Failed: {failed}")
    print()
    
    if failed == 0:
        print("[OK] All public hostnames configured successfully!")
        print()
        print("Next steps:")
        print("1. Verify hostnames in Cloudflare dashboard:")
        print("   https://one.dash.cloudflare.com/ -> Networks -> Tunnels -> datacrew-services")
        print("2. Update .env file with CLOUDFLARE_TUNNEL_TOKEN")
        print("3. Update hostname environment variables to use *.datacrew.space")
        print("4. Start services: python start_services.py --profile gpu-nvidia")
    else:
        print("[WARNING] Some hostnames failed to configure.")
        print("   You may need to configure them manually in the Cloudflare dashboard")


if __name__ == "__main__":
    main()

