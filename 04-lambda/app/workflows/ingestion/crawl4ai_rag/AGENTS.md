# Crawl4AI RAG Project - AGENTS.md

> **Override**: This file extends [../../../../AGENTS.md](../../../../AGENTS.md). Project-specific rules take precedence.

## Related API Documentation

- **[API Strategy](../../../../docs/API_STRATEGY.md)** - Route naming conventions, error handling, and API standards

## Overview

The Crawl4AI RAG project provides automated web crawling with immediate ingestion into the MongoDB RAG knowledge base. It crawls websites, extracts content, and automatically processes it into searchable chunks with embeddings, making web content immediately available for semantic search.

**Key Capabilities:**
- **Single Page Crawling**: Crawl individual URLs and extract structured content (markdown, text, metadata)
- **Deep Crawling**: Recursively crawl websites following internal links up to specified depth
- **Automatic Ingestion**: Crawled content is automatically chunked, embedded, and stored in MongoDB RAG
- **Markdown Download**: Download pages as markdown files without MongoDB ingestion (new MCP tools)
- **Authentication Support**: Crawl authenticated pages using cookies and custom headers
- **Domain Filtering**: Control crawling scope with allowed domains and subdomains
- **Metadata Extraction**: Extracts page titles, descriptions, images, and links automatically
- **Chunking Configuration**: Configurable chunk size and overlap for optimal retrieval
- **User-Scoped Data**: All crawled content is tagged with `user_email` for RLS filtering

**Use Cases:**
- Documentation Ingestion: Crawl and ingest technical documentation for Q&A
- Website Knowledge Base: Build searchable knowledge bases from website content
- Content Discovery: Automatically discover and index related pages from a starting URL
- Research Automation: Crawl research papers, articles, or documentation sites
- Real-time Web Content: Make web content immediately searchable via RAG

## Component Identity

- **Project**: `crawl4ai_rag`
- **Location**: `04-lambda/src/workflows/ingestion/crawl4ai_rag/`
- **Purpose**: Web crawling and automatic ingestion into MongoDB RAG knowledge base
- **Dependencies**: MongoDB (01-data), Crawl4AI library, Ollama (02-compute for embeddings)
- **Agent**: `crawl4ai_agent` (Pydantic AI agent with StateDeps)

## Architecture & Patterns

### System Architecture

```mermaid
graph TB
    subgraph "API Layer"
        REST[ REST API<br/>/api/v1/crawl/* ]
        MCP[ MCP Tools<br/>crawl_single_page, crawl_deep<br/>download_page_markdown<br/>download_website_markdown ]
    end

    subgraph "Agent Layer"
        AGENT[ crawl4ai_agent<br/>Pydantic AI Agent ]
        TOOLS[ Agent Tools<br/>crawl_and_ingest_single_page<br/>crawl_and_ingest_deep ]
    end

    subgraph "Crawling Service"
        CRAWLER[ Crawler Service<br/>crawl_single_page<br/>crawl_deep ]
        CRAWL4AI[ Crawl4AI Library<br/>AsyncWebCrawler ]
    end

    subgraph "Ingestion Layer"
        INGESTER[ CrawledContentIngester<br/>Ingestion Adapter ]
        CHUNK[ Chunking<br/>Text Splitting ]
        EMBED[ Embedding<br/>Vector Generation ]
    end

    subgraph "Dependencies"
        DEPS[ Crawl4AIDependencies<br/>Crawler, MongoDB Client ]
        MONGO[ MongoDB<br/>RAG Storage ]
    end

    subgraph "External Services"
        WEB[ Web Pages<br/>HTTP/HTTPS ]
        OLLAMA[ Ollama<br/>Embeddings ]
    end

    REST --> AGENT
    MCP --> AGENT
    AGENT --> TOOLS
    TOOLS --> CRAWLER
    TOOLS --> INGESTER
    CRAWLER --> CRAWL4AI
    CRAWL4AI --> WEB
    INGESTER --> CHUNK
    INGESTER --> EMBED
    INGESTER --> DEPS
    EMBED --> OLLAMA
    DEPS --> MONGO
    CHUNK --> MONGO

    style AGENT fill:#e1f5ff
    style CRAWLER fill:#fff4e1
    style INGESTER fill:#e1ffe1
    style DEPS fill:#f0f0f0
    style MONGO fill:#ffe1e1
    style WEB fill:#ffe1e1
```

### Crawl & Ingest Flow

