# Crawl4AI RAG Sample Scripts

This directory contains sample scripts demonstrating how to use Crawl4AI RAG for web crawling and automatic ingestion into MongoDB.

## Available Scripts

### 1. `single_page_crawl_example.py`
Crawls a single web page and automatically ingests it into MongoDB RAG.

**Features:**
- Crawls individual URLs
- Extracts content as markdown
- Automatically chunks and embeds content
- Stores in MongoDB with vector indexes

**Usage:**
```bash
# Requires server environment (MongoDB, environment variables)
python sample/crawl4ai_rag/single_page_crawl_example.py

# Or use REST API (if server is running)
curl -X POST http://localhost:8000/api/v1/crawl/single \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "chunk_size": 1000, "chunk_overlap": 200}'
```

**Prerequisites:**
- MongoDB running
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, EMBEDDING_BASE_URL, etc.)
- Lambda server running (for REST API)

### 2. `deep_crawl_example.py`
Performs a deep recursive crawl of a website, following internal links up to a specified depth.

**Features:**
- Recursive crawling following internal links
- Configurable depth (default: 3 levels)
- Domain and subdomain filtering
- Concurrent crawling (up to 10 pages simultaneously)
- Automatic ingestion of all discovered pages

**Usage:**
```bash
# Requires server environment
python sample/crawl4ai_rag/deep_crawl_example.py

# Or use REST API
curl -X POST http://localhost:8000/api/v1/crawl/deep \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_depth": 3,
    "chunk_size": 1000,
    "chunk_overlap": 200
  }'
```

**Configuration:**
- `max_depth`: Maximum crawl depth (1-10, default: 3)
- `allowed_domains`: List of allowed domains for exact matching
- `allowed_subdomains`: List of allowed subdomain prefixes
- `max_concurrent`: Maximum concurrent browser sessions (default: 10)

### 3. `adaptive_crawl_example.py`
Demonstrates adaptive crawling strategies that adjust parameters based on site characteristics.

**Features:**
- Shallow crawl to assess site structure
- Dynamic depth adjustment based on site size
- Domain filtering for focused crawling
- Adaptive chunk sizes based on content type

**Usage:**
```bash
# Requires server environment
python sample/crawl4ai_rag/adaptive_crawl_example.py
```

### 4. `crawl_full_pipeline.py` (NEW - Comprehensive Test)
**Full pipeline test validating all crawl functionality including download, MongoDB ingestion, and Graphiti extraction.**

**Tests:**
1. **Download without MongoDB** (MCP tools)
   - `download_page_markdown` - Single page download
   - `download_website_markdown` - Deep crawl download

2. **Crawl with MongoDB RAG ingestion**
   - REST API `/api/v1/crawl/single`
   - Verifies chunks are created

3. **Graphiti knowledge graph extraction**
   - Verifies facts are extracted to Neo4j
   - Tests `/api/v1/graphiti/search` endpoint

4. **Authentication support**
   - Tests cookies and headers parameters

**Usage:**
```bash
# Run full pipeline test (requires Lambda server)
python sample/crawl4ai_rag/crawl_full_pipeline.py
```

**Output:**
- Validates all crawl operations
- Reports success/failure for each test
- Returns exit code 0 (all passed) or 1 (failures)

### 5. `extract_and_crawl.py`
Authenticated deep crawl using BrowserProfiler for identity-based crawling.

**Features:**
- Creates browser profile for authenticated sessions
- Opens headed browser for login
- Saves session state for headless crawling
- Downloads pages as markdown files (no MongoDB)

## Standalone Crawl4AI Tests

For testing Crawl4AI without the full server setup, see:
- `sample/capability/test_crawl_bluesmuse.py` - Basic crawl4ai test (no server required)
- `sample/capability/deep_crawl_bluesmuse.py` - Deep crawl test (requires server)

## Testing Results

✅ **Crawl4AI Installation Verified:**
- Crawl4AI package is installed and importable
- Basic crawl test (`test_crawl_bluesmuse.py`) completed successfully
- Successfully crawled https://www.bluesmuse.dance/ and extracted:
  - Markdown content (1799 characters)
  - Metadata (title, description, Open Graph tags)
  - Internal links (3 found)

## Prerequisites

### For Standalone Tests
- Python 3.10+
- Crawl4AI installed: `pip install crawl4ai`
- Playwright browsers installed: `crawl4ai-setup`

### For RAG Integration Tests
- All standalone prerequisites
- MongoDB running (01-data stack)
- Lambda server running (04-lambda stack)
- Environment variables configured:
  - `MONGODB_URI`
  - `MONGODB_DATABASE`
  - `LLM_BASE_URL`
  - `EMBEDDING_MODEL`
  - `EMBEDDING_BASE_URL`

## Running Tests

### Quick Test (No Server Required)
```bash
# Test basic crawl4ai functionality
python sample/capability/test_crawl_bluesmuse.py
```

### Full RAG Integration Test (Server Required)
```bash
# Ensure Lambda server is running
docker compose -p localai-lambda ps

# Test via REST API
curl -X POST http://localhost:8000/api/v1/crawl/single \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.bluesmuse.dance/", "chunk_size": 1000, "chunk_overlap": 200}'
```

## Troubleshooting

### Playwright Browsers Not Found
```bash
# Install Playwright browsers
crawl4ai-setup

# Or manually
python -m playwright install --with-deps chromium
```

### Server Not Running
```bash
# Start Lambda stack
python start_services.py --stack lambda

# Check server status
curl http://localhost:8000/health
```

### Environment Variables Missing
Ensure `.env` file has required variables:
- `MONGODB_URI=mongodb://admin:admin123@mongodb:27017/?directConnection=true`
- `MONGODB_DATABASE=rag_db`
- `LLM_BASE_URL=http://ollama:11434/v1`
- `EMBEDDING_MODEL=qwen3-embedding:4b`

## Documentation

- [Crawl4AI Official Docs](https://docs.crawl4ai.com/)
- [Crawl4AI RAG Project](../../04-lambda/src/workflows/ingestion/crawl4ai_rag/AGENTS.md)
- [RAG Functionality](../../04-lambda/docs/RAG_FUNCTIONALITY.md)
