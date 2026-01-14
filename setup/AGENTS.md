# Setup Scripts - AGENTS.md

> **Multi-Editor Support**: Both GitHub Copilot and Cursor AI read this file. Rules here override the root AGENTS.md for setup and installation concerns.

> **Override**: This file extends [../AGENTS.md](../AGENTS.md). Setup-specific rules take precedence.

## Component Identity

**Directory**: `setup/`  
**Purpose**: Setup, configuration, and validation scripts for the local AI package  
**Language**: Python 3.10+  
**Dependencies**: `python-dotenv`, `requests` (see individual scripts)

## Folder Structure

```
setup/
├── AGENTS.md                    # This file
├── README.md                    # Setup scripts overview
├── generate-env-passwords.py   # Password generation utility
├── configure_hostnames.py       # Hostname configuration sync
├── install_clis.py             # CLI tool installation
└── cloudflare/                  # Cloudflare setup scripts
    ├── setup_tunnel.py         # Automated tunnel setup
    ├── setup_dns.py            # DNS record management
    └── [other scripts...]
```

## Key Scripts

### Password Generation

**File**: `generate-env-passwords.py`  
**Purpose**: Generate secure passwords and keys for `.env` file

**Patterns**:
- XKCD-style passphrases for passwords (e.g., `POSTGRES_PASSWORD`)
- Hex strings for encryption keys (e.g., `N8N_ENCRYPTION_KEY`)
- Base64 strings for auth secrets (e.g., `INFISICAL_AUTH_SECRET`)
- Supabase JWT tokens (`JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY`)
- **Langfuse ENCRYPTION_KEY**: 64 hex characters (256 bits) - required for Langfuse
- **Supabase Secrets**: `SECRET_KEY_BASE` (64 hex chars), `VAULT_ENC_KEY` (32 hex chars), `PG_META_CRYPTO_KEY` (32 hex chars)
- **Logflare Tokens**: `LOGFLARE_PUBLIC_ACCESS_TOKEN` and `LOGFLARE_PRIVATE_ACCESS_TOKEN` (32 hex chars each)

**Usage**:
```bash
python setup/generate-env-passwords.py
```

**Key Files**:
- `setup/generate-env-passwords.py` - Main password generator
- `.env_sample` - Template with variable names (in repo root)

**Supabase Environment Variables**:
The script generates the following Supabase-specific variables:
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` - Database connection (defaults: `supabase-db`, `5432`, `postgres`)
- `JWT_EXPIRY` - JWT token expiration in seconds (default: `3600`)
- `SECRET_KEY_BASE` - 64 hex characters for Realtime/Pooler encryption
- `VAULT_ENC_KEY` - 32 hex characters for Supabase Vault encryption
- `PG_META_CRYPTO_KEY` - 32 hex characters for Postgres Meta encryption
- `LOGFLARE_PUBLIC_ACCESS_TOKEN` - 32 hex characters for Logflare public access
- `LOGFLARE_PRIVATE_ACCESS_TOKEN` - 32 hex characters for Logflare private access
- `POOLER_TENANT_ID` - UUID for Supabase Pooler tenant
- `POOLER_DEFAULT_POOL_SIZE`, `POOLER_MAX_CLIENT_CONN`, `POOLER_DB_POOL_SIZE` - Pooler configuration (defaults: `20`, `100`, `10`)
- `POOLER_PROXY_PORT_TRANSACTION` - Pooler transaction proxy port (default: `6543`)
- `API_EXTERNAL_URL`, `SITE_URL`, `SUPABASE_PUBLIC_URL` - API and site URLs (defaults: `http://localhost:8011`, `http://localhost:3000`)
- `KONG_HTTP_PORT`, `KONG_HTTPS_PORT` - Kong gateway ports (defaults: `8011`, `8443`)
- `STUDIO_DEFAULT_ORGANIZATION`, `STUDIO_DEFAULT_PROJECT` - Studio defaults
- `PGRST_DB_SCHEMAS` - PostgREST database schemas (default: `public,storage,graphql_public`)
- Auth configuration variables: `DISABLE_SIGNUP`, `ENABLE_EMAIL_SIGNUP`, `ENABLE_EMAIL_AUTOCONFIRM`, etc.

### Cloudflare Setup

**Location**: `setup/cloudflare/`  
**Purpose**: Automated Cloudflare Tunnel and DNS configuration

**Key Scripts**:
- `setup_tunnel.py` - Complete tunnel setup (authenticates, creates tunnel, configures DNS)
- `setup_dns.py` - Add DNS records via Cloudflare API
- `setup_tunnel_routes.py` - Configure public hostnames in tunnel
- `configure_hostnames.py` - Sync hostnames between Caddy and Cloudflare
- `validate_setup.py` - Validate Cloudflare configuration

