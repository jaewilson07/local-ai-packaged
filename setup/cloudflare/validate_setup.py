#!/usr/bin/env python3
"""
validate_cloudflare_setup.py

Comprehensive validation script for Cloudflare Tunnel setup.
This script validates:
1. Environment variables (.env file)
2. Docker containers (cloudflared, caddy)
3. Cloudflare API configuration (tunnel, routes, DNS)
4. DNS resolution
5. Service accessibility
"""

import os
import sys
import subprocess
import requests
import socket
import time
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Configuration
DOMAIN = "datacrew.space"
SERVICES = {
    "n8n": {"subdomain": "n8n", "env_var": "N8N_HOSTNAME"},
    "webui": {"subdomain": "webui", "env_var": "WEBUI_HOSTNAME"},
    "flowise": {"subdomain": "flowise", "env_var": "FLOWISE_HOSTNAME"},
    "langfuse": {"subdomain": "langfuse", "env_var": "LANGFUSE_HOSTNAME"},
    "supabase": {"subdomain": "supabase", "env_var": "SUPABASE_HOSTNAME"},
    "neo4j": {"subdomain": "neo4j", "env_var": "NEO4J_HOSTNAME"},
    "comfyui": {"subdomain": "comfyui", "env_var": "COMFYUI_HOSTNAME"},
    "infisical": {"subdomain": "infisical", "env_var": "INFISICAL_HOSTNAME"},
}

# Cloudflare API configuration
CLOUDFLARE_EMAIL = os.getenv("CLOUDFLARE_EMAIL", "")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")

# Results tracking
results = {
    "passed": [],
    "failed": [],
    "warnings": [],
    "skipped": [],
}


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_result(status, message, details=""):
    """Print a validation result."""
    # Use ASCII characters for Windows compatibility
    icon = "[OK]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[WARN]" if status == "WARN" else "[SKIP]"
    print(f"{icon} {message}")
    if details:
        print(f"   {details}")
    
    if status == "PASS":
        results["passed"].append(message)
    elif status == "FAIL":
        results["failed"].append(message)
    elif status == "WARN":
        results["warnings"].append(message)
    else:
        results["skipped"].append(message)


def get_auth_headers():
    """Get authentication headers for Cloudflare API."""
    if CLOUDFLARE_API_TOKEN and CLOUDFLARE_API_TOKEN.strip():
        return {
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json",
        }
    elif CLOUDFLARE_EMAIL and CLOUDFLARE_EMAIL.strip() and CLOUDFLARE_API_KEY and CLOUDFLARE_API_KEY.strip():
        return {
            "X-Auth-Email": CLOUDFLARE_EMAIL.strip(),
            "X-Auth-Key": CLOUDFLARE_API_KEY.strip(),
            "Content-Type": "application/json",
        }
    else:
        return None


def get_zone_id():
    """Get Zone ID from Cloudflare API."""
    if CLOUDFLARE_ZONE_ID:
        return CLOUDFLARE_ZONE_ID
    
    headers = get_auth_headers()
    if not headers:
        return None
    
    url = "https://api.cloudflare.com/client/v4/zones"
    params = {"name": DOMAIN}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("result"):
                return data["result"][0]["id"]
    except Exception:
        pass
    
    return None


