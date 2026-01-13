#!/usr/bin/env python3
"""
Sync environment variables from .env file to Infisical.

This script reads secrets from the .env file and uploads them to Infisical
using the REST API. It filters out non-sensitive configuration.

Usage:
    python 00-infrastructure/scripts/sync-env-to-infisical.py [--dry-run] [--env-file .env]

Requirements:
    Set these environment variables (or they'll be read from .env):
    - INFISICAL_CLIENT_ID
    - INFISICAL_CLIENT_SECRET
    - INFISICAL_PROJECT_ID
    - INFISICAL_ENVIRONMENT (default: dev)
    - INFISICAL_HOST (default: http://infisical-backend:8080)
"""

import argparse
import os
import re
import sys
from pathlib import Path

import requests

# Patterns for variables that should NOT be synced to Infisical
NON_SECRET_PATTERNS = [
    r".*_HOSTNAME$",
    r".*_PORT$",
    r".*_HOST$",
    r"^INFISICAL_.*$",  # Don't sync Infisical config to Infisical
    r"^LOG_LEVEL$",
    r"^TZ$",
    r"^PUID$",
    r"^PGID$",
]

# Patterns for variables that SHOULD be synced (secrets)
SECRET_PATTERNS = [
    r".*_PASSWORD$",
    r".*_SECRET$",
    r".*_KEY$",
    r".*_TOKEN$",
    r".*_API_KEY$",
    r".*_CLIENT_ID$",
    r".*_CLIENT_SECRET$",
    r"^DOCKER_HUB_.*$",
    r"^SMTP_.*$",
    r"^POSTGRES_PASSWORD$",
    r"^JWT_SECRET$",
    r"^ANON_KEY$",
    r"^SERVICE_ROLE_KEY$",
    r"^DASHBOARD_.*$",
    r"^STUDIO_.*$",
    r"^FLOWISE_.*$",
    r"^N8N_.*$",
    r"^LANGFUSE_.*$",
    r"^OPENAI_.*$",
    r"^ANTHROPIC_.*$",
    r"^GOOGLE_.*$",
    r"^CLOUDFLARE_.*$",
    r"^DISCORD_.*$",
    r"^MONGODB_.*$",
    r"^SUPABASE_.*$",
    r"^MINIO_.*$",
    r"^IMMICH_.*$",
    r"^NEO4J_.*$",
]


def should_sync(key: str, value: str) -> tuple[bool, str]:
    """Determine if a variable should be synced to Infisical."""
    if not value or not value.strip():
        return False, "empty value"

    # Check exclusion patterns first
    for pattern in NON_SECRET_PATTERNS:
        if re.match(pattern, key, re.IGNORECASE):
            return False, f"excluded: {pattern}"

    # Check inclusion patterns
    for pattern in SECRET_PATTERNS:
        if re.match(pattern, key, re.IGNORECASE):
            return True, f"matches: {pattern}"

    return False, "not identified as secret"


def parse_env_file(env_file_path: Path) -> dict[str, str]:
    """Parse .env file and return dictionary of key-value pairs."""
    env_vars = {}

    if not env_file_path.exists():
        print(f"Error: .env file not found at {env_file_path}")
        sys.exit(1)

    with env_file_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            # Remove quotes
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            if key:
                env_vars[key] = value

    return env_vars


def get_access_token(host: str, client_id: str, client_secret: str) -> str | None:
    """Get access token via Universal Auth."""
    try:
        response = requests.post(
            f"{host}/api/v1/auth/universal-auth/login",
            json={"clientId": client_id, "clientSecret": client_secret},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("accessToken")
    except requests.RequestException as e:
        print(f"Error authenticating with Infisical: {e}")
        return None


def get_existing_secrets(
    host: str, token: str, project_id: str, environment: str
) -> dict[str, dict]:
    """Get existing secrets from Infisical."""
    try:
        response = requests.get(
            f"{host}/api/v3/secrets/raw",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "workspaceId": project_id,
                "environment": environment,
                "secretPath": "/",
            },
            timeout=10,
        )
        response.raise_for_status()
        secrets = {}
        for secret in response.json().get("secrets", []):
            secrets[secret["secretKey"]] = {
                "value": secret.get("secretValue", ""),
                "id": secret.get("id"),
            }
        return secrets
    except requests.RequestException as e:
        print(f"Error fetching existing secrets: {e}")
        return {}


