# Migrating ComfyUI to local-ai-packaged

## Complexity Assessment: **Medium to High**

### Current Setup Differences

#### ComfyUI (Current)
- **Architecture**: Single container with ai-dock base image
- **Caddy**: Built into container with `universal-config` authentication
- **Services**: ComfyUI, Jupyter, Service Portal, API Wrapper (all in one container)
- **Authentication**: ai-dock token system (`WEB_TOKEN`, `WEB_PASSWORD_B64`)
- **Port**: 8188 (with Caddy inside)

#### local-ai-packaged
- **Architecture**: Multiple separate containers
- **Caddy**: Separate container, simple reverse proxy (no auth)
- **Services**: Each service is its own container
- **Authentication**: None (or service-specific)
- **Port**: Various ports, routed through Caddy

## Migration Options

### Option 1: Add ComfyUI as Separate Service (Recommended)

**Complexity**: Medium  
**Pros**: Clean separation, no Caddy conflicts  
**Cons**: Lose built-in API wrapper, need to handle auth separately

#### Steps:

1. **Add ComfyUI service to docker-compose.yml**:

```yaml
  comfyui:
    image: ghcr.io/ai-dock/comfyui:latest
    container_name: comfyui
    restart: unless-stopped
    ports:
      - 127.0.0.1:8188:8188
    expose:
      - 8188/tcp
    environment:
      - WEB_ENABLE_AUTH=false  # Disable ai-dock auth, use Caddy instead
      - COMFYUI_PORT_HOST=8188
    volumes:
      - comfyui_workspace:/workspace
      - comfyui_models:/opt/ComfyUI/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.comfyui.rule=Host(`comfyui.localhost`) || Host(`comfyui.${DOMAIN:-localhost}`)"
      - "traefik.http.routers.comfyui.entrypoints=web"
      - "traefik.http.services.comfyui.loadbalancer.server.port=8188"
```

2. **Add to Caddyfile** (if using Caddy instead of Traefik):

```caddy
# ComfyUI
{$COMFYUI_HOSTNAME:-:8188} {
    reverse_proxy comfyui:8188
}
```

3. **Add volume**:

```yaml
volumes:
  comfyui_workspace:
  comfyui_models:
```

**Issues to Address**:
- ❌ API wrapper won't be accessible (it's on port 38188 inside container)
- ❌ Need to access ComfyUI native API directly
- ❌ Lose ai-dock authentication (but can add Caddy auth if needed)

### Option 2: Keep ComfyUI Separate, Route Through Caddy

**Complexity**: Low  
**Pros**: Minimal changes, keeps existing setup  
**Cons**: Still have two Caddy instances (but they don't conflict)

#### Steps:

1. **Keep ComfyUI running in its own project**
2. **Add to local-ai-packaged Caddyfile**:

```caddy
# ComfyUI (external)
{$COMFYUI_HOSTNAME:-:8188} {
    reverse_proxy localhost:8188
}
```

3. **Add environment variable**:

```yaml
environment:
  - COMFYUI_HOSTNAME=${COMFYUI_HOSTNAME:-:8188}
```

**Pros**:
- ✅ No migration needed
- ✅ Keep all ComfyUI features (API wrapper, auth, etc.)
- ✅ Caddies don't conflict (different ports)
- ✅ Can access both directly and through Caddy

### Option 3: Extract ComfyUI to Standalone Container

**Complexity**: High  
**Pros**: Full control, matches local-ai-packaged pattern  
**Cons**: Lose API wrapper, need to rebuild setup

#### Steps:

1. **Use official ComfyUI image or build custom**:

```yaml
  comfyui:
    image: comfyanonymous/comfyui:latest
    # or build from source
    build:
      context: ./comfyui
    container_name: comfyui
    restart: unless-stopped
    ports:
      - 127.0.0.1:8188:8188
    volumes:
      - comfyui_models:/app/models
      - comfyui_output:/app/output
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

2. **Add API wrapper as separate service** (if needed):

```yaml
  comfyui-api-wrapper:
    build:
      context: ./comfyui-api-wrapper
    depends_on:
      - comfyui
    environment:
      - COMFYUI_API_BASE=http://comfyui:8188
```

**Issues**:
- ❌ Need to rebuild API wrapper
- ❌ Lose ai-dock features
- ❌ More complex setup

## Recommendation: **Option 2** (Keep Separate, Route Through Caddy)

### Why?

1. **No conflicts**: ComfyUI's Caddy runs on port 8188, local-ai-packaged Caddy runs on 80/443
2. **Keep features**: Maintain API wrapper, authentication, all ai-dock features
3. **Easy integration**: Just add one Caddy route
4. **Flexibility**: Can access ComfyUI directly or through unified Caddy
5. **No migration**: No data to move, no reconfiguration

### Implementation:

1. **Add to local-ai-packaged/Caddyfile**:

```caddy
# ComfyUI (routed from separate container)
{$COMFYUI_HOSTNAME:-:8188} {
    reverse_proxy localhost:8188
}
```

2. **Add to docker-compose.yml environment**:

```yaml
caddy:
  environment:
    - COMFYUI_HOSTNAME=${COMFYUI_HOSTNAME:-:8188}
```

3. **Access ComfyUI**:
   - Direct: `http://localhost:8188`
   - Through Caddy: `http://localhost:8188` (same, but unified routing)
   - API: `http://localhost:8188/ai-dock/api/payload` (with token)

### Alternative: Use Traefik Labels

Since local-ai-packaged uses Traefik, you could also:

1. **Add ComfyUI to docker-compose.yml** (even if in separate project):

```yaml
  comfyui:
    image: ghcr.io/ai-dock/comfyui:latest
    container_name: comfyui
    # ... config ...
    networks:
      - localai_default  # Connect to local-ai-packaged network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.comfyui.rule=Host(`comfyui.localhost`) || Host(`comfyui.${DOMAIN:-localhost}`)"
      - "traefik.http.routers.comfyui.entrypoints=web"
      - "traefik.http.services.comfyui.loadbalancer.server.port=8188"
```

2. **Connect networks**:

```yaml
networks:
  localai_default:
    external: true
```

## Summary

| Option | Complexity | Pros | Cons |
|--------|-----------|------|------|
| 1. Add as service | Medium | Clean, matches pattern | Lose API wrapper, auth |
| 2. Route through Caddy | **Low** | **No migration, keep features** | **Two Caddies (but no conflict)** |
| 3. Extract standalone | High | Full control | Lose features, rebuild |

**Best Choice**: Option 2 - Keep ComfyUI separate but route through local-ai-packaged Caddy. This gives you unified access without losing any features or requiring migration.


