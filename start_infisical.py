#!/usr/bin/env python3
"""
start_infisical.py

This script manages Infisical services:
- infisical-backend: Main Infisical application
- infisical-db: PostgreSQL database for Infisical
- infisical-redis: Redis cache for Infisical

All services use the Docker Compose project name ("localai") and external network ("ai-network").
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        if result.stdout:
            print("Stdout:", result.stdout)
        if result.stderr:
            print("Stderr:", result.stderr)
        if check:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
    if result.stdout:
        print(result.stdout)
    return result


def load_env_file(env_path=None):
    """Load environment variables from .env file."""
    if env_path is None:
        # Try to find .env file in current directory or infisical-standalone
        env_paths = [".env", os.path.expanduser("~/infisical-standalone/.env")]
        for path in env_paths:
            if os.path.exists(path):
                env_path = path
                break
        else:
            return {}

    env_vars = {}
    if env_path and os.path.exists(env_path):
        env_path_obj = Path(env_path)
        with env_path_obj.open(encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
    return env_vars


def check_required_env_vars():
    """Check if required Infisical environment variables are set."""
    env_vars = load_env_file()
    required_vars = [
        "INFISICAL_ENCRYPTION_KEY",
        "INFISICAL_AUTH_SECRET",
        "INFISICAL_POSTGRES_PASSWORD",
    ]

    missing = []
    for var in required_vars:
        if not env_vars.get(var) and not os.environ.get(var):
            missing.append(var)

    if missing:
        print("❌ Error: Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file.")
        return False

    return True


def wait_for_infisical(max_retries=30, retry_interval=2):
    """Wait for Infisical to become ready by checking its health endpoint."""
    print("Waiting for Infisical to become ready...")

    for i in range(max_retries):
        try:
            # Try to check health endpoint via docker exec using wget
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "infisical-backend",
                    "wget",
                    "--no-verbose",
                    "--tries=1",
                    "--spider",
                    "http://localhost:8080/api/status",
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                print("✓ Infisical is ready!")
                return True
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            pass
        except Exception as e:
            print(f"Error checking Infisical health: {e}")

        if i < max_retries - 1:
            print(f"Infisical not ready yet, waiting {retry_interval}s... ({i + 1}/{max_retries})")
            time.sleep(retry_interval)

    print("⚠️  Warning: Infisical did not become ready within the expected time.")
    print("You may need to check the Infisical container logs manually.")
    return False


def manage_infisical(action="start", environment="private"):
    """Start or stop Infisical services."""

    # Use standalone Infisical directory
    infisical_dir = "/home/jaewilson07/GitHub/infisical-standalone"
    compose_file = os.path.join(infisical_dir, "docker-compose.yml")
    override_file = os.path.join(infisical_dir, f"docker-compose.override.{environment}.yml")

    if not os.path.exists(compose_file):
        print(f"❌ Error: Docker Compose file not found at {compose_file}")
        print(f"   Please ensure Infisical is set up in {infisical_dir}")
        return False

    # Build docker compose command
    cmd = ["docker", "compose", "-p", "infisical"]
    cmd.extend(["-f", compose_file])

    if os.path.exists(override_file):
        cmd.extend(["-f", override_file])

    # Try to use .env from local-ai-packaged project, or from infisical-standalone
    # Use absolute paths to avoid issues when running from different directories
    current_dir = os.getcwd()
    env_file_paths = [
        os.path.join(current_dir, ".env"),  # Current directory (local-ai-packaged)
        os.path.join(infisical_dir, ".env"),  # Standalone directory
    ]

    env_file_path = None
    for path in env_file_paths:
        if os.path.exists(path):
            env_file_path = os.path.abspath(path)
            break

    if env_file_path:
        cmd.extend(["--env-file", env_file_path])
    else:
        print("⚠️  Warning: No .env file found. Using environment variables from shell.")

    if action == "stop":
        cmd.append("down")
        print("Stopping Infisical services...")
    else:
        cmd.extend(["up", "-d"])
        print("Starting Infisical services...")

    try:
        # Run from the infisical directory
        run_command(cmd, cwd=infisical_dir)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error {action}ing Infisical services: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Manage Infisical services (backend, database, redis).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_infisical.py                    # Start Infisical services
  python start_infisical.py --action stop       # Stop Infisical services
  python start_infisical.py --environment public # Start with public environment overrides
        """,
    )
    parser.add_argument(
        "--action",
        choices=["start", "stop"],
        default="start",
        help="Action to perform: start or stop services (default: start)",
    )
    parser.add_argument(
        "--environment",
        choices=["private", "public"],
        default="private",
        help="Environment to use for Docker Compose (default: private)",
    )
    parser.add_argument(
        "--skip-wait",
        action="store_true",
        help="Skip waiting for Infisical to become ready after starting",
    )
    args = parser.parse_args()

    # Stop logic is simpler - just stop services
    if args.action == "stop":
        success = manage_infisical(action="stop", environment=args.environment)
        if success:
            print("✓ Infisical services stopped successfully!")
        else:
            sys.exit(1)
        return

    # Start logic (includes pre-flight checks)
    print("=" * 70)
    print("Infisical Service Manager")
    print("=" * 70)
    print()

    # Check required environment variables
    if not check_required_env_vars():
        sys.exit(1)

    print("✓ Required environment variables are set")
    print()

    # Start services
    success = manage_infisical(action="start", environment=args.environment)

    if not success:
        print("❌ Error: Failed to start Infisical services. Check the error messages above.")
        sys.exit(1)

    # Wait for Infisical to be ready
    if not args.skip_wait:
        print()
        wait_for_infisical()

    print()
    print("=" * 70)
    print("✓ Infisical services started successfully!")
    print("=" * 70)
    print()
    print("Infisical is running standalone at: /home/jaewilson07/GitHub/infisical-standalone")
    print()
    print("Access Infisical:")
    print("  - Local: http://localhost:8020")
    print("  - Via Caddy: https://infisical.datacrew.space (if configured)")
    print()
    print("Next steps:")
    print("  1. Open Infisical UI in your browser")
    print("  2. Create a project and add secrets")
    print("  3. Sync secrets to .env: infisical export --format=dotenv > .env.infisical")
    print()
    print("Note: Infisical runs independently from local-ai-packaged services.")


if __name__ == "__main__":
    main()