def check_env_variables():
    """Check environment variables in .env file."""
    print_header("1. Environment Variables (.env file)")
    
    # Check tunnel token
    tunnel_token = os.getenv("CLOUDFLARE_TUNNEL_TOKEN", "")
    if tunnel_token and tunnel_token.strip():
        print_result("PASS", f"CLOUDFLARE_TUNNEL_TOKEN is set", f"Token length: {len(tunnel_token)}")
    else:
        print_result("FAIL", "CLOUDFLARE_TUNNEL_TOKEN is not set", "Add this to your .env file")
    
    # Check hostname variables
    hostnames_configured = 0
    hostnames_missing = []
    
    for service_name, config in SERVICES.items():
        env_var = config["env_var"]
        hostname = os.getenv(env_var, "")
        
        if hostname and hostname.strip():
            expected = f"{config['subdomain']}.{DOMAIN}"
            if expected in hostname:
                print_result("PASS", f"{env_var} is configured", f"Value: {hostname}")
                hostnames_configured += 1
            else:
                print_result("WARN", f"{env_var} is set but may be incorrect", f"Value: {hostname}, Expected: {expected}")
                hostnames_configured += 1
        else:
            hostnames_missing.append(env_var)
            print_result("FAIL", f"{env_var} is not set", f"Expected: {config['subdomain']}.{DOMAIN}")
    
    if hostnames_configured == len(SERVICES):
        print_result("PASS", f"All {len(SERVICES)} hostname variables are configured")
    else:
        print_result("WARN", f"Only {hostnames_configured}/{len(SERVICES)} hostname variables configured")


