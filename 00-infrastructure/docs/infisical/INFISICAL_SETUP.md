# Infisical Encryption Key Setup - Fixed

## What Was Fixed

The `INFISICAL_ENCRYPTION_KEY` has been added to `.env.global` so Docker Compose can properly load it.

## Current Configuration

✅ **Encryption Key**: `7e806f8a12d4a535988a89201841f310` (32 hex characters - correct format)
✅ **Auth Secret**: `tDCbwCTc6B/blBN6dxYQdJH3QjmoGTLvL+KVzZ9stQg=` (base64 encoded)

Both are now in `/home/jaewilson07/GitHub/local-ai-packaged/.env.global`

## How to Use

### Option 1: Use the Helper Script (Recommended)

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged/00-infrastructure

# Start services
./docker-compose.infisical.sh up -d

# Stop services  
./docker-compose.infisical.sh down

# View logs
./docker-compose.infisical.sh logs -f infisical-backend

# Check status
./docker-compose.infisical.sh ps
```

### Option 2: Export Variables Manually

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged

# Load variables
source .env.global
export INFISICAL_ENCRYPTION_KEY
export INFISICAL_AUTH_SECRET

# Then run docker-compose normally
cd 00-infrastructure
docker compose up -d
```

### Option 3: Use Standard docker-compose (if variables are exported)

If you've already exported the variables in your shell session:

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged/00-infrastructure
docker compose up -d
```

## Verification

Check that the encryption key is properly loaded:

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged/00-infrastructure

# Method 1: Using helper script
./docker-compose.infisical.sh config | grep -A 5 "infisical-backend:" | grep ENCRYPTION_KEY

# Method 2: After exporting variables
source ../.env.global
export INFISICAL_ENCRYPTION_KEY INFISICAL_AUTH_SECRET
docker compose config | grep -A 5 "infisical-backend:" | grep ENCRYPTION_KEY
```

You should see:
```
ENCRYPTION_KEY: 7e806f8a12d4a535988a89201841f310
```

## Why This Was Needed

Docker Compose's `${VARIABLE}` syntax in the `environment:` section requires variables to be available in the shell environment when docker-compose runs. The `env_file` directive loads variables into the container, but doesn't make them available for variable substitution in the compose file itself.

By adding the variables to `.env.global` and exporting them (via the helper script or manually), Docker Compose can properly resolve `${INFISICAL_ENCRYPTION_KEY}` and `${INFISICAL_AUTH_SECRET}`.

## Troubleshooting

### Warning: "INFISICAL_ENCRYPTION_KEY variable is not set"

This means the variable isn't exported in your shell. Use Option 1 or Option 2 above.

### Encryption Key Length Error

The encryption key must be exactly **32 hex characters** (16 bytes). Current key is correct:
```bash
echo -n "7e806f8a12d4a535988a89201841f310" | wc -c
# Should output: 32
```

### Container Still Shows Errors

1. Restart the container after fixing the variables:
   ```bash
   cd 00-infrastructure
   ./docker-compose.infisical.sh restart infisical-backend
   ```

2. Check logs:
   ```bash
   ./docker-compose.infisical.sh logs infisical-backend --tail 50
   ```

3. Verify database connection:
   ```bash
   docker exec infisical-backend wget -qO- http://localhost:8080/api/health
   ```

