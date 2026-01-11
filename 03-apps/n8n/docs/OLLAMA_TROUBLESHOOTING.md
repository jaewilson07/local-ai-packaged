# Ollama Connection Troubleshooting

## Quick Answer: No API Key Required

**Ollama does NOT require an API key** for local use. Leave the API Key field **empty** in n8n credentials.

## Common Issues and Solutions

### Issue 1: "Unable to Connect" Error

**Most Common Cause**: Wrong Base URL format

**Correct URLs**:
- ✅ **Docker (default)**: `http://ollama:11434`
- ✅ **Local Mac Ollama**: `http://host.docker.internal:11434`
- ❌ **Wrong**: `http://localhost:11434` (won't work from Docker container)
- ❌ **Wrong**: `https://ollama:11434` (Ollama uses HTTP, not HTTPS)

**Steps to Fix**:
1. Go to n8n UI → Settings → Credentials
2. Edit your Ollama credential
3. Verify Base URL is exactly: `http://ollama:11434` (no trailing slash)
4. Ensure API Key field is **empty**
5. Save and test again

### Issue 2: Verify Network Connectivity

Test if n8n can reach Ollama:

```bash
# Test from n8n container
docker exec n8n wget -q -O- http://ollama:11434/api/tags

# Should return JSON with models list
```

If this fails, check:
- Both containers are running: `docker ps | grep -E "n8n|ollama"`
- Both on same network: `docker network inspect ai-network | grep -E "n8n|ollama"`

### Issue 3: Check Container Status

```bash
# Check if containers are running
docker ps --filter "name=ollama" --format "{{.Names}} {{.Status}}"
docker ps --filter "name=n8n" --format "{{.Names}} {{.Status}}"
```

If Ollama shows "unhealthy" but is still running, it might still work. Check logs:
```bash
docker logs ollama --tail 50
```

### Issue 4: URL Format Checklist

When configuring Ollama credential in n8n, ensure:

- [ ] Base URL starts with `http://` (not `https://`)
- [ ] Uses container name `ollama` (not `localhost`)
- [ ] Includes port `:11434`
- [ ] No trailing slash: `http://ollama:11434` ✅ (not `http://ollama:11434/` ❌)
- [ ] API Key field is **empty** (unless using authenticated proxy)

### Issue 5: Test Connection Manually

From your host machine, test Ollama directly:

```bash
# Test Ollama API
curl http://localhost:11434/api/tags

# Should return JSON with available models
```

If this works but n8n doesn't, the issue is the URL in n8n credentials.

## Step-by-Step Fix

1. **Verify containers are running**:
   ```bash
   docker ps | grep -E "n8n|ollama"
   ```

2. **Test network connectivity**:
   ```bash
   docker exec n8n ping -c 2 ollama
   ```

3. **Test API access**:
   ```bash
   docker exec n8n wget -q -O- http://ollama:11434/api/tags
   ```

4. **Fix n8n credential**:
   - Go to n8n UI → Settings → Credentials
   - Find your Ollama credential
   - Set Base URL to: `http://ollama:11434`
   - Leave API Key empty
   - Save

5. **Test in workflow**:
   - Add an Ollama node to a workflow
   - Select your credential
   - Try to list models or make a test request

## Still Not Working?

If you've verified all the above:

1. **Check n8n logs**:
   ```bash
   docker logs n8n --tail 100 | grep -i ollama
   ```

2. **Check Ollama logs**:
   ```bash
   docker logs ollama --tail 100
   ```

3. **Restart both services**:
   ```bash
   docker restart n8n ollama
   ```

4. **Verify network**:
   ```bash
   docker network inspect ai-network | grep -A 5 "ollama\|n8n"
   ```

## Common Mistakes

❌ **Using localhost**: `http://localhost:11434` - Won't work from Docker container  
❌ **Using HTTPS**: `https://ollama:11434` - Ollama uses HTTP  
❌ **Trailing slash**: `http://ollama:11434/` - Can cause issues  
❌ **Wrong port**: `http://ollama:8080` - Ollama uses 11434  
❌ **Adding API key**: Ollama doesn't need one for local use  

✅ **Correct**: `http://ollama:11434` with empty API key field
