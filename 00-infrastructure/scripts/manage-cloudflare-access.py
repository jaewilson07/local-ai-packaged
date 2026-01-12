#!/usr/bin/env python3
"""
cloudflare_manage_unified_access_for_services.py

Manage unified access policies across all Cloudflare Tunnel applications.
This script ensures all applications use the same reusable access policies.

================================================================================
COMPREHENSIVE DOCUMENTATION: MANAGING ACCESS TO APPS
================================================================================

OVERVIEW
--------
When you have multiple applications exposed through Cloudflare Tunnel (ComfyUI,
N8N, Open WebUI, etc.), managing access policies individually becomes tedious
and error-prone. This script helps you create and manage unified access policies
that can be shared across all applications.

THE PROBLEM
-----------
- Each application needs its own access policy
- Updating access rules requires changing each application individually
- Inconsistencies can occur between applications
- Managing multiple policies is time-consuming

THE SOLUTION: REUSABLE POLICIES
-------------------------------
Cloudflare Access supports reusable policies that can be shared across multiple
applications. Benefits:
- ✅ Consistency: All applications use the same access rules
- ✅ Centralized Management: Update once, applies everywhere
- ✅ Easier Maintenance: No need to update each application individually
- ✅ Reduced Errors: Single source of truth for access rules

QUICK START
-----------
1. Configure your access rules in Infisical or .env:
   ```bash
   CLOUDFLARE_ACCESS_EMAILS=jaewilson07@gmail.com,user2@example.com
   CLOUDFLARE_ACCESS_EMAIL_DOMAIN=@datacrew.space  # Optional
   GOOGLE_IDP_ID=783bfc56-e5c3-451f-9eb9-c8d5f741b1c3  # Optional, for Google OAuth
   ```

2. Create the standard reusable policy:
   ```bash
   python3 cloudflare_manage_unified_access_for_services.py --create-policy
   ```

3. Apply to all applications (via dashboard recommended):
   - Go to https://one.dash.cloudflare.com/
   - Access → Applications → [Your App]
   - Policies → Add a policy → Select "Standard Access Policy"
   - Repeat for each application

4. List all applications and their policies:
   ```bash
   python3 cloudflare_manage_unified_access_for_services.py --list
   ```

SETUP STEPS (DETAILED)
----------------------

Step 1: Configure Standard Access Rules
----------------------------------------
Set your standard access configuration in Infisical or `.env`:

```bash
# Standard emails allowed across all applications
CLOUDFLARE_ACCESS_EMAILS=jaewilson07@gmail.com,user2@example.com

# OR email domain (allows everyone from a domain)
CLOUDFLARE_ACCESS_EMAIL_DOMAIN=@datacrew.space

# Google OAuth IDP ID (optional, if using Google OAuth)
GOOGLE_IDP_ID=783bfc56-e5c3-451f-9eb9-c8d5f741b1c3
```

Step 2: Create Standard Reusable Policy
----------------------------------------
Run the management script to create a standard reusable policy:

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged
python3 00-infrastructure/docs/cloudflare/setup/cloudflare_manage_unified_access_for_services.py --create-policy
```

This will:
- ✅ Create a reusable policy named "Standard Access Policy"
- ✅ Configure it with your access rules (emails, Google OAuth, etc.)
- ✅ Make it available to all applications

Step 3: Apply to All Applications
-----------------------------------
Via Dashboard (Recommended):
1. Go to https://one.dash.cloudflare.com/
2. Navigate to Access → Applications
3. For each application:
   - Click on the application
   - Go to Policies tab
   - Click Add a policy
   - Select "Standard Access Policy" from reusable policies
   - Click Save

Via API Script:
```bash
python3 cloudflare_manage_unified_access_for_services.py --apply-all
```

Note: The API has limitations for adding reusable policies. You may need to
add them via the dashboard.

Step 4: Verify Configuration
-----------------------------
List all applications and their policies:

```bash
python3 cloudflare_manage_unified_access_for_services.py --list
```

This will show:
- All applications
- Their current policies
- Which ones use the standard reusable policy

ADDING A NEW APPLICATION
-----------------------
When you add a new application to your tunnel:

1. Create Access Application (via dashboard or API):
   - Name: YourApp
   - Domain: yourapp.datacrew.space

2. Add Standard Policy:
   - Go to Access → Applications → YourApp
   - Click Add a policy
   - Select "Standard Access Policy"
   - Save

3. Link to Tunnel Route:
   - Go to Networks → Tunnels → Your tunnel
   - Edit route for yourapp.datacrew.space
   - Under Access, select YourApp
   - Save

That's it! The new application now uses the same access rules as all your
other applications.

UPDATING ACCESS RULES
----------------------
When you need to update who can access your applications:

Method 1: Update Reusable Policy (Recommended)
1. Go to Access → Authentication → Policies (or find it via an application)
2. Find "Standard Access Policy"
3. Click Edit
4. Update the access rules (emails, groups, etc.)
5. Click Save

Result: All applications using this policy automatically get the updated rules!

Method 2: Update via Script
1. Update environment variables:
   ```bash
   infisical secrets set CLOUDFLARE_ACCESS_EMAILS=newuser@example.com,another@example.com
   ```

2. Recreate the policy:
   ```bash
   python3 cloudflare_manage_unified_access_for_services.py --create-policy
   ```

Note: You may need to remove the old policy first if recreating.

WILDCARD ACCESS PROTECTION
--------------------------
To protect datacrew.space and all its subdomains:

1. Create Wildcard Application:
   - Application name: Datacrew Wildcard Access
   - Application Domain: *.datacrew.space
   - Add "Standard Access Policy"

2. Create Root Domain Application:
   - Application name: Datacrew Root Access
   - Application Domain: datacrew.space
   - Add "Standard Access Policy"

3. Link to Tunnel Routes:
   - Networks → Tunnels → Your tunnel
   - For catch-all route, set Access to "Datacrew Wildcard Access"
   - For root domain route, set Access to "Datacrew Root Access"

Precedence: Specific applications (like comfyui.datacrew.space) take precedence
over wildcard applications, which is the desired behavior.

GOOGLE OAUTH SETUP
------------------
To enable Google OAuth authentication:

1. Create OAuth2 Application in Google Cloud Platform:
   - Go to https://console.cloud.google.com/
   - APIs & Services → Credentials
   - Create OAuth Client ID (Web application)
   - Authorized redirect URI: https://your-app.datacrew.space/cdn-cgi/access/callback

2. Add Google Identity Provider in Cloudflare:
   - Go to https://one.dash.cloudflare.com/
   - Access → Authentication → Login methods
   - Add new → Google
   - Enter Client ID and Client Secret
   - Save and note the IDP ID

3. Configure Policy with Google OAuth:
   - Set GOOGLE_IDP_ID in Infisical/.env
   - Run: python3 cloudflare_manage_unified_access_for_services.py --create-policy

Or update existing policy:
   - Access → Applications → Your App
   - Edit policy → Enable Google under Identity Providers

ENVIRONMENT VARIABLES
---------------------
Required:
- CLOUDFLARE_API_TOKEN: Cloudflare API token with Access permissions
  OR
- CLOUDFLARE_EMAIL + CLOUDFLARE_API_KEY: Global API key (less secure)

Optional:
- CLOUDFLARE_ACCESS_EMAILS: Comma-separated list of allowed emails
- CLOUDFLARE_ACCESS_EMAIL_DOMAIN: Email domain (e.g., @datacrew.space)
- GOOGLE_IDP_ID: Google Identity Provider ID for OAuth
- CLOUDFLARE_ACCOUNT_ID: Account ID (auto-detected if not provided)

USAGE EXAMPLES
--------------

# List all applications and policies
python3 cloudflare_manage_unified_access_for_services.py --list

# Create standard reusable policy
python3 cloudflare_manage_unified_access_for_services.py --create-policy

# Apply standard policy to all applications (check status)
python3 cloudflare_manage_unified_access_for_services.py --apply-all

# Create policy with custom name
python3 cloudflare_manage_unified_access_for_services.py --create-policy --policy-name "Team Access Policy"

TROUBLESHOOTING
---------------

Policy Not Showing in Application:
- Reusable policies must be added via the dashboard (API limitations)
- Go to Access → Applications → Your app → Policies → Add a policy

Policy Changes Not Applying:
- Cloudflare caches policies - wait a few minutes
- Clear browser cache and cookies
- Verify the policy is actually reusable (reusable: true)

Multiple Policies Conflict:
- Check policy precedence (lower numbers evaluated first)
- Ensure allow policies have lower precedence than deny policies
- Consider consolidating into a single reusable policy

API Errors:
- Verify CLOUDFLARE_API_TOKEN has Access permissions
- Check account ID is correct
- Ensure at least one application exists before creating reusable policy

BEST PRACTICES
--------------
1. One Standard Policy: Create a single reusable policy for all applications
2. Naming Convention: Use clear names like "Standard Access Policy" or "Team Access Policy"
3. Documentation: Document who should have access and why
4. Regular Review: Periodically review access logs to ensure policies are working
5. Test Changes: Test policy changes on a single application before applying everywhere

ADVANCED: MULTIPLE POLICY LEVELS
---------------------------------
You can create multiple reusable policies for different access levels:

- "Admin Access Policy": Full access (admins only)
- "Team Access Policy": Standard access (team members)
- "Read-Only Access Policy": Limited access (viewers)

Then apply the appropriate policy to each application based on its sensitivity.

API REFERENCE
-------------
The script uses these Cloudflare API endpoints:

- List Applications: GET /accounts/{account_id}/access/apps
- List Policies: GET /accounts/{account_id}/access/apps/{app_id}/policies
- Create Policy: POST /accounts/{account_id}/access/apps/{app_id}/policies
- Update Policy: PUT /accounts/{account_id}/access/apps/{app_id}/policies/{policy_id}

For more details, see:
https://developers.cloudflare.com/api/operations/access-policies-list-access-policies

RELATED SCRIPTS
---------------
- setup_comfyui_access.py: Configure Access for a specific application (ComfyUI)
- setup_wildcard_access.py: Set up wildcard domain protection
- update_policy_with_google_oauth.py: Update existing policy with Google OAuth

================================================================================
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

ACCOUNT_ID = "7552371386451b222f527fa794562a37"

# Standard reusable policy configuration
STANDARD_POLICY_NAME = "Standard Access Policy"
STANDARD_POLICY_DESCRIPTION = "Unified access policy for all tunnel applications"


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


def get_all_applications(headers, account_id):
    """Get all Access applications."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps"
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        print(f"[ERROR] Failed to get applications: HTTP {response.status_code}")
        return []

    data = response.json()
    if not data.get("success"):
        print(f"[ERROR] API error: {data.get('errors', [{}])[0].get('message', 'Unknown')}")
        return []

    return data.get("result", [])


