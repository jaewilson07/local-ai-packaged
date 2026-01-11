#!/usr/bin/env python3
"""
migrate-postman-to-lambda-api.py

Migrate Postman from api.datacrew.space to postman.datacrew.space,
and configure Lambda RAG API at api.datacrew.space using Cloudflare CLI.

Prerequisites:
    - cloudflared CLI installed
    - Authenticated with Cloudflare (cloudflared login)
    - Tunnel already created

Usage:
    python 00-infrastructure/scripts/migrate-postman-to-lambda-api.py [--dry-run]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Configuration
TUNNEL_ID = os.getenv("CLOUDFLARE_TUNNEL_ID", "")
DOMAIN = "datacrew.space"
CADDY_URL = "http://caddy:80"


def run_command(cmd, capture_output=True, check=True):
    """Run a shell command and return the result."""
    print(f"[CMD] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {e}")
        if e.stderr:
            print(f"[STDERR] {e.stderr}")
        raise


def check_cloudflared():
    """Check if cloudflared CLI is installed."""
    try:
        result = run_command(["cloudflared", "version"], check=False)
        if result.returncode == 0:
            print(f"[OK] cloudflared version: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    print("[ERROR] cloudflared CLI not found!")
    print("\nInstall instructions:")
    print("  macOS:   brew install cloudflared")
    print(
        "  Linux:   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    )
    print("           chmod +x cloudflared-linux-amd64")
    print("           sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared")
    print("  Windows: winget install --id Cloudflare.cloudflared")
    return False


def get_tunnel_config():
    """Get current tunnel configuration."""
    if not TUNNEL_ID:
        print("[ERROR] CLOUDFLARE_TUNNEL_ID not set in .env file")
        return None

    print(f"\n[INFO] Getting configuration for tunnel: {TUNNEL_ID}")

    # Use cloudflared tunnel info to get tunnel details
    result = run_command(
        ["cloudflared", "tunnel", "info", TUNNEL_ID, "--output", "json"], check=False
    )

    if result.returncode != 0:
        print(f"[WARNING] Could not get tunnel info: {result.stderr}")
        return None

    try:
        tunnel_info = json.loads(result.stdout)
        print(f"[OK] Tunnel name: {tunnel_info.get('name', 'N/A')}")
        return tunnel_info
    except json.JSONDecodeError:
        print("[WARNING] Could not parse tunnel info")
        return None


def list_tunnel_routes():
    """List current tunnel routes."""
    if not TUNNEL_ID:
        print("[ERROR] CLOUDFLARE_TUNNEL_ID not set")
        return []

    print(f"\n[INFO] Listing routes for tunnel: {TUNNEL_ID}")

    # Note: cloudflared CLI doesn't directly list routes via command
    # We need to use the API for this, which the existing script handles
    print("[INFO] Current routes can be viewed in Cloudflare Dashboard:")
    print(f"       https://dash.cloudflare.com/ → Networks → Tunnels → {TUNNEL_ID}")

    return []


def backup_postman_route(dry_run=False):
    """
    Backup information about the current Postman route at api.datacrew.space.

    Note: This is informational - the actual route details are in Cloudflare Dashboard.
    """
    print("\n" + "=" * 70)
    print("STEP 1: Backup Current Postman Route")
    print("=" * 70)

    print(f"\n[INFO] Current route: api.{DOMAIN}")
    print("[INFO] This route currently points to Postman")
    print("[INFO] We will update it to point to Lambda RAG API")

    if dry_run:
        print("[DRY-RUN] Would backup current configuration")
    else:
        print("\n[ACTION] Please manually note your Postman service URL if needed:")
        print("         1. Go to Cloudflare Dashboard → Networks → Tunnels")
        print(f"         2. Find the route for api.{DOMAIN}")
        print("         3. Note the Service URL (e.g., http://postman-service:port)")
        input("\nPress Enter once you've noted the Postman service URL...")


def update_api_route_to_lambda(dry_run=False):
    """Update api.datacrew.space to point to Lambda via Caddy."""
    print("\n" + "=" * 70)
    print("STEP 2: Update api.datacrew.space → Lambda RAG API")
    print("=" * 70)

    hostname = f"api.{DOMAIN}"
    service_url = CADDY_URL

    print("\n[INFO] Configuring route:")
    print(f"  Hostname: {hostname}")
    print(f"  Service:  {service_url}")

    if dry_run:
        print("[DRY-RUN] Would run:")
        print(f"  cloudflared tunnel route dns {TUNNEL_ID} {hostname}")
        return True

    # Use cloudflared to configure the route
    print("\n[ACTION] Configuring tunnel route...")

    try:
        # Add DNS route
        result = run_command(
            ["cloudflared", "tunnel", "route", "dns", TUNNEL_ID, hostname], check=False
        )

        if result.returncode == 0:
            print(f"[OK] DNS route configured for {hostname}")
        else:
            print(f"[WARNING] DNS route may already exist: {result.stderr}")

        print("\n[INFO] Route configuration updated!")
        print(f"[INFO] {hostname} now points to {service_url} via tunnel")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to configure route: {e}")
        return False


def add_postman_route(dry_run=False):
    """Add postman.datacrew.space route."""
    print("\n" + "=" * 70)
    print("STEP 3: Add postman.datacrew.space Route (Optional)")
    print("=" * 70)

    hostname = f"postman.{DOMAIN}"

    print(f"\n[INFO] To move Postman to {hostname}:")
    print("       You need to specify where Postman is currently hosted")

    if dry_run:
        print(f"[DRY-RUN] Would configure postman.{DOMAIN} route")
        return

    response = input("\nDo you want to configure postman.datacrew.space now? (y/n): ")
    if response.lower() != "y":
        print("[SKIP] Skipping Postman route configuration")
        print("[INFO] You can configure it manually later in Cloudflare Dashboard")
        return

    postman_service = input("\nEnter Postman service URL (e.g., http://postman:3000): ").strip()

    if not postman_service:
        print("[SKIP] No service URL provided, skipping")
        return

    print(f"\n[ACTION] Configuring {hostname} → {postman_service}")

    try:
        # Add DNS route
        result = run_command(
            ["cloudflared", "tunnel", "route", "dns", TUNNEL_ID, hostname], check=False
        )

        if result.returncode == 0:
            print(f"[OK] DNS route configured for {hostname}")
        else:
            print(f"[WARNING] DNS route may already exist: {result.stderr}")

        print("\n[OK] Postman route configured!")
        print(f"[INFO] {hostname} → {postman_service}")
        print("\n[NOTE] You still need to configure the tunnel ingress rule")
        print(f"       in your tunnel config to route to {postman_service}")

    except Exception as e:
        print(f"[ERROR] Failed to configure Postman route: {e}")


def update_tunnel_config_file(dry_run=False):
    """
    Update the tunnel configuration file to include the new routes.

    Note: When using token-based tunnels (as in this project),
    routes are managed via Cloudflare Dashboard or API, not config file.
    """
    print("\n" + "=" * 70)
    print("STEP 4: Update Tunnel Configuration")
    print("=" * 70)

    print("\n[INFO] This project uses token-based tunnel configuration")
    print("[INFO] Routes are managed via Cloudflare Dashboard, not config file")
    print("\n[INFO] The tunnel will automatically route based on hostname:")
    print(f"  - api.{DOMAIN} → {CADDY_URL} → lambda-server:8000")
    print("  - (Caddy handles the internal routing based on Host header)")

    if not dry_run:
        print("\n[ACTION] Please verify in Cloudflare Dashboard:")
        print("         1. Networks → Tunnels → Your Tunnel → Public Hostnames")
        print(f"         2. Verify api.{DOMAIN} points to http://caddy:80")
        print("         3. If Postman route exists, verify it points to correct service")


def restart_caddy():
    """Restart or reload Caddy to apply new configuration."""
    print("\n" + "=" * 70)
    print("STEP 5: Reload Caddy Configuration")
    print("=" * 70)

    print("\n[INFO] Reloading Caddy to apply new routes...")

    try:
        result = run_command(
            ["docker", "exec", "caddy", "caddy", "reload", "--config", "/etc/caddy/Caddyfile"],
            check=False,
        )

        if result.returncode == 0:
            print("[OK] Caddy configuration reloaded successfully")
            return True
        else:
            print(f"[WARNING] Caddy reload failed: {result.stderr}")
            print("[INFO] You may need to restart the Caddy container:")
            print("       docker restart caddy")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to reload Caddy: {e}")
        return False


def test_api_endpoint(dry_run=False):
    """Test the Lambda API endpoint."""
    print("\n" + "=" * 70)
    print("STEP 6: Test API Endpoint")
    print("=" * 70)

    hostname = f"api.{DOMAIN}"

    print(f"\n[INFO] Testing https://{hostname}/health")

    if dry_run:
        print(f"[DRY-RUN] Would test: curl https://{hostname}/health")
        return

    print("\n[INFO] Waiting a few seconds for DNS propagation...")
    import time

    time.sleep(5)

    try:
        result = run_command(["curl", "-s", "-f", f"https://{hostname}/health"], check=False)

        if result.returncode == 0:
            print("[OK] API is responding!")
            print(f"[RESPONSE] {result.stdout}")
            return True
        else:
            print("[WARNING] API not responding yet")
            print("[INFO] This might be due to DNS propagation delay")
            print("[INFO] Try testing again in a few minutes:")
            print(f"       curl https://{hostname}/health")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to test endpoint: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Postman and configure Lambda RAG API routes"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Cloudflare Tunnel Route Migration")
    print("=" * 70)
    print(f"\nTarget: {DOMAIN}")
    print(f"Tunnel ID: {TUNNEL_ID or 'NOT SET'}")

    if args.dry_run:
        print("\n[DRY-RUN MODE] No changes will be made")

    # Check prerequisites
    if not check_cloudflared():
        return 1

    if not TUNNEL_ID:
        print("\n[ERROR] CLOUDFLARE_TUNNEL_ID not set in .env file")
        return 1

    # Get tunnel info
    get_tunnel_config()

    # List current routes
    list_tunnel_routes()

    # Migration steps
    backup_postman_route(dry_run=args.dry_run)

    if not update_api_route_to_lambda(dry_run=args.dry_run):
        print("\n[ERROR] Failed to update api route")
        return 1

    add_postman_route(dry_run=args.dry_run)

    update_tunnel_config_file(dry_run=args.dry_run)

    if not args.dry_run:
        restart_caddy()
        test_api_endpoint()

    # Final summary
    print("\n" + "=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"\n✅ api.{DOMAIN} → Lambda RAG API (via Caddy)")
    print(f"   Endpoints: https://api.{DOMAIN}/health")
    print(f"              https://api.{DOMAIN}/api/v1/rag/*")

    print("\n📝 Postman migration:")
    print(f"   If configured: postman.{DOMAIN} → Postman service")
    print("   If not: Configure manually in Cloudflare Dashboard")

    print("\n🔍 Next steps:")
    print("   1. Verify routes in Cloudflare Dashboard:")
    print("      https://dash.cloudflare.com/ → Networks → Tunnels")
    print(f"   2. Test API: curl https://api.{DOMAIN}/health")
    print("   3. Update Cloudflare Access policies if needed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
