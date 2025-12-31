# Cloudflare Design Choices and Configuration Challenges

This document tracks design decisions, configuration challenges, and solutions related to Cloudflare setup for this project.

## Architecture Decisions

### Why Cloudflare Tunnel vs Direct DNS

**Decision:** Use Cloudflare Tunnel instead of direct DNS with port forwarding.

**Rationale:**
- No port forwarding required - works behind NAT/firewalls
- Works with dynamic IP addresses
- Origin IP completely hidden from public
- Free SSL certificates automatically provisioned
- DDoS protection included
- No firewall/router configuration needed
- Perfect for home servers or any environment where ports can't be opened

**Trade-offs:**
- Requires Cloudflare account (free tier works)
- All traffic routes through Cloudflare (acceptable for most use cases)
- Slight latency increase (minimal in practice)

### Service Routing Strategy

**Decision:** Route all services through Caddy, then through Cloudflare Tunnel.

**Architecture:**
```
Internet → Cloudflare Tunnel → Caddy (reverse proxy) → Services
```

**Rationale:**
- Caddy provides local reverse proxy and SSL termination
- Single entry point simplifies routing
- Caddy handles hostname-based routing internally
- Cloudflare Tunnel only needs to route to Caddy (port 80)
- Easier to add/remove services without touching Cloudflare config

**Alternative Considered:**
- Direct routing from Cloudflare Tunnel to each service
- Rejected because it would require more Cloudflare configuration changes

**For detailed information:** See [Caddy and Cloudflare Integration](./caddy-integration.md)

## Configuration Challenges

### Challenge 1: Email Records Must Be DNS Only

**Issue:** MX, SPF, DKIM, and DMARC records must be set to "DNS only" (grey cloud) in Cloudflare, not proxied.

**Solution:**
- All email-related DNS records are explicitly set to DNS only
- Created automated script (`setup_dns.py`) to ensure correct proxy settings
- Documented in setup guide with clear warnings

**Why:** Email servers need direct DNS resolution, not proxied traffic.

### Challenge 2: DNS Record Migration from Squarespace

**Issue:** When switching nameservers to Cloudflare, existing DNS records must be copied to prevent service interruption.

**Solution:**
- Created comprehensive guide for copying DNS records before switching
- Automated script (`setup_dns.py`) to bulk-add DNS records
- Verification steps using MXToolbox before switching nameservers

**Lessons Learned:**
- Always copy ALL DNS records before switching nameservers
- Email records are critical - missing them breaks email delivery
- Custom service records (Postman, Domo, Circle) also need to be migrated

### Challenge 3: DMARC Setup Sequence

**Issue:** DMARC must be set up after SPF and DKIM, or it can block legitimate emails.

**Solution:**
- Documented phased approach: SPF → DKIM → DMARC
- Start with `p=none` (monitoring mode) for safety
- Gradual enforcement: `p=none` → `p=quarantine` → `p=reject`
- Clear warnings in documentation about setup order

**Why:** DMARC relies on SPF and DKIM to authenticate emails. If they're not set up first, DMARC will fail authentication.

### Challenge 4: Tunnel Token Management

**Issue:** Tunnel tokens are long and need to be securely stored in `.env` file.

**Solution:**
- Token stored in `.env` file (not committed to git)
- Automated setup script generates and updates token
- Clear instructions for manual token retrieval if needed

**Future Consideration:** Consider using Infisical for tunnel token storage.

### Challenge 5: Hostname Configuration

**Issue:** Services need hostnames configured in both Caddy and Cloudflare Tunnel.

**Solution:**
- Environment variables for each service hostname (e.g., `N8N_HOSTNAME=n8n.datacrew.space`)
- Caddy reads hostnames from environment variables
- Cloudflare Tunnel routes configured with matching hostnames
- Automated script (`setup/cloudflare/configure_hostnames.py`) to sync configurations

**Why:** Ensures consistency between Caddy routing and Cloudflare Tunnel routing.

## Solutions and Workarounds

### Automated Setup Scripts

Created several Python scripts to automate common tasks:

1. **`setup/cloudflare/setup_tunnel.py`** - Creates Cloudflare Tunnel and generates token
2. **`setup/cloudflare/setup_dns.py`** - Adds DNS records to Cloudflare (with correct proxy settings)
3. **`setup/cloudflare/setup_tunnel_routes.py`** - Configures public hostnames in tunnel
4. **`setup/cloudflare/configure_hostnames.py`** - Syncs hostname configuration
5. **`setup/cloudflare/update_env_tunnel.py`** - Updates `.env` with tunnel token
6. **`setup/cloudflare/validate_setup.py`** - Validates Cloudflare configuration

**Benefits:**
- Reduces manual errors
- Ensures consistent configuration
- Faster setup process
- Repeatable for multiple environments

### Email Health Monitoring

**Solution:** Use MXToolbox for ongoing email health monitoring.

**Process:**
1. Regular checks at https://mxtoolbox.com/emailhealth/datacrew.space/
2. Address warnings and errors promptly
3. Monitor DMARC reports (when enabled)
4. Document fixes in this file

### DNS Propagation Handling

**Challenge:** DNS changes can take up to 24 hours to propagate.

**Solution:**
- Document expected propagation times
- Provide verification commands and tools
- Set expectations in setup guide
- Use DNS checker tools to verify propagation

## Future Considerations

### Cloud Service Integration

**Planned:** Add cloud services (e.g., RunPod for ComfyUI) to the stack.

**Approach:**
- Option 1: Proxy through Caddy (add route in Caddyfile)
- Option 2: Direct tunnel route to cloud service
- Decision will depend on service requirements

### Access Control

**Consideration:** Add Cloudflare Access policies for sensitive services.

**Benefits:**
- Additional security layer
- User authentication before service access
- Audit logging

### Rate Limiting

**Consideration:** Configure WAF rate limiting in Cloudflare dashboard.

**Use Case:** Protect services from abuse and DDoS attacks.

### Monitoring and Observability

**Future Enhancement:** Set up Cloudflare Analytics and monitoring.

**Potential:**
- Traffic analytics
- Error rate monitoring
- Performance metrics

## Configuration Files

### Key Files

- `Caddyfile` - Caddy reverse proxy configuration
- `.env` - Environment variables (hostnames, tunnel token)
- `docker-compose.yml` - Service definitions
- Cloudflare Dashboard - Tunnel and DNS configuration

### Environment Variables

Critical Cloudflare-related variables:
- `CLOUDFLARE_TUNNEL_TOKEN` - Tunnel authentication token
- `N8N_HOSTNAME`, `WEBUI_HOSTNAME`, etc. - Service hostnames

## Troubleshooting Notes

### Common Issues

1. **Tunnel not connecting**
   - Check token is correct in `.env`
   - Verify cloudflared container can reach Caddy
   - Check Cloudflare dashboard for tunnel status

2. **DNS not resolving**
   - Verify nameservers are correctly set
   - Check DNS propagation status
   - Ensure DNS records exist in Cloudflare

3. **Email not working**
   - Verify MX records are DNS only (not proxied)
   - Check SPF, DKIM, DMARC records exist
   - Wait for DNS propagation

4. **SSL certificate errors**
   - Ensure DNS is fully propagated
   - Check SSL/TLS encryption mode in Cloudflare dashboard
   - Verify domain is properly added to Cloudflare

## References

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
- [MXToolbox Email Health Check](https://mxtoolbox.com/emailhealth/datacrew.space/)
- [Setup Guide](./setup.md)
- [Email Health Troubleshooting](./email-health.md)

