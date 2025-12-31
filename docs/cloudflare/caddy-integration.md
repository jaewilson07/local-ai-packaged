# Caddy and Cloudflare Integration

This document explains how Caddy and Cloudflare Tunnel work together to provide secure, accessible services without port forwarding.

## Architecture Overview

The integration follows a two-layer architecture:

```
Internet
   │
   ▼
Cloudflare Network (SSL/TLS termination, DDoS protection)
   │
   ▼
Cloudflare Tunnel (encrypted connection, no port forwarding)
   │
   ▼
Caddy (reverse proxy, hostname routing, security headers)
   │
   ▼
Individual Services (n8n, webui, flowise, etc.)
```

## How They Work Together

### Layer 1: Cloudflare Tunnel

**Role:** Secure connection from Cloudflare's network to your local infrastructure

**Responsibilities:**
- Establishes outbound connection (no port forwarding needed)
- Encrypts traffic between Cloudflare and your server
- Handles SSL/TLS termination (HTTPS to HTTP conversion)
- Provides DDoS protection
- Hides origin IP address

**Configuration:**
- All tunnel routes point to `http://caddy:80`
- Host header is set to the specific subdomain (e.g., `n8n.datacrew.space`)
- Single tunnel handles all services

**Example Tunnel Route:**
```
Subdomain: n8n
Domain: datacrew.space
Service URL: http://caddy:80
Host Header: n8n.datacrew.space
```

### Layer 2: Caddy Reverse Proxy

**Role:** Internal routing and request handling

**Responsibilities:**
- Receives all traffic from Cloudflare Tunnel
- Routes requests to appropriate services based on hostname
- Adds security headers to responses
- Handles service-to-service communication
- Provides local reverse proxy functionality

**Configuration:**
- Listens on internal port 80 only (no external exposure)
- Uses hostname-based routing from `Caddyfile`
- Each service has its own hostname block

**Example Caddyfile Block:**
```caddy
{$N8N_HOSTNAME} {
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
    reverse_proxy n8n:5678
}
```

## Request Flow

### Step-by-Step Request Journey

1. **User Request:**
   ```
   User → https://n8n.datacrew.space
   ```

2. **DNS Resolution:**
   ```
   DNS → Points to Cloudflare's edge servers
   ```

3. **Cloudflare Edge:**
   ```
   Cloudflare → Terminates SSL/TLS
   → Applies DDoS protection
   → Routes through tunnel
   ```

4. **Cloudflare Tunnel:**
   ```
   Tunnel → Encrypted connection to your server
   → Routes to http://caddy:80
   → Sets Host header: n8n.datacrew.space
   ```

5. **Caddy Receives Request:**
   ```
   Caddy → Reads Host header
   → Matches to {$N8N_HOSTNAME} block
   → Applies security headers
   → Routes to n8n:5678
   ```

6. **Service Response:**
   ```
   n8n → Response with headers
   → Caddy adds security headers
   → Returns to Cloudflare Tunnel
   → Cloudflare encrypts (HTTPS)
   → Returns to user
   ```

## Key Design Decisions

### Why Route Everything Through Caddy?

**Single Entry Point:**
- Cloudflare Tunnel only needs one route configuration
- All services accessible through one tunnel
- Simpler Cloudflare configuration

**Centralized Management:**
- Security headers configured in one place (Caddyfile)
- Easy to add/remove services without touching Cloudflare
- Consistent security policies across all services

**Local Routing:**
- Caddy handles hostname-based routing internally
- No need to configure individual Cloudflare routes per service
- Services can communicate with each other via Docker network

### Why Not Route Directly to Services?

**Alternative Approach (Not Used):**
```
Cloudflare Tunnel → n8n:5678 (direct)
Cloudflare Tunnel → webui:8080 (direct)
Cloudflare Tunnel → flowise:3001 (direct)
...
```

**Why We Don't Use This:**
- Requires multiple Cloudflare route configurations
- No centralized security headers
- More complex to manage
- Harder to add new services

## Configuration Details

### Cloudflare Tunnel Configuration

All services use the same tunnel route pattern:

```yaml
Service: n8n
  Subdomain: n8n
  Domain: datacrew.space
  Service URL: http://caddy:80
  Host Header: n8n.datacrew.space

Service: webui
  Subdomain: webui
  Domain: datacrew.space
  Service URL: http://caddy:80  # Same as n8n
  Host Header: webui.datacrew.space  # Different header
```

**Key Points:**
- All routes point to `http://caddy:80`
- Each route has a unique Host header
- Cloudflare handles SSL/TLS termination
- No need to configure individual service ports

### Caddy Configuration

Caddy uses environment variables for hostnames:

```caddy
{$N8N_HOSTNAME} {
    # Security headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
    # Route to service
    reverse_proxy n8n:5678
}
```

**Key Points:**
- `auto_https off` - SSL handled by Cloudflare
- Hostname from environment variable
- Security headers added to all responses
- Direct routing to service container

### Environment Variables

Hostnames are configured via environment variables:

```bash
# For Cloudflare Tunnel (production)
N8N_HOSTNAME=n8n.datacrew.space
WEBUI_HOSTNAME=webui.datacrew.space
# etc.

# For local development (port-based)
N8N_HOSTNAME=:8001
WEBUI_HOSTNAME=:8002
# etc.
```

**Benefits:**
- Same Caddyfile works for local and production
- Easy to switch between modes
- No code changes needed

## SSL/TLS Handling

### Cloudflare Handles SSL

