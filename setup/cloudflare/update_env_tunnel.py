#!/usr/bin/env python3
"""
update_env_tunnel.py

Update .env file with Cloudflare Tunnel token and hostname configuration.
"""

import os
import re
import sys

# Tunnel token from earlier setup
TUNNEL_TOKEN = "eyJhIjoiNzU1MjM3MTM4NjQ1MWIyMjJmNTI3ZmE3OTQ1NjJhMzciLCJzIjoiTFZhcFltSW5Sbk9adzQ1RUdRR0hnb1dFQTZtM1h3RWUzd0dETUp6eDB1Zz0iLCJ0IjoiMzg4NWQxM2QtMmQ0OC00N2VlLTgxMWMtODc4OTIwYmU0ZDY5In0="

DOMAIN = "datacrew.space"
SERVICES = {
    "n8n": "n8n",
    "webui": "webui",
    "flowise": "flowise",
    "langfuse": "langfuse",
    "supabase": "supabase",
    "neo4j": "neo4j",
    "comfyui": "comfyui",
    "infisical": "infisical",
}


def update_env_file():
    """Update .env file with tunnel token and hostnames."""
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print(f"[WARNING] .env file not found. Creating new one...")
        content = ""
    else:
        with open(env_file, 'r') as f:
            content = f.read()
    
    # Update or add CLOUDFLARE_TUNNEL_TOKEN
    if "CLOUDFLARE_TUNNEL_TOKEN" in content:
        content = re.sub(
            r'CLOUDFLARE_TUNNEL_TOKEN=.*',
            f'CLOUDFLARE_TUNNEL_TOKEN={TUNNEL_TOKEN}',
            content
        )
    else:
        if not content.endswith('\n'):
            content += '\n'
        content += f"\n# Cloudflare Tunnel Configuration\n"
        content += f"CLOUDFLARE_TUNNEL_TOKEN={TUNNEL_TOKEN}\n"
    
    # Update hostnames
    for service_name, subdomain in SERVICES.items():
        hostname = f"{subdomain}.{DOMAIN}"
        env_var = f"{service_name.upper()}_HOSTNAME"
        
        if env_var in content:
            content = re.sub(
                rf'{env_var}=.*',
                f'{env_var}={hostname}',
                content
            )
        else:
            if not content.endswith('\n'):
                content += '\n'
            content += f"{env_var}={hostname}\n"
    
    # Write back
    with open(env_file, 'w') as f:
        f.write(content)
    
    print(f"[OK] Updated {env_file}")
    print(f"   - Added CLOUDFLARE_TUNNEL_TOKEN")
    print(f"   - Updated {len(SERVICES)} hostname variables to use {DOMAIN} subdomains")


if __name__ == "__main__":
    update_env_file()

