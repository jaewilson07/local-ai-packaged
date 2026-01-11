# Troubleshooting ComfyUI LoRA Endpoints

## Redirect Loop Issue

If you're seeing "redirected too many times" when accessing the LoRA endpoints, check the following:

### 1. Use the Correct Hostname

**❌ Wrong:**
```
https://datacrew.space/api/v1/comfyui/loras
```

**✅ Correct:**
```
https://api.datacrew.space/api/v1/comfyui/loras
```

The Lambda API is configured for `api.datacrew.space`, not the root domain.

### 2. Verify Cloudflare Access Configuration

The endpoint requires Cloudflare Access authentication. Verify:

1. **Check Cloudflare Access Application:**
   - Go to [Cloudflare One Dashboard](https://one.dash.cloudflare.com/)
   - Navigate to **Access** → **Applications**
   - Look for "Lambda API" or `api.datacrew.space`
   - Verify it's enabled and configured correctly

2. **Verify Tunnel Route:**
   - Go to **Networks** → **Tunnels**
   - Check that `api.datacrew.space` route exists
   - Verify it points to your tunnel

3. **Check Access Policies:**
   - Make sure you have an access policy that allows your email/group
   - Verify the policy includes the correct path: `/api/v1/comfyui/*`

### 3. Test Authentication

If Cloudflare Access is working correctly, you should:
1. Be automatically redirected to Google OAuth login (if not already authenticated)
2. After login, be redirected back with the JWT token in the `Cf-Access-Jwt-Assertion` header
3. The endpoint should then work

### 4. Common Issues

**Issue: Redirect Loop**
- **Cause**: Cloudflare Access application might be misconfigured
- **Solution**: Check Access application settings, verify domain matches exactly

**Issue: 403 Forbidden**
- **Cause**: Missing or invalid JWT token
- **Solution**: Make sure you're accessing through Cloudflare Access (not direct IP)

**Issue: 404 Not Found**
- **Cause**: Wrong hostname or route not configured
- **Solution**: Use `api.datacrew.space` not `datacrew.space`

### 5. Testing with curl

Once authenticated through Cloudflare Access in your browser:

1. Open browser DevTools (F12)
2. Go to Network tab
3. Access `https://api.datacrew.space/api/v1/comfyui/loras`
4. Find the request in Network tab
5. Copy the `Cf-Access-Jwt-Assertion` header value
6. Use it in curl:

```bash
curl -X GET "https://api.datacrew.space/api/v1/comfyui/loras" \
  -H "Cf-Access-Jwt-Assertion: your-jwt-token-here"
```

### 6. Verify Caddy Configuration

Check that Caddy is routing correctly:

```bash
# Check Caddy logs
docker logs caddy

# Verify route exists
docker exec caddy cat /etc/caddy/Caddyfile | grep -A 10 "api.datacrew.space"
```

The route should show:
```
@lambda_api host api.datacrew.space
handle @lambda_api {
    reverse_proxy lambda-server:8000
}
```
