# Supabase Configuration

This directory contains documentation for configuring and managing Supabase in the local-ai-packaged setup.

## Overview

Supabase is configured as a self-hosted instance with the following components:

- **PostgreSQL Database** - Primary database with extensions
- **Auth (GoTrue)** - Authentication and user management
- **PostgREST** - Auto-generated REST API
- **Realtime** - Real-time subscriptions via WebSockets
- **Storage** - S3-compatible file storage with MinIO
- **Edge Functions** - Serverless functions runtime
- **Studio** - Web-based management dashboard
- **Kong** - API gateway
- **Analytics (Logflare)** - Logging and analytics

## Table of Contents

- [Initial Setup](#initial-setup)
- [Environment Variables](#environment-variables)
- [Storage Configuration](#storage-configuration)
- [Accessing Services](#accessing-services)
- [Troubleshooting](#troubleshooting)

## Initial Setup

### Prerequisites

1. Docker and Docker Compose installed
2. Python 3.x (for start script)
3. Environment variables configured (see below)

### Quick Start

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Generate required secrets**:
   ```bash
   # Generate JWT Secret (32+ characters, base64)
   openssl rand -base64 32
   
   # Generate Postgres password (strong password)
   openssl rand -base64 24
   
   # Generate Anon Key and Service Role Key
   # These are JWT tokens - use Supabase CLI or generate manually
   ```

3. **Start services**:
   ```bash
   python start_services.py --profile gpu-nvidia
   # or
   python start_services.py --profile cpu
   ```

## Environment Variables

### Required Supabase Variables

Add these to your `.env` file:

```bash
############
# Supabase Secrets
############
POSTGRES_PASSWORD=your-secure-postgres-password
JWT_SECRET=your-jwt-secret-base64-string
ANON_KEY=your-anon-key-jwt-token
SERVICE_ROLE_KEY=your-service-role-key-jwt-token
DASHBOARD_USERNAME=your-dashboard-username
DASHBOARD_PASSWORD=your-dashboard-password
POOLER_TENANT_ID=your-pooler-tenant-id
POOLER_DB_POOL_SIZE=5
```

### Generating Keys

The easiest way to generate Supabase keys is using the Supabase CLI:

```bash
# Install Supabase CLI
npm install -g supabase

# Generate keys
supabase gen keys
```

Or manually generate using the Supabase key generation script or online tools.

### Optional Variables

```bash
############
# Supabase Storage (S3 Compatible)
############
# Override default MinIO credentials
SUPABASE_MINIO_ROOT_USER=supa-storage
SUPABASE_MINIO_ROOT_PASSWORD=your-secure-password

############
# Supabase Configuration
############
POSTGRES_PORT=5432
POSTGRES_HOST=db
POSTGRES_DB=postgres
KONG_HTTP_PORT=8000
KONG_HTTPS_PORT=8443
SUPABASE_PUBLIC_URL=http://localhost:8000
API_EXTERNAL_URL=http://localhost:8000
SITE_URL=http://localhost:3000
```

## Storage Configuration

Supabase Storage is configured with **S3-compatible backend** using MinIO.

### Features

- ✅ S3-compatible API
- ✅ Persistent storage (Docker named volume)
- ✅ Image transformation via imgproxy
- ✅ Fine-grained access control
- ✅ Automatic bucket creation

### MinIO Configuration

- **Service Name**: `supabase-minio`
- **Internal Ports**: 9020 (API), 9021 (Console)
- **External Access** (private mode): `localhost:9020`, `localhost:9021`
- **Volume**: `supabase_minio_data` (persistent)

### Accessing MinIO Console

1. **Local Development**:
   - Console: `http://localhost:9021`
   - API: `http://localhost:9020`
   - Default credentials: `supa-storage` / `secret1234`

2. **Using MinIO Client**:
   ```bash
   # Install MinIO client
   brew install minio/stable/mc  # macOS
   # or download from https://min.io/download
   
   # Configure alias
   mc alias set supabase-minio http://localhost:9020 supa-storage secret1234
   
   # List buckets
   mc ls supabase-minio
   
   # Create bucket
   mc mb supabase-minio/my-bucket
   ```

### Customizing MinIO Credentials

To use custom credentials, add to your `.env`:

```bash
SUPABASE_MINIO_ROOT_USER=your-username
SUPABASE_MINIO_ROOT_PASSWORD=your-secure-password
```

> ⚠️ **Important**: Change default credentials in production!

### Storage Backend

The storage service is configured to use S3 backend automatically via the `docker-compose.s3.yml` override file. The configuration includes:

- **Storage Backend**: `s3`
- **S3 Endpoint**: `http://supabase-minio:9020`
- **S3 Protocol**: `http`
- **Path Style**: Enabled (required for MinIO)
- **Bucket**: `stub` (default, can be customized)

## Accessing Services

### Studio (Dashboard)

- **Local**: `http://localhost:3000` (if exposed)
- **Via Caddy**: Configured via `SUPABASE_HOSTNAME` environment variable
- **Default**: Access through Kong gateway at configured hostname

### API Endpoints

- **REST API**: `http://localhost:8000/rest/v1/`
- **Auth API**: `http://localhost:8000/auth/v1/`
- **Storage API**: `http://localhost:8000/storage/v1/`
- **Realtime**: `ws://localhost:8000/realtime/v1/`

### Database Connection

- **Host**: `localhost` (or `db` from within Docker network)
- **Port**: `5432` (or configured `POSTGRES_PORT`)
- **Database**: `postgres`
- **User**: `postgres`
- **Password**: Value from `POSTGRES_PASSWORD`

### Connection String Example

```
postgresql://postgres:YOUR_PASSWORD@localhost:5432/postgres
```

## Service Architecture

```
┌─────────────┐
│   Kong      │ ← API Gateway (Port 8000)
│  (Gateway)  │
└──────┬──────┘
       │
       ├──→ Studio (Dashboard)
       ├──→ Auth (GoTrue)
       ├──→ PostgREST (REST API)
       ├──→ Realtime (WebSockets)
       ├──→ Storage (S3 API)
       └──→ Edge Functions
       
┌─────────────┐
│ PostgreSQL  │ ← Database (Port 5432)
└─────────────┘

┌─────────────┐
│   MinIO     │ ← S3 Storage (Port 9020/9021)
└─────────────┘
```

## Troubleshooting

### Services Not Starting

1. **Check Docker logs**:
   ```bash
   docker compose logs supabase-db
   docker compose logs supabase-storage
   ```

2. **Verify environment variables**:
   ```bash
   docker compose config | grep -A 5 SUPABASE
   ```

3. **Check port conflicts**:
   ```bash
   # Check if ports are in use
   netstat -an | grep 8000
   netstat -an | grep 5432
   ```

### Storage Issues

1. **MinIO not accessible**:
   - Check if `supabase-minio` container is running
   - Verify ports 9020/9021 are not blocked
   - Check MinIO logs: `docker compose logs supabase-minio`

2. **Bucket creation fails**:
   - Verify MinIO credentials in environment variables
   - Check `supabase-minio-createbucket` container logs
   - Manually create bucket via MinIO console

3. **Storage API errors**:
   - Verify `STORAGE_BACKEND=s3` in storage service
   - Check S3 endpoint configuration
   - Verify MinIO is healthy: `curl http://localhost:9020/minio/health/live`

### Database Connection Issues

1. **Connection refused**:
   - Ensure database container is healthy
   - Check `POSTGRES_HOST` and `POSTGRES_PORT` variables
   - Verify password matches in all services

2. **Authentication failed**:
   - Verify `POSTGRES_PASSWORD` is set correctly
   - Check database logs for authentication errors
   - Ensure password doesn't contain special characters that need escaping

### Key Generation Issues

1. **Invalid JWT tokens**:
   - Regenerate using Supabase CLI
   - Ensure keys are properly formatted (base64)
   - Verify `JWT_SECRET` matches across all services

### Reset Everything

To completely reset Supabase (⚠️ **deletes all data**):

```bash
# Stop services
docker compose down

# Remove volumes
docker compose down -v

# Remove Supabase volumes specifically
docker volume rm local-ai-packaged_supabase_minio_data
docker volume rm supabase_db-config

# Restart
python start_services.py
```

## Additional Resources

- [Supabase Official Docs](https://supabase.com/docs)
- [Self-Hosting Guide](https://supabase.com/docs/guides/self-hosting/docker)
- [Storage Documentation](https://supabase.com/docs/guides/storage)
- [Supabase GitHub](https://github.com/supabase/supabase)

## Configuration Files

- **Main Compose**: `supabase/docker/docker-compose.yml`
- **S3 Override**: `supabase/docker/docker-compose.s3.yml`
- **Environment Template**: `supabase/docker/.env.example`

