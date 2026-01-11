#!/usr/bin/env python3
"""
setup-cloudflare-tunnel-routes.py

Configure Cloudflare Tunnel public hostnames via API.
This script configures routing for all services through the tunnel.

Usage:
    python setup-cloudflare-tunnel-routes.py [--remove HOSTNAME]

    Without --remove: Configure all service routes
    With --remove: Remove a specific route (e.g., --remove infisical.datacrew.space)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from project root
script_dir = Path(__file__).parent
# Go up 2 levels: scripts -> infrastructure -> local-ai-packaged (project root)
project_root = script_dir.parent.parent
env_path = project_root / ".env"

# Debug: Print paths for troubleshooting
if os.getenv("DEBUG_CLOUDFLARE_SCRIPT"):
    print(f"[DEBUG] Script dir: {script_dir}")
    print(f"[DEBUG] Project root: {project_root}")
    print(f"[DEBUG] Env path: {env_path}")
    print(f"[DEBUG] Env exists: {env_path.exists()}")

# Load .env file (override=True to ensure .env values take precedence)
load_result = load_dotenv(env_path, override=True)

if os.getenv("DEBUG_CLOUDFLARE_SCRIPT"):
    print(f"[DEBUG] load_dotenv returned: {load_result}")
    print(
        f"[DEBUG] CLOUDFLARE_API_TOKEN loaded: {'Yes' if os.getenv('CLOUDFLARE_API_TOKEN') else 'No'}"
    )
    print(f"[DEBUG] CLOUDFLARE_EMAIL loaded: {'Yes' if os.getenv('CLOUDFLARE_EMAIL') else 'No'}")


# Cache for Infisical secrets to avoid multiple CLI calls
_infisical_secrets_cache: dict[str, str] | None = None
_infisical_secrets_attempted = False


def get_infisical_secrets() -> dict[str, str]:
    """
    Get secrets from Infisical using CLI.
    Caches results to avoid multiple CLI calls.

    Returns:
        Dictionary of secret key-value pairs, empty dict if Infisical unavailable
    """
    global _infisical_secrets_cache, _infisical_secrets_attempted

    # Return cached result if available
    if _infisical_secrets_cache is not None:
        return _infisical_secrets_cache

    # If we've already attempted and failed, return empty dict immediately
    if _infisical_secrets_attempted:
        return {}

    secrets_dict = {}
    _infisical_secrets_attempted = True

    try:
        # Check if Infisical CLI is available and authenticated
        result = subprocess.run(
            ["infisical", "export", "--format=dotenv"],
            capture_output=True,
            text=True,
            timeout=5,  # Reduced timeout from 30s to 5s to avoid hanging
            check=False,
        )

        if result.returncode == 0 and result.stdout:
            # Parse the dotenv format output
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]
                    secrets_dict[key] = value
    except subprocess.TimeoutExpired:
        # CLI call timed out - Infisical may be unreachable
        pass
    except FileNotFoundError:
        # Infisical CLI not installed
        pass
    except Exception:
        # Infisical not available or not authenticated - that's okay
        pass

    # Cache the result (even if empty)
    _infisical_secrets_cache = secrets_dict
    return secrets_dict


def get_env_var(key: str, default: str = "") -> str:
    """
    Get environment variable from Infisical first, then .env file.

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        Environment variable value
    """
    # Try Infisical first
    infisical_secrets = get_infisical_secrets()
    if key in infisical_secrets:
        return infisical_secrets[key]

    # Fall back to .env file
    return os.getenv(key, default)


# Configuration
DOMAIN = "datacrew.space"
# Get tunnel ID from Infisical or use default
TUNNEL_ID = get_env_var(
    "CLOUDFLARE_TUNNEL_ID", "bff69fdf-293d-4511-b318-7e55e0ca22de"
)  # datacrew-services tunnel
ZONE_ID = get_env_var("CLOUDFLARE_ZONE_ID", "77d3277e791671bfe46f0bac478a6f5b")
# Default account ID (can be overridden via env)
ACCOUNT_ID = get_env_var("CLOUDFLARE_ACCOUNT_ID", "7552371386451b222f527fa794562a37")

# For Global API Key
CLOUDFLARE_EMAIL = get_env_var("CLOUDFLARE_EMAIL", "")
CLOUDFLARE_API_KEY = get_env_var("CLOUDFLARE_API_KEY", "")
# For API Token
API_TOKEN = get_env_var("CLOUDFLARE_API_TOKEN", "")

# Services configuration
SERVICES = {
    "n8n": {"subdomain": "n8n", "port": 5678},
    "openwebui": {"subdomain": "openwebui", "port": 8080},  # Open WebUI (replaces webui)
    "flowise": {"subdomain": "flowise", "port": 3001},
    "langfuse": {"subdomain": "langfuse", "port": 3000},
    "supabase": {"subdomain": "supabase", "port": 8000},
    "neo4j": {"subdomain": "neo4j", "port": 7474},
    "comfyui": {"subdomain": "comfyui", "port": 8188},
    "ollama": {"subdomain": "ollama", "port": 11434},
    "infisical": {"subdomain": "infisical", "port": 8080},
    "lambda": {"subdomain": "api", "port": 8000},  # MongoDB RAG API
    "mongodb": {"subdomain": "mongodb", "port": 8081},  # MongoDB Express
    "qdrant": {"subdomain": "qdrant", "port": 6333},  # Qdrant Web UI
    "immich": {"subdomain": "immich", "port": 2283},  # Immich photo/video backup
}

CADDY_URL = "http://caddy:80"


def get_auth_headers():
    """Get authentication headers for Cloudflare API."""
    # Always get fresh credentials from Infisical (don't use module-level vars)
    api_token = get_env_var("CLOUDFLARE_API_TOKEN", "")
    email = get_env_var("CLOUDFLARE_EMAIL", "")
    api_key = get_env_var("CLOUDFLARE_API_KEY", "")

    # Also check for CLOUDFLARE_GLOBAL_API_KEY as fallback (common alternative name)
    if not api_key:
        api_key = get_env_var("CLOUDFLARE_GLOBAL_API_KEY", "")

    if api_token and api_token.strip():
        return {
            "Authorization": f"Bearer {api_token.strip()}",
            "Content-Type": "application/json",
        }
    elif email and email.strip() and api_key and api_key.strip():
        return {
            "X-Auth-Email": email.strip(),
            "X-Auth-Key": api_key.strip(),
            "Content-Type": "application/json",
        }
    else:
        # Debug: Check what we actually got
        debug_info = []
        if api_token:
            debug_info.append(f"API_TOKEN found (length: {len(api_token)})")
        else:
            debug_info.append("API_TOKEN not found")
        if email:
            debug_info.append(f"EMAIL found: {email}")
        else:
            debug_info.append("EMAIL not found")
        if api_key:
            debug_info.append(f"API_KEY found (length: {len(api_key)})")
        else:
            debug_info.append("API_KEY not found")

        error_msg = "Either API token or email+API key must be provided (check Infisical or .env)"
        error_msg += f"\n   Debug: {', '.join(debug_info)}"
        raise ValueError(error_msg)


def get_account_id(headers):
    """Get Cloudflare account ID if not provided."""
    if ACCOUNT_ID:
        return ACCOUNT_ID

    try:
        # Try to get account ID from zone first (most reliable)
        if ZONE_ID:
            zone_url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}"
            response = requests.get(zone_url, headers=headers, timeout=30)
            if response.status_code == 200:
                zone_data = response.json()
                if zone_data.get("success"):
                    account = zone_data.get("result", {}).get("account", {})
                    if isinstance(account, dict):
                        account_id = account.get("id")
                    else:
                        account_id = account  # Sometimes it's just the ID string
                    if account_id:
                        print(f"[OK] Found Account ID from zone: {account_id}")
                        return account_id

        # Fall back to listing accounts
        url = "https://api.cloudflare.com/client/v4/accounts"
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                accounts = result.get("result", [])
                if accounts:
                    account_id = accounts[0]["id"]
                    print(f"[OK] Found Account ID from accounts list: {account_id}")
                    return account_id
    except Exception as e:
        print(f"[WARNING] Could not get Account ID: {e}")

    return None


def configure_public_hostname(subdomain, service_url, account_id, retry_count=3):
    """Configure a public hostname for the tunnel."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{TUNNEL_ID}/configurations"
    # Get fresh auth headers each time (in case Infisical credentials changed)
    headers = get_auth_headers()

    hostname = f"{subdomain}.{DOMAIN}"

    # Get current config with retry logic
    response = None
    for attempt in range(retry_count):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 429:
                if attempt < retry_count - 1:
                    wait_time = (attempt + 1) * 5  # Exponential backoff: 5s, 10s, 15s
                    print(f"[RATE_LIMIT] Waiting {wait_time}s before retry...", end=" ")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[ERROR] Rate limited after {retry_count} attempts")
                    print(
                        "   Please wait a few minutes and try again, or configure manually in Cloudflare dashboard"
                    )
                    return False
            elif response.status_code != 200:
                print(f"[ERROR] HTTP {response.status_code}")
                if response.status_code == 401:
                    print("   Authentication failed - check your API token")
                elif response.status_code == 404:
                    error_data = response.json() if response.text else {}
                    errors = error_data.get("errors", [])
                    if errors:
                        error_msg = errors[0].get("message", "Unknown error")
                        print(f"   {error_msg}")
                    print(f"   URL: {url}")
                    print("   This usually means the tunnel ID or account ID is incorrect")
                    print(f"   Tunnel ID: {TUNNEL_ID}")
                    print(f"   Account ID: {account_id}")
                else:
                    try:
                        error_data = response.json()
                        errors = error_data.get("errors", [])
                        if errors:
                            print(f"   {errors[0].get('message', 'Unknown error')}")
                    except Exception:
                        print(f"   Response: {response.text[:200]}")
                return False
            break  # Success, exit retry loop
        except Exception as e:
            if attempt < retry_count - 1:
                time.sleep(2)
                continue
            print(f"[ERROR] {e}")
            return False

    if not response:
        return False

    try:
        config = response.json()
        if not config.get("success"):
            print(
                f"[ERROR] API error: {config.get('errors', [{}])[0].get('message', 'Unknown error')}"
            )
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
        new_rule = {"hostname": hostname, "service": service_url}

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
        update_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{TUNNEL_ID}/configurations"
        update_data = {"config": config_data}

        update_response = requests.put(update_url, headers=headers, json=update_data, timeout=30)

        if update_response.status_code == 200:
            result = update_response.json()
            if result.get("success"):
                print(f"[OK] Configured {hostname} -> {service_url}")
                return True
            else:
                errors = result.get("errors", [])
                if errors:
                    print(f"[ERROR] {hostname}: {errors[0].get('message', 'Unknown error')}")
                return False
        else:
            print(f"[ERROR] {hostname}: HTTP {update_response.status_code}")
            return False

    except Exception as e:
        print(f"[ERROR] {hostname}: {e}")
        return False


