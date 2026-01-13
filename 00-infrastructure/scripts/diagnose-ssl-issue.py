#!/usr/bin/env python3
"""
Diagnose SSL/TLS issues causing Chrome "Dangerous Site" warning
"""

import os
import subprocess
import sys
from pathlib import Path

import requests

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
TEST_HOSTNAME = "n8n.datacrew.space"

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_EMAIL = os.getenv("CLOUDFLARE_EMAIL", "")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "")


def get_auth_headers():
    """Get authentication headers for Cloudflare API."""
    if CLOUDFLARE_API_TOKEN and CLOUDFLARE_API_TOKEN.strip():
        return {
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN.strip()}",
            "Content-Type": "application/json",
        }
    if CLOUDFLARE_EMAIL and CLOUDFLARE_API_KEY:
        return {
            "X-Auth-Email": CLOUDFLARE_EMAIL.strip(),
            "X-Auth-Key": CLOUDFLARE_API_KEY.strip(),
            "Content-Type": "application/json",
        }
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


def check_ssl_certificate():
    """Check SSL certificate using openssl."""
    print("=" * 60)
    print("1. Checking SSL Certificate")
    print("=" * 60)

    try:
        result = subprocess.run(
            [
                "openssl",
                "s_client",
                "-connect",
                f"{TEST_HOSTNAME}:443",
                "-servername",
                TEST_HOSTNAME,
            ],
            input=b"",
            capture_output=True,
            timeout=10,
            check=False,
        )

        output = result.stdout.decode()

        # Check for certificate details
        if "Certificate chain" in output:
            print("✅ SSL certificate found")

            # Extract issuer
            for line in output.split("\n"):
                if "issuer=" in line:
                    print(f"  Issuer: {line.strip()}")
                if "subject=" in line:
                    print(f"  Subject: {line.strip()}")

            # Check for errors
            if "Verify return code: 0 (ok)" in output:
                print("✅ Certificate verification: OK")
                return True
            for line in output.split("\n"):
                if "Verify return code:" in line:
                    print(f"❌ Certificate verification: {line.strip()}")
                    return False
        else:
            print("❌ No certificate found or connection failed")
            return False

    except FileNotFoundError:
        print("⚠️  openssl not found, skipping certificate check")
        return None
    except Exception as e:
        print(f"❌ Error checking certificate: {e}")
        return False


def check_ssl_mode(headers, zone_id):
    """Check Cloudflare SSL/TLS mode."""
    print("\n" + "=" * 60)
    print("2. Checking Cloudflare SSL/TLS Mode")
    print("=" * 60)

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/ssl"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                ssl_mode = data["result"]["value"]
                print(f"  Current mode: {ssl_mode}")

                print("\n  📚 SSL/TLS Mode Explanation:")
                print("    - flexible: HTTPS to visitors, HTTP to origin (simplest)")
                print("    - full: HTTPS to visitors, HTTPS to origin (self-signed OK)")
                print("    - full_strict: HTTPS to visitors, valid HTTPS to origin (most secure)")

                print("\n  🔍 Analysis:")
                if ssl_mode == "flexible":
                    print("    ✅ Flexible mode is correct for Cloudflare Tunnel with HTTP origin")
                    print("       (Tunnel encrypts the connection, Caddy serves HTTP)")
                elif ssl_mode == "full":
                    print("    ⚠️  Full mode expects HTTPS on origin")
                    print("       Your Caddy has 'auto_https off', so it serves HTTP only")
                    print("       This WILL cause SSL errors!")
                    print("\n    🔧 Recommended fix: Change to 'flexible' mode")
                    return {"mode": ssl_mode, "issue": "mismatch"}
                elif ssl_mode == "full_strict":
                    print("    ❌ Full (strict) mode requires valid HTTPS certificate on origin")
                    print("       Your Caddy has 'auto_https off', so it serves HTTP only")
                    print("       This WILL cause SSL errors!")
                    print("\n    🔧 Recommended fix: Change to 'flexible' mode")
                    return {"mode": ssl_mode, "issue": "mismatch"}

                return {"mode": ssl_mode, "issue": None}
    except Exception as e:
        print(f"❌ Error checking SSL mode: {e}")

    return {"mode": None, "issue": "unknown"}


def check_http_strict_transport_security(headers, zone_id):
    """Check HSTS settings."""
    print("\n" + "=" * 60)
    print("3. Checking HSTS (HTTP Strict Transport Security)")
    print("=" * 60)

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/security_header"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                hsts = data["result"]["value"]
                if hsts.get("strict_transport_security", {}).get("enabled"):
                    print("  ✅ HSTS is enabled")
                    max_age = hsts["strict_transport_security"].get("max_age")
                    print(f"    Max age: {max_age} seconds")
                else:
                    print("  [i] HSTS is disabled (OK for testing)")
    except Exception as e:
        print(f"  ⚠️  Could not check HSTS: {e}")


def fix_ssl_mode(headers, zone_id):
    """Fix SSL/TLS mode to flexible."""
    print("\n" + "=" * 60)
    print("🔧 Fixing SSL/TLS Mode")
    print("=" * 60)

    print("\n  Changing SSL/TLS mode to 'flexible'...")
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/ssl"
    payload = {"value": "flexible"}

    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("  ✅ SSL/TLS mode changed to 'flexible'")
                print("\n  ⏱️  Changes may take 1-5 minutes to propagate")
                print("     Clear browser cache and try again")
                return True

        print(f"  ❌ Failed to update SSL mode: {response.status_code}")
        print(f"     {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ Error fixing SSL mode: {e}")

    return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Diagnose SSL/TLS issues")
    parser.add_argument("--fix", action="store_true", help="Automatically fix SSL mode")
    args = parser.parse_args()

    print("=" * 60)
    print("SSL/TLS Diagnostic Tool")
    print("=" * 60)
    print(f"Testing: {TEST_HOSTNAME}\n")

    # Check certificate
    check_ssl_certificate()

    # Check Cloudflare settings
    headers = get_auth_headers()
    zone_id = get_zone_id(headers)

    if not zone_id:
        print("\n❌ Could not get zone ID")
        sys.exit(1)

    ssl_info = check_ssl_mode(headers, zone_id)
    check_http_strict_transport_security(headers, zone_id)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    if ssl_info.get("issue") == "mismatch":
        print("\n❌ PROBLEM FOUND:")
        print(f"   Cloudflare SSL mode: {ssl_info.get('mode')}")
        print("   Origin (Caddy): HTTP only (auto_https off)")
        print("   → Mode mismatch causes SSL errors\n")

        if args.fix:
            if fix_ssl_mode(headers, zone_id):
                print("\n✅ Fix applied! Wait 1-5 minutes, then:")
                print("   1. Clear browser cache")
                print("   2. Try accessing the site again")
        else:
            print("   🔧 To fix automatically, run:")
            print("      python3 00-infrastructure/scripts/diagnose-ssl-issue.py --fix")
    else:
        print("\n✅ SSL configuration looks correct")
        print("   If you're still seeing errors:")
        print("   1. Clear browser cache and cookies")
        print("   2. Try incognito/private mode")
        print("   3. Check browser console for specific errors")


if __name__ == "__main__":
    main()