```mermaid
sequenceDiagram
    participant Client
    participant Agent as crawl4ai_agent
    participant Tool as crawl_and_ingest_single_page
    participant Crawler as crawl_single_page
    participant Crawl4AI as AsyncWebCrawler
    participant Ingester as CrawledContentIngester
    participant Chunk as Chunking
    participant Embed as Embedding
    participant MongoDB

    Client->>Agent: POST /crawl/single with URL
    Agent->>Tool: crawl_and_ingest_single_page(url)
    Tool->>Crawler: crawl_single_page(url)
    Crawler->>Crawl4AI: Run crawler with config
    Crawl4AI->>Crawl4AI: Fetch page, extract content
    Crawl4AI-->>Crawler: CrawledPage (markdown, metadata)
    Crawler-->>Tool: CrawledPage result

    Tool->>Ingester: ingest_crawled_content(crawled_page)
    Ingester->>Chunk: Split into chunks
    Chunk-->>Ingester: Document chunks

    loop For each chunk
        Ingester->>Embed: Generate embedding
        Embed->>Embed: Call Ollama API
        Embed-->>Ingester: Vector embedding
        Ingester->>MongoDB: Store chunk + embedding
    end

    Ingester-->>Tool: Ingestion result
    Tool-->>Agent: Crawl + ingest summary
    Agent-->>Client: Success with page/chunk counts
```

### Deep Crawl Flow

```mermaid
sequenceDiagram
    participant Agent as crawl4ai_agent
    participant Tool as crawl_and_ingest_deep
    participant Crawler as crawl_deep
    participant Crawl4AI as AsyncWebCrawler
    participant Ingester as CrawledContentIngester
    participant MongoDB

    Agent->>Tool: crawl_and_ingest_deep(url, max_depth=3)
    Tool->>Crawler: crawl_deep(url, max_depth, allowed_domains)

    Crawler->>Crawler: Initialize visited set, queue
    Crawler->>Crawl4AI: Crawl starting page
    Crawl4AI-->>Crawler: Page + links

    loop For each depth level
        loop For each URL in queue
            Crawler->>Crawler: Check domain/subdomain filters
            Crawler->>Crawl4AI: Crawl URL
            Crawl4AI-->>Crawler: Page + links
            Crawler->>Crawler: Add new links to queue
        end
    end

    Crawler-->>Tool: List of CrawledPage objects

    loop For each crawled page
        Tool->>Ingester: ingest_crawled_content(page)
        Ingester->>MongoDB: Store chunks + embeddings
    end

    Tool-->>Agent: Summary (pages crawled, chunks created)
```

### File Organization

```
crawl4ai_rag/
├── AGENTS.md             # This file
├── __init__.py           # Package exports
├── config.py             # Project-specific configuration
├── router.py             # FastAPI REST API endpoints (/api/v1/crawl/*)
├── tools.py              # Core tools (crawl_and_ingest_single_page, crawl_and_ingest_deep)
├── workflow.py           # Workflow orchestration
├── ai/                   # Pydantic AI agent components
│   ├── agent.py          # Main Crawl4AI agent definition
│   └── dependencies.py   # Crawl4AIDependencies (Crawler, config)
├── schemas/              # Request/response models
│   └── __init__.py       # CrawlSinglePageRequest, CrawlDeepRequest, CrawlResponse
├── services/             # Business logic services
│   ├── crawler.py        # Core crawling logic (crawl_single_page, crawl_deep)
│   ├── downloader.py     # Markdown file downloading utilities
│   ├── pagination.py     # Pagination handling for crawled content
│   └── extractors/       # Content extraction utilities
│       ├── base.py       # Base extractor class
│       └── circle.py     # Circle.so-specific extractor
├── ingestion/            # Ingestion adapter for crawled content
│   └── adapter.py        # CrawledContentIngester (deprecated - use ContentIngestionService)
└── utils/                # Utility functions
    ├── filename.py       # Filename sanitization
    └── html_converter.py # HTML to markdown conversion
```

### Key Patterns

**DO's:**
- ✅ **Use Crawl4AIDependencies**: Always initialize and cleanup in try/finally blocks
  ```python
  deps = Crawl4AIDependencies()
  await deps.initialize()
  try:
      # Use deps.crawler, deps.mongo_client
  finally:
      await deps.cleanup()
  ```

- ✅ **Crawl and Ingest**: Use `crawl_and_ingest_single_page` or `crawl_and_ingest_deep` for combined operations
  ```python
  # In tools.py
  result = await crawl_and_ingest_single_page(
      ctx, url, chunk_size=1000, chunk_overlap=200
  )
  ```

