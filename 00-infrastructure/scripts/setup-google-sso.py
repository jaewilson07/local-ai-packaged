#!/usr/bin/env python3
"""
Setup Google SSO for Infisical

This script configures Google OAuth2 authentication for Infisical by:
1. Reading Google OAuth credentials from a JSON file
2. Adding/updating the required environment variables in .env
3. Optionally syncing to Infisical secrets manager
4. Restarting Infisical backend to apply changes

Usage:
    python3 setup-google-sso.py --client-secret-file <path-to-json>
    python3 setup-google-sso.py --client-secret-file <path-to-json> --site-url https://your-domain.com
    python3 setup-google-sso.py --client-secret-file <path-to-json> --sync-to-infisical
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def read_google_credentials(file_path: str) -> tuple[str, str]:
    """Read Google OAuth2 credentials from JSON file."""
    try:
        file_path_obj = Path(file_path)
        with file_path_obj.open() as f:
            data = json.load(f)

        # Handle both "web" and "installed" app types
        if "web" in data:
            client_id = data["web"]["client_id"]
            client_secret = data["web"]["client_secret"]
        elif "installed" in data:
            client_id = data["installed"]["client_id"]
            client_secret = data["installed"]["client_secret"]
        else:
            raise ValueError("Invalid Google OAuth2 credentials file format")

        return client_id, client_secret
    except FileNotFoundError:
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON file: {file_path}")
        sys.exit(1)
    except KeyError as e:
        print(f"❌ Error: Missing key in credentials file: {e}")
        sys.exit(1)


def get_env_file_path() -> Path:
    """Get the path to the .env file."""
    # Assume script is in 00-infrastructure/scripts/
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    env_file = repo_root / ".env"
    return env_file


def read_env_file(env_file: Path) -> dict[str, str]:
    """Read environment variables from .env file."""
    env_vars = {}
    if env_file.exists():
        with env_file.open() as f:
            for raw_line in f:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


def write_env_file(env_file: Path, env_vars: dict[str, str]):
    """Write environment variables to .env file."""
    lines = []

    # Read existing file to preserve comments and order
    if env_file.exists():
        with env_file.open() as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    if key in env_vars:
                        # Update existing variable
                        lines.append(f"{key}={env_vars[key]}\n")
                        del env_vars[key]
                    else:
                        lines.append(line)
                else:
                    lines.append(line)

    # Add new variables at the end
    if env_vars:
        if lines and not lines[-1].endswith("\n\n"):
            lines.append("\n")
        lines.append("# Google SSO Configuration\n")
        for key, value in env_vars.items():
            lines.append(f"{key}={value}\n")

    with env_file.open("w") as f:
        f.writelines(lines)


def generate_auth_secret() -> str:
    """Generate a random AUTH_SECRET if not already set."""
    result = subprocess.run(
        ["openssl", "rand", "-base64", "32"], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def sync_to_infisical(env_file: Path):
    """Sync environment variables to Infisical."""
    script_dir = Path(__file__).parent
    sync_script = script_dir / "sync-env-to-infisical.py"

    if not sync_script.exists():
        print("⚠️  Warning: sync-env-to-infisical.py not found, skipping sync")
        return

    print("\n📤 Syncing to Infisical...")
    try:
        subprocess.run(["python3", str(sync_script), "--env-file", str(env_file)], check=True)
        print("✅ Synced to Infisical successfully")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Warning: Failed to sync to Infisical: {e}")


def restart_infisical():
    """Restart Infisical backend to apply changes."""
    print("\n🔄 Restarting Infisical backend...")
    try:
        subprocess.run(["docker", "restart", "infisical-backend"], check=True, capture_output=True)
        print("✅ Infisical backend restarted successfully")
        print("\n⏳ Waiting for Infisical to be ready...")
        subprocess.run(["sleep", "5"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Warning: Failed to restart Infisical: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Setup Google SSO for Infisical",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic setup with local client secret file
  python3 setup-google-sso.py --client-secret-file /path/to/client_secret.json

  # Setup with custom site URL
  python3 setup-google-sso.py --client-secret-file /path/to/client_secret.json --site-url https://infisical.example.com

  # Setup and sync to Infisical
  python3 setup-google-sso.py --client-secret-file /path/to/client_secret.json --sync-to-infisical

  # Setup with Windows path (WSL)
  python3 setup-google-sso.py --client-secret-file /mnt/c/Users/username/Downloads/client_secret.json
        """,
    )
    parser.add_argument(
        "--client-secret-file", required=True, help="Path to Google OAuth2 client secret JSON file"
    )
    parser.add_argument(
        "--site-url",
        help="Site URL for Infisical (e.g., https://infisical.example.com). If not provided, will use existing SITE_URL or default to http://localhost:8080",
    )
    parser.add_argument(
        "--sync-to-infisical",
        action="store_true",
        help="Sync environment variables to Infisical after updating .env",
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Do not restart Infisical backend after configuration",
    )
    parser.add_argument(
        "--env-file", help="Path to .env file (default: auto-detect from repo root)"
    )

    args = parser.parse_args()

    print("🔐 Setting up Google SSO for Infisical\n")

    # Read Google credentials
    print(f"📖 Reading Google OAuth2 credentials from: {args.client_secret_file}")
    client_id, client_secret = read_google_credentials(args.client_secret_file)
    print(f"✅ Client ID: {client_id}")
    print(f"✅ Client Secret: {client_secret[:10]}...")

    # Get .env file path
    env_file = Path(args.env_file) if args.env_file else get_env_file_path()

    print(f"\n📝 Updating environment file: {env_file}")

    # Read existing environment variables
    env_vars = read_env_file(env_file)

    # Prepare updates
    updates = {
        "CLIENT_ID_GOOGLE_LOGIN": client_id,
        "CLIENT_SECRET_GOOGLE_LOGIN": client_secret,
    }

    # Handle SITE_URL
    if args.site_url:
        updates["SITE_URL"] = args.site_url
    elif "SITE_URL" not in env_vars:
        updates["SITE_URL"] = "http://localhost:8080"
        print("⚠️  Warning: SITE_URL not set, using default: http://localhost:8080")

    # Generate AUTH_SECRET if not exists
    if "AUTH_SECRET" not in env_vars and "INFISICAL_AUTH_SECRET" not in env_vars:
        auth_secret = generate_auth_secret()
        updates["INFISICAL_AUTH_SECRET"] = auth_secret
        print(f"✅ Generated new AUTH_SECRET: {auth_secret[:10]}...")

    # Update .env file
    env_vars.update(updates)
    write_env_file(env_file, env_vars)
    print("✅ Environment file updated")

    # Print summary
    print("\n📋 Configuration Summary:")
    print(f"   CLIENT_ID_GOOGLE_LOGIN: {updates['CLIENT_ID_GOOGLE_LOGIN']}")
    print(f"   CLIENT_SECRET_GOOGLE_LOGIN: {updates['CLIENT_SECRET_GOOGLE_LOGIN'][:10]}...")
    if "SITE_URL" in updates:
        print(f"   SITE_URL: {updates['SITE_URL']}")
    if "INFISICAL_AUTH_SECRET" in updates:
        print(f"   INFISICAL_AUTH_SECRET: {updates['INFISICAL_AUTH_SECRET'][:10]}... (generated)")

    # Sync to Infisical if requested
    if args.sync_to_infisical:
        sync_to_infisical(env_file)

    # Restart Infisical backend
    if not args.no_restart:
        restart_infisical()

    print("\n✅ Google SSO configuration complete!")
    print("\n📝 Next Steps:")
    print("   1. Ensure your Google OAuth2 app has the correct redirect URI:")
    site_url = updates.get("SITE_URL", env_vars.get("SITE_URL", "http://localhost:8080"))
    print(f"      {site_url}/api/v1/sso/google")
    print("   2. Log in to Infisical web UI and enable Google SSO in organization settings")
    print("   3. Test login with: infisical login")
    print("\n   For CLI authentication in containerized environments:")
    print("      infisical login -i")


if __name__ == "__main__":
    main()
