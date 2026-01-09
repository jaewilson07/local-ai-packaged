#!/usr/bin/env python3
"""
setup-lambda-api-access.py

Create Cloudflare Access application for Lambda API and link it to the tunnel route.
This script creates the Access application and applies the standard access policy.

Usage:
    python setup-lambda-api-access.py
"""

import requests
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Optional

# Load .env from project root
script_dir = Path(__file__).parent
# Calculate project root: 00-infrastructure/scripts -> 00-infrastructure -> root
project_root = script_dir.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try loading from current directory if script is run from project root
    current_dir_env = Path(".env")
    if current_dir_env.exists():
        load_dotenv(current_dir_env)

# Configuration
DOMAIN = "datacrew.space"
SUBDOMAIN = "api"
FULL_DOMAIN = f"{SUBDOMAIN}.{DOMAIN}"
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
TUNNEL_ID = os.getenv("CLOUDFLARE_TUNNEL_ID", "")

STANDARD_POLICY_NAME = "Standard Access Policy"


def get_infisical_secrets() -> Dict[str, str]:
    """Get secrets from Infisical using CLI."""
    secrets_dict = {}
    try:
        result = subprocess.run(
            ["infisical", "export", "--format=dotenv"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    secrets_dict[key] = value
    except Exception:
        pass
    return secrets_dict

def get_env_var(key: str, default: str = "") -> str:
    """Get environment variable from Infisical first, then .env file."""
    infisical_secrets = get_infisical_secrets()
    if key in infisical_secrets:
        return infisical_secrets[key]
    return os.getenv(key, default)


def get_auth_headers():
    """Get authentication headers for Cloudflare API."""
    api_token = get_env_var("CLOUDFLARE_API_TOKEN", "")
    email = get_env_var("CLOUDFLARE_EMAIL", "")
    api_key = get_env_var("CLOUDFLARE_API_KEY", "")
    
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
        raise ValueError("Either API token or email+API key must be provided (check Infisical or .env)")


def get_account_id(headers):
    """Get Cloudflare account ID."""
    if ACCOUNT_ID:
        return ACCOUNT_ID
    
    # Try to get from API
    try:
        response = requests.get(
            "https://api.cloudflare.com/client/v4/accounts",
            headers=headers,
            timeout=30,
        )
        if response.status_code == 200:
            accounts = response.json().get("result", [])
            if accounts:
                return accounts[0]["id"]
    except Exception:
        pass
    
    raise ValueError("CLOUDFLARE_ACCOUNT_ID must be set or auto-detected from API")


def get_standard_policy_id(headers, account_id):
    """Get the standard reusable policy ID if it exists."""
    # Get all reusable policies
    policies_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/policies"
    
    try:
        response = requests.get(policies_url, headers=headers, timeout=30)
        if response.status_code == 200:
            policies = response.json().get("result", [])
            for policy in policies:
                if policy.get("name") == STANDARD_POLICY_NAME and policy.get("reusable"):
                    return policy.get("id")
    except Exception:
        pass
    
    return None


def create_lambda_api_access_application(headers, account_id):
    """Create or update Lambda API Access application."""
    apps_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps"
    
    # Check if application already exists
    response = requests.get(apps_url, headers=headers, timeout=30)
    if response.status_code == 200:
        apps = response.json().get("result", [])
        for app in apps:
            if app.get("domain") == FULL_DOMAIN:
                app_id = app["id"]
                print(f"[OK] Lambda API Access application already exists: {FULL_DOMAIN} (ID: {app_id})")
                return app_id
    
    # Get standard policy ID
    policy_id = get_standard_policy_id(headers, account_id)
    
    # Get access rules from environment
    allowed_emails_str = get_env_var("CLOUDFLARE_ACCESS_EMAILS", "")
    allowed_emails = [e.strip() for e in allowed_emails_str.split(",") if e.strip()] if allowed_emails_str else []
    allowed_email_domain = get_env_var("CLOUDFLARE_ACCESS_EMAIL_DOMAIN", "")
    google_idp_id = get_env_var("GOOGLE_IDP_ID", "")
    
    # Build include rules
    include_rules = []
    if allowed_emails:
        for email in allowed_emails:
            include_rules.append({"email": {"email": email}})
    if allowed_email_domain:
        include_rules.append({"email_domain": {"domain": allowed_email_domain}})
    if not include_rules:
        include_rules.append({"everyone": {}})
    
    # Create application data
    app_data = {
        "name": "Lambda API",
        "domain": FULL_DOMAIN,
        "type": "self_hosted",
        "session_duration": "24h",
        "policies": [{
            "name": "Lambda API Access Policy",
            "decision": "allow",
            "include": include_rules
        }]
    }
    
    # Add Google OAuth if configured
    if google_idp_id:
        app_data["policies"][0]["identity_provider_selectors"] = [google_idp_id]
    
    # If standard policy exists, reference it instead
    if policy_id:
        app_data["policies"] = [{"id": policy_id}]
        print(f"[INFO] Using standard reusable policy (ID: {policy_id})")
    
    # Create application
    print(f"[INFO] Creating Lambda API Access application for {FULL_DOMAIN}...")
    response = requests.post(apps_url, headers=headers, json=app_data, timeout=30)
    
    if response.status_code in [200, 201]:
        result = response.json()
        if result.get("success"):
            app_id = result["result"]["id"]
            print(f"[OK] Created Lambda API Access application (ID: {app_id})")
            return app_id
    
    print(f"[ERROR] Failed to create application: HTTP {response.status_code}")
    print(f"   Response: {response.text[:300]}")
    return None


def link_access_to_tunnel_route(headers, account_id, app_id):
    """Link Access application to tunnel route."""
    if not TUNNEL_ID:
        print("[WARNING] CLOUDFLARE_TUNNEL_ID not set, cannot link Access application")
        print("   Link manually in Cloudflare dashboard:")
        print(f"   https://one.dash.cloudflare.com/ → Networks → Tunnels → [Your Tunnel]")
        return False
    
    # Get tunnel configuration
    tunnel_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{TUNNEL_ID}/configurations"
    response = requests.get(tunnel_url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"[WARNING] Could not get tunnel configuration: HTTP {response.status_code}")
        print(f"   You may need to link the Access application manually in the dashboard")
        return False
    
    config = response.json()
    if not config.get("success"):
        print(f"[WARNING] Could not get tunnel configuration")
        print(f"   You may need to link the Access application manually in the dashboard")
        return False
    
    config_data = config.get("result", {}).get("config", {})
    ingress = config_data.get("ingress", [])
    
    # Find the api.datacrew.space route
    route_found = False
    for rule in ingress:
        if rule.get("hostname") == FULL_DOMAIN:
            route_found = True
            # Update route to include Access application
            rule["access"] = {"app_id": app_id}
            print(f"[INFO] Found tunnel route for {FULL_DOMAIN}, linking Access application...")
            break
    
    if not route_found:
        print(f"[WARNING] Tunnel route for {FULL_DOMAIN} not found")
        print(f"   Create the route first using setup-cloudflare-tunnel-routes.py")
        print(f"   Then link the Access application manually in the dashboard")
        return False
    
    # Update tunnel configuration
    config_data["ingress"] = ingress
    update_data = {"config": config_data}
    
    update_response = requests.put(tunnel_url, headers=headers, json=update_data, timeout=30)
    
    if update_response.status_code == 200:
        result = update_response.json()
        if result.get("success"):
            print(f"[OK] Linked Access application to tunnel route")
            return True
    
    print(f"[WARNING] Failed to link Access application: HTTP {update_response.status_code}")
    print(f"   Response: {update_response.text[:300]}")
    print(f"   Link manually in Cloudflare dashboard:")
    print(f"   1. Go to https://one.dash.cloudflare.com/")
    print(f"   2. Networks → Tunnels → {TUNNEL_ID}")
    print(f"   3. Find route for {FULL_DOMAIN}")
    print(f"   4. Click Edit")
    print(f"   5. Under Access, select 'Lambda API'")
    return False


def main():
    """Main function."""
    print("=" * 60)
    print("Lambda API Cloudflare Access Setup")
    print("=" * 60)
    print()
    
    try:
        headers = get_auth_headers()
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    
    # Get account ID
    try:
        account_id = get_account_id(headers)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    
    # Create Access application
    app_id = create_lambda_api_access_application(headers, account_id)
    
    if not app_id:
        print("\n[ERROR] Failed to create Access application")
        sys.exit(1)
    
    # Link to tunnel route
    print()
    print("[INFO] Linking Access application to tunnel route...")
    linked = link_access_to_tunnel_route(headers, account_id, app_id)
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"[OK] Access application created: {FULL_DOMAIN}")
    print(f"[OK] Application ID: {app_id}")
    
    if linked:
        print(f"[OK] Access application linked to tunnel route")
    else:
        print(f"[WARNING] Access application not linked to tunnel route")
        print(f"   Link manually in Cloudflare dashboard:")
        print(f"   https://one.dash.cloudflare.com/ → Networks → Tunnels → {TUNNEL_ID}")
    
    print()
    print("Next steps:")
    print("1. Verify Access application in dashboard:")
    print("   https://one.dash.cloudflare.com/ → Access → Applications → Lambda API")
    print("2. Ensure access policy is configured correctly")
    print("3. Test access: Visit https://api.datacrew.space/mcp/openapi.json")
    print("4. You should be redirected to Cloudflare Access login")


if __name__ == "__main__":
    main()

