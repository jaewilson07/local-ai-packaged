#!/usr/bin/env python3
"""
setup_cloudflare_dns.py

Automated script to add all DNS records to Cloudflare via API.
This script will add all your DNS records (email, custom services, etc.) to Cloudflare.

Prerequisites:
1. Cloudflare API token with DNS edit permissions
2. Domain already added to Cloudflare account
3. Zone ID for your domain

To get API token:
1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token"
3. Use "Edit zone DNS" template
4. Select your zone (datacrew.space)
5. Copy the token

To get Zone ID:
1. Go to Cloudflare dashboard
2. Select your domain (datacrew.space)
3. Zone ID is shown in the right sidebar under "API"
"""

import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()
import os

# Configuration
DOMAIN = "datacrew.space"
# For Global API Key (use these):
CLOUDFLARE_EMAIL = os.getenv("CLOUDFLARE_EMAIL", "")  # Your Cloudflare account email
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "")  # Your Global API Key
# For API Token (alternative):
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")  # API Token (if using token instead)
ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")  # Optional: can be set in .env or auto-detected

# DNS Records to add
DNS_RECORDS = [
    # Google Workspace MX Records (must be DNS only)
    {
        "type": "MX",
        "name": "@",
        "priority": 1,
        "content": "aspmx.l.google.com",
        "proxied": False,
    },
    {
        "type": "MX",
        "name": "@",
        "priority": 5,
        "content": "alt1.aspmx.l.google.com",
        "proxied": False,
    },
    {
        "type": "MX",
        "name": "@",
        "priority": 5,
        "content": "alt2.aspmx.l.google.com",
        "proxied": False,
    },
    {
        "type": "MX",
        "name": "@",
        "priority": 10,
        "content": "alt3.aspmx.l.google.com",
        "proxied": False,
    },
    {
        "type": "MX",
        "name": "@",
        "priority": 10,
        "content": "alt4.aspmx.l.google.com",
        "proxied": False,
    },
    # Google Workspace TXT Records
    {
        "type": "TXT",
        "name": "@",
        "content": "google-site-verification=uZqWkV9T5euAZHiQiy3IZd9lc3iErKCzCkM4Vdk7wRE",
        "proxied": False,
    },
    {
        "type": "TXT",
        "name": "@",
        "content": "v=spf1 include:_spf.google.com ~all",
        "proxied": False,
    },
    # Google Workspace DKIM Record
    {
        "type": "TXT",
        "name": "google._domainkey",
        "content": "v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEApEdIcdUY+yPtirZ393obxADSf3sYIfembtUE7eSf51ei3jKXshuvpHjFxKlOwnsKqZKAGOyepQ76GFkK1mGKVUGOQY9og4Lt34YSFYITQkaJVEbPGZL+BWXsq0+04JaTO34r36v7gVRjkDaoNXtiPIoI7IctfBpdxfrJgKTxWDtBnkdjhIOBCTE8d5HRC2dw0WlpY2qatLKrWbwAJjNy9TFjETZAw4TYQk3iBhMhHKFfnO7f6MDqF4GSvAIImmRYh3Q2M6vMZhX8hoCkraVpq94ZKT6JVaHdB+GTI/PBkrpt/KkKYevKL4lGLMzjckPC5jXyUecRB2ezzVyTfwXJEQIDAQAB",
        "proxied": False,
    },
    # Note: DMARC record needs to be added manually if desired
    # Postman Records
    {"type": "CNAME", "name": "api", "content": "phs.getpostman.com", "proxied": True},
    {
        "type": "TXT",
        "name": "@",
        "content": "postman-domain-verification=9fdabc206f5846514ace93f25cf690ab1afb756f866014a4d323c89928cc7d800d5d558dcc24954542eb8c96b604c3b71874a7f77f60e79b7b145e19b6457b0e",
        "proxied": False,
    },
    # Domo Library A Records
    {"type": "A", "name": "domolibrary", "content": "185.199.108.153", "proxied": True},
    {"type": "A", "name": "domolibrary", "content": "185.199.109.153", "proxied": True},
    # Circle Community
    {
        "type": "CNAME",
        "name": "community",
        "content": "datacrew.circle.so",
        "proxied": True,
    },
    # Squarespace Domain Connect (optional)
    {
        "type": "CNAME",
        "name": "_domainconnect",
        "content": "_domainconnect.domains.squarespace.com",
        "proxied": False,
    },
]