def get_reusable_policies(headers, account_id):
    """Get all reusable policies."""
    # Reusable policies are stored at account level, not app level
    # We need to get them from any app that uses them
    apps = get_all_applications(headers, account_id)

    all_policies = {}
    for app in apps:
        app_id = app.get("id")
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps/{app_id}/policies"
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                policies = data.get("result", [])
                for policy in policies:
                    if policy.get("reusable"):
                        policy_id = policy.get("id")
                        if policy_id not in all_policies:
                            all_policies[policy_id] = policy

    return list(all_policies.values())


def create_or_get_standard_reusable_policy(headers, account_id):
    """Create or get the standard reusable policy."""
    # Get existing reusable policies
    reusable_policies = get_reusable_policies(headers, account_id)

    # Check if standard policy already exists
    for policy in reusable_policies:
        if policy.get("name") == STANDARD_POLICY_NAME:
            print(f"[SKIP] Standard reusable policy already exists: {STANDARD_POLICY_NAME}")
            return policy.get("id")

    # Get configuration from environment
    ALLOWED_EMAILS_STR = get_env_var("CLOUDFLARE_ACCESS_EMAILS", "")  # noqa: N806
    ALLOWED_EMAILS = ALLOWED_EMAILS_STR.split(",") if ALLOWED_EMAILS_STR else []  # noqa: N806
    ALLOWED_EMAIL_DOMAIN = get_env_var("CLOUDFLARE_ACCESS_EMAIL_DOMAIN", "")  # noqa: N806
    GOOGLE_IDP_ID = get_env_var("GOOGLE_IDP_ID", "")  # noqa: N806

    # Build include rules
    include_rules = []

    if ALLOWED_EMAILS and ALLOWED_EMAILS[0]:
        for raw_email in ALLOWED_EMAILS:
            email = raw_email.strip()
            if email:
                include_rules.append({"email": {"email": email}})

    if ALLOWED_EMAIL_DOMAIN:
        include_rules.append({"email_domain": {"domain": ALLOWED_EMAIL_DOMAIN}})

    if not include_rules:
        print("[WARNING] No access rules specified. Using 'everyone' rule (Email OTP).")
        include_rules.append({"everyone": {}})

    # Create policy data
    policy_data = {
        "name": STANDARD_POLICY_NAME,
        "decision": "allow",
        "include": include_rules,
        "reusable": True,  # Make it reusable
    }

    # Add Google OAuth if configured
    if GOOGLE_IDP_ID:
        policy_data["identity_provider_selectors"] = [GOOGLE_IDP_ID]

    # Create policy on first application (reusable policies are account-level)
    apps = get_all_applications(headers, account_id)
    if not apps:
        print("[ERROR] No applications found. Create at least one application first.")
        return None

    # Use first app to create reusable policy
    app_id = apps[0].get("id")
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps/{app_id}/policies"
    )

    try:
        response = requests.post(url, headers=headers, json=policy_data, timeout=30)
        if response.status_code in [200, 201]:
            result = response.json()
            if result.get("success"):
                policy_id = result["result"]["id"]
                print(
                    f"[OK] Created standard reusable policy: {STANDARD_POLICY_NAME} (ID: {policy_id})"
                )
                return policy_id
            else:
                errors = result.get("errors", [])
                if errors:
                    print(
                        f"[ERROR] Failed to create policy: {errors[0].get('message', 'Unknown error')}"
                    )
                return None
        else:
            print(f"[ERROR] Failed to create policy: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"[ERROR] Exception creating policy: {e}")
        return None


def apply_standard_policy_to_all_apps(headers, account_id, policy_id):
    """Apply the standard reusable policy to all applications."""
    apps = get_all_applications(headers, account_id)

    if not apps:
        print("[WARNING] No applications found")
        return

    print(f"\n[INFO] Applying standard policy to {len(apps)} application(s)...")

    for app in apps:
        app_id = app.get("id")
        app_name = app.get("name")
        app_domain = app.get("domain")

        # Get current policies
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps/{app_id}/policies"
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"   ⚠️  {app_name} ({app_domain}): Could not get policies")
            continue

        data = response.json()
        if not data.get("success"):
            print(f"   ⚠️  {app_name} ({app_domain}): API error")
            continue

        policies = data.get("result", [])

        # Check if standard policy is already applied
        has_standard_policy = False
        for policy in policies:
            if policy.get("id") == policy_id:
                has_standard_policy = True
                break

        if has_standard_policy:
            print(f"   ✅ {app_name} ({app_domain}): Already has standard policy")
        else:
            # Add standard policy to this app
            # Note: We can't directly add a reusable policy via API in the same way
            # Instead, we need to reference it by ID
            # However, Cloudflare API doesn't support "adding" a reusable policy directly
            # We need to create a new policy that references the reusable one, or
            # update the app's allowed_idps to match

            # For now, we'll just verify the policy exists and provide instructions
            print(f"   ⚠️  {app_name} ({app_domain}): Standard policy not applied")
            print("      Note: Reusable policies must be added via dashboard:")
            print("      1. Go to: https://one.dash.cloudflare.com/")
            print(f"      2. Access → Applications → {app_name}")
            print(f"      3. Edit policies → Add '{STANDARD_POLICY_NAME}'")
            print("      4. Save")


