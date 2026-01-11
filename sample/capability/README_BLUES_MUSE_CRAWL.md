# Blues Muse Crawl & RAG Validation

This document describes how to crawl the Blues Muse website and validate MongoDB RAG ingestion.

## Scripts Created

1. **`crawl_bluesmuse_rag.py`** - REST API-based crawler
   - Uses HTTP requests to `/api/v1/crawl/single` and `/api/v1/crawl/deep`
   - Validates ingestion via `/api/v1/rag/search`
   - Requires Lambda server to be running

2. **`crawl_bluesmuse_rag_direct.py`** - Direct Python imports
   - Uses direct Python imports (bypasses REST API)
   - Requires proper environment variables
   - Can run outside Docker if env vars are set

## Usage

### Option 1: REST API (Recommended)

```bash
# 1. Ensure Lambda server is running
docker ps | grep lambda-server

# 2. Single page crawl
curl -X POST http://localhost:8000/api/v1/crawl/single \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.bluesmuse.dance/",
    "chunk_size": 1000,
    "chunk_overlap": 200
  }'

# 3. Deep crawl (depth 2)
curl -X POST http://localhost:8000/api/v1/crawl/deep \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.bluesmuse.dance/",
    "max_depth": 2,
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "allowed_domains": ["bluesmuse.dance", "www.bluesmuse.dance"]
  }'

# 4. Validate MongoDB RAG ingestion
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Blues Muse",
    "search_type": "hybrid",
    "match_count": 10
  }'
```

### Option 2: Using Python Script

```bash
# Run the REST API-based script
python sample/capability/crawl_bluesmuse_rag.py
```

### Option 3: Using Existing Samples

The existing sample scripts in `sample/crawl4ai_rag/` can be modified to target Blues Muse:

```bash
# Edit single_page_crawl_example.py to use Blues Muse URL
# Then run inside Docker container (if environment is configured)
```

## Expected Results

### Single Page Crawl
- **Pages crawled**: 1
- **Chunks created**: ~5-10 (depending on content length)
- **Document ID**: MongoDB document ID for the crawled page

### Deep Crawl (depth 2)
- **Pages crawled**: 5-20 (depending on site structure)
- **Chunks created**: 50-200 (depending on content)
- **Documents created**: Multiple document IDs

### MongoDB RAG Validation
- **Matches found**: Should return results when searching for "Blues Muse" or "blues dancing"
- **Results**: Should include chunks from crawled pages with relevance scores

## Troubleshooting

1. **Server not accessible**: Ensure Lambda server is running and healthy
   ```bash
   docker ps | grep lambda-server
   curl http://localhost:8000/health
   ```

2. **Environment variables**: Scripts need proper MongoDB, Ollama, and Neo4j configuration
   - Check `.env` file or Docker environment
   - Ensure services are running (MongoDB, Ollama, Neo4j)

3. **Timeout errors**: Deep crawls can take time
   - Increase timeout values
   - Reduce `max_depth` if needed

4. **No search results**: Wait a few seconds after crawling for ingestion to complete
   - MongoDB ingestion happens asynchronously
   - Graphiti extraction also happens asynchronously

## Notes

- Graphiti is enabled by default (`USE_GRAPHITI=true`)
- All crawled content is automatically ingested into both MongoDB RAG and Graphiti
- Deep crawls respect `allowed_domains` to stay within the target site
- Chunk size and overlap can be adjusted based on content needs
