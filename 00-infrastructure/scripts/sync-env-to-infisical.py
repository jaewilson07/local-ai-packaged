#!/usr/bin/env python3
"""
Sync environment variables from .env file to Infisical.

This script reads secrets from the .env file and uploads them to Infisical
using the Infisical CLI. It filters out non-sensitive configuration like
hostnames, ports, and URLs.

Usage:
    python 00-infrastructure/scripts/sync-env-to-infisical.py [--dry-run] [--env-file .env]
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Patterns for variables that should NOT be synced to Infisical
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

# Patterns for variables that SHOULD be synced (secrets)
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


def should_sync_to_infisical(key: str, value: str) -> tuple[bool, str]:
    """
    Determine if a variable should be synced to Infisical.

    Returns:
        Tuple of (should_sync: bool, reason: str)
    """
    # Skip empty values
    if not value or not value.strip():
        return False, "empty value"

    # Skip commented lines (handled by parser)
    if value.strip().startswith("#"):
        return False, "commented"

    # Check exclusion patterns first
    for pattern in NON_SECRET_PATTERNS:
        if re.match(pattern, key, re.IGNORECASE):
            return False, f"matches exclusion pattern: {pattern}"

    # Check inclusion patterns
    for pattern in SECRET_PATTERNS:
        if re.match(pattern, key, re.IGNORECASE):
            return True, f"matches secret pattern: {pattern}"

    # Default: don't sync if not explicitly a secret
    return False, "not identified as secret"


def parse_env_file(env_file_path: Path) -> dict[str, str]:
    """
    Parse .env file and return dictionary of key-value pairs.

    Handles:
    - Comments (lines starting with #)
    - Empty lines
    - Quoted values
    - Multi-line values (basic support)
    """
    env_vars = {}

    if not env_file_path.exists():
        print(f"Error: .env file not found at {env_file_path}")
        sys.exit(1)

    with open(env_file_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            # Strip whitespace
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE
            if "=" not in line:
                print(f"Warning: Skipping malformed line {line_num}: {line}")
                continue

            key, value = line.split("=", 1)
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
    except Exception:
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
        # If authenticated, this should either succeed or show a project error
        # If not authenticated, it will show auth error
        output = (result.stdout or result.stderr or "").lower()
        return not ("authenticate" in output or "login" in output)
    except Exception:
        return False


def get_infisical_secrets() -> dict[str, str]:
    """
    Get all secrets from Infisical.

    Returns:
        Dictionary of secret key-value pairs
    """
    secrets_dict = {}

    try:
        # Export secrets from Infisical
        result = subprocess.run(
            ["infisical", "export", "--format=dotenv"],
            capture_output=True,
            text=True,
            timeout=30,
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

    except Exception as e:
        print(f"Warning: Could not fetch secrets from Infisical: {e}")

    return secrets_dict


def set_infisical_secret(key: str, value: str, dry_run: bool = False) -> bool:
    """
    Set a secret in Infisical using CLI.

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        print(f"  [DRY RUN] Would set: {key}")
        return True

    try:
        # Use infisical secrets set command
        # Format: infisical secrets set KEY=value
        # The CLI expects key=value as a single argument
        cmd = ["infisical", "secrets", "set", f"{key}={value}"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
            return True
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print(f"  Error setting {key}: {error_msg.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  Timeout setting {key}")
        return False
    except Exception as e:
        print(f"  Exception setting {key}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Sync environment variables from .env to Infisical"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without actually syncing",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=".env",
        help="Path to .env file (default: .env)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--check-missing",
        action="store_true",
        help="Only sync secrets that don't exist in Infisical",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt before syncing each secret",
    )

    args = parser.parse_args()

    # Find project root (where .env file should be)
    # Script is at 00-infrastructure/scripts/, project root is 2 levels up
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    env_file_path = project_root / args.env_file

    print("=" * 70)
    print("Infisical Secret Sync")
    print("=" * 70)
    print(f"Reading from: {env_file_path}")
    print()

    # Check Infisical CLI
    if not check_infisical_cli():
        print("Error: Infisical CLI not found.")
        print("Install it with: python setup/install_clis.py")
        print("Or visit: https://infisical.com/docs/cli/overview")
        sys.exit(1)

    print("✓ Infisical CLI found")

    # Check authentication (skip for dry-run)
    if not args.dry_run and not check_infisical_auth():
        print()
        print("Warning: Infisical CLI may not be authenticated.")
        print("Run: infisical login")
        print("Or: infisical init")
        print()
        if not args.force:
            response = input("Continue anyway? (y/N): ")
            if response.lower() != "y":
                print("Aborted.")
                sys.exit(1)

    # Parse .env file
    print("✓ Parsing .env file...")
    env_vars = parse_env_file(env_file_path)
    print(f"✓ Found {len(env_vars)} environment variables")
    print()

    # Get existing Infisical secrets if --check-missing is enabled
    existing_infisical_secrets = {}
    if args.check_missing and not args.dry_run:
        print("Checking existing secrets in Infisical...")
        existing_infisical_secrets = get_infisical_secrets()
        print(f"✓ Found {len(existing_infisical_secrets)} existing secrets in Infisical")
        print()

    # Filter secrets
    secrets_to_sync = {}
    skipped = {}
    already_in_infisical = {}

    for key, value in env_vars.items():
        should_sync, reason = should_sync_to_infisical(key, value)
        if should_sync:
            # If --check-missing, skip secrets that already exist in Infisical
            if args.check_missing and key in existing_infisical_secrets:
                already_in_infisical[key] = existing_infisical_secrets[key]
            else:
                secrets_to_sync[key] = value
        else:
            skipped[key] = reason

    print("=" * 70)
    print(f"Secrets to sync: {len(secrets_to_sync)}")
    if args.check_missing and already_in_infisical:
        print(f"Already in Infisical (skipped): {len(already_in_infisical)}")
    print(f"Skipped (non-secrets): {len(skipped)}")
    print("=" * 70)
    print()

    if not secrets_to_sync:
        print("No secrets found to sync.")
        print()
        print("Secrets are identified by patterns like:")
        print("  - *_PASSWORD")
        print("  - *_SECRET")
        print("  - *_KEY")
        print("  - *_TOKEN")
        print("  - *_API_KEY")
        print("  - DOCKER_HUB_*")
        print("  - SMTP_*")
        sys.exit(0)

    # Show what will be synced
    if args.check_missing and already_in_infisical:
        print("Secrets already in Infisical (will be skipped):")
        for key in sorted(already_in_infisical.keys()):
            value_preview = (
                already_in_infisical[key][:20] + "..."
                if len(already_in_infisical[key]) > 20
                else already_in_infisical[key]
            )
            print(f"  - {key} = {value_preview}")
        print()

    print("Secrets to sync:")
    for key in sorted(secrets_to_sync.keys()):
        value_preview = (
            secrets_to_sync[key][:20] + "..."
            if len(secrets_to_sync[key]) > 20
            else secrets_to_sync[key]
        )
        print(f"  - {key} = {value_preview}")
    print()

    if args.dry_run:
        print("=" * 70)
        print("DRY RUN MODE - No secrets were actually synced")
        print("=" * 70)
        print()
        print("To actually sync, run without --dry-run:")
        print(f"  python {sys.argv[0]}")
        return

    # Confirm before syncing
    if not args.force:
        print("This will upload the above secrets to Infisical.")
        response = input("Continue? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Sync secrets
    print()
    print("=" * 70)
    print("Syncing secrets to Infisical...")
    print("=" * 70)

    success_count = 0
    failed_count = 0
    skipped_count = 0
    failed_keys = []

    for key, value in sorted(secrets_to_sync.items()):
        # Interactive mode: prompt before each secret
        if args.interactive:
            value_preview = value[:30] + "..." if len(value) > 30 else value
            response = input(f"Sync {key} = {value_preview}? (y/N/s to skip): ").strip().lower()
            if response in {"s", "skip"} or response not in {"y", "yes"}:
                print(f"  Skipped {key}")
                skipped_count += 1
                continue

        print(f"Setting {key}...", end=" ", flush=True)
        if set_infisical_secret(key, value, dry_run=False):
            print("✓")
            success_count += 1
        else:
            print("✗")
            failed_count += 1
            failed_keys.append(key)

    print()
    print("=" * 70)
    print("Sync Complete")
    print("=" * 70)
    print(f"Successfully synced: {success_count}")
    if skipped_count > 0:
        print(f"Skipped: {skipped_count}")
    if failed_count > 0:
        print(f"Failed: {failed_count}")
        print()
        print("Failed keys:")
        for key in failed_keys:
            print(f"  - {key}")
        print()
        print("You may need to:")
        print("  1. Check Infisical authentication: infisical login")
        print("  2. Check project initialization: infisical init")
        print("  3. Manually set failed secrets via UI or CLI")
        sys.exit(1)
    else:
        print()
        print("All secrets successfully synced to Infisical!")
        print()
        print("Next steps:")
        print("  1. Verify secrets in Infisical UI")
        print("  2. Remove synced secrets from .env file (optional)")
        print("  3. Services will now use secrets from Infisical")


if __name__ == "__main__":
    main()