def remove_tunnel_route(hostname: str, account_id: str) -> bool:
    """Remove a specific route from tunnel configuration."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{TUNNEL_ID}/configurations"
    headers = get_auth_headers()

    # Get current config
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 404:
            print("[INFO] Tunnel configuration not found via API endpoint")
            print(f"[INFO] The route for {hostname} may not exist or may need manual removal")
            print("[INFO] Check Cloudflare Dashboard: https://one.dash.cloudflare.com/")
            return True  # Not an error - just means we can't verify/remove via API

        if response.status_code != 200:
            print(f"[ERROR] Failed to get tunnel config: HTTP {response.status_code}")
            if response.text:
                print(f"   Response: {response.text[:200]}")
            return False

        result = response.json()
        if not result.get("success"):
            error_msg = result.get("errors", [{}])[0].get("message", "Unknown error")
            if "not found" in error_msg.lower():
                print("[INFO] Tunnel configuration not found - routes may be managed elsewhere")
                return True
            print(f"[ERROR] API error: {error_msg}")
            return False

        config_data = result.get("result", {}).get("config", {})
        ingress = config_data.get("ingress", [])

        if not ingress:
            print(f"[INFO] No ingress rules found. Route {hostname} may already be removed.")
            return True

        # Find and remove the route
        original_count = len(ingress)
        ingress = [rule for rule in ingress if rule.get("hostname") != hostname]
        removed_count = original_count - len(ingress)

        if removed_count == 0:
            print(f"[INFO] Route {hostname} not found in tunnel configuration")
            return True

        # Update config
        config_data["ingress"] = ingress

        # Send update
        update_data = {"config": config_data}
        update_response = requests.put(url, headers=headers, json=update_data, timeout=30)

        if update_response.status_code == 200:
            result = update_response.json()
            if result.get("success"):
                print(f"[OK] Removed {hostname} from tunnel configuration")
                return True
            else:
                errors = result.get("errors", [])
                if errors:
                    print(f"[ERROR] {errors[0].get('message', 'Unknown error')}")
                return False
        else:
            print(f"[ERROR] HTTP {update_response.status_code}")
            if update_response.text:
                print(f"   Response: {update_response.text[:200]}")
            return False

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Configure or remove Cloudflare Tunnel routes")
    parser.add_argument(
        "--remove",
        type=str,
        metavar="HOSTNAME",
        help="Remove a specific route (e.g., infisical.datacrew.space)",
    )
    args = parser.parse_args()

    print("=" * 60)
    if args.remove:
        print("Remove Cloudflare Tunnel Route")
    else:
        print("Cloudflare Tunnel Public Hostnames Configuration")
    print("=" * 60)
    print()

    try:
        headers = get_auth_headers()
        # Verify token is valid by checking if we can retrieve it from Infisical
        api_token = get_env_var("CLOUDFLARE_API_TOKEN", "")
        if api_token:
            print(
                f"[OK] Authentication configured (token retrieved from Infisical, length: {len(api_token)})"
            )
        else:
            print("[OK] Authentication configured (using email+API key)")
    except ValueError as e:
        print(f"[ERROR] {e}")
        print(
            "   Set CLOUDFLARE_API_TOKEN or CLOUDFLARE_EMAIL + CLOUDFLARE_API_KEY in Infisical or .env"
        )
        sys.exit(1)

    # Get account ID (try to fetch, but use default if available)
    account_id = get_account_id(headers)
    if not account_id:
        if ACCOUNT_ID:
            print(f"[INFO] Using default Account ID: {ACCOUNT_ID}")
            account_id = ACCOUNT_ID
        else:
            print("[ERROR] Could not determine Account ID")
            print("   Set CLOUDFLARE_ACCOUNT_ID in .env or ensure API token has account access")
            sys.exit(1)

    print(f"[OK] Tunnel ID: {TUNNEL_ID}")
    print(f"[OK] Zone ID: {ZONE_ID}")
    print(f"[OK] Account ID: {account_id}")
    print()

    # Handle remove operation
    if args.remove:
        hostname = args.remove
        if not hostname.endswith(DOMAIN):
            print(f"[WARNING] Hostname {hostname} doesn't match domain {DOMAIN}")
            print("   Proceeding anyway...")

        print(f"Removing route: {hostname}")
        print()

        if remove_tunnel_route(hostname, account_id):
            print()
            print("[OK] Route removed successfully!")
            print()
            print("Note: You can verify this in the Cloudflare dashboard:")
            print("https://one.dash.cloudflare.com/ -> Networks -> Tunnels -> Your tunnel")
        else:
            print()
            print("[ERROR] Failed to remove route")
            print("You may need to remove it manually in the Cloudflare dashboard:")
            print(
                "https://one.dash.cloudflare.com/ -> Networks -> Tunnels -> Your tunnel -> Configure -> Public Hostnames"
            )
            sys.exit(1)
        return

    # Handle add operation (default)
    print("Configuring public hostnames...")
    print("All services will route through Caddy (http://caddy:80)")
    print("Caddy will route to the correct service based on hostname")
    print()

    configured = 0
    failed = 0

    for _service_name, config in SERVICES.items():
        subdomain = config["subdomain"]
        hostname = f"{subdomain}.{DOMAIN}"

        print(f"Configuring {hostname}...", end=" ... ")

        # Add small delay to avoid rate limiting
        if configured > 0 or failed > 0:
            time.sleep(1)

        if configure_public_hostname(subdomain, CADDY_URL, account_id):
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
        print("4. (Optional) Set up Cloudflare Access for Neo4j:")
        print("   python 00-infrastructure/scripts/setup-neo4j-access.py")
        print("5. Start services: python start_services.py --profile gpu-nvidia")
    else:
        print("[WARNING] Some hostnames failed to configure.")
        print("   You may need to configure them manually in the Cloudflare dashboard")


if __name__ == "__main__":
    main()
