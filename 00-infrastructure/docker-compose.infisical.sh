#!/bin/bash
# Helper script to run docker-compose with Infisical environment variables loaded
# This ensures INFISICAL_ENCRYPTION_KEY and INFISICAL_AUTH_SECRET are available

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load environment variables from .env.global and .env
if [ -f "$PROJECT_ROOT/.env.global" ]; then
    set -a
    source "$PROJECT_ROOT/.env.global"
    set +a
fi

if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # Source .env but ignore errors from invalid lines
    source "$PROJECT_ROOT/.env" 2>/dev/null || true
    set +a
fi

# Verify required variables are set
if [ -z "$INFISICAL_ENCRYPTION_KEY" ]; then
    echo "ERROR: INFISICAL_ENCRYPTION_KEY is not set!"
    exit 1
fi

if [ -z "$INFISICAL_AUTH_SECRET" ]; then
    echo "ERROR: INFISICAL_AUTH_SECRET is not set!"
    exit 1
fi

# Export variables for docker-compose
export INFISICAL_ENCRYPTION_KEY
export INFISICAL_AUTH_SECRET

# Run docker-compose with all arguments
cd "$SCRIPT_DIR"
docker compose "$@"

