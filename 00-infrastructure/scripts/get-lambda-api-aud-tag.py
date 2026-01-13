#!/usr/bin/env python3
"""
get-lambda-api-aud-tag.py

Retrieve the AUD tag for the Lambda API Cloudflare Access application.
This script queries the Cloudflare API to get the Application Audience (AUD) tag
which is required for JWT validation.

Usage:
    python get-lambda-api-aud-tag.py
"""

import os
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from project root
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    current_dir_env = Path(".env")
    if current_dir_env.exists():
        load_dotenv(current_dir_env)

# Configuration
DOMAIN = "datacrew.space"
SUBDOMAIN = "api"
FULL_DOMAIN = f"{SUBDOMAIN}.{DOMAIN}"
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")


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
    if email and email.strip() and api_key and api_key.strip():
        return {
            "X-Auth-Email": email.strip(),
            "X-Auth-Key": api_key.strip(),
            "Content-Type": "application/json",
        }
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
    except (requests.exceptions.RequestException, KeyError, ValueError):
        pass

    raise ValueError("CLOUDFLARE_ACCOUNT_ID must be set or auto-detected from API")


def get_aud_tag(headers, account_id):
    """Get AUD tag for Lambda API Access application."""
    apps_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps"

    try:
        response = requests.get(apps_url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"[ERROR] Failed to get applications: HTTP {response.status_code}")
            print(f"   Response: {response.text[:300]}")
            return None

        apps = response.json().get("result", [])
        for app in apps:
            if app.get("domain") == FULL_DOMAIN:
                aud_tag = app.get("aud")
                if aud_tag:
                    return aud_tag
                print("[WARNING] Application found but no AUD tag in response")
                print(f"   Application ID: {app.get('id')}")
                print(f"   Application name: {app.get('name')}")
                # Try to get detailed app info
                app_id = app.get("id")
                app_detail_url = f"{apps_url}/{app_id}"
                detail_response = requests.get(app_detail_url, headers=headers, timeout=30)
                if detail_response.status_code == 200:
                    detail = detail_response.json().get("result", {})
                    aud_tag = detail.get("aud")
                    if aud_tag:
                        return aud_tag

        print(f"[ERROR] Application not found for domain: {FULL_DOMAIN}")
        print("   Available applications:")
        for app in apps:
            print(f"   - {app.get('name')} ({app.get('domain')})")
        return None

    except Exception as e:
        print(f"[ERROR] Exception while fetching applications: {e}")
        return None


def main():
    """Main function."""
    print(f"Getting AUD tag for Lambda API Access application: {FULL_DOMAIN}")
    print()

    try:
        headers = get_auth_headers()
        account_id = get_account_id(headers)
        print(f"[INFO] Using Cloudflare account: {account_id}")

        aud_tag = get_aud_tag(headers, account_id)

        if aud_tag:
            print()
            print("=" * 60)
            print("AUD TAG FOUND")
            print("=" * 60)
            print(f"AUD Tag: {aud_tag}")
            print()
            print("Add this to your environment variables:")
            print(f"  CLOUDFLARE_AUD_TAG={aud_tag}")
            print()
            print("Or add to docker-compose.yml:")
            print(f"  CLOUDFLARE_AUD_TAG: {aud_tag}")
            print()
            print("Or set in Infisical:")
            print(f"  infisical secrets set CLOUDFLARE_AUD_TAG={aud_tag}")
            print("=" * 60)
            return 0
        print()
        print("[ERROR] Could not retrieve AUD tag")
        print("   Make sure the Lambda API Access application exists")
        print("   Run: python setup-lambda-api-access.py")
        return 1

    except ValueError as e:
        print(f"[ERROR] {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
