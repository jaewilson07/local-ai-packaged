# n8n Ollama Integration Setup

This guide explains how to configure n8n to access Ollama for LLM, chat, and embedding nodes.

## Quick Setup

### Default Configuration (Docker)

When both n8n and Ollama run in Docker containers on the `ai-network`:

1. **Access n8n UI**: Navigate to `http://localhost:5678`
2. **Create Credential**: Settings → Credentials → Add Credential → Select "Ollama"
3. **Configure**:
   - **Base URL**: `http://ollama:11434`
   - **API Key**: Leave empty (not needed for local Ollama)
4. **Save**: Name it "Ollama account" (or your preferred name)

### Mac Users (Local Ollama)

If Ollama runs locally on your Mac (not in Docker):

1. **Access n8n UI**: Navigate to `http://localhost:5678`
2. **Create Credential**: Settings → Credentials → Add Credential → Select "Ollama"
3. **Configure**:
   - **Base URL**: `http://host.docker.internal:11434`
   - **API Key**: Leave empty
4. **Save**: Name it "Local Ollama service"

## Using Ollama in Workflows

### Available Nodes

- **Chat Ollama** (`@n8n/n8n-nodes-langchain.lmChatOllama`) - For conversational agents
- **Ollama** (`@n8n/n8n-nodes-langchain.lmOllama`) - For LLM completions
- **Embeddings Ollama** (`@n8n/n8n-nodes-langchain.embeddingsOllama`) - For text embeddings

### Configuration Steps

1. Add the desired Ollama node to your workflow
2. Select your Ollama credential from the dropdown
3. Choose the model (e.g., `qwen2.5:7b-instruct-q4_K_M`, `llama3.1:latest`)
4. Configure node-specific options (temperature, top-k, etc.)

## Available Models

Models are pulled automatically when the Ollama service starts. Common models include:

- **Chat Models**: `qwen2.5:7b-instruct-q4_K_M`, `llama3.1:latest`, `llama3.2:latest`
- **Embedding Models**: `qwen3-embedding:4b`

To see all available models, check the Ollama service logs or use:
```bash
docker exec ollama ollama list
```

## Troubleshooting

### Connection Issues

**Problem**: n8n can't connect to Ollama

**Solutions**:
1. Verify both containers are running:
   ```bash
   docker ps | grep -E "n8n|ollama"
   ```

2. Test network connectivity from n8n container:
   ```bash
   docker exec n8n ping -c 2 ollama
   ```

3. Verify Ollama API is accessible:
   ```bash
   docker exec n8n curl -f http://ollama:11434/api/tags
   ```

4. Check Ollama container logs:
   ```bash
   docker logs ollama
   ```

### Credential Issues

**Problem**: Credential not appearing in node dropdown

**Solutions**:
1. Ensure credential is saved and not in draft state
2. Refresh the node configuration
3. Verify credential type matches node requirement (all Ollama nodes use "Ollama" credential type)

### Model Not Found

**Problem**: Selected model doesn't exist

**Solutions**:
1. Pull the model in Ollama:
   ```bash
   docker exec ollama ollama pull <model-name>
   ```

2. Verify model is available:
   ```bash
   docker exec ollama ollama list
   ```

## Architecture Notes

- **Network**: Both services use `ai-network` (external Docker network)
- **Service Discovery**: Container names (`ollama`, `n8n`) are used as hostnames
- **Port**: Ollama exposes port `11434` internally (not mapped to host)
- **Communication**: n8n → Ollama via HTTP on port 11434

## Related Documentation

- [n8n Ollama Credentials](https://docs.n8n.io/integrations/builtin/credentials/ollama/)
- [n8n Ollama Chat Model Node](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.lmchatollama/)
- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
