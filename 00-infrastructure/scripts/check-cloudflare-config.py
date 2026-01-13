#!/usr/bin/env python3
"""
Check and fix Cloudflare configuration for Infisical header/session issues
"""

import os
import sys
from pathlib import Path
from typing import Any

import requests

# Load .env file
try:
    from dotenv import load_dotenv

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    env_file = project_root / ".env"
    load_dotenv(env_file)
except ImportError:
    # If python-dotenv not available, try to load manually
    pass

# Configuration
DOMAIN = "datacrew.space"
INFISICAL_SUBDOMAIN = "infisical"
INFISICAL_HOSTNAME = f"{INFISICAL_SUBDOMAIN}.{DOMAIN}"

# Get credentials from environment
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_EMAIL = os.getenv("CLOUDFLARE_EMAIL", "")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "")


def get_auth_headers() -> dict[str, str]:
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
    raise ValueError(
        "Cloudflare credentials not found!\n"
        "Set one of:\n"
        "  - CLOUDFLARE_API_TOKEN (recommended)\n"
        "  - CLOUDFLARE_EMAIL + CLOUDFLARE_API_KEY"
    )


def get_zone_id(headers: dict[str, str]) -> str | None:
    """Get zone ID for the domain."""
    url = f"https://api.cloudflare.com/client/v4/zones?name={DOMAIN}"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("result"):
                zone_id = data["result"][0]["id"]
                print(f"✅ Found zone ID: {zone_id}")
                return zone_id
        print(f"❌ Failed to get zone ID: {response.status_code}")
        return None
    except Exception as e:
        print(f"❌ Error getting zone ID: {e}")
        return None


def check_ssl_tls_mode(headers: dict[str, str], zone_id: str) -> dict[str, Any]:
    """Check SSL/TLS encryption mode."""
    print("\n" + "=" * 60)
    print("1. Checking SSL/TLS Mode")
    print("=" * 60)

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/ssl"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                ssl_mode = data["result"]["value"]
                print(f"   Current SSL/TLS Mode: {ssl_mode}")

                if ssl_mode == "flexible":
                    print("   ❌ PROBLEM: SSL/TLS mode is 'flexible'")
                    print("      This breaks secure cookies and sessions!")
                    print("      → Should be 'full' or 'full_strict'")
                    return {"status": "error", "current": ssl_mode, "should_be": "full"}
                if ssl_mode in ["full", "full_strict"]:
                    print("   ✅ SSL/TLS mode is correct")
                    return {"status": "ok", "current": ssl_mode}
                print(f"   ⚠️  Unknown SSL mode: {ssl_mode}")
                return {"status": "warning", "current": ssl_mode}
        print(f"   ❌ Failed to get SSL settings: {response.status_code}")
        return {"status": "error"}
    except Exception as e:
        print(f"   ❌ Error checking SSL mode: {e}")
        return {"status": "error"}


