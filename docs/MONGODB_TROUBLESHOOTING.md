# MongoDB Troubleshooting Guide

This guide helps diagnose and resolve MongoDB connection issues in the local-ai-packaged stack.

## Quick Diagnostics

### 1. Verify MongoDB Service is Running

```bash
# Check container status
docker compose -p localai-data ps mongodb

# Check container logs
docker compose -p localai-data logs --tail=50 mongodb

# Check if MongoDB is responding
docker exec mongodb mongosh --eval "db.adminCommand('ping')"
```

### 2. Test MongoDB Connection

Use the provided test script:

```bash
# Test MongoDB connection from host
python sample/data/test_mongodb_connection.py
```

This script will:
- Check if MongoDB container is running
- Display the connection URI being used (password masked)
- Test connection with authentication
- List available databases

### 3. Test Health Endpoint

Test the Lambda server's MongoDB health endpoint:

```bash
# Test health endpoint
python sample/data/test_mongodb_health.py

# Or direct curl
curl http://localhost:8000/health/mongodb
```

## Common Error Messages

### ServerSelectionTimeoutError

**Error**: `ServerSelectionTimeoutError: No servers match selector "Primary()"`

**Causes**:
1. MongoDB container is not running
2. Network connectivity issues between containers
3. Replica set not initialized (for replica set connections)
4. Authentication failure
5. Wrong connection string format

**Solutions**:

1. **Verify MongoDB is running**:
   ```bash
   docker compose -p localai-data ps mongodb
   # Should show "Up" status
   ```

2. **Check network connectivity**:
   ```bash
   # From Lambda server container
   docker exec lambda-server ping -c 2 mongodb

   # Verify both containers are on ai-network
   docker network inspect ai-network | grep -E "mongodb|lambda-server"
   ```

3. **Check connection string format**:
   - For direct connection: `mongodb://admin:password@mongodb:27017/?directConnection=true&authSource=admin`
   - For replica set: `mongodb://admin:password@mongodb:27017/?replicaSet=rs0&authSource=admin`
   - Verify credentials match `MONGODB_ROOT_USERNAME` and `MONGODB_ROOT_PASSWORD` in `.env`

4. **Check MongoDB logs for errors**:
   ```bash
   docker compose -p localai-data logs mongodb | tail -50
   ```

### ConnectionFailure

**Error**: `ConnectionFailure: [Errno 111] Connection refused`

**Causes**:
1. MongoDB container not running
2. Port not exposed or firewall blocking
3. Wrong hostname in connection string

**Solutions**:

1. **Start MongoDB service**:
   ```bash
   python start_services.py --stack data
   # Or
   docker compose -p localai-data up -d mongodb
   ```

2. **Verify container name**:
   - Connection string should use `mongodb` (container name)
   - Not `localhost` or `127.0.0.1` (unless using directConnection from host)

3. **Check port mapping**:
   ```bash
   docker compose -p localai-data ps mongodb
   # Should show port 27017
   ```

### Authentication Failed

**Error**: `Authentication failed` or `not authorized`

**Causes**:
1. Wrong username/password
2. Missing `authSource=admin` in connection string
3. User doesn't exist in MongoDB

**Solutions**:

1. **Verify credentials in `.env`**:
   ```bash
   grep MONGODB_ROOT_USERNAME .env
   grep MONGODB_ROOT_PASSWORD .env
   ```

2. **Check connection string includes authSource**:
   ```
   mongodb://admin:password@mongodb:27017/?directConnection=true&authSource=admin
   ```

3. **Test authentication directly**:
   ```bash
   docker exec mongodb mongosh -u admin -p admin123 --authenticationDatabase admin --eval "db.adminCommand('ping')"
   ```

### Configuration Mismatch

**Error**: `500 Internal Server Error` with MongoDB connection issues

**Causes**:
1. Different projects using different MongoDB connection variables
2. Inconsistent connection string formats
3. Missing environment variables

**Solutions**:

1. **Verify all projects use `MONGODB_URI`**:
   - Lambda server uses: `MONGODB_URI` (from `server.config.settings`)
   - Discord characters now uses: `MONGODB_URI` (from global settings)
   - Check `.env` file has `MONGODB_URI` set

2. **Check docker-compose.yml passes correct URI**:
   ```yaml
   # In 04-lambda/docker-compose.yml
   environment:
     MONGODB_URI: mongodb://${MONGODB_ROOT_USERNAME:-admin}:${MONGODB_ROOT_PASSWORD:-admin123}@mongodb:27017/?directConnection=true
   ```

3. **Verify connection string format**:
   - Must include authentication: `mongodb://user:pass@host:port`
   - Must include query parameters: `?directConnection=true&authSource=admin`
   - For replica sets: `?replicaSet=rs0&authSource=admin`

## Configuration Checklist

### Environment Variables

Verify these are set in `.env`:

```bash
# MongoDB credentials
MONGODB_ROOT_USERNAME=admin
MONGODB_ROOT_PASSWORD=admin123

# MongoDB connection (used by Lambda server)
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/?directConnection=true&authSource=admin
MONGODB_DATABASE=rag_db
```

