# ComfyUI API Access Audit

**Date:** 2026-01-02  
**Purpose:** Document current API access patterns before implementing Cloudflare Access

## Summary

All current ComfyUI API access uses **local access patterns** (localhost/127.0.0.1). No scripts currently use remote domain-based URLs, which means **no immediate breaking changes** when Cloudflare Access is enabled.

## Local Access Scripts (UNAFFECTED)

These scripts use `localhost:8188` or `127.0.0.1:8188` and will continue working unchanged:

### Python Scripts
1. **`sample_api_call.py`**
   - URL: `http://localhost:8188`
   - Status: ✅ No changes needed
   - Location: `02-compute/data/comfyui/sample_api_call.py`

2. **`sample_api_call_authenticated.py`**
   - URL: `http://localhost:8188`
   - Status: ✅ No changes needed
   - Location: `02-compute/data/comfyui/sample_api_call_authenticated.py`

3. **`validate_api.py`**
   - URL: `http://localhost:8188`
   - Status: ✅ No changes needed
   - Location: `02-compute/data/comfyui/validate_api.py`

4. **`sample_api_call_direct.py`**
   - Uses direct container access (docker exec)
   - Status: ✅ No changes needed
   - Location: `02-compute/data/comfyui/sample_api_call_direct.py`

### Example Scripts (ComfyUI Core)
- `ComfyUI/script_examples/basic_api_example.py` - Uses `127.0.0.1:8188`
- `ComfyUI/script_examples/websockets_api_example.py` - Uses `127.0.0.1:8188`
- `ComfyUI/script_examples/websockets_api_example_ws_images.py` - Uses `127.0.0.1:8188`

## Remote Access Scripts (REQUIRES TOKEN)

**Current Status:** ⚠️ **NONE FOUND**

No scripts currently use `https://comfyui.datacrew.space` or other domain-based URLs.

**Future Remote Access:**
- Any new scripts using `https://comfyui.datacrew.space` will require `CF-Access-Token` header
- Service token will be stored in `COMFYUI_ACCESS_TOKEN` environment variable

## Service-to-Service Communication

### Docker Network Access
- Services using `http://comfyui:8188` (Docker container name)
- Status: ✅ No changes needed
- Bypasses Cloudflare Tunnel entirely

### External Service Calls
- No external services currently calling ComfyUI via domain
- Future external services will need service token

## Recommendations

1. **For New Remote Scripts:**
   - Use the `utils/comfyui_api_client.py` helper function
   - Store service token in `.env` as `COMFYUI_ACCESS_TOKEN`
   - Or use Infisical for production secrets

2. **For Local Development:**
   - Continue using `http://localhost:8188`
   - No authentication needed
   - Works unchanged

3. **For Service-to-Service:**
   - Use Docker network names (`http://comfyui:8188`)
   - No authentication needed
   - More efficient than going through Cloudflare

## Impact Assessment

### Before Cloudflare Access
- ✅ All current scripts work
- ✅ No authentication required for local access

### After Cloudflare Access
- ✅ All local scripts continue working (unchanged)
- ✅ Browser access requires Google OAuth
- ⚠️ Future remote scripts need service token
- ✅ Service-to-service (Docker network) unchanged

## Next Steps

1. Implement Cloudflare Access (browser authentication)
2. Create service token for future API access
3. Create `utils/comfyui_api_client.py` helper function
4. Document service token usage for future remote scripts


