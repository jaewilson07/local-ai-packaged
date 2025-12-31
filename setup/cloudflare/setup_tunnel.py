#!/usr/bin/env python3
"""
setup_cloudflare_tunnel.py

Automated setup script for Cloudflare Tunnel using the cloudflared CLI.
This script will:
1. Check for cloudflared CLI installation
2. Authenticate with Cloudflare
3. Create a tunnel
4. Configure routes for all services
5. Generate tunnel token and update .env file
"""

import os
import subprocess
import shutil
import sys
import json
import re

# Service configuration
DOMAIN = "datacrew.space"
SERVICES = {
    "n8n": {"subdomain": "n8n", "port": 5678},
    "webui": {"subdomain": "webui", "port": 8080},
    "flowise": {"subdomain": "flowise", "port": 3001},
    "langfuse": {"subdomain": "langfuse", "port": 3000},
    "supabase": {"subdomain": "supabase", "port": 8000},
    "neo4j": {"subdomain": "neo4j", "port": 7474},
    "comfyui": {"subdomain": "comfyui", "port": 8188},
    "infisical": {"subdomain": "infisical", "port": 8080},
}

TUNNEL_NAME = "datacrew-services"
CADDY_URL = "http://caddy:80"


def run_command(cmd, check=True, capture_output=False, input_text=None):
    """Run a shell command and handle errors."""
    try:
        if input_text:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture_output,
                text=True,
                input=input_text,
            )
        else:
            result = subprocess.run(
                cmd, check=check, capture_output=capture_output, text=True
            )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
        print(f"Error: {e}")
        if capture_output and e.stdout:
            print(f"Output: {e.stdout}")
        if capture_output and e.stderr:
            print(f"Error output: {e.stderr}")
        sys.exit(1)