- ✅ **Use Crawler Service**: Use `services/crawler.py` for core crawling logic
  ```python
  from server.projects.crawl4ai_rag.services.crawler import crawl_single_page, crawl_deep
  ```

- ✅ **Configure Chunking**: Always specify chunk_size and chunk_overlap for ingestion
  ```python
  result = await crawl_and_ingest_single_page(
      ctx, url, chunk_size=1000, chunk_overlap=200
  )
  ```

**DON'Ts:**
- ❌ **Don't skip ingestion**: Always ingest crawled content into MongoDB RAG
- ❌ **Don't hardcode chunk sizes**: Use configurable chunk_size and chunk_overlap
- ❌ **Don't bypass crawler service**: Use services/crawler.py, not direct Crawl4AI calls
- ❌ **Don't ignore crawl errors**: Log errors but continue with successful pages

## Key Files & JIT Search

**Touch Points:**
- `agent.py:25` - `crawl4ai_agent` definition with tools
- `dependencies.py:14` - `Crawl4AIDependencies` class
- `tools.py:16` - `crawl_and_ingest_single_page` function
- `tools.py:85` - `crawl_and_ingest_deep` function
- `services/crawler.py:12` - Core crawling logic

**Search Hints:**
```bash
# Find Crawl4AI agent tools
rg -n "@crawl4ai_agent\.tool" 04-lambda/src/crawl4ai_rag/

# Find crawling operations
rg -n "crawl_(single_page|deep)" 04-lambda/src/crawl4ai_rag/

# Find ingestion logic
rg -n "CrawledContentIngester|ingest_crawled" 04-lambda/src/crawl4ai_rag/
```

## Testing & Validation

**Manual Testing:**

For **local development** with `DEV_MODE=true`:
```bash
# Crawl single page (with user email header for RLS)
curl -X POST http://localhost:8000/api/v1/crawl/single \
  -H "Content-Type: application/json" \
  -H "X-User-Email: your-email@example.com" \
  -d '{"url": "https://example.com", "chunk_size": 1000, "chunk_overlap": 200}'

# Deep crawl
curl -X POST http://localhost:8000/api/v1/crawl/deep \
  -H "Content-Type: application/json" \
  -H "X-User-Email: your-email@example.com" \
  -d '{"url": "https://example.com", "max_depth": 2, "chunk_size": 1000}'
```

For **production** (requires Cloudflare Access JWT):
```bash
# Get JWT from browser's Cf-Access-Jwt-Assertion header
curl -X POST http://lambda-server:8000/api/v1/crawl/single \
  -H "Content-Type: application/json" \
  -H "Cf-Access-Jwt-Assertion: YOUR_JWT_TOKEN" \
  -d '{"url": "https://example.com", "chunk_size": 1000, "chunk_overlap": 200}'
```

**Automated Validation:**
```bash
# Run validation tests
cd 04-lambda && python -m pytest tests/test_crawl4ai_validation.py -v
```

**Validation Strategy:**
- Verify crawled pages: Check that pages are successfully crawled
- Validate ingestion: Verify content is ingested into MongoDB RAG (`rag_db.documents`, `rag_db.chunks`)
- Test chunking: Verify chunks are created with correct size and overlap
- Check user tagging: Verify `user_email` is properly set on documents and chunks
- Check error handling: Test with invalid URLs, network errors
- Test authentication: Verify cookies and headers work for protected pages
- Test file saving: Verify markdown files are saved correctly

## MCP Tools Reference

### Ingestion Tools (with MongoDB)

**`crawl_single_page`** - Crawl and ingest a single page
- Parameters: `url`, `chunk_size`, `chunk_overlap`, `cookies`, `headers`
- Returns: Success status, pages crawled, chunks created, document IDs

**`crawl_deep`** - Deep crawl and ingest multiple pages
- Parameters: `url`, `max_depth`, `allowed_domains`, `allowed_subdomains`, `chunk_size`, `chunk_overlap`, `cookies`, `headers`
- Returns: Success status, pages crawled, chunks created, document IDs

### Download Tools (without MongoDB)

**`download_page_markdown`** - Download a single page as markdown
- Parameters: `url`, `save_to_file`, `output_path`, `cookies`, `headers`
- Returns: Markdown content, metadata, optional file path

**`download_website_markdown`** - Deep crawl and download multiple pages as markdown
- Parameters: `url`, `max_depth`, `allowed_domains`, `allowed_subdomains`, `save_to_files`, `output_directory`, `cookies`, `headers`
- Returns: Array of pages with markdown content, metadata, optional file paths

