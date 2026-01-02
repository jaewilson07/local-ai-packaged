# Supabase Docker Directory Requirements

## Overview

The `supabase/docker/` directory contains files needed for running Supabase locally. However, **you don't need the entire Supabase repository** - only specific subdirectories are required.

## Essential: `supabase/docker/volumes/` ✅

**Status**: **REQUIRED** - These files are actively used by `compose/supabase/docker-compose.yml`

The `volumes/` subdirectory contains configuration files and data that are mounted into Supabase containers:

### Database Initialization Scripts (`volumes/db/`)

These SQL files configure the PostgreSQL database on startup:

- **`jwt.sql`** - Sets JWT secret and expiration from environment variables
- **`roles.sql`** - Creates Supabase-specific database roles (anon, authenticated, service_role, etc.)
- **`webhooks.sql`** - Creates webhook event triggers
- **`realtime.sql`** - Sets up Realtime extension and triggers
- **`_supabase.sql`** - Internal Supabase schema initialization
- **`logs.sql`** - Analytics/logging schema setup
- **`pooler.sql`** - Connection pooler configuration
- **`data/`** - PostgreSQL data directory (persistent storage, contains actual database files)

**Mounted in**: `db` service (PostgreSQL container)

### API Gateway Configuration (`volumes/api/`)

- **`kong.yml`** - Kong API gateway declarative configuration
  - Defines routes, consumers, ACLs, and plugins
  - Contains environment variable placeholders (e.g., `$SUPABASE_ANON_KEY`)

**Mounted in**: `kong` service

### Storage Configuration (`volumes/storage/`)

- **`stub/`** - Empty directory used as storage backend mount point
- Used by both `storage` and `imgproxy` services

**Mounted in**: `storage` and `imgproxy` services

### Edge Functions (`volumes/functions/`)

- **`main/index.ts`** - Main edge function entry point
- **`hello/index.ts`** - Example edge function
- Your custom edge functions go here

**Mounted in**: `functions` service (edge-runtime container)

### Logging Configuration (`volumes/logs/`)

- **`vector.yml`** - Vector log aggregation configuration
  - Configures log collection from Docker containers
  - Sends logs to Logflare (analytics service)

**Mounted in**: `vector` service

### Pooler Configuration (`volumes/pooler/`)

- **`pooler.exs`** - Supavisor (connection pooler) configuration
  - Elixir configuration file for connection pooling

**Mounted in**: `supavisor` service

## Optional: `supabase/docker/docker-compose.yml` ⚠️

**Status**: **OPTIONAL** - Only needed if you use the update script

This file is:

- **Used by**: `scripts/update-supabase-compose.py` to sync changes from upstream Supabase
- **Not used by**: The actual running services (they use `compose/supabase/docker-compose.yml`)

**If you don't use the update script**: You can safely ignore or remove this file.

**If you want to keep it updated**: This file comes from the official Supabase repository. You would need to:

1. Clone the Supabase repository into `supabase/` directory
2. Run `scripts/update-supabase-compose.py` to sync changes to `compose/supabase/docker-compose.yml`

## Optional: `supabase/docker/docker-compose.s3.yml` ⚠️

**Status**: **OPTIONAL** - Only needed if you use the update script

Similar to `docker-compose.yml`, this file contains S3 storage configuration that gets merged by the update script.

## What You DON'T Need

You **don't need**:

- The entire Supabase repository source code
- Development files (`dev/`, `utils/`, etc.)
- Documentation files (unless you want to reference them)
- Build files or Dockerfiles (you use pre-built images)

## Can You Use Just Docker Images?

**Short answer**: No, not completely.

**Why**: While Supabase services run as Docker images (e.g., `supabase/postgres:15.8.1.085`), they require:

1. **Configuration files** - Kong config, pooler config, vector config
2. **Initialization scripts** - SQL files that set up the database schema
3. **Persistent storage** - Database data directory
4. **Environment-specific values** - JWT secrets, passwords (from `.env`)

These can't be embedded in Docker images because they're:

- Environment-specific (different secrets per deployment)
- User-customizable (edge functions, storage configuration)
- Runtime-generated (database data)

## Current Architecture

The project uses:

- **Docker images** from Docker Hub (e.g., `supabase/postgres`, `supabase/studio`)
- **Configuration files** from `supabase/docker/volumes/` (mounted as volumes)
- **Compose file** at `compose/supabase/docker-compose.yml` (customized for this project)

This gives you:

- ✅ Official, maintained Docker images
- ✅ Customizable configuration
- ✅ Persistent data storage
- ✅ Easy updates (just pull new images)

## Summary

| Directory/File                          | Status            | Required For       |
| --------------------------------------- | ----------------- | ------------------ |
| `supabase/docker/volumes/`              | ✅ **REQUIRED**   | Running services   |
| `supabase/docker/docker-compose.yml`    | ⚠️ **OPTIONAL**   | Update script only |
| `supabase/docker/docker-compose.s3.yml` | ⚠️ **OPTIONAL**   | Update script only |
| Rest of `supabase/docker/`              | ❌ **NOT NEEDED** | Development only   |

## Migration Path

If you want to minimize what you keep:

1. **Keep**: `supabase/docker/volumes/` (essential)
2. **Optional**: Keep `supabase/docker/docker-compose.yml` if you use the update script
3. **Remove**: Everything else in `supabase/docker/` if you don't need it

The services will continue to work as long as `volumes/` is present and properly referenced in `compose/supabase/docker-compose.yml`.
