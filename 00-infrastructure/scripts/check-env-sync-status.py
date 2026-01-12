#!/usr/bin/env python3
"""
Check sync status between .env file and Infisical.

This script compares secrets in the .env file with secrets in Infisical,
and provides a report showing:
- Secrets that exist only in .env (not in Infisical)
- Secrets that exist only in Infisical (not in .env)
- Secrets with mismatched values
- Whether .env is still required

Usage:
    python 00-infrastructure/scripts/check-env-sync-status.py [--env-file .env] [--verbose]
"""

import argparse
import re
import subprocess
from pathlib import Path

# Patterns for variables that should be synced (secrets)
SECRET_PATTERNS = [
    r".*_PASSWORD$",  # All passwords
    r".*_SECRET$",  # All secrets
    r".*_KEY$",  # All keys (encryption keys, etc.)
    r".*_TOKEN$",  # All tokens
    r".*_API_KEY$",  # API keys
    r".*_CLIENT_ID$",  # OAuth client IDs
    r".*_CLIENT_SECRET$",  # OAuth client secrets
    r"^DOCKER_HUB_USERNAME$",  # Docker Hub username
    r"^DOCKER_HUB_PASSWORD$",  # Docker Hub password
    r"^DOCKER_HUB_TOKEN$",  # Docker Hub token
    r"^SMTP_.*$",  # SMTP credentials
]

# Patterns for variables that should NOT be synced (non-secrets)
NON_SECRET_PATTERNS = [
    r".*_HOSTNAME$",  # Hostnames (N8N_HOSTNAME, etc.)
    r".*_PORT$",  # Port numbers
    r".*_URL$",  # URLs (SITE_URL, etc.)
    r".*_SITE_URL$",  # Site URLs
    r"^INFISICAL_HOSTNAME$",  # Infisical hostname config
    r"^INFISICAL_SITE_URL$",  # Infisical site URL config
    r"^INFISICAL_HTTPS_ENABLED$",  # Infisical HTTPS setting
    r"^INFISICAL_POSTGRES_HOST$",  # Infisical DB host (non-secret)
    r"^INFISICAL_POSTGRES_PORT$",  # Infisical DB port (non-secret)
    r"^INFISICAL_POSTGRES_DATABASE$",  # Infisical DB name (non-secret)
    r"^INFISICAL_POSTGRES_USERNAME$",  # Infisical DB user (non-secret)
]


def is_secret_key(key: str) -> bool:
    """Check if a key should be treated as a secret."""
    # Check exclusion patterns first
    for pattern in NON_SECRET_PATTERNS:
        if re.match(pattern, key, re.IGNORECASE):
            return False

    # Check inclusion patterns
    return any(re.match(pattern, key, re.IGNORECASE) for pattern in SECRET_PATTERNS)


