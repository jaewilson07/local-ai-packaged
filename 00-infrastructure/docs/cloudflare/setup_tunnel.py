#!/usr/bin/env python3
"""
Cloudflare Tunnel Setup Script

This script helps set up Cloudflare Tunnel for the AI Homelab project.
It will:
1. Check for cloudflared CLI installation
2. Authenticate with Cloudflare (if needed)
3. Create a tunnel (or use existing)
4. Configure routes for all services
5. Generate tunnel token and update .env file
"""

import subprocess
import sys
import os
import re
from pathlib import Path

def run_command(cmd, check=True, capture_output=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}", file=sys.stderr)
        return None

def check_cloudflared_installed():
    """Check if cloudflared CLI is installed."""
    result = run_command("which cloudflared", check=False)
    if result and result.returncode == 0:
        version_result = run_command("cloudflared --version", check=False)
        if version_result:
            print(f"✅ Cloudflared CLI found: {version_result.stdout.strip()}")
            return True
    print("❌ Cloudflared CLI not found.")
    print("   Install it first: python3 utils/setup/install_clis.py")
    return False

def check_cloudflare_auth():
    """Check if user is authenticated with Cloudflare."""
    result = run_command("cloudflared tunnel list", check=False)
    if result and result.returncode == 0:
        print("✅ Authenticated with Cloudflare")
        return True
    print("❌ Not authenticated with Cloudflare")
    return False

def authenticate_cloudflare():
    """Authenticate with Cloudflare."""
    print("\n🔐 Authenticating with Cloudflare...")
    print("This will open a browser window for authentication.")
    result = run_command("cloudflared tunnel login", check=False, capture_output=False)
    if result and result.returncode == 0:
        print("✅ Authentication successful!")
        return True
    return False

def list_tunnels():
    """List existing tunnels."""
    result = run_command("cloudflared tunnel list", check=False)
    if result and result.returncode == 0:
        print("\n📋 Existing tunnels:")
        print(result.stdout)
        return result.stdout
    return None

def create_tunnel(tunnel_name="datacrew-services"):
    """Create a new Cloudflare tunnel."""
    print(f"\n🚇 Creating tunnel: {tunnel_name}")
    result = run_command(f"cloudflared tunnel create {tunnel_name}", check=False)
    if result and result.returncode == 0:
        print(f"✅ Tunnel '{tunnel_name}' created successfully!")
        return True
    elif result and "already exists" in result.stderr.lower():
        print(f"ℹ️  Tunnel '{tunnel_name}' already exists")
        return True
    else:
        print(f"❌ Failed to create tunnel: {result.stderr if result else 'Unknown error'}")
        return False

def get_tunnel_token(tunnel_name="datacrew-services"):
    """Get the tunnel token for a named tunnel."""
    print(f"\n🔑 Getting token for tunnel: {tunnel_name}")
    
    # Try to get token using cloudflared tunnel token command
    result = run_command(f"cloudflared tunnel token {tunnel_name}", check=False)
    if result and result.returncode == 0 and result.stdout.strip():
        token = result.stdout.strip()
        print("✅ Token retrieved successfully!")
        return token
    
    # Alternative: Get token from tunnel info
    result = run_command(f"cloudflared tunnel info {tunnel_name}", check=False)
    if result and result.returncode == 0:
        # Try to extract token from output
        match = re.search(r'token["\']?\s*[:=]\s*([^\s"\']+)', result.stdout)
        if match:
            return match.group(1)
    
    print("⚠️  Could not automatically retrieve token.")
    print("   You'll need to get it manually from the Cloudflare dashboard:")
    print("   1. Go to https://one.dash.cloudflare.com/")
    print("   2. Navigate to Networks → Tunnels")
    print(f"   3. Click on '{tunnel_name}'")
    print("   4. Copy the token from the Token field")
    return None

def update_env_file(token):
    """Update .env file with the tunnel token."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("⚠️  .env file not found. Creating it...")
        env_file.touch()
    
    # Read current content
    content = env_file.read_text()
    
    # Check if token already exists
    if "CLOUDFLARE_TUNNEL_TOKEN" in content:
        # Update existing token
        pattern = r'^CLOUDFLARE_TUNNEL_TOKEN=.*$'
        new_line = f"CLOUDFLARE_TUNNEL_TOKEN={token}\n"
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
            print("✅ Updated existing CLOUDFLARE_TUNNEL_TOKEN in .env")
        else:
            content += new_line
            print("✅ Added CLOUDFLARE_TUNNEL_TOKEN to .env")
    else:
        # Add new token
        content += f"\n# Cloudflare Tunnel Token\nCLOUDFLARE_TUNNEL_TOKEN={token}\n"
        print("✅ Added CLOUDFLARE_TUNNEL_TOKEN to .env")
    
    # Write back
    env_file.write_text(content)
    print(f"✅ Token saved to {env_file.absolute()}")

def main():
    """Main setup function."""
    print("=" * 60)
    print("Cloudflare Tunnel Setup")
    print("=" * 60)
    
    # Step 1: Check cloudflared installation
    if not check_cloudflared_installed():
        sys.exit(1)
    
    # Step 2: Check authentication
    if not check_cloudflare_auth():
        if not authenticate_cloudflare():
            print("❌ Authentication failed. Please try again.")
            sys.exit(1)
    
    # Step 3: List existing tunnels
    list_tunnels()
    
    # Step 4: Create or use existing tunnel
    tunnel_name = input("\nEnter tunnel name (default: datacrew-services): ").strip() or "datacrew-services"
    if not create_tunnel(tunnel_name):
        sys.exit(1)
    
    # Step 5: Get tunnel token
    token = get_tunnel_token(tunnel_name)
    
    if not token:
        token = input("\nPlease enter your tunnel token manually: ").strip()
        if not token:
            print("❌ No token provided. Exiting.")
            sys.exit(1)
    
    # Step 6: Update .env file
    update_env_file(token)
    
    print("\n" + "=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Configure tunnel routes in Cloudflare dashboard:")
    print("   https://one.dash.cloudflare.com/ → Networks → Tunnels → " + tunnel_name)
    print("2. Add public hostnames for each service (see docs/cloudflare/setup.md)")
    print("3. Restart infrastructure stack:")
    print("   ./start-stack.sh infrastructure")
    print("\nFor detailed route configuration, see:")
    print("  00-infrastructure/docs/cloudflare/setup.md")

if __name__ == "__main__":
    main()
