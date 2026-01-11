# Deep Research Agent - Sample Scripts

This directory contains sample scripts for testing and demonstrating the Deep Research Agent.

## Available Scripts

### 1. `test_searxng_simple.py`
**Status**: ✅ Working

Tests SearXNG search integration directly without requiring the full server.

```bash
python sample/deep_research/test_searxng_simple.py
```

**What it does:**
- Connects to SearXNG at `http://localhost:8081`
- Searches for "blues muse"
- Displays top 3 results

### 2. `example_queries.py`
**Status**: ✅ Working

Displays a collection of example queries you can use with the Linear Researcher agent.

```bash
python sample/deep_research/example_queries.py
```

**What it does:**
- Lists 15 example queries organized by category
- Shows how to run queries using `run_research.py`

### 3. `run_research.py`
**Status**: ⚠️ Requires server or clean environment

Main script for running research queries through the Linear Researcher agent.

```bash
# With default query
python sample/deep_research/run_research.py

# With custom query
python sample/deep_research/run_research.py "Who is the CEO of Anthropic?"

# With verbose output
python sample/deep_research/run_research.py "What is quantum computing?" --verbose
```

**What it does:**
- Executes the full Linear Researcher workflow:
  1. Search the web
  2. Fetch top result
  3. Parse document
  4. Ingest knowledge
  5. Query knowledge base
  6. Generate answer

**Note**: This script requires either:
- The Lambda server to be running and accessible
- A clean environment without extra Settings validation errors

### 4. `test_via_api.py`
**Status**: ⚠️ Requires server to be running

Tests the agent via the Lambda server REST API.

```bash
# For local development (uses internal network, no auth required)
python sample/deep_research/test_via_api.py

# For external API access (requires JWT token)
export API_BASE_URL=https://api.datacrew.space
export CF_ACCESS_JWT=your-cloudflare-access-jwt-token
python sample/deep_research/test_via_api.py
```

**What it does:**
- Tests server connectivity
- Tests MCP tools via REST API
- Can be extended to test full agent workflow
- Automatically uses internal network URLs when running locally (no auth required)

### 5. `test_linear_researcher.py`
**Status**: ⚠️ Requires server or clean environment

Unit test script for the Linear Researcher agent.

```bash
python sample/deep_research/test_linear_researcher.py
```

## Prerequisites

### For Direct Scripts (test_searxng_simple.py, example_queries.py)
- Python 3.10+
- SearXNG running (for test_searxng_simple.py)

### For Agent Scripts (run_research.py, test_linear_researcher.py)
- Lambda server running at `http://localhost:8000`
- OR clean environment with only required variables
- MongoDB running (for knowledge storage)
- Ollama or OpenAI configured (for LLM and embeddings)
- SearXNG running (for web search)

## Environment Variables

Required environment variables (can be set in `.env` or environment):

```bash
MONGODB_URI=mongodb://localhost:27017/test
MONGODB_DATABASE=test_db
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=test-key
EMBEDDING_BASE_URL=http://localhost:11434/v1
EMBEDDING_API_KEY=test-key
SEARXNG_URL=http://localhost:8081
CLOUDFLARE_EMAIL=your-email@example.com  # For user identification
API_BASE_URL=http://lambda-server:8000     # Defaults to internal network
CF_ACCESS_JWT=your-jwt-token              # Only required for external URLs
```

**Note**: Scripts that make HTTP API calls automatically use internal network URLs (`http://lambda-server:8000`) when running locally, which bypasses Cloudflare Access authentication. For external URLs, set `API_BASE_URL` and `CF_ACCESS_JWT`.

## Testing Status

### ✅ Working
- SearXNG integration (test_searxng_simple.py)
- Example queries display (example_queries.py)

### ⚠️ Requires Server
- Full agent workflow (run_research.py)
- API-based testing (test_via_api.py)

### 🔧 Known Issues
- Settings validation errors when running scripts directly (due to extra .env variables)
- Server startup issues (asyncpg dependency missing)

## Quick Start

1. **Test SearXNG** (works immediately):
   ```bash
   python sample/deep_research/test_searxng_simple.py
   ```

2. **See example queries**:
   ```bash
   python sample/deep_research/example_queries.py
   ```

3. **Run full research** (requires server):
   ```bash
   # Start server first
   python start_services.py --stack lambda

   # Then run research
   python sample/deep_research/run_research.py "Who is the CEO of Anthropic?"
   ```

## Example Queries

Here are some example queries you can try:

- "Who is the CEO of Anthropic?"
- "What is the latest news about LK-99 superconductor?"
- "Explain how quantum computing works"
- "What are the main features of GPT-4?"
- "How does LangGraph work?"

See `example_queries.py` for the full list.
