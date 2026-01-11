# Cloudflared Certificate Backup with Infisical

## Overview

Yes! Infisical can back up your Cloudflared origin certificate. The certificate is stored in `~/.cloudflared/cert.pem` and can be backed up to Infisical for safekeeping and easy restoration.

## What is the Cloudflared Certificate?

The origin certificate (`cert.pem`) is created when you run `cloudflared tunnel login`. It's used to authenticate your local cloudflared instance with Cloudflare's network.

**Location**: `~/.cloudflared/cert.pem`

**Purpose**: Authenticates your cloudflared client with Cloudflare

**Why Backup?**
- If you lose this certificate, you'll need to re-authenticate
- Useful when setting up on a new machine
- Ensures you can restore your tunnel configuration

## Backup Methods

### Method 1: Automated Script (Recommended)

```bash
# Backup certificate to Infisical
./utils/scripts/backup-cloudflared-cert.sh
```

This script will:
1. Check if the certificate exists
2. Encode it as base64
3. Store it in Infisical as `CLOUDFLARE_ORIGIN_CERT`

### Method 2: Manual Backup via Infisical CLI

```bash
# Encode and store certificate
cat ~/.cloudflared/cert.pem | base64 -w 0 | infisical secrets set CLOUDFLARE_ORIGIN_CERT
```

### Method 3: Manual Backup via Infisical UI

1. Open Infisical UI: `http://localhost:8010`
2. Navigate to your project and environment
3. Click "Add Secret"
4. Key: `CLOUDFLARE_ORIGIN_CERT`
5. Value: Copy the entire content of `~/.cloudflared/cert.pem` (or base64 encoded)
6. Save

## Restore Certificate

### Automated Restore

```bash
# Restore certificate from Infisical
./utils/scripts/restore-cloudflared-cert.sh
```

### Manual Restore

```bash
# Get certificate from Infisical and restore
infisical secrets get CLOUDFLARE_ORIGIN_CERT --plain | base64 -d > ~/.cloudflared/cert.pem
chmod 600 ~/.cloudflared/cert.pem
```

## Important Notes

### Certificate vs Token

**Two different things:**
- **Origin Certificate** (`cert.pem`) - Authenticates cloudflared CLI with Cloudflare
- **Tunnel Token** (`CLOUDFLARE_TUNNEL_TOKEN`) - Used by Docker container to run tunnel

**Both should be backed up:**
- Certificate → Infisical (as `CLOUDFLARE_ORIGIN_CERT`)
- Tunnel Token → Infisical (as `CLOUDFLARE_TUNNEL_TOKEN`)

### When You Need the Certificate

The certificate is needed when:
- Running `cloudflared tunnel` commands from CLI
- Setting up tunnels manually
- Managing tunnel configuration via CLI

The Docker container uses the **tunnel token** instead, so it doesn't need the certificate file.

### Security

- Certificate is stored base64-encoded in Infisical
- Infisical encrypts all secrets at rest
- Certificate file should have permissions `600` (owner read/write only)
- Never commit certificate to version control

## Integration with Docker

The Docker container doesn't use the certificate file - it uses the tunnel token. However, if you want to use the certificate in Docker:

```yaml
cloudflared:
  volumes:
    - ~/.cloudflared/cert.pem:/etc/cloudflared/cert.pem:ro
  environment:
    - TUNNEL_ORIGIN_CERT=/etc/cloudflared/cert.pem
```

But for most use cases, the tunnel token is sufficient and simpler.

## Backup Checklist

- [ ] Certificate backed up to Infisical (`CLOUDFLARE_ORIGIN_CERT`)
- [ ] Tunnel token backed up to Infisical (`CLOUDFLARE_TUNNEL_TOKEN`)
- [ ] API token backed up to Infisical (`CLOUDFLARE_API_TOKEN`)
- [ ] Certificate file permissions set correctly (`chmod 600 ~/.cloudflared/cert.pem`)

## Related Documentation

- [Infisical Usage Guide](../../docs/infisical/usage.md)
- [Cloudflare Setup Guide](./setup.md)
- [Infisical Setup Guide](../../docs/infisical/setup.md)
