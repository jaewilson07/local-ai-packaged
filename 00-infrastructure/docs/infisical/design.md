# Infisical Design Documentation

Architecture, design decisions, and integration patterns for Infisical in local-ai-packaged.

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Why Infisical?](#why-infisical)
3. [Architecture Overview](#architecture-overview)
4. [Integration with local-ai-packaged](#integration-with-local-ai-packaged)
5. [Service Dependencies](#service-dependencies)
6. [Network Architecture](#network-architecture)
7. [Security Model](#security-model)
8. [Benefits and Trade-offs](#benefits-and-trade-offs)

---

## Problem Statement

### Secret Management Challenges

Managing secrets in a self-hosted environment presents several challenges:

#### 1. Security Risks

- `.env` files can be accidentally committed to version control
- Secrets stored in plain text are vulnerable to exposure
- No centralized way to rotate or audit secrets
- Difficult to track who accessed which secrets

#### 2. Operational Complexity

- Secrets scattered across multiple `.env` files
- Difficult to share secrets across team members securely
- No version history for secret changes
- Manual synchronization between environments
- Hard to know which secrets are actually being used

#### 3. Scalability Issues

- Adding new services requires updating multiple files
- No easy way to manage secrets for multiple environments
- Difficult to maintain consistency across deployments
- No automated secret rotation

---

## Why Infisical?

Infisical is an open-source secret management platform that addresses these challenges.

### Key Features

✅ **Centralized Secret Storage** - All secrets in one secure location  
✅ **Web UI** - Easy-to-use interface for managing secrets  
✅ **CLI Integration** - Automated secret fetching for scripts  
✅ **Environment Management** - Separate secrets for dev/prod  
✅ **Audit Logging** - Track who accessed what secrets and when  
✅ **Version History** - See changes to secrets over time  
✅ **Team Collaboration** - Share secrets securely with team members  
✅ **Self-Hosted** - Complete control over your secrets (no cloud dependency)

### Why Not Alternatives?

**HashiCorp Vault:**
- More complex setup and operation
- Overkill for single-user or small team setups
- Requires more infrastructure resources

**AWS Secrets Manager / Azure Key Vault:**
- Cloud-dependent (we want self-hosted)
- Vendor lock-in
- Additional costs

**Doppler / 1Password:**
- Cloud-based (we want self-hosted)
- Subscription costs
- Less control over data

**Plain `.env` files:**
- No encryption at rest
- No audit logging
- Easy to accidentally commit
- No version history

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    local-ai-packaged                        │
│                                                             │
│  ┌──────────────┐                                          │
│  │ start_       │  Exports secrets                         │
│  │ services.py  │────────────────┐                         │
│  └──────────────┘                │                         │
│                                   ▼                         │
│                          ┌─────────────────┐               │
│                          │ .env.infisical  │               │
│                          └─────────────────┘               │
│                                   │                         │
│                                   │ Read by                │
│                                   ▼                         │
│  ┌──────────────────────────────────────────────────────┐ │
│  │            Docker Compose Services                    │ │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │ │
│  │  │ n8n    │ │ Ollama │ │ Flowise│ │ ...    │        │ │
│  │  └────────┘ └────────┘ └────────┘ └────────┘        │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Fetches via CLI
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Infisical Stack                          │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │ Infisical UI │◄────────┤ Infisical    │                │
│  │ (Web)        │         │ Backend      │                │
│  │ Port 8020    │         │ (API)        │                │
│  └──────────────┘         └──────┬───────┘                │
│                                   │                         │
│                          Stores   │                         │
│                                   ▼                         │
│                          ┌─────────────────┐               │
│                          │ PostgreSQL      │               │
│                          │ (infisical-db)  │               │
│                          └─────────────────┘               │
│                                   │                         │
│                          Cache    │                         │
│                                   ▼                         │
│                          ┌─────────────────┐               │
│                          │ Redis           │               │
│                          │ (infisical-     │               │
│                          │  redis)         │               │
│                          └─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### Infisical Backend
- **Image**: `infisical/infisical:latest`
- **Container**: `infisical-backend`
- **Port**: 8080 (internal), exposed via Caddy
- **Purpose**: API server for secret management
- **Key Features**:
  - REST API for secret operations
  - OAuth/SSO authentication
  - Audit logging
  - Version history

#### Infisical Database
- **Image**: `postgres:14-alpine`
- **Container**: `infisical-db`
- **Port**: 5432 (internal only)
- **Purpose**: Store encrypted secrets and metadata
- **Key Features**:
  - Dedicated PostgreSQL instance (separate from Supabase)
  - Encrypted at rest
  - Regular backups

#### Infisical Redis
- **Image**: `redis:7-alpine`
- **Container**: `infisical-redis`
- **Port**: 6379 (internal only)
- **Purpose**: Cache and session storage
- **Key Features**:
  - Dedicated Redis instance (separate from main Redis)
  - Session management
  - Performance optimization

---

## Integration with local-ai-packaged

### Integration Flow

1. **Secret Storage:**
   - Secrets are stored in Infisical (via web UI or CLI)
   - Organized by project and environment (development/production)

2. **Secret Export:**
   - `start_services.py` calls `export_infisical_secrets()`
   - Infisical CLI exports secrets to `.env.infisical` file
   - Format: Standard `.env` format (KEY=VALUE)

3. **Service Startup:**
   - Docker Compose reads `.env.infisical` as an env file
   - Services receive secrets as environment variables
   - Works seamlessly with existing Docker Compose setup

4. **Fallback:**
   - If Infisical is unavailable, falls back to `.env` file
   - Ensures services can start even if Infisical is down

### Code Integration

The integration is handled in `start_services.py`:

```python
def export_infisical_secrets(env_file_path=".env.infisical"):
    """Export secrets from Infisical to a temporary .env file."""
    # Checks for Infisical CLI
    # Exports secrets using: infisical export --format=dotenv
    # Returns path to .env.infisical file

def start_local_ai(profile=None, environment=None, use_infisical=False):
    """Start the local AI services."""
    if use_infisical:
        infisical_env_file = export_infisical_secrets()
        if infisical_env_file:
            cmd.extend(["--env-file", infisical_env_file])
            # Docker Compose uses .env.infisical for secrets
```

### Secret Separation

**Secrets stored in Infisical:**
- Database passwords (PostgreSQL, MongoDB, ClickHouse)
- API keys (N8N, JWT secrets)
- Encryption keys (N8N, Langfuse)
- Service credentials (Neo4j, MinIO)
- Docker Hub credentials
- Cloudflare tokens

**Configuration in `.env` (not synced):**
- Hostnames (N8N_HOSTNAME, WEBUI_HOSTNAME, etc.)
- Port numbers
- Non-sensitive configuration
- Infisical configuration itself

---

## Service Dependencies

### Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Stack                      │
│                                                             │
│  ┌──────────────┐                                          │
│  │ ai-network   │  ← Created by infrastructure stack       │
│  └──────────────┘                                          │
│         │                                                   │
│         │ Used by all services                             │
│         ▼                                                   │
│  ┌──────────────┐         ┌──────────────┐                │
│  │ Caddy        │         │ Redis        │                │
│  │ (Reverse     │         │ (Main)       │                │
│  │  Proxy)      │         └──────────────┘                │
│  └──────┬───────┘                                          │
│         │                                                   │
│         │ Routes to                                        │
│         ▼                                                   │
│  ┌──────────────────────────────────────────────────────┐ │
│  │            Infisical Services                         │ │
│  │                                                       │ │
│  │  ┌──────────────┐                                    │ │
│  │  │ infisical-db │  ← PostgreSQL                      │ │
│  │  └──────┬───────┘                                    │ │
│  │         │                                             │ │
│  │         │ Depends on                                 │ │
│  │         ▼                                             │ │
│  │  ┌──────────────┐                                    │ │
│  │  │ infisical-   │  ← Redis                           │ │
│  │  │ redis        │                                    │ │
│  │  └──────┬───────┘                                    │ │
│  │         │                                             │ │
│  │         │ Both healthy before                        │ │
│  │         ▼                                             │ │
│  │  ┌──────────────┐                                    │ │
│  │  │ infisical-   │  ← Backend API                     │ │
│  │  │ backend      │                                    │ │
│  │  └──────────────┘                                    │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Startup Order

1. **Infrastructure Stack** (00-infrastructure)
   - Creates `ai-network`
   - Starts Caddy (reverse proxy)
   - Starts Redis (main)

2. **Infisical Database** (infisical-db)
   - PostgreSQL container
   - Health check: `pg_isready`

3. **Infisical Redis** (infisical-redis)
   - Redis container
   - Health check: `redis-cli ping`

4. **Infisical Backend** (infisical-backend)
   - Waits for database and Redis to be healthy
   - Health check: `/api/health` endpoint
   - Start period: 30 seconds

### Health Checks

All Infisical services have health checks:

```yaml
infisical-db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 10s
    timeout: 5s
    retries: 5

infisical-redis:
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5

infisical-backend:
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:8080/api/health"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s
  depends_on:
    infisical-db:
      condition: service_healthy
    infisical-redis:
      condition: service_healthy
```

---

## Network Architecture

### Network Configuration

All services use the external `ai-network`:

```yaml
networks:
  default:
    external: true
    name: ai-network
```

**Critical**: The infrastructure stack must start first to create `ai-network`. Other stacks depend on it.

### Service Discovery

Services use container names as hostnames:

- `infisical-backend:8080` - Infisical API
- `infisical-db:5432` - PostgreSQL database
- `infisical-redis:6379` - Redis cache
- `caddy:80` - Reverse proxy

### Port Strategy

**Private Environment** (development):
- Port 8020 exposed directly: `http://localhost:8020`
- Direct port mapping bypasses Caddy
- Useful for local development

**Public Environment** (production):
- Only ports 80/443 exposed
- All traffic via Caddy reverse proxy
- Cloudflare Tunnel for external access: `https://infisical.datacrew.space`

### Routing

**Localhost Access:**
```
Browser → http://localhost:8020 → infisical-backend:8080
```

**Cloudflare Access:**
```
Browser → https://infisical.datacrew.space
        ↓
Cloudflare Tunnel (cloudflared)
        ↓
Caddy (reverse proxy)
        ↓
infisical-backend:8080
```

---

## Security Model

### Encryption

**At Rest:**
- Secrets encrypted in PostgreSQL using `INFISICAL_ENCRYPTION_KEY`
- Database files encrypted at filesystem level (optional)
- Encryption key stored in `.env` (never commit to git)

**In Transit:**
- HTTPS for all external communication (via Cloudflare Tunnel)
- Internal communication over Docker network (encrypted by Docker)
- TLS for PostgreSQL connections (optional)

### Authentication

**User Authentication:**
- Email/password (requires SMTP configuration)
- Google OAuth/SSO (optional)
- Session-based authentication
- Secure cookies (HTTPS required in production)

**CLI Authentication:**
- OAuth flow via browser
- Token stored locally in `~/.infisical/`
- Token expiration and renewal

**Machine Identity:**
- Client ID and Client Secret
- Used for automated access (CI/CD, scripts)
- Scoped permissions (read-only, read-write)

### Authorization

**Role-Based Access Control (RBAC):**
- Organization-level roles (admin, member, viewer)
- Project-level permissions
- Environment-specific access

**Audit Logging:**
- All secret access logged
- User actions tracked
- Timestamp and IP address recorded

### Network Security

**Capabilities:**
- Infisical backend: `CAP_DROP: ALL` (hardened)
- Database: Standard PostgreSQL capabilities
- Redis: Standard Redis capabilities

**Trust Proxy:**
- Enabled for reverse proxy support
- Properly forwards client IP addresses
- Required for Cloudflare Tunnel

---

## Benefits and Trade-offs

### Benefits

#### Security
- ✅ **No secrets in version control** - `.env` files only contain non-sensitive config
- ✅ **Encrypted storage** - Secrets encrypted at rest in PostgreSQL
- ✅ **Access control** - Who can access which secrets
- ✅ **Audit trail** - See who changed what and when

#### Operational Efficiency
- ✅ **Single source of truth** - All secrets in one place
- ✅ **Easy rotation** - Update once, all services get new value
- ✅ **Environment separation** - Different secrets for dev/prod
- ✅ **Team collaboration** - Share secrets securely

#### Developer Experience
- ✅ **Web UI** - No need to edit `.env` files manually
- ✅ **CLI integration** - Works with existing scripts
- ✅ **Automatic sync** - No manual copying needed
- ✅ **Fallback support** - Can still use `.env` if needed

### Trade-offs

#### Complexity
- ❌ **Additional infrastructure** - Requires PostgreSQL, Redis, and Infisical backend
- ❌ **Learning curve** - Team needs to learn Infisical UI and CLI
- ❌ **Setup time** - Initial setup takes longer than plain `.env` files

#### Dependencies
- ❌ **Service dependency** - Services depend on Infisical being available
- ❌ **Network dependency** - Requires `ai-network` to be created first
- ❌ **CLI dependency** - Requires Infisical CLI to be installed

#### Operational
- ❌ **Backup complexity** - Need to backup Infisical database
- ❌ **Migration effort** - Moving secrets from `.env` to Infisical takes time
- ❌ **Debugging** - Harder to debug secret issues (need to check Infisical)

### Mitigation Strategies

**For Complexity:**
- Provide comprehensive documentation (this guide)
- Automated setup scripts (`setup-project.py`)
- Gradual migration path (hybrid approach)

**For Dependencies:**
- Fallback to `.env` if Infisical unavailable
- Health checks ensure services wait for Infisical
- Clear error messages and troubleshooting guide

**For Operational:**
- Automated backup scripts (future)
- Migration guides and examples
- Diagnostic commands and troubleshooting decision tree

---

## Design Decisions

### Why Dedicated PostgreSQL?

**Decision:** Use a dedicated PostgreSQL instance for Infisical instead of sharing Supabase's PostgreSQL.

**Rationale:**
- **Isolation:** Infisical data separate from application data
- **Security:** Different encryption keys and access controls
- **Reliability:** Infisical database issues don't affect Supabase
- **Simplicity:** Easier to backup and restore independently

### Why Dedicated Redis?

**Decision:** Use a dedicated Redis instance for Infisical instead of sharing the main Redis.

**Rationale:**
- **Isolation:** Infisical sessions separate from application cache
- **Performance:** No contention with n8n job queues
- **Security:** Different access controls
- **Reliability:** Infisical Redis issues don't affect other services

### Why Hybrid Approach?

**Decision:** Support both Infisical and `.env` files during migration.

**Rationale:**
- **Gradual migration:** No big-bang cutover
- **Testing:** Can test Infisical without breaking existing setup
- **Rollback:** Easy to revert if issues arise
- **Flexibility:** Users can choose when to migrate

### Why Port 8020?

**Decision:** Use port 8020 for Infisical instead of default 8080.

**Rationale:**
- **No conflicts:** Port 8080 commonly used by other services
- **Consistency:** Follows port numbering scheme (8001-n8n, 8002-flowise, etc.)
- **Clarity:** Easy to remember and document

---

## Related Documentation

- [Setup Guide](./setup.md) - Initial setup and configuration
- [Usage Guide](./usage.md) - Day-to-day operations and secret management
- [Troubleshooting Guide](./troubleshooting_configuration.md) - Comprehensive troubleshooting
- [Infrastructure AGENTS.md](../../AGENTS.md) - Infrastructure stack rules and patterns