def create_secret(
    host: str,
    token: str,
    project_id: str,
    environment: str,
    key: str,
    value: str,
) -> bool:
    """Create a new secret in Infisical."""
    try:
        response = requests.post(
            f"{host}/api/v3/secrets/raw/{key}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "workspaceId": project_id,
                "environment": environment,
                "secretPath": "/",
                "secretValue": value,
                "type": "shared",
            },
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"  Error creating {key}: {e}")
        return False


def update_secret(
    host: str,
    token: str,
    project_id: str,
    environment: str,
    key: str,
    value: str,
) -> bool:
    """Update an existing secret in Infisical."""
    try:
        response = requests.patch(
            f"{host}/api/v3/secrets/raw/{key}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "workspaceId": project_id,
                "environment": environment,
                "secretPath": "/",
                "secretValue": value,
            },
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"  Error updating {key}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Sync .env to Infisical")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually sync")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Find project root
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    env_file = project_root / args.env_file

    print(f"Reading from: {env_file}")

    # Parse .env file first to get Infisical config
    env_vars = parse_env_file(env_file)

    # Get Infisical config
    # Try internal hostname first, fall back to public URL
    internal_host = "http://infisical-backend:8080"
    public_host = "https://infisical.datacrew.space"

    host = os.environ.get("INFISICAL_HOST", env_vars.get("INFISICAL_HOST", ""))

    # If not specified or using internal hostname, try internal first
    if not host or "infisical-backend" in host:
        # Test if internal hostname is reachable
        try:
            import socket

            socket.create_connection(("infisical-backend", 8080), timeout=2)
            host = internal_host
            print("Note: Using internal Docker network")
        except (TimeoutError, OSError):
            host = public_host
            print("Note: Using public URL (not inside Docker network)")
    client_id = os.environ.get("INFISICAL_CLIENT_ID", env_vars.get("INFISICAL_CLIENT_ID", ""))
    client_secret = os.environ.get(
        "INFISICAL_CLIENT_SECRET", env_vars.get("INFISICAL_CLIENT_SECRET", "")
    )
    project_id = os.environ.get("INFISICAL_PROJECT_ID", env_vars.get("INFISICAL_PROJECT_ID", ""))
    environment = os.environ.get(
        "INFISICAL_ENVIRONMENT", env_vars.get("INFISICAL_ENVIRONMENT", "dev")
    )

    if not all([client_id, client_secret, project_id]):
        print("Error: Missing Infisical configuration")
        print("  Required: INFISICAL_CLIENT_ID, INFISICAL_CLIENT_SECRET, INFISICAL_PROJECT_ID")
        sys.exit(1)

    print(f"Infisical host: {host}")
    print(f"Project ID: {project_id}")
    print(f"Environment: {environment}")
    print()

    # Authenticate
    print("Authenticating with Infisical...")
    token = get_access_token(host, client_id, client_secret)
    if not token:
        sys.exit(1)
    print("✓ Authenticated")
    print()

    # Get existing secrets
    print("Fetching existing secrets...")
    existing = get_existing_secrets(host, token, project_id, environment)
    print(f"✓ Found {len(existing)} existing secrets")
    print()

    # Filter secrets to sync
    to_sync = {}
    skipped = []
    for key, value in env_vars.items():
        should, reason = should_sync(key, value)
        if should:
            to_sync[key] = value
        elif args.verbose:
            skipped.append((key, reason))

    print(f"Secrets to sync: {len(to_sync)}")
    if args.verbose and skipped:
        print(f"Skipped: {len(skipped)}")
        for key, reason in skipped[:10]:
            print(f"  - {key}: {reason}")
        if len(skipped) > 10:
            print(f"  ... and {len(skipped) - 10} more")
    print()

    if args.dry_run:
        print("DRY RUN - would sync:")
        for key in sorted(to_sync.keys()):
            status = "UPDATE" if key in existing else "CREATE"
            print(f"  [{status}] {key}")
        return

    # Sync secrets
    created = 0
    updated = 0
    unchanged = 0
    errors = 0

    for key, value in sorted(to_sync.items()):
        if key in existing:
            if existing[key]["value"] == value:
                unchanged += 1
                if args.verbose:
                    print(f"  [UNCHANGED] {key}")
            elif update_secret(host, token, project_id, environment, key, value):
                updated += 1
                print(f"  [UPDATED] {key}")
            else:
                errors += 1
        elif create_secret(host, token, project_id, environment, key, value):
            created += 1
            print(f"  [CREATED] {key}")
        else:
            errors += 1

    print()
    print("=" * 40)
    print(f"Created:   {created}")
    print(f"Updated:   {updated}")
    print(f"Unchanged: {unchanged}")
    print(f"Errors:    {errors}")
    print("=" * 40)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
