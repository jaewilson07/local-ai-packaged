#!/usr/bin/env python3
"""
Script to add Twingate connector IP bypass to Caddy base_config.
This allows Twingate connector to access services without authentication.
"""
import os
import re
import sys
from pathlib import Path

CADDY_BASE_CONFIG = Path("/opt/caddy/share/base_config")
# Default to Docker bridge network ranges - adjust if your Twingate connector uses different IPs
TRUSTED_IPS = os.getenv("TWINGATE_TRUSTED_IPS", "172.17.0.0/16,172.22.0.0/16").split(",")

def main():
    if not CADDY_BASE_CONFIG.exists():
        print(f"Error: Caddy base_config not found at {CADDY_BASE_CONFIG}", file=sys.stderr)
        sys.exit(1)
    
    # Read current config
    with open(CADDY_BASE_CONFIG, 'r') as f:
        content = f.read()
    
    # Check if bypass is already configured in base_config
    bypass_configured = "@twingate_trusted" in content
    
    # Create backup
    backup_path = CADDY_BASE_CONFIG.with_suffix(f".backup.{int(__import__('time').time())}")
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"Created backup: {backup_path}")
    
    # Build trusted IP matcher using remote_ip directive
    ip_list = " ".join(ip.strip() for ip in TRUSTED_IPS)
    trusted_matcher = f"""    @twingate_trusted {{
        remote_ip {ip_list}
    }}
    
"""
    
    # Add @twingate_trusted matcher before @authorized if not already present
    if not bypass_configured:
        if "@authorized {" in content:
            content = content.replace("@authorized {", trusted_matcher + "    @authorized {")
        else:
            print("Warning: @authorized matcher not found in config", file=sys.stderr)
            sys.exit(1)
        
        # Create backup
        backup_path = CADDY_BASE_CONFIG.with_suffix(f".backup.{int(__import__('time').time())}")
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"Created backup: {backup_path}")
        
        # Write updated config
        with open(CADDY_BASE_CONFIG, 'w') as f:
            f.write(content)
        print("Added @twingate_trusted matcher to base_config")
    else:
        print("@twingate_trusted matcher already exists in base_config")
    
    # Modify service config files to use @twingate_trusted || @authorized
    service_config_dir = CADDY_BASE_CONFIG.parent
    service_configs = [f for f in service_config_dir.glob("service_config_*") if not f.name.endswith('.backup')]
    
    for service_config in service_configs:
        if service_config == CADDY_BASE_CONFIG:
            continue
        try:
            with open(service_config, 'r') as f:
                service_content = f.read()
            
            # Replace reverse_proxy @authorized with route that checks @twingate_trusted OR @authorized
            # In Caddy, multiple matchers mean AND, so we need route blocks for OR logic
            original_content = service_content
            
            # Pattern 1: reverse_proxy @authorized localhost:PORT
            # Replace with: route @twingate_trusted { reverse_proxy localhost:PORT } route @authorized { reverse_proxy localhost:PORT }
            def replace_reverse_proxy(match):
                full_line = match.group(0)
                # Extract the localhost:PORT part
                port_match = re.search(r'localhost:([^\s]+)', full_line)
                if port_match:
                    port = port_match.group(1)
                    return f'route @twingate_trusted {{\n        reverse_proxy localhost:{port}\n    }}\n    route @authorized {{\n        reverse_proxy localhost:{port}\n    }}'
                return full_line
            
            service_content = re.sub(
                r'reverse_proxy @authorized localhost:([^\s]+)',
                replace_reverse_proxy,
                service_content
            )
            
            if service_content != original_content:
                # Create backup
                backup_path = service_config.with_suffix(f"{service_config.suffix}.backup.{int(__import__('time').time())}")
                with open(backup_path, 'w') as f:
                    f.write(original_content)
                # Write updated content
                with open(service_config, 'w') as f:
                    f.write(service_content)
                print(f"Updated {service_config.name}")
        except Exception as e:
            print(f"Warning: Could not update {service_config.name}: {e}", file=sys.stderr)
    
    # Write updated config
    with open(CADDY_BASE_CONFIG, 'w') as f:
        f.write(content)
    
    print("Successfully added Twingate bypass to Caddy config")
    print(f"Trusted IPs: {', '.join(TRUSTED_IPS)}")
    print("\nRestart Caddy service for changes to take effect:")
    print("  docker exec comfyui-supervisor-1 supervisorctl restart caddy")

if __name__ == "__main__":
    main()

