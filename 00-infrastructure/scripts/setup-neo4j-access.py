#!/usr/bin/env python3
"""
setup-neo4j-access.py

Create Cloudflare Access application for Neo4j and link it to the tunnel route.
This script creates the Access application and applies the standard access policy.

Usage:
    python setup-neo4j-access.py
"""

import os
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from project root
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Configuration
DOMAIN = "datacrew.space"
SUBDOMAIN = "neo4j"
FULL_DOMAIN = f"{SUBDOMAIN}.{DOMAIN}"
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "7552371386451b222f527fa794562a37")
TUNNEL_ID = os.getenv("CLOUDFLARE_TUNNEL_ID", "bff69fdf-293d-4511-b318-7e55e0ca22de")


def get_infisical_secrets() -> dict[str, str]:
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
            for raw_line in result.stdout.strip().split("\n"):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]
                    secrets_dict[key] = value
    except (subprocess.SubprocessError, OSError, ValueError):
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
        raise ValueError(
            "Either API token or email+API key must be provided (check Infisical or .env)"
        )


def get_standard_policy_id(headers, account_id):
    """Get the standard reusable policy ID."""
    # Get all applications to find reusable policies
    apps_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps"
    response = requests.get(apps_url, headers=headers, timeout=30)

    if response.status_code != 200:
        return None

    apps = response.json().get("result", [])
    if not apps:
        return None

    # Get policies from first app
    app_id = apps[0].get("id")
    policies_url = f"{apps_url}/{app_id}/policies"
    response = requests.get(policies_url, headers=headers, timeout=30)

    if response.status_code != 200:
        return None

    policies = response.json().get("result", [])
    for policy in policies:
        if policy.get("reusable") and policy.get("name") == "Standard Access Policy":
            return policy.get("id")

    return None


def create_neo4j_access_application(headers, account_id):
    """Create or update Neo4j Access application."""
    apps_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps"

    # Check if application already exists
    response = requests.get(apps_url, headers=headers, timeout=30)
    if response.status_code == 200:
        apps = response.json().get("result", [])
        for app in apps:
            if app.get("domain") == FULL_DOMAIN:
                app_id = app["id"]
                print(f"[OK] Neo4j Access application already exists: {FULL_DOMAIN} (ID: {app_id})")
                return app_id

    # Get standard policy ID
    policy_id = get_standard_policy_id(headers, account_id)

    # Create application data
    app_data = {
        "name": "Neo4j",
        "domain": FULL_DOMAIN,
        "type": "self_hosted",
        "session_duration": "24h",
    }

    # If standard policy exists, reference it
    if policy_id:
        app_data["policies"] = [{"id": policy_id}]
        print(f"[INFO] Using standard reusable policy (ID: {policy_id})")
    else:
        # Create a basic policy if standard doesn't exist
        print("[WARNING] Standard reusable policy not found. Creating basic policy.")
        app_data["policies"] = [
            {"name": "Neo4j Access Policy", "decision": "allow", "include": [{"everyone": {}}]}
        ]

    # Create application
    print(f"[INFO] Creating Neo4j Access application for {FULL_DOMAIN}...")
    response = requests.post(apps_url, headers=headers, json=app_data, timeout=30)

    if response.status_code in [200, 201]:
        result = response.json()
        if result.get("success"):
            app_id = result["result"]["id"]
            print(f"[OK] Created Neo4j Access application (ID: {app_id})")
            return app_id
        else:
            errors = result.get("errors", [])
            if errors:
                print(
                    f"[ERROR] Failed to create application: {errors[0].get('message', 'Unknown error')}"
                )
            return None
    else:
        print(f"[ERROR] Failed to create application: HTTP {response.status_code}")
        if response.text:
            print(f"   Response: {response.text[:300]}")
        return None


def link_access_to_tunnel_route(headers, account_id, app_id):
    """Link Access application to tunnel route."""
    # Get tunnel configuration
    tunnel_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{TUNNEL_ID}/configurations"
    response = requests.get(tunnel_url, headers=headers, timeout=30)

    if response.status_code != 200:
        print(f"[WARNING] Could not get tunnel configuration: HTTP {response.status_code}")
        print("   You may need to link the Access application manually in the dashboard")
        return False

    config = response.json()
    if not config.get("success"):
        print("[WARNING] Could not get tunnel configuration")
        print("   You may need to link the Access application manually in the dashboard")
        return False

    config_data = config.get("result", {}).get("config", {})
    ingress = config_data.get("ingress", [])

    # Find the Neo4j route
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
        print("   Create the route first using setup-cloudflare-tunnel-routes.py")
        print("   Then link the Access application manually in the dashboard")
        return False

    # Update tunnel configuration
    config_data["ingress"] = ingress
    update_data = {"config": config_data}

    update_response = requests.put(tunnel_url, headers=headers, json=update_data, timeout=30)

    if update_response.status_code == 200:
        result = update_response.json()
        if result.get("success"):
            print("[OK] Linked Access application to tunnel route")
            return True
        else:
            errors = result.get("errors", [])
            if errors:
                print(
                    f"[ERROR] Failed to link Access application: {errors[0].get('message', 'Unknown error')}"
                )
            return False
    else:
        print(
            f"[WARNING] Failed to link Access application via API: HTTP {update_response.status_code}"
        )
        print("   Link manually in dashboard:")
        print("   1. Go to https://one.dash.cloudflare.com/")
        print(f"   2. Networks → Tunnels → {TUNNEL_ID}")
        print(f"   3. Configure → Public Hostnames → {FULL_DOMAIN}")
        print("   4. Under Access, select 'Neo4j'")
        return False


def main():
    """Main function."""
    print("=" * 60)
    print("Neo4j Cloudflare Access Setup")
    print("=" * 60)
    print()

    try:
        headers = get_auth_headers()
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    # Create Access application
    app_id = create_neo4j_access_application(headers, ACCOUNT_ID)

    if not app_id:
        print("\n[ERROR] Failed to create Access application")
        sys.exit(1)

    # Link to tunnel route
    print()
    print("[INFO] Linking Access application to tunnel route...")
    linked = link_access_to_tunnel_route(headers, ACCOUNT_ID, app_id)

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"[OK] Access application created: {FULL_DOMAIN}")
    print(f"[OK] Application ID: {app_id}")

    if linked:
        print("[OK] Access application linked to tunnel route")
    else:
        print("[WARNING] Access application not linked to tunnel route")
        print("   Link manually in Cloudflare dashboard:")
        print(f"   https://one.dash.cloudflare.com/ → Networks → Tunnels → {TUNNEL_ID}")

    print()
    print("Next steps:")
    print("1. Verify Access application in dashboard:")
    print("   https://one.dash.cloudflare.com/ → Access → Applications → Neo4j")
    print("2. Ensure standard access policy is applied (if using reusable policy)")
    print("3. Test access: Visit https://neo4j.datacrew.space")
    print("4. Users will authenticate with Google OAuth, then Neo4j native auth")


if __name__ == "__main__":
    main()
