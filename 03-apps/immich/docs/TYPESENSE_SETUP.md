# Immich Typesense Setup

This guide covers Typesense configuration for Immich text search functionality.

## Overview

Typesense is a fast, typo-tolerant search engine that powers Immich's metadata search capabilities. It enables fast searching of photo/video metadata, tags, and descriptions.

## Architecture

- **Service**: `immich-typesense`
- **Image**: `typesense/typesense:latest`
- **Ports**:
  - `8108` - API (HTTP)
  - `8107` - Peer communication
- **Data Volume**: `03-apps/immich/data/typesense`

## Configuration

### API Key

Typesense requires an API key for authentication. Generate a secure key:

```bash
openssl rand -hex 32
```

Store this key in:
- `.env` file: `IMMICH_TYPESENSE_API_KEY=your-generated-key`
- Or Infisical (recommended for production)

### Environment Variables

Key configuration variables:

- `IMMICH_TYPESENSE_API_KEY` - API key for Typesense authentication (required)
- `TYPESENSE_ENABLED=true` - Enable Typesense in Immich (set automatically)
- `TYPESENSE_HOST=immich-typesense` - Typesense container hostname
- `TYPESENSE_PORT=8108` - Typesense API port
- `TYPESENSE_PROTOCOL=http` - Protocol (http for internal communication)

These are automatically configured in the docker-compose setup.

## Starting Typesense

Typesense starts automatically with the Immich stack:

```bash
python start_services.py --profile gpu-nvidia --stack apps
```

The service will:
1. Start Typesense container
2. Wait for health check to pass
3. Start Immich services that depend on Typesense

## Health Check

Typesense includes a health check endpoint:

```bash
# Check health from host
curl http://localhost:8108/health

# Check health from within Docker network
docker exec immich-typesense curl -f http://localhost:8108/health
```

Expected response: `{"ok":true}`

## Verifying Setup

### Check Service Status

```bash
docker compose -p localai-apps ps immich-typesense
```

Service should show as "healthy" or "running".

### Check Logs

```bash
docker compose -p localai-apps logs -f immich-typesense
```

Look for:
- "Typesense server started"
- No error messages about API key or data directory

### Test Search in Immich

1. Upload some photos with metadata (tags, descriptions)
2. Use the search function in Immich web interface
3. Search should return results quickly

## Data Persistence

Typesense data is stored in:
- **Host Path**: `03-apps/immich/data/typesense`
- **Container Path**: `/data`

This ensures search indexes persist across container restarts.

## Backup

### Backup Typesense Data

```bash
# Stop Typesense (optional, but recommended)
docker compose -p localai-apps stop immich-typesense

# Backup data directory
tar -czf typesense_backup_$(date +%Y%m%d).tar.gz 03-apps/immich/data/typesense

# Restart Typesense
docker compose -p localai-apps start immich-typesense
```

### Restore Typesense Data

```bash
# Stop Typesense
docker compose -p localai-apps stop immich-typesense

# Restore data
tar -xzf typesense_backup_YYYYMMDD.tar.gz -C 03-apps/immich/data/

# Restart Typesense
docker compose -p localai-apps start immich-typesense
```

## Troubleshooting

### Typesense Not Starting

1. **Check logs:**
   ```bash
   docker compose -p localai-apps logs immich-typesense
   ```

2. **Verify API key is set:**
   ```bash
   docker exec immich-typesense env | grep TYPESENSE_API_KEY
   ```

3. **Check data directory permissions:**
   ```bash
   ls -la 03-apps/immich/data/typesense
   ```

### Search Not Working

1. **Verify Typesense is running:**
   ```bash
   docker compose -p localai-apps ps immich-typesense
   ```

2. **Check Immich can connect:**
   ```bash
   docker compose -p localai-apps logs immich-server | grep -i typesense
   ```

3. **Verify API key matches:**
   - Typesense API key must match in both services
   - Check `.env` or Infisical for correct value

### Performance Issues

1. **Index Size:**
   - Large libraries may require more memory
   - Monitor Typesense memory usage

2. **Concurrent Searches:**
   - High search load may impact performance
   - Consider scaling if needed

3. **Data Directory:**
   - Ensure data directory is on fast storage (SSD recommended)

## Advanced Configuration

### Memory Limits

If needed, adjust Typesense memory limits in docker-compose:

```yaml
immich-typesense:
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 1G
```

### Custom Typesense Settings

Typesense can be configured via environment variables or configuration files. See [Typesense documentation](https://typesense.org/docs/) for advanced options.

## Disabling Typesense

If you need to disable Typesense (not recommended):

1. Set `TYPESENSE_ENABLED=false` in Immich environment
2. Stop Typesense service: `docker compose -p localai-apps stop immich-typesense`
3. Note: Search functionality will be limited or unavailable

## References

- [Typesense Documentation](https://typesense.org/docs/)
- [Immich Typesense Integration](https://docs.immich.app/administration/typesense)