def list_all_applications_and_policies(headers, account_id):
    """List all applications and their policies."""
    apps = get_all_applications(headers, account_id)

    if not apps:
        print("[INFO] No applications found")
        return

    print(f"\n[INFO] Found {len(apps)} application(s):\n")

    for app in apps:
        app_id = app.get("id")
        app_name = app.get("name")
        app_domain = app.get("domain")

        print(f"Application: {app_name}")
        print(f"  Domain: {app_domain}")
        print(f"  ID: {app_id}")

        # Get policies
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps/{app_id}/policies"
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                policies = data.get("result", [])
                reusable = [p for p in policies if p.get("reusable")]
                non_reusable = [p for p in policies if not p.get("reusable")]

                print(f"  Policies ({len(policies)} total):")
                if reusable:
                    print(f"    Reusable ({len(reusable)}):")
                    for p in reusable:
                        print(f"      - {p.get('name')} ({p.get('decision')})")
                if non_reusable:
                    print(f"    App-specific ({len(non_reusable)}):")
                    for p in non_reusable:
                        print(f"      - {p.get('name')} ({p.get('decision')})")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage unified access policies across Cloudflare Tunnel applications"
    )
    parser.add_argument(
        "--create-policy", action="store_true", help="Create standard reusable policy"
    )
    parser.add_argument(
        "--apply-all", action="store_true", help="Apply standard policy to all applications"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all applications and their policies"
    )
    parser.add_argument(
        "--policy-name", default=STANDARD_POLICY_NAME, help="Name of the standard policy"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Cloudflare Unified Access Policy Manager")
    print("=" * 60)
    print()

    try:
        headers = get_auth_headers()
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    if args.list or (not args.create_policy and not args.apply_all):
        list_all_applications_and_policies(headers, ACCOUNT_ID)

    if args.create_policy:
        print("\n[INFO] Creating standard reusable policy...")
        policy_id = create_or_get_standard_reusable_policy(headers, ACCOUNT_ID)

        if policy_id:
            print(f"\n[OK] Standard policy ID: {policy_id}")
            print("\nTo apply this policy to all applications:")
            print("  1. Run: python3 manage_unified_access.py --apply-all")
            print("  2. Or manually add it in the Cloudflare dashboard")

    if args.apply_all:
        print("\n[INFO] Applying standard policy to all applications...")
        reusable_policies = get_reusable_policies(headers, ACCOUNT_ID)

        standard_policy = None
        for policy in reusable_policies:
            if policy.get("name") == STANDARD_POLICY_NAME:
                standard_policy = policy
                break

        if not standard_policy:
            print(f"[ERROR] Standard policy '{STANDARD_POLICY_NAME}' not found")
            print("   Create it first: python3 manage_unified_access.py --create-policy")
            sys.exit(1)

        policy_id = standard_policy.get("id")
        apply_standard_policy_to_all_apps(headers, ACCOUNT_ID, policy_id)

    print("\n" + "=" * 60)
    print("Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