**Why:**
- Cloudflare provides free SSL certificates
- Automatic certificate management
- No need for Let's Encrypt on local server
- Works behind NAT/firewall

**Configuration:**
- Cloudflare: SSL/TLS mode set to "Full" or "Full (strict)"
- Tunnel: Routes HTTPS traffic, converts to HTTP
- Caddy: Receives HTTP, no SSL needed

### Caddy SSL Disabled

**Caddyfile Configuration:**
```caddy
{
    auto_https off  # SSL handled by Cloudflare
}
```

**Why:**
- Cloudflare terminates SSL before tunnel
- Traffic inside tunnel is already encrypted
- No need for local SSL certificates
- Simpler configuration

## Security Headers

### Caddy Adds Security Headers

All services get consistent security headers:

```caddy
header {
    X-Content-Type-Options "nosniff"
    X-Frame-Options "DENY"
    X-XSS-Protection "1; mode=block"
    Referrer-Policy "strict-origin-when-cross-origin"
}
```

**Benefits:**
- Centralized security policy
- Consistent across all services
- Easy to update
- Services don't need to implement headers

### Cloudflare Additional Security

Cloudflare provides additional security layers:

- **DDoS Protection** - Automatic mitigation
- **WAF (Web Application Firewall)** - Configurable rules
- **Rate Limiting** - Prevent abuse
- **Bot Management** - Filter malicious bots

## Adding New Services

### Step 1: Add to Caddyfile

```caddy
{$NEW_SERVICE_HOSTNAME} {
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
    reverse_proxy new-service:8080
}
```

### Step 2: Add Environment Variable

```bash
NEW_SERVICE_HOSTNAME=newservice.datacrew.space
```

### Step 3: Add Cloudflare Tunnel Route

In Cloudflare dashboard:
- Subdomain: `newservice`
- Domain: `datacrew.space`
- Service URL: `http://caddy:80`
- Host Header: `newservice.datacrew.space`

**That's it!** No need to:
- Open ports
- Configure SSL certificates
- Update firewall rules
- Modify service configuration

## Troubleshooting

### Service Not Accessible

**Check Cloudflare Tunnel:**
```bash
docker logs cloudflared
```

**Check Caddy:**
```bash
docker logs caddy
```

**Verify Host Header:**
- Ensure Cloudflare route has correct Host header
- Ensure Caddyfile has matching hostname block
- Check environment variable is set correctly

### SSL Certificate Errors

**Check Cloudflare SSL Mode:**
- Should be "Full" or "Full (strict)"
- Not "Flexible" (causes issues)

**Verify Tunnel Connection:**
- Check tunnel is connected in Cloudflare dashboard
- Verify tunnel token is correct

### Routing Issues

**Check Caddyfile Syntax:**
```bash
docker exec caddy caddy validate --config /etc/caddy/Caddyfile
```

**Verify Service is Running:**
```bash
docker ps | grep new-service
```

**Test Direct Connection:**
```bash
docker exec caddy curl http://new-service:8080
```

## Performance Considerations

### Latency

**Cloudflare Tunnel:**
- Adds minimal latency (~10-50ms typically)
- Encrypted connection is fast
- Edge network is globally distributed

**Caddy:**
- Very low overhead
- Efficient reverse proxy
- Minimal processing time

### Caching

**Cloudflare Caching:**
- Can be configured in Cloudflare dashboard
- Useful for static assets
- Reduces load on origin

**Caddy Caching:**
- Can be added to Caddyfile if needed
- Useful for frequently accessed content
- Reduces service load

## Benefits of This Architecture

### Security

✅ **No Port Forwarding** - Firewall stays closed  
✅ **Encrypted Connection** - End-to-end encryption  
✅ **DDoS Protection** - Automatic mitigation  
✅ **Origin IP Hidden** - Server IP not exposed  
✅ **Security Headers** - Consistent across services  

### Operational

✅ **Easy to Add Services** - Just update Caddyfile  
✅ **Centralized Management** - One place for routing  
✅ **Works Behind NAT** - No router configuration  
✅ **Dynamic IP Support** - No static IP needed  
✅ **Free SSL** - Automatic certificate management  

### Development

✅ **Local Development** - Same Caddyfile works locally  
✅ **Easy Testing** - Test services before deploying  
✅ **Consistent Environment** - Same setup everywhere  
✅ **No Code Changes** - Services don't need modifications  

## Comparison with Alternatives

### Direct DNS with Port Forwarding

**Alternative:**
```
Internet → Router (port 443) → Caddy → Services
```

**Our Approach:**
```
Internet → Cloudflare → Tunnel → Caddy → Services
```

**Advantages of Our Approach:**
- No port forwarding needed
- Works with dynamic IP
- Origin IP hidden
- DDoS protection included
- Free SSL certificates

### Direct Cloudflare Tunnel to Services

**Alternative:**
```
Cloudflare Tunnel → n8n:5678
Cloudflare Tunnel → webui:8080
...
```

**Our Approach:**
```
Cloudflare Tunnel → Caddy:80 → All Services
```

**Advantages of Our Approach:**
- Single tunnel route
- Centralized security headers
- Easier to manage
- Consistent configuration

## Related Documentation

- [Cloudflare Setup Guide](./setup.md) - Complete setup instructions
- [Design Choices](./design-choices.md) - Architecture decisions
- [Caddyfile](../Caddyfile) - Caddy configuration file
- [Docker Compose](../docker-compose.yml) - Service definitions

## References

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Caddy Documentation](https://caddyserver.com/docs/)
- [Caddy Reverse Proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)

