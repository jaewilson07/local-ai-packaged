#!/usr/bin/env python3
"""
check_access_policy.py

Check which Cloudflare Access applications a given email has access to.
"""

import argparse
import os
import subprocess
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from project root
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)


def get_infisical_secrets() -> dict[str, str]:
    """Get secrets from Infisical using CLI."""
    secrets_dict = {}
    try:
        result = subprocess.run(
            ["infisical", "export", "--format=dotenv"],
            capture_output=True,
            text=True,
            timeout=30,
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


def email_matches_rule(email: str, rule: dict) -> bool:
    """Check if an email matches a policy rule."""
    if "email" in rule:
        rule_email = rule["email"].get("email", "")
        return email.lower() == rule_email.lower()
    elif "email_domain" in rule:
        domain = rule["email_domain"].get("domain", "")
        if domain.startswith("@"):
            domain = domain[1:]
        return email.lower().endswith(f"@{domain.lower()}")
    elif "everyone" in rule:
        return True  # Everyone rule matches all emails
    return False


def check_email_access_to_app(
    email: str, app: dict, policies: list[dict]
) -> tuple[bool, list[str]]:
    """Check if email has access to an application based on policies.

    Returns:
        Tuple of (has_access, reasons) where reasons is a list of policy names that grant access.
    """
    reasons = []

    for policy in policies:
        decision = policy.get("decision", "allow")
        if decision != "allow":
            continue  # Only check allow policies

        include_rules = policy.get("include", [])
        for rule in include_rules:
            if email_matches_rule(email, rule):
                reasons.append(policy.get("name", "Unnamed Policy"))
                break

    return len(reasons) > 0, reasons


def get_auth_headers():
    """Get authentication headers for Cloudflare API."""
    API_TOKEN = get_env_var("CLOUDFLARE_API_TOKEN", "")  # noqa: N806
    CLOUDFLARE_EMAIL = get_env_var("CLOUDFLARE_EMAIL", "")  # noqa: N806
    CLOUDFLARE_API_KEY = get_env_var("CLOUDFLARE_API_KEY", "")  # noqa: N806

    if API_TOKEN and API_TOKEN.strip():
        return {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
        }
    elif (
        CLOUDFLARE_EMAIL
        and CLOUDFLARE_EMAIL.strip()
        and CLOUDFLARE_API_KEY
        and CLOUDFLARE_API_KEY.strip()
    ):
        return {
            "X-Auth-Email": CLOUDFLARE_EMAIL.strip(),
            "X-Auth-Key": CLOUDFLARE_API_KEY.strip(),
            "Content-Type": "application/json",
        }
    else:
        raise ValueError("Either API token or email+API key must be provided")


def main():
    parser = argparse.ArgumentParser(
        description="Check which Cloudflare Access applications an email has access to"
    )
    parser.add_argument("email", help="Email address to check access for")
    parser.add_argument(
        "--account-id",
        help="Cloudflare Account ID (defaults to CLOUDFLARE_ACCOUNT_ID from .env)",
        default=None,
    )
    parser.add_argument(
        "--tunnel-id",
        help="Cloudflare Tunnel ID (defaults to CLOUDFLARE_TUNNEL_ID from .env)",
        default=None,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed policy information for each application",
    )

    args = parser.parse_args()
    email = args.email.lower().strip()

    # Get account_id and tunnel_id from args or .env
    account_id = args.account_id or get_env_var("CLOUDFLARE_ACCOUNT_ID", "")
    tunnel_id = args.tunnel_id or get_env_var("CLOUDFLARE_TUNNEL_ID", "")

    if not account_id:
        print(
            "[ERROR] Account ID is required. Set CLOUDFLARE_ACCOUNT_ID in .env or use --account-id"
        )
        return

    print("=" * 70)
    print(f"Cloudflare Access Check for: {email}")
    print("=" * 70)
    print()

    try:
        headers = get_auth_headers()
    except ValueError as e:
        print(f"[ERROR] {e}")
        return

    # Get all Access Applications
    print("Fetching Access Applications...")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps"
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        print(f"[ERROR] Failed to fetch applications: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        return

    data = response.json()
    if not data.get("success"):
        error_msg = data.get("errors", [{}])[0].get("message", "Unknown error")
        print(f"[ERROR] API error: {error_msg}")
        return

    apps = data.get("result", [])
    print(f"Found {len(apps)} Access Application(s)\n")

    accessible_apps = []
    inaccessible_apps = []

    # Check each application
    for app in apps:
        app_id = app.get("id")
        app_name = app.get("name", "Unnamed")
        app_domain = app.get("domain", "N/A")

        # Get policies for this application
        policy_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps/{app_id}/policies"
        policy_response = requests.get(policy_url, headers=headers, timeout=30)

        if policy_response.status_code != 200:
            if args.verbose:
                print(
                    f"⚠️  {app_name} ({app_domain}): Could not fetch policies (HTTP {policy_response.status_code})"
                )
            inaccessible_apps.append((app, "Could not fetch policies"))
            continue

        policy_data = policy_response.json()
        if not policy_data.get("success"):
            if args.verbose:
                print(f"⚠️  {app_name} ({app_domain}): API error fetching policies")
            inaccessible_apps.append((app, "API error"))
            continue

        policies = policy_data.get("result", [])
        has_access, reasons = check_email_access_to_app(email, app, policies)

        if has_access:
            accessible_apps.append((app, reasons))
            print(f"✅ {app_name}")
            print(f"   Domain: {app_domain}")
            print(f"   Granted by: {', '.join(reasons) if reasons else 'Unknown'}")
            if args.verbose:
                print(f"   App ID: {app_id}")
                print(f"   Session Duration: {app.get('session_duration', 'N/A')}")
            print()
        else:
            inaccessible_apps.append((app, "No matching policies"))
            if args.verbose:
                print(f"❌ {app_name}")
                print(f"   Domain: {app_domain}")
                print("   Reason: No matching policies")
                print(f"   Total policies: {len(policies)}")
                print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Email: {email}")
    print(f"Accessible Applications: {len(accessible_apps)}")
    print(f"Inaccessible Applications: {len(inaccessible_apps)}")
    print()

    if accessible_apps:
        print("✅ Applications with ACCESS:")
        for app, reasons in accessible_apps:
            print(f"   - {app.get('name')} ({app.get('domain')})")
            if reasons:
                print(f"     Policies: {', '.join(reasons)}")
        print()

    if args.verbose and inaccessible_apps:
        print("❌ Applications WITHOUT ACCESS:")
        for app, reason in inaccessible_apps:
            print(f"   - {app.get('name')} ({app.get('domain')}) - {reason}")
        print()

    # Check tunnel configuration if tunnel_id is provided
    if tunnel_id:
        print("=" * 70)
        print("Tunnel Route Configuration")
        print("=" * 70)
        tunnel_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations"
        tunnel_response = requests.get(tunnel_url, headers=headers, timeout=30)

        if tunnel_response.status_code == 200:
            tunnel_data = tunnel_response.json()
            if tunnel_data.get("success"):
                config = tunnel_data.get("result", {}).get("config", {})
                ingress = config.get("ingress", [])

                print(f"Found {len(ingress)} tunnel route(s):\n")
                for rule in ingress:
                    hostname = rule.get("hostname", "N/A")
                    origin_request = rule.get("originRequest", {})
                    access_config = origin_request.get("access", {})
                    access_enabled = access_config.get("required", False)

                    # Check if this hostname matches any accessible app
                    matching_app = None
                    for app, _ in accessible_apps:
                        if app.get("domain") == hostname:
                            matching_app = app
                            break

                    status = "✅" if matching_app else "⚠️"
                    print(f"{status} {hostname}")
                    if access_enabled:
                        print(f"   Access: Enabled (App Tag: {access_config.get('audTag', 'N/A')})")
                        if matching_app:
                            print(
                                f"   ✅ Matches accessible application: {matching_app.get('name')}"
                            )
                    else:
                        print("   Access: Disabled")
                    print()
            else:
                print("⚠️  Could not parse tunnel configuration")
        else:
            print(f"⚠️  Could not fetch tunnel config: HTTP {tunnel_response.status_code}")


if __name__ == "__main__":
    main()