def check_infisical_cli() -> bool:
    """Check if Infisical CLI is installed and available."""
    try:
        result = subprocess.run(
            ["infisical", "--version"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except (subprocess.SubprocessError, OSError):
        return False


def check_infisical_auth() -> bool:
    """Check if Infisical CLI is authenticated."""
    try:
        result = subprocess.run(
            ["infisical", "secrets"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        output = (result.stdout or result.stderr or "").lower()
        return not ("authenticate" in output or "login" in output)
    except (subprocess.SubprocessError, OSError):
        return False


def get_infisical_secrets() -> dict[str, str]:
    """
    Get all secrets from Infisical.

    Returns:
        Dictionary of secret key-value pairs
    """
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
                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]
                    secrets_dict[key] = value

    except Exception as e:
        print(f"Error: Could not fetch secrets from Infisical: {e}")
        return {}

    return secrets_dict


def parse_env_file(env_file_path: Path) -> dict[str, str]:
    """
    Parse .env file and return dictionary of key-value pairs.

    Returns:
        Dictionary of environment variables
    """
    env_vars = {}

    if not env_file_path.exists():
        return env_vars

    with env_file_path.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue

            # Parse KEY=VALUE
            if "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            # Skip if key is empty
            if not key:
                continue

            env_vars[key] = value

    return env_vars


def main():
    parser = argparse.ArgumentParser(
        description="Check sync status between .env file and Infisical"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=".env",
        help="Path to .env file (default: .env)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed information about all secrets",
    )

    args = parser.parse_args()

    # Find project root
    # Script is at 00-infrastructure/scripts/, project root is 2 levels up
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    env_file_path = project_root / args.env_file

    print("=" * 70)
    print("Sync Status Report")
    print("=" * 70)
    print()

    # Check Infisical availability
    infisical_available = False
    if check_infisical_cli():
        if check_infisical_auth():
            infisical_available = True
            print("✓ Infisical CLI available and authenticated")
        else:
            print("⚠ Infisical CLI found but not authenticated")
            print("  Run: infisical login")
    else:
        print("⚠ Infisical CLI not found")
        print("  Install with: python setup/install_clis.py")

    print()

    # Get secrets from .env
    print(f"Reading .env file: {env_file_path}")
    env_vars = parse_env_file(env_file_path)

    # Filter to only secrets
    env_secrets = {k: v for k, v in env_vars.items() if is_secret_key(k)}

    if env_file_path.exists():
        print(f"✓ Found {len(env_secrets)} secrets in .env file")
    else:
        print("⚠ .env file not found")

    print()

    # Get secrets from Infisical
    infisical_secrets = {}
    if infisical_available:
        print("Fetching secrets from Infisical...")
        all_infisical = get_infisical_secrets()
        infisical_secrets = {k: v for k, v in all_infisical.items() if is_secret_key(k)}
        print(f"✓ Found {len(infisical_secrets)} secrets in Infisical")
    else:
        print("⚠ Skipping Infisical (not available)")

    print()

    # Compare secrets
    env_secret_keys = set(env_secrets.keys())
    infisical_secret_keys = set(infisical_secrets.keys())

    only_in_env = env_secret_keys - infisical_secret_keys
    only_in_infisical = infisical_secret_keys - env_secret_keys
    in_both = env_secret_keys & infisical_secret_keys

    # Check for mismatched values
    mismatched = []
    for key in in_both:
        if env_secrets[key] != infisical_secrets[key]:
            mismatched.append(key)

    # Generate report
    print("=" * 70)
    print("Sync Status Summary")
    print("=" * 70)
    print()

    print(f"Secrets in Infisical: {len(infisical_secret_keys)}")
    print(f"Secrets in .env: {len(env_secret_keys)}")
    print(f"Secrets in both: {len(in_both)}")
    print()

    # Determine .env requirement status
    env_status = "OPTIONAL"
    recommendation = ""

    if only_in_env:
        env_status = "REQUIRED"
        recommendation = (
            f"Run sync_to_infisical.py to migrate {len(only_in_env)} secret(s) to Infisical"
        )
    elif mismatched:
        env_status = "OUT OF SYNC"
        recommendation = "Run sync_from_infisical.py to sync Infisical values to .env"
    elif infisical_available and len(infisical_secret_keys) > 0:
        env_status = "OPTIONAL"
        recommendation = ".env can be used as fallback, but Infisical is the source of truth"
    else:
        env_status = "REQUIRED"
        recommendation = "Infisical not available - .env is required"

    print(f".env Status: {env_status}")
    if only_in_env:
        print(f"  Reason: {len(only_in_env)} secret(s) exist only in .env")
    elif mismatched:
        print(f"  Reason: {len(mismatched)} secret(s) have mismatched values")
    elif not infisical_available:
        print("  Reason: Infisical not available")
    else:
        print("  Reason: All secrets are in Infisical")

    print()

    # Detailed information
    if args.verbose or only_in_env or only_in_infisical or mismatched:
        print("=" * 70)
        print("Detailed Comparison")
        print("=" * 70)
        print()

        if only_in_env:
            print(f"Secrets only in .env ({len(only_in_env)}):")
            for key in sorted(only_in_env):
                value_preview = (
                    env_secrets[key][:30] + "..."
                    if len(env_secrets[key]) > 30
                    else env_secrets[key]
                )
                print(f"  - {key} = {value_preview}")
            print()

        if only_in_infisical:
            print(f"Secrets only in Infisical ({len(only_in_infisical)}):")
            for key in sorted(only_in_infisical):
                value_preview = (
                    infisical_secrets[key][:30] + "..."
                    if len(infisical_secrets[key]) > 30
                    else infisical_secrets[key]
                )
                print(f"  - {key} = {value_preview}")
            print()

        if mismatched:
            print(f"Mismatched values ({len(mismatched)}):")
            for key in sorted(mismatched):
                env_preview = (
                    env_secrets[key][:20] + "..."
                    if len(env_secrets[key]) > 20
                    else env_secrets[key]
                )
                infisical_preview = (
                    infisical_secrets[key][:20] + "..."
                    if len(infisical_secrets[key]) > 20
                    else infisical_secrets[key]
                )
                print(f"  - {key}")
                print(f"    .env:      {env_preview}")
                print(f"    Infisical: {infisical_preview}")
            print()

    # Recommendations
    print("=" * 70)
    print("Recommendations")
    print("=" * 70)
    print()

    if recommendation:
        print(f"→ {recommendation}")
    else:
        print("→ No action needed - everything is in sync")

    print()

    if only_in_env:
        print("To migrate secrets from .env to Infisical:")
        print("  python 00-infrastructure/scripts/sync-env-to-infisical.py")
        print()

    if mismatched or only_in_infisical:
        print("To sync secrets from Infisical to .env:")
        print("  python 00-infrastructure/scripts/sync-infisical-to-env.py")
        print()

    if env_status == "OPTIONAL" and infisical_available:
        print("Since all secrets are in Infisical, .env is optional.")
        print("You can remove secrets from .env and keep only non-secret configuration.")
        print("Services will use Infisical as the source of truth.")
        print()


if __name__ == "__main__":
    main()
