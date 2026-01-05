#!/bin/bash
# Script to add Twingate connector IP bypass to Caddy base_config
# This allows Twingate connector to access services without authentication

CADDY_BASE_CONFIG="/opt/caddy/share/base_config"
TRUSTED_IPS="${TWINGATE_TRUSTED_IPS:-172.17.0.0/16}"

if [ ! -f "$CADDY_BASE_CONFIG" ]; then
    echo "Error: Caddy base_config not found at $CADDY_BASE_CONFIG"
    exit 1
fi

# Check if bypass is already added
if grep -q "@twingate_trusted" "$CADDY_BASE_CONFIG"; then
    echo "Twingate bypass already configured in Caddy base_config"
    exit 0
fi

# Create backup
cp "$CADDY_BASE_CONFIG" "${CADDY_BASE_CONFIG}.backup.$(date +%s)"

# Build the IP matcher expression
IFS=',' read -ra IPS <<< "$TRUSTED_IPS"
IP_MATCHER=""
for ip in "${IPS[@]}"; do
    ip=$(echo "$ip" | xargs) # trim whitespace
    if [ -n "$IP_MATCHER" ]; then
        IP_MATCHER="${IP_MATCHER} || "
    fi
    IP_MATCHER="${IP_MATCHER}{http.request.remote.host} =~ \"^${ip//\//.*}\""
done

# Add the trusted IP matcher before @authorized
sed -i "/@authorized {/i\\
    @twingate_trusted {\\
        remote_ip $TRUSTED_IPS\\
    }\\
" "$CADDY_BASE_CONFIG"

# Modify @authorized to include trusted IPs
# Find the @authorized block and add the trusted IP check
sed -i "/@authorized {/,/}/ {
    /expression \\\\/a\\
            {http.request.remote.host} =~ \"^172\\.17\\.\" || \\
            {http.request.remote.host} =~ \"^172\\.22\\.\" || \\
" "$CADDY_BASE_CONFIG"

# Actually, let's use a simpler approach - modify the expression directly
# Replace the @authorized expression to include trusted IPs
sed -i 's/@authorized {/@twingate_trusted {\n        remote_ip '"$TRUSTED_IPS"'\n    }\n\n    @authorized {/' "$CADDY_BASE_CONFIG"

# Now modify the @authorized expression to include the trusted IP check
# This is tricky with sed, so let's use a Python script instead
python3 << 'PYTHON_SCRIPT'
import re
import sys

config_path = "/opt/caddy/share/base_config"
trusted_ips = "${TRUSTED_IPS}".split(",")

with open(config_path, 'r') as f:
    content = f.read()

# Add @twingate_trusted matcher before @authorized
if "@twingate_trusted" not in content:
    # Build remote_ip directive
    ip_list = " ".join(trusted_ips)
    trusted_matcher = f"""    @twingate_trusted {{
        remote_ip {ip_list}
    }}
    
"""
    content = content.replace("@authorized {", trusted_matcher + "    @authorized {")

# Modify @authorized expression to include trusted IP check
# Find the @authorized block
pattern = r'(@authorized \{[^}]*expression \\\s*\n(?:\s+[^\n]*\n)*)'
match = re.search(pattern, content, re.MULTILINE)

if match:
    authorized_block = match.group(1)
    # Check if trusted IP check is already there
    if "twingate_trusted" not in authorized_block:
        # Add trusted IP check at the beginning of the expression
        # Find the expression line and add our check
        new_block = re.sub(
            r'(expression \\\s*\n)',
            r'\1            @twingate_trusted || \\\n',
            authorized_block
        )
        content = content.replace(authorized_block, new_block)

with open(config_path, 'w') as f:
    f.write(content)

print("Successfully added Twingate bypass to Caddy config")
PYTHON_SCRIPT

echo "Caddy base_config updated with Twingate bypass"
echo "Restart Caddy service for changes to take effect:"
echo "  docker exec comfyui-supervisor-1 supervisorctl restart caddy"