def fix_ssl_tls_mode(headers: dict[str, str], zone_id: str, mode: str = "full") -> bool:
    """Fix SSL/TLS mode."""
    print(f"\n   🔧 Fixing SSL/TLS mode to '{mode}'...")
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/ssl"
    payload = {"value": mode}
    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"   ✅ SSL/TLS mode updated to '{mode}'")
                return True
        print(f"   ❌ Failed to update SSL mode: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False
    except Exception as e:
        print(f"   ❌ Error updating SSL mode: {e}")
        return False


def check_page_rules(headers: dict[str, str], zone_id: str) -> dict[str, Any]:
    """Check Page Rules for API caching."""
    print("\n" + "=" * 60)
    print("2. Checking Page Rules (Caching)")
    print("=" * 60)

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/pagerules"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                rules = data.get("result", [])
                print(f"   Found {len(rules)} page rule(s)")

                api_rules = []
                for rule in rules:
                    targets = rule.get("targets", [])
                    for target in targets:
                        if target.get("constraint", {}).get("operator") == "matches":
                            pattern = target.get("constraint", {}).get("value", "")
                            if "/api" in pattern or INFISICAL_HOSTNAME in pattern:
                                api_rules.append(
                                    {
                                        "id": rule.get("id"),
                                        "pattern": pattern,
                                        "actions": rule.get("actions", []),
                                    }
                                )

                if api_rules:
                    print("   ✅ Found API-related page rules:")
                    for rule in api_rules:
                        print(f"      - Pattern: {rule['pattern']}")
                        cache_action = None
                        for action in rule["actions"]:
                            if action.get("id") == "cache_level":
                                cache_action = action.get("value")
                                break
                        if cache_action:
                            print(f"        Cache Level: {cache_action}")
                            if cache_action != "bypass":
                                print("        ⚠️  Should be 'bypass' for API endpoints")
                        else:
                            print("        ⚠️  No cache level set - should be 'bypass'")
                    return {"status": "found", "rules": api_rules}
                print("   ⚠️  No page rules found for API endpoints")
                print(
                    "      → Should create rule: infisical.datacrew.space/api/* → Cache Level: Bypass"
                )
                return {"status": "missing"}
        print(f"   ❌ Failed to get page rules: {response.status_code}")
        return {"status": "error"}
    except Exception as e:
        print(f"   ❌ Error checking page rules: {e}")
        return {"status": "error"}


def create_api_bypass_rule(headers: dict[str, str], zone_id: str) -> bool:
    """Create a page rule to bypass cache for API endpoints."""
    print(f"\n   🔧 Creating page rule to bypass cache for {INFISICAL_HOSTNAME}/api/*...")
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/pagerules"
    payload = {
        "targets": [
            {
                "target": "url",
                "constraint": {"operator": "matches", "value": f"{INFISICAL_HOSTNAME}/api/*"},
            }
        ],
        "actions": [
            {"id": "cache_level", "value": "bypass"},
            {"id": "disable_apps", "value": True},
            {"id": "disable_performance", "value": True},
        ],
        "priority": 1,
        "status": "active",
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("   ✅ Page rule created successfully")
                return True
        print(f"   ❌ Failed to create page rule: {response.status_code}")
        print(f"   Response: {response.text[:300]}")
        return False
    except Exception as e:
        print(f"   ❌ Error creating page rule: {e}")
        return False


def check_transform_rules(headers: dict[str, str], zone_id: str) -> dict[str, Any]:
    """Check Transform Rules for header modifications."""
    print("\n" + "=" * 60)
    print("3. Checking Transform Rules (Header Modifications)")
    print("=" * 60)

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                rulesets = data.get("result", [])
                print(f"   Found {len(rulesets)} ruleset(s)")

                header_rules = []
                for ruleset in rulesets:
                    if ruleset.get("kind") in [
                        "http_request_header_modification",
                        "http_response_header_modification",
                    ]:
                        ruleset_id = ruleset.get("id")
                        ruleset_name = ruleset.get("name", "unknown")

                        # Get rules in this ruleset
                        rules_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets/{ruleset_id}"
                        rules_response = requests.get(rules_url, headers=headers, timeout=30)
                        if rules_response.status_code == 200:
                            rules_data = rules_response.json()
                            if rules_data.get("success"):
                                rules = rules_data.get("result", {}).get("rules", [])
                                for rule in rules:
                                    if INFISICAL_HOSTNAME in str(rule.get("expression", "")):
                                        header_rules.append({"ruleset": ruleset_name, "rule": rule})

                if header_rules:
                    print("   ⚠️  Found Transform Rules affecting Infisical:")
                    for rule_info in header_rules:
                        print(f"      - Ruleset: {rule_info['ruleset']}")
                        print(f"        Expression: {rule_info['rule'].get('expression', 'N/A')}")
                        actions = rule_info["rule"].get("action_parameters", {})
                        if "headers" in actions:
                            for header in actions["headers"]:
                                print(
                                    f"        Header: {header.get('name')} = {header.get('value')}"
                                )
                                if "content-type" in header.get("name", "").lower():
                                    print("        ❌ PROBLEM: This modifies Content-Type header!")
                    return {"status": "found", "rules": header_rules}
                print("   ✅ No Transform Rules found affecting Infisical")
                return {"status": "ok"}
        print(f"   ❌ Failed to get transform rules: {response.status_code}")
        return {"status": "error"}
    except Exception as e:
        print(f"   ❌ Error checking transform rules: {e}")
        return {"status": "error"}


def check_access_applications(
    headers: dict[str, str], account_id: str | None = None
) -> dict[str, Any]:
    """Check Cloudflare Access applications."""
    print("\n" + "=" * 60)
    print("4. Checking Cloudflare Access Applications")
    print("=" * 60)

    # First, get account ID if not provided
    if not account_id:
        try:
            account_url = "https://api.cloudflare.com/client/v4/accounts"
            account_response = requests.get(account_url, headers=headers, timeout=30)
            if account_response.status_code == 200:
                account_data = account_response.json()
                if account_data.get("success") and account_data.get("result"):
                    account_id = account_data["result"][0]["id"]
                    print(f"   Found account ID: {account_id}")
        except Exception as e:
            print(f"   ⚠️  Could not get account ID: {e}")
            print("   Skipping Access check (requires account-level API)")
            return {"status": "skipped"}

    if not account_id:
        print("   ⚠️  Account ID required for Access check")
        print("   → Check manually in Zero Trust dashboard")
        return {"status": "manual_check"}

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                apps = data.get("result", [])
                print(f"   Found {len(apps)} Access application(s)")

                infisical_apps = []
                for app in apps:
                    domain = app.get("domain", "")
                    if INFISICAL_HOSTNAME in domain or INFISICAL_SUBDOMAIN in domain.lower():
                        infisical_apps.append(app)

                if infisical_apps:
                    print("   ⚠️  Found Cloudflare Access application(s) for Infisical:")
                    for app in infisical_apps:
                        print(f"      - Name: {app.get('name', 'N/A')}")
                        print(f"        Domain: {app.get('domain', 'N/A')}")
                        print(f"        ID: {app.get('id', 'N/A')}")
                        print("      → This might interfere with Infisical's own auth!")
                    return {"status": "found", "apps": infisical_apps}
                print("   ✅ No Cloudflare Access applications found for Infisical")
                return {"status": "ok"}
        print(f"   ❌ Failed to get Access applications: {response.status_code}")
        return {"status": "error"}
    except Exception as e:
        print(f"   ❌ Error checking Access applications: {e}")
        return {"status": "error"}


def check_browser_integrity(headers: dict[str, str], zone_id: str) -> dict[str, Any]:
    """Check Browser Integrity Check setting."""
    print("\n" + "=" * 60)
    print("5. Checking Browser Integrity Check")
    print("=" * 60)

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/security_level"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                level = data["result"]["value"]
                print(f"   Current Security Level: {level}")

                if level in ["high", "under_attack"]:
                    print("   ⚠️  Security level is high - might block legitimate requests")
                    print("      → Consider setting to 'medium'")
                    return {"status": "high", "current": level}
                print("   ✅ Security level is reasonable")
                return {"status": "ok", "current": level}
        print(f"   ❌ Failed to get security level: {response.status_code}")
        return {"status": "error"}
    except Exception as e:
        print(f"   ❌ Error checking security level: {e}")
        return {"status": "error"}


def purge_cache(headers: dict[str, str], zone_id: str) -> bool:
    """Purge Cloudflare cache."""
    print("\n" + "=" * 60)
    print("6. Purging Cloudflare Cache")
    print("=" * 60)

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
    payload = {"purge_everything": True}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("   ✅ Cache purged successfully")
                return True
        print(f"   ❌ Failed to purge cache: {response.status_code}")
        return False
    except Exception as e:
        print(f"   ❌ Error purging cache: {e}")
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check and fix Cloudflare configuration for Infisical"
    )
    parser.add_argument("--fix-ssl", action="store_true", help="Fix SSL/TLS mode to 'full'")
    parser.add_argument(
        "--create-page-rule", action="store_true", help="Create API bypass page rule"
    )
    parser.add_argument("--purge-cache", action="store_true", help="Purge Cloudflare cache")
    parser.add_argument("--fix-all", action="store_true", help="Apply all fixes")
    args = parser.parse_args()

    print("=" * 60)
    print("Cloudflare Configuration Check for Infisical")
    print("=" * 60)
    print(f"\nChecking configuration for: {INFISICAL_HOSTNAME}")
    print()

    # Check credentials
    try:
        headers = get_auth_headers()
        print("✅ Cloudflare API credentials found")
    except ValueError as e:
        print(f"❌ {e}")
        print("\nPlease set credentials in .env file:")
        print("  CLOUDFLARE_API_TOKEN=your_token_here")
        print("\nOr:")
        print("  CLOUDFLARE_EMAIL=your_email@example.com")
        print("  CLOUDFLARE_API_KEY=your_api_key_here")
        sys.exit(1)

    # Get zone ID
    zone_id = get_zone_id(headers)
    if not zone_id:
        print("\n❌ Could not get zone ID. Exiting.")
        sys.exit(1)

    # Run checks
    results = {}

    # 1. SSL/TLS Mode
    ssl_result = check_ssl_tls_mode(headers, zone_id)
    results["ssl"] = ssl_result

    # 2. Page Rules
    page_rules_result = check_page_rules(headers, zone_id)
    results["page_rules"] = page_rules_result

    # 3. Transform Rules
    transform_result = check_transform_rules(headers, zone_id)
    results["transform"] = transform_result

    # 4. Access Applications
    access_result = check_access_applications(headers)
    results["access"] = access_result

    # 5. Browser Integrity
    security_result = check_browser_integrity(headers, zone_id)
    results["security"] = security_result

    # Summary
    print("\n" + "=" * 60)
    print("Summary & Recommendations")
    print("=" * 60)

    issues_found = False

    if ssl_result.get("status") == "error":
        print("\n❌ ISSUE: SSL/TLS mode is 'flexible'")
        print("   → This MUST be fixed!")
        issues_found = True

    if page_rules_result.get("status") == "missing":
        print("\n⚠️  RECOMMENDATION: Create page rule to bypass cache for /api/*")
        issues_found = True

    if transform_result.get("status") == "found":
        print("\n⚠️  WARNING: Transform Rules found that might modify headers")
        print("   → Review and disable if modifying Content-Type")
        issues_found = True

    if access_result.get("status") == "found":
        print("\n⚠️  WARNING: Cloudflare Access enabled for Infisical")
        print("   → This might interfere with Infisical's authentication")
        issues_found = True

    if not issues_found:
        print("\n✅ No major issues found!")
        print("   Cloudflare configuration looks good.")

    # Check API permissions
    print("\n" + "=" * 60)
    print("API Permissions Check")
    print("=" * 60)

    # Test token permissions
    test_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/ssl"
    test_response = requests.get(test_url, headers=headers, timeout=30)

    if test_response.status_code == 403:
        print("❌ API token lacks required permissions")
        print("   Required permissions:")
        print("   - Zone:Zone Settings:Read")
        print("   - Zone:Zone Settings:Edit")
        print("   - Zone:Page Rules:Read")
        print("   - Zone:Page Rules:Edit")
        print("   - Zone:Cache Purge:Edit")
        print("\n   Update your API token at:")
        print("   https://dash.cloudflare.com/profile/api-tokens")
        print("\n   Or use Global API Key + Email (less secure)")
        return

    # Auto-fix options (non-interactive - show recommendations)
    print("\n" + "=" * 60)
    print("Recommended Fixes")
    print("=" * 60)

    fixes_needed = []

    if ssl_result.get("status") == "error":
        print("\n🔧 SSL/TLS Mode needs fixing")
        print("   Run this command to fix:")
        print("   python3 00-infrastructure/scripts/check-cloudflare-config.py --fix-ssl")
        fixes_needed.append("ssl")

    if page_rules_result.get("status") == "missing":
        print("\n🔧 Page Rule needs to be created")
        print("   Run this command to fix:")
        print("   python3 00-infrastructure/scripts/check-cloudflare-config.py --create-page-rule")
        fixes_needed.append("page_rule")

    if fixes_needed:
        print("\n   Or fix all at once:")
        print("   python3 00-infrastructure/scripts/check-cloudflare-config.py --fix-all")

    print("\n🔧 To purge cache:")
    print("   python3 00-infrastructure/scripts/check-cloudflare-config.py --purge-cache")

    # Apply fixes if requested
    if (args.fix_all or args.fix_ssl) and ssl_result.get("status") == "error":
        fix_ssl_tls_mode(headers, zone_id, "full")

    if (args.fix_all or args.create_page_rule) and page_rules_result.get("status") == "missing":
        create_api_bypass_rule(headers, zone_id)

    if args.fix_all or args.purge_cache:
        purge_cache(headers, zone_id)

    print("\n✅ Check complete!")
    print("\nNext steps:")
    print("1. Clear browser cache and cookies")
    print("2. Try logging into Infisical again")
    print("3. Check browser console for any remaining errors")


if __name__ == "__main__":
    main()
