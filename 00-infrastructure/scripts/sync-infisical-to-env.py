#!/usr/bin/env python3
"""
Sync environment variables from Infisical to .env file.

This script exports secrets from Infisical and updates the .env file,
preserving non-secret configuration like hostnames, ports, and URLs.

Usage:
    python 00-infrastructure/scripts/sync-infisical-to-env.py [--dry-run] [--env-file .env] [--overwrite-empty]
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Patterns for variables that should be synced from Infisical (secrets)
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

# Patterns for variables that should NOT be synced from Infisical
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
        # If authenticated, this should either succeed or show a project error
        # If not authenticated, it will show auth error
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


def parse_env_file(env_file_path: Path) -> tuple[dict[str, str], list[str]]:
    """
    Parse .env file and return dictionary of key-value pairs and list of lines.

    Returns:
        Tuple of (env_vars: Dict[str, str], lines: List[str])
    """
    env_vars = {}
    lines = []

    if not env_file_path.exists():
        return env_vars, lines

    with env_file_path.open(encoding="utf-8") as f:
        for _line_num, line in enumerate(f, 1):
            lines.append(line)
            # Strip whitespace
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

    return env_vars, lines


def main():
    parser = argparse.ArgumentParser(
        description="Sync environment variables from Infisical to .env file"
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
        "--overwrite-empty",
        action="store_true",
        help="Only overwrite empty values in .env (default: overwrite all secret values)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    # Find project root (where .env file should be)
    # Script is at 00-infrastructure/scripts/, project root is 2 levels up
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    env_file_path = project_root / args.env_file

    print("=" * 70)
    print("Infisical → .env Sync")
    print("=" * 70)
    print(f"Target .env file: {env_file_path}")
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
        print("Error: Infisical CLI is not authenticated.")
        print("Run: infisical login")
        print("Or: infisical init")
        sys.exit(1)

    print("✓ Infisical CLI authenticated")
    print()

    # Get secrets from Infisical
    print("Fetching secrets from Infisical...")
    infisical_secrets = get_infisical_secrets()

    if not infisical_secrets:
        print("Warning: No secrets found in Infisical.")
        print("Make sure you're authenticated and have secrets configured.")
        sys.exit(1)

    print(f"✓ Found {len(infisical_secrets)} secrets in Infisical")
    print()

    # Parse .env file
    print(f"Reading .env file: {env_file_path}")
    env_vars, env_lines = parse_env_file(env_file_path)

    if not env_file_path.exists():
        print(f"Creating new .env file at {env_file_path}")
        env_lines = []

    # Filter secrets from Infisical
    secrets_to_sync = {}
    for key, value in infisical_secrets.items():
        if is_secret_key(key):
            secrets_to_sync[key] = value

    print(f"Secrets to sync: {len(secrets_to_sync)}")
    print()

    if not secrets_to_sync:
        print("No secrets found to sync.")
        print("Secrets are identified by patterns like:")
        print("  - *_PASSWORD")
        print("  - *_SECRET")
        print("  - *_KEY")
        print("  - *_TOKEN")
        sys.exit(0)

    # Determine what will be updated
    updates = {}
    additions = []

    for key, value in secrets_to_sync.items():
        if key in env_vars:
            # Check if we should update
            if args.overwrite_empty:
                # Only update if current value is empty
                if not env_vars[key] or not env_vars[key].strip():
                    updates[key] = value
            # Update if value is different
            elif env_vars[key] != value:
                updates[key] = value
        else:
            # New key to add
            additions.append((key, value))

    # Show what will be synced
    print("=" * 70)
    print("Sync Preview")
    print("=" * 70)

    if updates:
        print(f"\nSecrets to update ({len(updates)}):")
        for key in sorted(updates.keys()):
            old_value_preview = (
                env_vars[key][:20] + "..." if len(env_vars[key]) > 20 else env_vars[key]
            )
            new_value_preview = (
                updates[key][:20] + "..." if len(updates[key]) > 20 else updates[key]
            )
            print(f"  - {key}")
            print(f"    Old: {old_value_preview}")
            print(f"    New: {new_value_preview}")

    if additions:
        print(f"\nSecrets to add ({len(additions)}):")
        for key, value in sorted(additions):
            value_preview = value[:20] + "..." if len(value) > 20 else value
            print(f"  - {key} = {value_preview}")

    if not updates and not additions:
        print("\n✓ .env file is already in sync with Infisical")
        sys.exit(0)

    print()

    if args.dry_run:
        print("=" * 70)
        print("DRY RUN MODE - No changes were made")
        print("=" * 70)
        print()
        print("To actually sync, run without --dry-run:")
        print(f"  python {sys.argv[0]}")
        return

    # Confirm before syncing
    if not args.force:
        print("This will update the .env file with secrets from Infisical.")
        response = input("Continue? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Update .env file
    print()
    print("=" * 70)
    print("Updating .env file...")
    print("=" * 70)

    new_lines = []
    updated_count = 0
    added_count = 0

    # Track which keys we've processed
    processed_keys = set()

    for line in env_lines:
        stripped = line.strip()

        # Preserve comments and empty lines
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        # Process KEY=VALUE lines
        if "=" in stripped:
            key, value = stripped.split("=", 1)
            key = key.strip()
            processed_keys.add(key)

            # Update if this is a secret that needs updating
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated_count += 1
                print(f"  Updated: {key}")
            else:
                # Keep original line
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Add new secrets at the end
    for key, value in additions:
        if key not in processed_keys:
            new_lines.append(f"{key}={value}\n")
            added_count += 1
            print(f"  Added: {key}")

    # Write updated .env file
    try:
        with env_file_path.open("w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print()
        print("=" * 70)
        print("Sync Complete")
        print("=" * 70)
        print(f"Updated: {updated_count} secret(s)")
        print(f"Added: {added_count} secret(s)")
        print()
        print(f"✓ .env file updated at {env_file_path}")
        print()
        print("The .env file now contains secrets from Infisical as a fallback.")
        print("Services can use either Infisical (preferred) or .env file.")

    except Exception as e:
        print(f"\nError: Failed to write .env file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