**Patterns**:
- Interactive prompts for user input
- Automatic `.env` file updates
- Token-based authentication (Cloudflare API tokens)
- Browser-based OAuth for tunnel setup

**Key Files**:
- `setup/cloudflare/setup_tunnel.py` - Main setup script
- `00-infrastructure/scripts/setup-cloudflare-tunnel-routes.py` - Route configuration (infrastructure stack)

### CLI and Dependency Installation

**File**: `install_clis.py`  
**Purpose**: Install required CLI tools (cloudflared, infisical, etc.) and Python dependencies

**What it installs**:
- Infisical CLI
- Google Cloud CLI (gcloud)
- Cloudflared CLI
- pre-commit hooks
- Python dependencies for samples and tests (from `04-lambda/pyproject.toml`)

**Patterns**:
- Platform detection (Linux/Mac/Windows)
- Package manager detection (apt/yum/brew)
- Version verification after installation
- Uses `uv` if available (preferred), falls back to `pip`
- Installs Python dependencies with `[test,samples]` extras

**Usage**:
```bash
python setup/install_clis.py
```

This will install all CLI tools and Python dependencies needed for running samples and tests.

## Architecture Patterns

### Environment Variable Management

**Three Sources**:
1. `.env` file (root directory) - Primary source
2. `.env.global` - Shared non-sensitive defaults
3. Infisical - Optional secret management (overrides `.env`)

**Script Behavior**:
- Scripts read from `.env` by default
- Scripts can update `.env` (with user confirmation)
- Never commit `.env` files (in `.gitignore`)

### Script Organization

**By Function**:
- `setup_*.py` - Initial configuration scripts
- `configure_*.py` - Update existing configuration
- `update_*.py` - Sync configuration between systems
- `validate_*.py` - Verify setup correctness
- `generate-*.py` - Generate values (passwords, keys, etc.)

### Error Handling

**Patterns**:
- Interactive prompts for missing required values
- Clear error messages with remediation steps
- Dry-run mode (`--dry-run`) for validation scripts
- Backup creation before modifying files

## Key Files & Search Hints

```bash
# Find setup scripts
ls setup/*.py

# Find Cloudflare scripts
ls setup/cloudflare/*.py

# Find password generation logic
rg -n "XKCD\|passphrase\|hex\|base64" setup/generate-env-passwords.py

# Find environment variable usage
rg -n "\.env\|dotenv\|load_dotenv" setup/

# Find Cloudflare API calls
rg -n "cloudflare\|api\|token" setup/cloudflare/
```

## Testing & Validation

### Manual Validation

**Password Generator**:
```bash
# Test password generation
python setup/generate-env-passwords.py --dry-run

# Verify .env file updates
diff .env .env.backup
```

**Cloudflare Setup**:
```bash
# Validate tunnel configuration
python setup/cloudflare/validate_setup.py

# Test DNS records
dig +short n8n.yourdomain.com
```

### Common Issues

1. **Import Errors**: Install dependencies: `pip install requests python-dotenv`
2. **Permission Errors**: Make scripts executable: `chmod +x setup/*.py`
3. **API Token Issues**: Verify token has correct permissions in Cloudflare dashboard
4. **.env File Not Found**: Run scripts from project root directory

## Do's and Don'ts

### ✅ DO
- Run setup scripts from project root
- Use `--dry-run` flag to preview changes
- Backup `.env` before running scripts that modify it
- Verify script output before committing changes
- Use interactive prompts for sensitive values

### ❌ DON'T
- Commit `.env` files with secrets
- Hardcode API tokens or passwords in scripts
- Run destructive scripts without confirmation
- Skip validation after setup
- Modify `.env_sample` without updating documentation

## Domain Dictionary

- **XKCD Password**: Passphrase-style password (e.g., "correct-horse-battery-staple")
- **Cloudflare Tunnel**: Zero-trust tunnel (no port forwarding required)
- **Tunnel Token**: Authentication token for Cloudflare Tunnel (stored in `CLOUDFLARE_TUNNEL_TOKEN`)
- **API Token**: Cloudflare API token for DNS/zone management (different from tunnel token)
- **Dry Run**: Preview mode that shows what would change without making changes

---

**See Also**:
- [../AGENTS.md](../AGENTS.md) for universal rules
- [README.md](README.md) for detailed script documentation
- [../docs/cloudflare/setup.md](../docs/cloudflare/setup.md) for Cloudflare setup guide
