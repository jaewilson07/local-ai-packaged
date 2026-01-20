# Setup Scripts

This directory contains setup and validation scripts for configuring the local AI package.

## Cloudflare Setup Scripts

All Cloudflare-related setup scripts are in the [`cloudflare/`](./cloudflare/) directory.

### Quick Start

For automated Cloudflare Tunnel setup, run:

```bash
python setup/cloudflare/setup_tunnel.py
```

This will guide you through the complete setup process.

### Available Scripts

#### `setup_tunnel.py`

**Purpose:** Automated Cloudflare Tunnel setup

**What it does:**
- Checks for `cloudflared` CLI installation
- Authenticates with Cloudflare (opens browser)
- Creates a tunnel
- Configures DNS records for all services
- Generates tunnel token and updates `.env` file
- Guides you through configuring public hostnames

**Usage:**
```bash
python setup/cloudflare/setup_tunnel.py
```

**Prerequisites:**
- `cloudflared` CLI installed (see [cloudflare-access-setup skill](../.cursor/skills/cloudflare-access-setup/SKILL.md))
- Domain added to Cloudflare account
- Cloudflare account access

#### `setup_dns.py`

**Purpose:** Add DNS records to Cloudflare via API

**What it does:**
- Adds all DNS records (MX, TXT, CNAME, A records) to Cloudflare
- Sets correct proxy settings (DNS only for email records)
- Skips records that already exist
- Automatically gets Zone ID

**Usage:**
```bash
python setup/cloudflare/setup_dns.py
```

**Prerequisites:**
- Cloudflare API token with DNS edit permissions
- Domain already added to Cloudflare account

**To get API token:**
1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token"
3. Use "Edit zone DNS" template
4. Select your zone (e.g., `datacrew.space`)
5. Copy the token

#### `setup_tunnel_routes.py`

**Purpose:** Configure public hostnames in Cloudflare Tunnel

**What it does:**
- Configures routes for all services in the tunnel
- Sets up hostname routing to Caddy
- Creates DNS records automatically

**Usage:**
```bash
python setup/cloudflare/setup_tunnel_routes.py
```

**Prerequisites:**
- Tunnel already created
- Tunnel token in `.env` file or environment variable

#### `configure_hostnames.py`

**Purpose:** Sync hostname configuration between Caddy and Cloudflare

**What it does:**
- Updates hostname environment variables
- Ensures consistency between Caddy and Cloudflare Tunnel routing

**Usage:**
```bash
python setup/cloudflare/configure_hostnames.py
```

#### `update_env_tunnel.py`

**Purpose:** Update `.env` file with Cloudflare Tunnel token

**What it does:**
- Adds or updates `CLOUDFLARE_TUNNEL_TOKEN` in `.env` file
- Preserves existing environment variables

**Usage:**
```bash
python setup/cloudflare/update_env_tunnel.py
```

**Note:** Usually called automatically by `setup_tunnel.py`, but can be run manually if needed.

#### `validate_setup.py`

**Purpose:** Validate Cloudflare configuration

**What it does:**
- Checks tunnel connection status
- Verifies DNS records are correct
- Validates hostname configuration
- Reports any issues found

**Usage:**
```bash
python setup/cloudflare/validate_setup.py
```

**Use cases:**
- After initial setup to verify everything is working
- When troubleshooting connection issues
- Before making configuration changes

## Script Dependencies

All scripts require Python 3 and may use the following packages:
- `requests` - For API calls
- `python-dotenv` - For `.env` file handling

Install dependencies:
```bash
# Install CLI tools and Python dependencies (recommended)
python setup/install_clis.py

# Or install just Python dependencies manually
pip install requests python-dotenv
```

**Note**: The `install_clis.py` script also installs all Python dependencies needed for running samples and tests from `04-lambda/pyproject.toml` (including `pydantic-ai`, `neo4j`, `requests`, etc.).

## Environment Variables

Scripts may use or update the following environment variables:

- `CLOUDFLARE_TUNNEL_TOKEN` - Tunnel authentication token
- `CLOUDFLARE_API_TOKEN` - API token for DNS operations (optional, can be entered interactively)
- `N8N_HOSTNAME`, `WEBUI_HOSTNAME`, etc. - Service hostnames

## Documentation

For detailed setup instructions, see:
- [cloudflare-access-setup skill](../.cursor/skills/cloudflare-access-setup/SKILL.md) - Cloudflare Access setup
- [00-infrastructure/AGENTS.md](../00-infrastructure/AGENTS.md) - Infrastructure stack details

## Troubleshooting

### Script not found

If you get "command not found" errors, make sure you're running scripts from the project root:

```bash
# From project root
python setup/cloudflare/setup_tunnel.py
```

### Permission errors

On Linux/Mac, you may need to make scripts executable:

```bash
chmod +x setup/cloudflare/*.py
```

### Import errors

Install required Python packages:

```bash
pip install requests python-dotenv
```

### API authentication issues

- Verify your Cloudflare API token has correct permissions
- Check that the token hasn't expired
- Ensure you're using the correct zone/domain

## Script Organization

Scripts are organized by functionality:
- **Setup scripts** - Initial configuration (`setup_*.py`)
- **Configuration scripts** - Update existing config (`configure_*.py`, `update_*.py`)
- **Validation scripts** - Verify setup (`validate_*.py`)

This organization makes it easy to find the right script for your task.

## Environment Setup

Environment configuration files and scripts are in the [`env/`](./env/) directory:

- **[Environment Setup Guide](./env/README.md)** - How to set up your `.env` file with XKCD-style passwords
- **`generate_passwords.py`** - Script to generate secure passphrases for all required secrets

### Quick Start

Generate passwords for your `.env` file:

```bash
python setup/generate-env-passwords.py
```

This will generate XKCD-style passphrases and hex strings for all required secrets.

## ComfyUI Model Configuration

ComfyUI model provisioning documentation is in the [`comfyui/`](./comfyui/) directory:

- **[ComfyUI Model Configuration](./comfyui/README.md)** - How to configure and provision models for ComfyUI
- Explains `models.yml` format and `provision-models.py` script
