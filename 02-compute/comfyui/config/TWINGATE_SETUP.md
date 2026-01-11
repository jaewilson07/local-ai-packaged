# Twingate Connector Setup for ComfyUI

## Problem

Caddy reverse proxy requires authentication for all requests. When Twingate connector tries to access services through Caddy (on ports like 8188, 8888, etc.), it gets blocked because it doesn't provide authentication credentials.

## Solution

This setup adds an IP-based bypass in Caddy that allows requests from Twingate connector IPs to bypass authentication.

## Quick Setup

### Step 1: Identify Twingate Connector IP

Find your Twingate connector's IP address:

```bash
docker inspect twingate-connector --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

Or check the network:

```bash
docker network inspect bridge --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\n"}}{{end}}' | grep twingate
```

### Step 2: Configure Trusted IPs

Edit your `.env` file or `docker-compose.yaml` to set the trusted IP ranges:

```bash
# In .env file or docker-compose.yaml environment section
TWINGATE_TRUSTED_IPS=172.17.0.0/16,172.22.0.0/16
```

**Note:** The default includes common Docker network ranges. Adjust if your Twingate connector uses different IPs.

### Step 3: Apply the Bypass

Run the script inside the container to modify Caddy config:

```bash
# Copy the script into the container
docker cp config/caddy-twingate-bypass.py comfyui-supervisor-1:/tmp/

# Run the script
docker exec comfyui-supervisor-1 python3 /tmp/caddy-twingate-bypass.py

# Restart Caddy to apply changes
docker exec comfyui-supervisor-1 supervisorctl restart caddy
```

### Step 4: Verify

Check that the bypass was added:

```bash
docker exec comfyui-supervisor-1 grep -A 5 "@twingate_trusted" /opt/caddy/share/base_config
```

You should see:
```
@twingate_trusted {
    remote_ip 172.17.0.0/16 172.22.0.0/16
}
```

## Alternative: Direct Port Access (Bypass Caddy)

If you prefer to bypass Caddy entirely for Twingate, you can expose the internal service ports directly:

1. **ComfyUI direct access** (port 18188 inside container):
   - Currently not exposed, but ComfyUI runs on `localhost:18188` inside the container
   - Caddy proxies `:8188` → `localhost:18188`

2. **Jupyter direct access** (port 18888 inside container):
   - Currently not exposed, but Jupyter runs on `localhost:18888` inside the container  
   - Caddy proxies `:8888` → `localhost:18888`

To expose direct ports, add to `docker-compose.yaml`:

```yaml
ports:
  # ... existing ports ...
  # Direct ComfyUI access (bypasses Caddy)
  - ${COMFYUI_DIRECT_PORT:-18188}:18188
  # Direct Jupyter access (bypasses Caddy)
  - ${JUPYTER_DIRECT_PORT:-18888}:18888
```

Then configure Twingate to use these direct ports instead of the Caddy-proxied ports.

## Troubleshooting

### Script fails with "Caddy base_config not found"

Make sure the container is running:
```bash
docker ps | grep comfyui-supervisor
```

### Changes don't take effect

1. Verify the config was modified:
   ```bash
   docker exec comfyui-supervisor-1 cat /opt/caddy/share/base_config | grep -A 10 "@authorized"
   ```

2. Restart Caddy:
   ```bash
   docker exec comfyui-supervisor-1 supervisorctl restart caddy
   ```

3. Check Caddy logs:
   ```bash
   docker exec comfyui-supervisor-1 supervisorctl tail -f caddy
   ```

### Twingate still can't connect

1. Verify Twingate connector IP is in the trusted range:
   ```bash
   docker inspect twingate-connector --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
   ```

2. Check if Twingate connector is on the same Docker network:
   ```bash
   docker network ls
   docker network inspect <network_name>
   ```

3. Consider using direct port access (see Alternative section above)

## Security Considerations

- The IP-based bypass allows any request from the specified IP ranges to bypass authentication
- Only use this if you trust all containers/services on those networks
- Consider using more specific IP ranges (e.g., single IP instead of /16 subnet) if possible
- Monitor access logs to ensure only expected services are using the bypass

## Reverting Changes

If you need to revert the changes:

```bash
# Find the backup file
docker exec comfyui-supervisor-1 ls -la /opt/caddy/share/base_config.backup.*

# Restore from backup (replace TIMESTAMP with actual timestamp)
docker exec comfyui-supervisor-1 cp /opt/caddy/share/base_config.backup.TIMESTAMP /opt/caddy/share/base_config

# Restart Caddy
docker exec comfyui-supervisor-1 supervisorctl restart caddy
```