def get_auth_headers(email=None, api_key=None, api_token=None):
    """Get authentication headers for Cloudflare API."""
    # Check for API token first (handle both None and empty string)
    if api_token and api_token.strip():
        # Use API Token (Bearer authentication)
        return {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
    # Check for Global API Key (handle both None and empty string)
    elif email and email.strip() and api_key and api_key.strip():
        # Use Global API Key (X-Auth-Email and X-Auth-Key)
        return {
            "X-Auth-Email": email.strip(),
            "X-Auth-Key": api_key.strip(),
            "Content-Type": "application/json",
        }
    else:
        raise ValueError("Either API token or email+API key must be provided")


def get_zone_id(email=None, api_key=None, api_token=None, domain=None):
    """Get Zone ID from domain name."""
    url = "https://api.cloudflare.com/client/v4/zones"
    headers = get_auth_headers(email=email, api_key=api_key, api_token=api_token)
    params = {"name": domain}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        data = response.json()

        if response.status_code == 200 and data.get("success") and data.get("result"):
            return data["result"][0]["id"]
        else:
            errors = data.get("errors", [])
            if errors:
                error_msg = errors[0].get("message", "Unknown error")
                print(f"[ERROR] {error_msg}")
            return None
    except Exception as e:
        print(f"[ERROR] Error getting Zone ID: {e}")
        return None


def list_existing_records(email=None, api_key=None, api_token=None, zone_id=None):
    """List all existing DNS records."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = get_auth_headers(email=email, api_key=api_key, api_token=api_token)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data["success"]:
            return {f"{r['type']}:{r['name']}:{r.get('content', '')}": r for r in data["result"]}
        return {}
    except Exception as e:
        print(f"[WARNING] Could not list existing records: {e}")
        return {}


def add_dns_record(email=None, api_key=None, api_token=None, zone_id=None, record=None):
    """Add a DNS record to Cloudflare."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = get_auth_headers(email=email, api_key=api_key, api_token=api_token)

    # Prepare record data
    data = {
        "type": record["type"],
        "name": record["name"],
        "content": record["content"],
        "ttl": 1,  # Auto TTL
    }

    # Add priority for MX records
    if record["type"] == "MX":
        data["priority"] = record["priority"]

    # Set proxy status (only for A, AAAA, CNAME)
    if record["type"] in ["A", "AAAA", "CNAME"]:
        data["proxied"] = record["proxied"]

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()

        if response.status_code == 200 and result.get("success"):
            return True, result["result"]
        else:
            # Get detailed error message
            errors = result.get("errors", [])
            if errors:
                error_msg = errors[0].get("message", "Unknown error")
                error_code = errors[0].get("code", "")
                return False, f"{error_msg} (code: {error_code})"
            else:
                return False, f"HTTP {response.status_code}: {result}"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {e!s}"
    except Exception as e:
        return False, f"Unexpected error: {e!s}"


def main():
    """Main function."""
    print("=" * 60)
    print("Cloudflare DNS Records Setup")
    print("=" * 60)
    print()

    # Get authentication credentials
    email = CLOUDFLARE_EMAIL.strip() if CLOUDFLARE_EMAIL else ""
    api_key = CLOUDFLARE_API_KEY.strip() if CLOUDFLARE_API_KEY else ""
    api_token = API_TOKEN.strip() if API_TOKEN else ""

    # Check if using Global API Key or API token (prioritize Global API Key)
    use_global_key = email and api_key and len(email) > 0 and len(api_key) > 0
    use_token = api_token and len(api_token) > 0

    if use_global_key:
        print("[OK] Using Global API Key from .env file")
        api_token = None
    elif use_token:
        print("[OK] Using API token from .env file")
        email = None
        api_key = None
    else:
        # Prompt for credentials
        use_token = (
            input("Do you want to use API Token? (y/n, default=n for Global API Key): ")
            .strip()
            .lower()
        )
        if use_token == "y":
            api_token = input("Enter your Cloudflare API token: ").strip()
            if not api_token:
                print("[ERROR] API token is required")
                sys.exit(1)
            email = None
            api_key = None
        else:
            email = input("Enter your Cloudflare account email: ").strip()
            api_key = input("Enter your Cloudflare Global API Key: ").strip()
            if not email or not api_key:
                print("[ERROR] Email and API key are required")
                sys.exit(1)
            api_token = None

    # Get Zone ID
    zone_id = ZONE_ID
    if not zone_id:
        print(f"Getting Zone ID for {DOMAIN}...")
        zone_id = get_zone_id(email, api_key, api_token, DOMAIN)
        if not zone_id:
            print("[ERROR] Could not get Zone ID. Please check your credentials and domain.")
            sys.exit(1)

    print(f"[OK] Zone ID: {zone_id}")
    print()

    # List existing records
    print("Checking existing DNS records...")
    # Pass None for unused auth method
    if use_global_key:
        existing = list_existing_records(email=email, api_key=api_key, zone_id=zone_id)
    else:
        existing = list_existing_records(api_token=api_token, zone_id=zone_id)
    print(f"Found {len(existing)} existing records")
    print()

    # Add records
    print("=" * 60)
    print("Adding DNS Records")
    print("=" * 60)
    print()

    added = 0
    skipped = 0
    failed = 0

    for record in DNS_RECORDS:
        record_key = f"{record['type']}:{record['name']}:{record['content']}"

        # Check if record already exists
        if record_key in existing:
            print(
                f"[SKIP] Skipping {record['type']} {record['name']} -> {record['content']} (already exists)"
            )
            skipped += 1
            continue

        # Special check for MX records (check by type, name, and priority)
        if record["type"] == "MX":
            exists = any(
                r["type"] == "MX"
                and r["name"] == record["name"]
                and r.get("priority") == record["priority"]
                and r.get("content") == record["content"]
                for r in existing.values()
            )
            if exists:
                print(
                    f"[SKIP] Skipping {record['type']} {record['name']} (priority {record['priority']}) -> {record['content']} (already exists)"
                )
                skipped += 1
                continue

        print(
            f"[ADD] Adding {record['type']} {record['name']} -> {record['content']}",
            end=" ... ",
        )

        # Pass None for unused auth method
        if email and api_key:
            success, result = add_dns_record(
                email=email, api_key=api_key, zone_id=zone_id, record=record
            )
        else:
            success, result = add_dns_record(api_token=api_token, zone_id=zone_id, record=record)

        if success:
            print("[OK]")
            added += 1
            # Add to existing to avoid duplicates
            existing[record_key] = result
            time.sleep(0.5)  # Rate limiting
        else:
            print(f"[ERROR] {result}")
            failed += 1

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"[OK] Added: {added}")
    print(f"[SKIP] Skipped: {skipped}")
    print(f"[ERROR] Failed: {failed}")
    print()

    if failed == 0:
        print("[OK] All DNS records added successfully!")
        print()
        print("[IMPORTANT] You still need to:")
        print("1. Add DKIM record from Google Workspace Admin Console")
        print("2. Add DMARC record (if you have one)")
        print("3. Verify all MX records are set to DNS only (grey cloud)")
        print("4. Update nameservers in Squarespace")
    else:
        print("[WARNING] Some records failed to add. Please check the errors above.")


if __name__ == "__main__":
    main()