## Authentication Guide

### When to Use Authentication

Use authentication when crawling:
- Pages behind login (forums, documentation portals, internal sites)
- APIs that require tokens
- Sites with session-based authentication

### Cookie Formats

**String format** (recommended for browser-extracted cookies):
```
"sessionid=abc123; csrftoken=xyz789; auth_token=mytoken"
```

**Dict format** (programmatic use):
```json
{"sessionid": "abc123", "csrftoken": "xyz789"}
```

### Header Format

```json
{"Authorization": "Bearer eyJhbGciOiJIUzI1NiIs...", "X-Custom-Header": "value"}
```

### Extracting Cookies from Browser

1. **Chrome DevTools**:
   - Open DevTools (F12) → Application → Cookies
   - Copy name and value for each cookie you need
   - Format as: `"name1=value1; name2=value2"`

2. **Firefox DevTools**:
   - Open DevTools (F12) → Storage → Cookies
   - Copy cookies in the same format

3. **Using Browser Extension**:
   - Use "EditThisCookie" or similar extension
   - Export cookies in JSON format
   - Convert to string or dict format

### Example: Authenticated Crawl

```bash
# Via MCP tool
curl -X POST http://lambda-server:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "crawl_single_page",
    "arguments": {
      "url": "https://members.example.com/dashboard",
      "cookies": "sessionid=abc123; csrftoken=xyz",
      "headers": {"Authorization": "Bearer mytoken"}
    }
  }'

# Via REST API
curl -X POST http://lambda-server:8000/api/v1/crawl/single \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://members.example.com/dashboard",
    "cookies": "sessionid=abc123; csrftoken=xyz",
    "headers": {"Authorization": "Bearer mytoken"},
    "chunk_size": 1000
  }'
```

### Example: Download Without Ingestion

```bash
# Download single page as markdown
curl -X POST http://lambda-server:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "download_page_markdown",
    "arguments": {
      "url": "https://example.com/docs/intro",
      "save_to_file": true,
      "output_path": "/tmp/docs"
    }
  }'

# Download entire docs site
curl -X POST http://lambda-server:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "download_website_markdown",
    "arguments": {
      "url": "https://docs.example.com",
      "max_depth": 3,
      "allowed_domains": ["docs.example.com"],
      "save_to_files": true,
      "output_directory": "/tmp/docs"
    }
  }'
```

## Domain Dictionary

- **Crawl4AI**: Web crawling library for extracting content from websites
- **Deep Crawl**: Recursive crawling following internal links up to specified depth
- **Single Page Crawl**: Crawling a single URL without following links
- **Ingestion**: Process of chunking, embedding, and storing crawled content in MongoDB RAG
- **Download Tools**: MCP tools that return markdown content without MongoDB ingestion

## Integration Points

- **MongoDB RAG**: Stores crawled content as searchable documents (`mongodb:27017`)
- **Ollama**: Generates embeddings for crawled content (`ollama:11434`)
- **REST API**: Endpoints in `server/api/crawl4ai_rag.py`
- **MCP Tools**: Exposed via `src/mcp_server/server.py`

## Configuration

**Required Environment Variables:**
- `MONGODB_URI` - MongoDB connection string
- `MONGODB_DATABASE` - Database name
- `LLM_BASE_URL` - LLM API base URL (default: http://ollama:11434/v1)
- `EMBEDDING_MODEL` - Embedding model (default: qwen3-embedding:4b)
- `USE_GRAPHITI` - Enable Graphiti ingestion (default: true, enabled by default for crawl4ai RAG flow)
- `NEO4J_URI` - Neo4j connection URI (default: bolt://neo4j:7687, required if Graphiti enabled)
- `NEO4J_USER` - Neo4j username (default: neo4j)
- `NEO4J_PASSWORD` - Neo4j password (required if Graphiti enabled)

**Crawl Configuration:**
- `chunk_size`: Chunk size for document splitting (default: 1000)
- `chunk_overlap`: Chunk overlap size (default: 200)
- `max_depth`: Maximum crawl depth for deep crawl (default: 3)
- `allowed_domains`: List of allowed domains for crawling
- `allowed_subdomains`: List of allowed subdomain prefixes

**Graphiti Integration:**
- Graphiti is **enabled by default** for crawl4ai RAG flow
- All crawled content is automatically ingested into Graphiti to extract entities and relationships
- Set `USE_GRAPHITI=false` to disable Graphiti ingestion
- Requires Neo4j to be running and accessible if Graphiti is enabled