def check_docker_containers():
    """Check Docker containers are running."""
    print_header("2. Docker Containers")
    
    # Check if Docker is available
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print_result("PASS", "Docker is installed", result.stdout.strip())
        else:
            print_result("FAIL", "Docker is not working properly")
            return
    except FileNotFoundError:
        print_result("FAIL", "Docker is not installed or not in PATH")
        return
    except Exception as e:
        print_result("FAIL", f"Error checking Docker: {e}")
        return
    
    # Check cloudflared container
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=cloudflared", "--format", "{{.Names}} {{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "cloudflared" in result.stdout:
            print_result("PASS", "cloudflared container is running", result.stdout.strip())
            
            # Check cloudflared logs for connection status
            try:
                log_result = subprocess.run(
                    ["docker", "logs", "--tail", "20", "cloudflared"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                logs = log_result.stdout.lower()
                if "connection established" in logs or "connected" in logs:
                    print_result("PASS", "cloudflared tunnel is connected", "Connection established")
                elif "error" in logs or "failed" in logs:
                    print_result("WARN", "cloudflared logs show errors", "Check logs: docker logs cloudflared")
                else:
                    print_result("WARN", "cloudflared connection status unclear", "Check logs: docker logs cloudflared")
            except Exception:
                print_result("WARN", "Could not check cloudflared logs")
        else:
            print_result("FAIL", "cloudflared container is not running", "Start with: docker-compose up -d cloudflared")
    except Exception as e:
        print_result("FAIL", f"Error checking cloudflared: {e}")
    
    # Check caddy container
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=caddy", "--format", "{{.Names}} {{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "caddy" in result.stdout:
            print_result("PASS", "caddy container is running", result.stdout.strip())
        else:
            print_result("FAIL", "caddy container is not running", "Start with: docker-compose up -d caddy")
    except Exception as e:
        print_result("FAIL", f"Error checking caddy: {e}")


def check_cloudflare_api():
    """Check Cloudflare API configuration."""
    print_header("3. Cloudflare API Configuration")
    
    headers = get_auth_headers()
    if not headers:
        print_result("WARN", "Cloudflare API credentials not configured", 
                    "Set CLOUDFLARE_API_TOKEN or CLOUDFLARE_EMAIL + CLOUDFLARE_API_KEY in .env")
        print_result("SKIP", "Skipping API-based checks")
        return
    
    # Test API authentication
    try:
        url = "https://api.cloudflare.com/client/v4/user/tokens/verify"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print_result("PASS", "Cloudflare API authentication successful")
            else:
                print_result("FAIL", "Cloudflare API authentication failed", str(data.get("errors", [])))
                return
        else:
            print_result("FAIL", f"Cloudflare API request failed", f"HTTP {response.status_code}")
            return
    except Exception as e:
        print_result("FAIL", f"Error connecting to Cloudflare API: {e}")
        return
    
    # Get Zone ID
    zone_id = get_zone_id()
    if zone_id:
        print_result("PASS", f"Domain {DOMAIN} found in Cloudflare", f"Zone ID: {zone_id}")
    else:
        print_result("FAIL", f"Domain {DOMAIN} not found in Cloudflare", "Add domain to Cloudflare account")
        return
    
    # Get Account ID (needed for tunnel API)
    try:
        url = "https://api.cloudflare.com/client/v4/accounts"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("result"):
                account_id = data["result"][0]["id"]
            else:
                account_id = None
        else:
            account_id = None
    except Exception:
        account_id = None
    
    # Check DNS records for services
    print("\n   Checking DNS records for services...")
    try:
        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
        response = requests.get(url, headers=headers, params={"per_page": 100}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                records = {r["name"]: r for r in data.get("result", [])}
                
                # Extract tunnel ID from DNS records
                tunnel_id = None
                for record_name, record in records.items():
                    if record["type"] == "CNAME" and "cfargotunnel.com" in record.get("content", ""):
                        # Extract tunnel ID from CNAME (format: tunnel-id.cfargotunnel.com)
                        content = record.get("content", "")
                        if ".cfargotunnel.com" in content:
                            tunnel_id = content.split(".cfargotunnel.com")[0]
                            break
                
                for service_name, config in SERVICES.items():
                    subdomain = config["subdomain"]
                    hostname = f"{subdomain}.{DOMAIN}"
                    
                    # Check for CNAME record pointing to tunnel
                    found = False
                    for record_name, record in records.items():
                        if record_name == hostname or record_name == subdomain:
                            if record["type"] in ["CNAME", "A"]:
                                print_result("PASS", f"DNS record exists for {hostname}", 
                                           f"Type: {record['type']}, Content: {record.get('content', 'N/A')}")
                                found = True
                                break
                    
                    if not found:
                        print_result("WARN", f"DNS record not found for {hostname}", 
                                   "DNS record may be auto-created by tunnel or needs manual creation")
                
                # Check tunnel routes if we have account ID and tunnel ID
                if account_id and tunnel_id:
                    print(f"\n   Checking tunnel routes (Tunnel ID: {tunnel_id})...")
                    try:
                        tunnel_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations"
                        tunnel_response = requests.get(tunnel_url, headers=headers, timeout=10)
                        if tunnel_response.status_code == 200:
                            tunnel_data = tunnel_response.json()
                            if tunnel_data.get("success"):
                                config = tunnel_data.get("result", {}).get("config", {})
                                ingress = config.get("ingress", [])
                                
                                # Count configured routes
                                configured_routes = []
                                for rule in ingress:
                                    hostname_val = rule.get("hostname")
                                    if hostname_val:
                                        configured_routes.append(hostname_val)
                                
                                if configured_routes:
                                    print_result("PASS", f"Tunnel has {len(configured_routes)} route(s) configured")
                                    
                                    # Check if all services have routes
                                    missing_routes = []
                                    for service_name, config in SERVICES.items():
                                        hostname = f"{config['subdomain']}.{DOMAIN}"
                                        if hostname not in configured_routes:
                                            missing_routes.append(hostname)
                                    
                                    if missing_routes:
                                        print_result("WARN", f"{len(missing_routes)} service(s) missing tunnel routes", 
                                                   f"Missing: {', '.join(missing_routes)}")
                                    else:
                                        print_result("PASS", "All services have tunnel routes configured")
                                else:
                                    print_result("WARN", "Tunnel has no routes configured", 
                                               "Configure routes in Cloudflare dashboard")
                            else:
                                print_result("WARN", "Could not retrieve tunnel configuration", 
                                           str(tunnel_data.get("errors", [])))
                        else:
                            print_result("WARN", f"Could not check tunnel configuration", 
                                       f"HTTP {tunnel_response.status_code}")
                    except Exception as e:
                        print_result("WARN", f"Error checking tunnel routes: {e}")
            else:
                print_result("WARN", "Could not retrieve DNS records", str(data.get("errors", [])))
        else:
            print_result("WARN", f"Could not check DNS records", f"HTTP {response.status_code}")
    except Exception as e:
        print_result("WARN", f"Error checking DNS records: {e}")


def check_dns_resolution():
    """Check DNS resolution for service subdomains."""
    print_header("4. DNS Resolution")
    
    for service_name, config in SERVICES.items():
        subdomain = config["subdomain"]
        hostname = f"{subdomain}.{DOMAIN}"
        
        try:
            # Try to resolve the hostname
            ip = socket.gethostbyname(hostname)
            print_result("PASS", f"{hostname} resolves", f"IP: {ip}")
        except socket.gaierror:
            print_result("WARN", f"{hostname} does not resolve", 
                        "DNS may not have propagated yet (can take up to 24 hours)")
        except Exception as e:
            print_result("WARN", f"Error resolving {hostname}: {e}")


def check_service_accessibility():
    """Check if services are accessible via HTTPS."""
    print_header("5. Service Accessibility (HTTPS)")
    
    print("   Note: This checks if services respond via HTTPS.")
    print("   Services may not be accessible if DNS hasn't propagated or tunnel isn't connected.\n")
    
    for service_name, config in SERVICES.items():
        subdomain = config["subdomain"]
        hostname = f"{subdomain}.{DOMAIN}"
        url = f"https://{hostname}"
        
        try:
            # Try HTTPS request with short timeout
            response = requests.get(url, timeout=5, allow_redirects=True, verify=True)
            if response.status_code < 500:
                print_result("PASS", f"{hostname} is accessible", f"HTTP {response.status_code}")
            else:
                print_result("WARN", f"{hostname} returned error", f"HTTP {response.status_code}")
        except requests.exceptions.SSLError:
            print_result("WARN", f"{hostname} SSL certificate issue", 
                        "Cloudflare may still be provisioning SSL certificate")
        except requests.exceptions.ConnectionError:
            print_result("WARN", f"{hostname} connection failed", 
                        "Service may not be running or DNS not propagated")
        except requests.exceptions.Timeout:
            print_result("WARN", f"{hostname} request timed out", 
                        "Service may be slow or unreachable")
        except Exception as e:
            print_result("WARN", f"{hostname} error: {str(e)[:50]}")


def print_summary():
    """Print validation summary."""
    print_header("Validation Summary")
    
    total = len(results["passed"]) + len(results["failed"]) + len(results["warnings"]) + len(results["skipped"])
    
    print(f"[OK] Passed:  {len(results['passed'])}")
    print(f"[FAIL] Failed:  {len(results['failed'])}")
    print(f"[WARN] Warnings: {len(results['warnings'])}")
    print(f"[SKIP] Skipped: {len(results['skipped'])}")
    print()
    
    if len(results["failed"]) == 0:
        if len(results["warnings"]) == 0:
            print("[SUCCESS] All checks passed! Cloudflare setup is complete.")
        else:
            print("[OK] Critical checks passed, but there are some warnings.")
            print("   Review the warnings above and address them if needed.")
    else:
        print("[FAIL] Some critical checks failed. Please address the failures above.")
        print()
        print("Common fixes:")
        print("  1. Ensure CLOUDFLARE_TUNNEL_TOKEN is set in .env")
        print("  2. Start Docker containers: docker-compose up -d")
        print("  3. Check cloudflared logs: docker logs cloudflared")
        print("  4. Verify tunnel routes in Cloudflare dashboard:")
        print("     https://one.dash.cloudflare.com/ -> Networks -> Tunnels")
        print("  5. Wait for DNS propagation (can take up to 24 hours)")


def main():
    """Main validation function."""
    print("=" * 70)
    print("  Cloudflare Tunnel Setup Validation")
    print("=" * 70)
    print(f"\nValidating Cloudflare setup for {DOMAIN}")
    print(f"Checking {len(SERVICES)} services\n")
    
    # Run all checks
    check_env_variables()
    check_docker_containers()
    check_cloudflare_api()
    check_dns_resolution()
    check_service_accessibility()
    
    # Print summary
    print_summary()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