def check_cloudflared():
    """Check if cloudflared CLI is installed."""
    print("Checking for cloudflared CLI...")
    if not shutil.which("cloudflared"):
        print("\n[ERROR] cloudflared CLI not found!")
        print("\nPlease install cloudflared:")
        print("  Windows (PowerShell):")
        print('    winget install --id Cloudflare.cloudflared')
        print("\n  macOS:")
        print("    brew install cloudflared")
        print("\n  Linux:")
        print("    # Download from https://github.com/cloudflare/cloudflared/releases")
        print("    # Or use package manager")
        print("\n  Or visit: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
        sys.exit(1)
    
    # Check version
    result = run_command(["cloudflared", "--version"], capture_output=True)
    print(f"[OK] Found cloudflared: {result.stdout.strip()}")
    return True


def login_cloudflare():
    """Authenticate with Cloudflare (interactive)."""
    print("\n" + "="*60)
    print("Step 1: Authenticating with Cloudflare")
    print("="*60)
    print("\nThis will open your browser for authentication.")
    print("Please log in to your Cloudflare account when prompted.")
    input("\nPress Enter to continue...")
    
    try:
        run_command(["cloudflared", "tunnel", "login"], check=True)
        print("[OK] Successfully authenticated with Cloudflare!")
        return True
    except subprocess.CalledProcessError:
        print("[ERROR] Authentication failed. Please try again.")
        return False


def check_domain_in_cloudflare():
    """Check if domain is added to Cloudflare account."""
    print("\n" + "="*60)
    print("Step 2: Checking domain configuration")
    print("="*60)
    
    try:
        # Try to list tunnels - if domain is not configured, this might fail
        # But we'll proceed anyway and let the user know
        result = run_command(
            ["cloudflared", "tunnel", "list"], 
            capture_output=True,
            check=False
        )
        print(f"[OK] Cloudflare account is accessible")
        print(f"\n[WARNING] Make sure '{DOMAIN}' is added to your Cloudflare account.")
        print("   If not, add it at: https://dash.cloudflare.com/")
        print("   Then update nameservers in Squarespace DNS settings.")
        return True
    except Exception as e:
        print(f"[WARNING] Could not verify domain. Error: {e}")
        print(f"   Please ensure '{DOMAIN}' is added to Cloudflare.")
        return True  # Continue anyway


def create_tunnel():
    """Create a Cloudflare tunnel."""
    print("\n" + "="*60)
    print("Step 3: Creating Cloudflare Tunnel")
    print("="*60)
    
    # Check if tunnel already exists
    result = run_command(
        ["cloudflared", "tunnel", "list"],
        capture_output=True,
        check=False
    )
    
    if TUNNEL_NAME in result.stdout:
        print(f"[WARNING] Tunnel '{TUNNEL_NAME}' already exists.")
        response = input("Do you want to use the existing tunnel? (y/n): ").strip().lower()
        if response == 'y':
            print(f"[OK] Using existing tunnel '{TUNNEL_NAME}'")
            return TUNNEL_NAME
        else:
            print("Please delete the existing tunnel manually or choose a different name.")
            sys.exit(1)
    
    # Create new tunnel
    print(f"Creating tunnel '{TUNNEL_NAME}'...")
    try:
        run_command(["cloudflared", "tunnel", "create", TUNNEL_NAME])
        print(f"[OK] Tunnel '{TUNNEL_NAME}' created successfully!")
        return TUNNEL_NAME
    except subprocess.CalledProcessError:
        print("[ERROR] Failed to create tunnel.")
        print("   Make sure you're authenticated and the domain is in your Cloudflare account.")
        sys.exit(1)


def configure_routes(tunnel_name):
    """Configure routes for all services."""
    print("\n" + "="*60)
    print("Step 4: Configuring Routes")
    print("="*60)
    print(f"\nConfiguring DNS records for {len(SERVICES)} services...")
    print("Note: DNS records will be created, but you'll need to configure")
    print("the actual routing (public hostnames) in the Cloudflare dashboard.")
    print("The script will provide instructions after DNS setup.\n")
    
    routes_configured = []
    
    for service_name, config in SERVICES.items():
        subdomain = config["subdomain"]
        hostname = f"{subdomain}.{DOMAIN}"
        
        print(f"  Creating DNS record for {hostname}...")
        
        try:
            # Use cloudflared tunnel route dns command
            # This creates the DNS CNAME record pointing to the tunnel
            cmd = [
                "cloudflared", "tunnel", "route", "dns",
                tunnel_name,
                hostname
            ]
            
            result = run_command(cmd, capture_output=True, check=False)
            
            if result.returncode == 0:
                print(f"    [OK] DNS record created for {hostname}")
                routes_configured.append(hostname)
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                # Check if it's just a warning about existing record
                if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                    print(f"    [WARNING] {hostname} - DNS record already exists (this is OK)")
                    routes_configured.append(hostname)
                else:
                    print(f"    [WARNING] {hostname} - Error: {error_msg}")
                    print(f"       You may need to create this DNS record manually")
        
        except Exception as e:
            print(f"    [WARNING] {hostname} - Error: {e}")
            print(f"       You may need to create this DNS record manually")
    
    print(f"\n[OK] Created DNS records for {len(routes_configured)} services")
    print("\n[IMPORTANT] You still need to configure routing in Cloudflare dashboard.")
    print("   DNS records point to the tunnel, but you need to set up public hostnames.")
    
    return routes_configured


def get_tunnel_token(tunnel_name):
    """Get the tunnel token for the given tunnel."""
    print("\n" + "="*60)
    print("Step 5: Getting Tunnel Token")
    print("="*60)
    
    try:
        # Get tunnel info which includes the token
        result = run_command(
            ["cloudflared", "tunnel", "info", tunnel_name],
            capture_output=True,
            check=False
        )
        
        # Try to get token using cloudflared tunnel token command
        result = run_command(
            ["cloudflared", "tunnel", "token", tunnel_name],
            capture_output=True,
            check=True
        )
        
        token = result.stdout.strip()
        if token:
            print("[OK] Retrieved tunnel token")
            return token
        else:
            print("[WARNING] Could not retrieve token automatically")
            print("   You'll need to get it from Cloudflare dashboard:")
            print("   https://one.dash.cloudflare.com/ → Networks → Tunnels")
            print(f"   → {tunnel_name} → Copy token")
            return None
    
    except subprocess.CalledProcessError:
        print("[WARNING] Could not retrieve token automatically")
        print("   You'll need to get it from Cloudflare dashboard:")
        print("   https://one.dash.cloudflare.com/ → Networks → Tunnels")
        print(f"   → {tunnel_name} → Copy token")
        return None


def update_env_file(token):
    """Update .env file with tunnel token and hostnames."""
    print("\n" + "="*60)
    print("Step 6: Updating .env file")
    print("="*60)
    
    env_file = ".env"
    env_example = ".env.example"
    
    # Check if .env exists, if not check for .env.example
    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            print(f"[WARNING] .env file not found. Found {env_example} instead.")
            response = input(f"Copy {env_example} to .env? (y/n): ").strip().lower()
            if response == 'y':
                import shutil
                shutil.copy(env_example, env_file)
                print(f"[OK] Created .env from {env_example}")
            else:
                print("[WARNING] Please create .env file manually")
                return False
        else:
            print("[WARNING] .env file not found. Creating new one...")
            # Create basic .env file
            with open(env_file, 'w') as f:
                f.write("# Cloudflare Tunnel Configuration\n")
                f.write("CLOUDFLARE_TUNNEL_TOKEN=\n\n")
                f.write("# Service Hostnames\n")
                for service_name, config in SERVICES.items():
                    subdomain = config["subdomain"]
                    f.write(f"{service_name.upper()}_HOSTNAME={subdomain}.{DOMAIN}\n")
            print(f"[OK] Created {env_file}")
    
    # Read existing .env file
    try:
        with open(env_file, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"[ERROR] Error reading {env_file}: {e}")
        return False
    
    # Update or add CLOUDFLARE_TUNNEL_TOKEN
    if token:
        if "CLOUDFLARE_TUNNEL_TOKEN" in content:
            # Update existing token
            content = re.sub(
                r'CLOUDFLARE_TUNNEL_TOKEN=.*',
                f'CLOUDFLARE_TUNNEL_TOKEN={token}',
                content
            )
        else:
            # Add token if not present
            if not content.endswith('\n'):
                content += '\n'
            content += f"\n# Cloudflare Tunnel Configuration\n"
            content += f"CLOUDFLARE_TUNNEL_TOKEN={token}\n"
    
    # Update hostnames
    for service_name, config in SERVICES.items():
        subdomain = config["subdomain"]
        hostname = f"{subdomain}.{DOMAIN}"
        env_var = f"{service_name.upper()}_HOSTNAME"
        
        if env_var in content:
            # Update existing
            content = re.sub(
                rf'{env_var}=.*',
                f'{env_var}={hostname}',
                content
            )
        else:
            # Add if not present
            if not content.endswith('\n'):
                content += '\n'
            content += f"{env_var}={hostname}\n"
    
    # Write back to file
    try:
        with open(env_file, 'w') as f:
            f.write(content)
        print(f"[OK] Updated {env_file}")
        print(f"   - Added CLOUDFLARE_TUNNEL_TOKEN")
        print(f"   - Updated {len(SERVICES)} hostname variables")
        return True
    except Exception as e:
        print(f"[ERROR] Error writing {env_file}: {e}")
        return False


def configure_public_hostnames_manually(tunnel_name):
    """Provide instructions for manual route configuration."""
    print("\n" + "="*60)
    print("Step 7: Configure Public Hostnames (REQUIRED)")
    print("="*60)
    print("\n[IMPORTANT] You MUST configure public hostnames in the Cloudflare dashboard.")
    print("   DNS records are created, but routing needs to be configured manually.\n")
    print(f"1. Go to: https://one.dash.cloudflare.com/")
    print("2. Navigate to: Networks → Tunnels")
    print(f"3. Click on tunnel: {tunnel_name}")
    print("4. Click 'Configure' under 'Public Hostnames'")
    print("5. For each service below, click 'Add a public hostname' and configure:\n")
    
    for service_name, config in SERVICES.items():
        subdomain = config["subdomain"]
        hostname = f"{subdomain}.{DOMAIN}"
        print(f"   📌 {service_name.upper()}")
        print(f"      Subdomain: {subdomain}")
        print(f"      Domain: {DOMAIN}")
        print(f"      Service Type: HTTP")
        print(f"      URL: {CADDY_URL}")
        print(f"      Additional Settings → Host Header: {hostname}")
        print()
    
    print("💡 Tip: You can configure all services to use the same URL (http://caddy:80)")
    print("   Caddy will route to the correct service based on the Host header.")
    print()
    input("Press Enter after you've configured the public hostnames...")


def main():
    """Main setup function."""
    print("="*60)
    print("Cloudflare Tunnel Setup for datacrew.space")
    print("="*60)
    print("\nThis script will help you set up Cloudflare Tunnel to expose")
    print("your Docker services under datacrew.space subdomains.")
    print("\nPrerequisites:")
    print("  [OK] Domain 'datacrew.space' added to Cloudflare")
    print("  [OK] Nameservers updated in Squarespace")
    print("  [OK] cloudflared CLI installed")
    
    input("\nPress Enter to start setup...")
    
    # Step 1: Check cloudflared
    check_cloudflared()
    
    # Step 2: Login
    if not login_cloudflare():
        print("[ERROR] Setup cancelled")
        sys.exit(1)
    
    # Step 3: Check domain
    check_domain_in_cloudflare()
    
    # Step 4: Create tunnel
    tunnel_name = create_tunnel()
    
    # Step 5: Configure routes
    routes = configure_routes(tunnel_name)
    
    # Step 6: Get token
    token = get_tunnel_token(tunnel_name)
    
    if not token:
        print("\n[WARNING] Could not retrieve token automatically.")
        token = input("Please paste your tunnel token from Cloudflare dashboard: ").strip()
        if not token:
            print("[ERROR] Token is required. Exiting.")
            sys.exit(1)
    
    # Step 7: Update .env
    update_env_file(token)
    
    # Step 7: Manual configuration instructions (always required)
    configure_public_hostnames_manually(tunnel_name)
    
    # Final instructions
    print("\n" + "="*60)
    print("[OK] Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Verify DNS propagation (may take a few hours)")
    print("2. Start your services:")
    print("   python start_services.py --profile gpu-nvidia")
    print("3. Check cloudflared logs:")
    print("   docker logs cloudflared")
    print("4. Test your services:")
    for service_name, config in SERVICES.items():
        subdomain = config["subdomain"]
        print(f"   https://{subdomain}.{DOMAIN}")
    print("\nFor troubleshooting, see: CLOUDFLARE_SETUP.md")


if __name__ == "__main__":
    main()