### Docker Compose Configuration

Verify MongoDB service in `01-data/mongodb/docker-compose.yml`:

```yaml
services:
  mongodb:
    image: mongodb/mongodb-atlas-local:latest
    container_name: mongodb
    environment:
      MONGODB_INITDB_ROOT_USERNAME: ${MONGODB_ROOT_USERNAME:-admin}
      MONGODB_INITDB_ROOT_PASSWORD: ${MONGODB_ROOT_PASSWORD:-admin123}
      MONGODB_REPLICA_SET_NAME: rs0
    networks:
      - default  # Should be ai-network
```

### Network Configuration

Verify both services are on `ai-network`:

```bash
# Check network exists
docker network inspect ai-network

# Verify containers are connected
docker network inspect ai-network | grep -E "mongodb|lambda-server"
```

## Step-by-Step Diagnostic Process

### Step 1: Verify Service Status

```bash
# Check MongoDB container
docker compose -p localai-data ps mongodb

# Expected output: Status should be "Up" or "Up (healthy)"
```

### Step 2: Test Direct Connection

```bash
# Test from MongoDB container itself
docker exec mongodb mongosh --eval "db.adminCommand('ping')"

# Expected output: { ok: 1 }
```

### Step 3: Test Network Connectivity

```bash
# Test from Lambda server container
docker exec lambda-server ping -c 2 mongodb

# Expected output: Should show successful ping responses
```

### Step 4: Test Connection with Authentication

```bash
# Run connection test script
python sample/data/test_mongodb_connection.py

# Expected output: All tests should pass
```

### Step 5: Test Health Endpoint

```bash
# Test Lambda server health endpoint
python sample/data/test_mongodb_health.py

# Or
curl http://localhost:8000/health/mongodb

# Expected output: {"status": "healthy", "service": "mongodb"}
```

## Troubleshooting Workflow

```
1. Is MongoDB container running?
   ├─ No → Start with: docker compose -p localai-data up -d mongodb
   └─ Yes → Continue

2. Can MongoDB respond to ping?
   ├─ No → Check logs: docker compose -p localai-data logs mongodb
   └─ Yes → Continue

3. Can Lambda server reach MongoDB?
   ├─ No → Check network: docker network inspect ai-network
   └─ Yes → Continue

4. Is connection string correct?
   ├─ No → Verify MONGODB_URI in .env and docker-compose.yml
   └─ Yes → Continue

5. Are credentials correct?
   ├─ No → Verify MONGODB_ROOT_USERNAME and MONGODB_ROOT_PASSWORD
   └─ Yes → Check MongoDB logs for detailed errors
```

## Advanced Diagnostics

### Check MongoDB Replica Set Status

```bash
docker exec mongodb mongosh --eval "rs.status()"
```

### Check MongoDB Users

```bash
docker exec mongodb mongosh -u admin -p admin123 --authenticationDatabase admin --eval "db.getUsers()"
```

### Check Connection String from Lambda Server

```bash
docker exec lambda-server env | grep MONGODB
```

### Monitor MongoDB Logs in Real-Time

```bash
docker compose -p localai-data logs -f mongodb
```

### Test Connection with Python

```python
import asyncio
from pymongo import AsyncMongoClient

async def test():
    uri = "mongodb://admin:admin123@mongodb:27017/?directConnection=true&authSource=admin"
    client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        result = await client.admin.command("ping")
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()

asyncio.run(test())
```

## Prevention

### Best Practices

1. **Always use `MONGODB_URI` environment variable** (not `MONGODB_URL`)
2. **Include authentication in connection string** (don't rely on defaults)
3. **Use `directConnection=true` for single-node setups**
4. **Include `authSource=admin` for authentication**
5. **Test connections after configuration changes**

### Configuration Pattern

All projects should use the global settings pattern:

```python
from server.config import settings as global_settings

# Use global settings for consistency
mongodb_uri = global_settings.mongodb_uri
mongodb_database = global_settings.mongodb_database
```

## Related Documentation

- [Data Stack AGENTS.md](../01-data/AGENTS.md) - MongoDB architecture details
- [Lambda Stack AGENTS.md](../04-lambda/AGENTS.md) - MongoDB connection patterns
- [Sample Test Scripts](../sample/data/) - Connection test utilities

## Getting Help

If issues persist after following this guide:

1. Collect diagnostic information:
   ```bash
   # Container status
   docker compose -p localai-data ps mongodb

   # Recent logs
   docker compose -p localai-data logs --tail=100 mongodb

   # Network info
   docker network inspect ai-network

   # Connection test output
   python sample/data/test_mongodb_connection.py
   ```

2. Check for known issues in [KNOWN_ISSUES.md](./KNOWN_ISSUES.md)

3. Review Lambda server logs:
   ```bash
   docker compose -p localai-lambda logs --tail=100 lambda-server | grep -i mongo
   ```
