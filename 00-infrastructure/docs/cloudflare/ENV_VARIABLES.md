# Environment Variables for Cloudflare Access

## Required for Cloudflare Access

### COMFYUI_ACCESS_TOKEN
**Purpose:** Service token for programmatic API access to ComfyUI via Cloudflare Access

**When to set:** After creating service token in Cloudflare Zero Trust dashboard

**How to get:**
1. Go to Cloudflare Zero Trust → Access → Service Tokens
2. Create token named `comfyui-api`
3. Copy the token (shown only once!)
4. Add to `.env` file or export as environment variable

**Example:**
```bash
# In .env file
COMFYUI_ACCESS_TOKEN=your-service-token-here

# Or export for current session
export COMFYUI_ACCESS_TOKEN=your-service-token-here
```

**Usage:**
- Required for API calls to `https://comfyui.datacrew.space`
- Not needed for local access (`http://localhost:8188`)
- Not needed for Docker network access (`http://comfyui:8188`)

**Security:**
- Store securely (never commit to git)
- Use Infisical for production secrets
- Rotate if compromised

## Related Variables

### COMFYUI_HOSTNAME
**Purpose:** Hostname for ComfyUI service (used by Caddy)

**Example:**
```bash
# For Cloudflare Tunnel (production)
COMFYUI_HOSTNAME=comfyui.datacrew.space

# For local development (port-based)
COMFYUI_HOSTNAME=:8009
```

### CLOUDFLARE_TUNNEL_TOKEN
**Purpose:** Token for Cloudflare Tunnel connection

**Note:** Required for Cloudflare Tunnel, but separate from Access token

## Environment Variable Priority

When using the API helper (`utils/comfyui_api_client.py`):

1. **Explicit parameter:** `get_comfyui_client("https://comfyui.datacrew.space")`
2. **Environment variable:** `COMFYUI_URL` (defaults to `http://localhost:8188`)
3. **Default:** `http://localhost:8188`

For authentication:
- Local URLs (`localhost`, `127.0.0.1`, `comfyui:8188`): No token needed
- Remote URLs (`datacrew.space`, `https://`): Requires `COMFYUI_ACCESS_TOKEN`

## Adding to .env File

Add this to your `.env` file after creating the service token:

```bash
############
# Cloudflare Access for ComfyUI
############
# Service token for API access (get from Cloudflare Zero Trust dashboard)
COMFYUI_ACCESS_TOKEN=your-service-token-here

# Optional: Override default ComfyUI URL
# COMFYUI_URL=http://localhost:8188
```

## Verification

After setting the token, verify it works:

```bash
# Test with verification script
python3 utils/verify_cloudflare_access.py

# Test with access test script
export COMFYUI_ACCESS_TOKEN=your-token
python3 utils/test_comfyui_access.py
```


