# Open WebUI Agentic Search Setup Guide

## Overview

This guide explains how to configure Open WebUI with agentic search and deep research capabilities using SearXNG. With this setup, Open WebUI will automatically search the web when needed, similar to ChatGPT's research mode.

## What is Agentic Search?

Agentic search enables the AI to:
- **Automatically decide** when to search the web based on conversation context
- **Search multiple engines** simultaneously via SearXNG metasearch
- **Synthesize results** from multiple sources into coherent responses
- **Access current information** not available in the knowledge base

## Prerequisites

- Open WebUI running and accessible
- Lambda server running with SearXNG integration
- SearXNG service running (already configured in `03-apps/docker-compose.yml`)
- MCP server configured in Open WebUI (see [MCP Integration Guide](./MCP_INTEGRATION.md))

## Configuration Steps

### Step 1: Verify SearXNG is Running

Check that SearXNG is accessible:

```bash
# Check container status
docker ps | grep searxng

# Test SearXNG directly
curl "http://searxng:8080/search?q=test&format=json"
```

### Step 2: Configure MCP Server in Open WebUI

1. **Access Admin Panel**
   - Log in to Open WebUI as an administrator
   - Navigate to **Settings** → **External Tools**

2. **Add/Verify Lambda MCP Server**
   - Ensure Lambda MCP server is configured:
     - **Type**: `MCP (Streamable HTTP)`
     - **Server URL**: `http://lambda-server:8000/mcp`
     - If using external access: `https://api.datacrew.space/mcp`

3. **Enable `web_search` Tool**
   - In the tool list, find `web_search`
   - Toggle it to **enabled**
   - The tool should appear as: "Search the web using SearXNG metasearch engine"

### Step 3: Configure Model for Automatic Tool Usage

Open WebUI automatically uses MCP tools when:
- The model supports function calling (most modern models do)
- Tools are enabled in the External Tools settings
- The conversation context suggests a search would be helpful

**No additional configuration needed** - Open WebUI handles tool selection automatically.

## How It Works

### Automatic Search Behavior

The AI will automatically use `web_search` when:
1. **Current information needed**: Questions about recent events, news, or real-time data
2. **Knowledge base lacks info**: Information not found in the RAG system
3. **User explicitly requests**: "Search for...", "Look up...", "Find information about..."
4. **Ambiguous queries**: When clarification requires current data

### Example Interactions

**User**: "What are the latest developments in AI?"

**AI Behavior**:
1. Recognizes need for current information
2. Automatically calls `web_search` tool with query: "latest developments in AI"
3. Receives ranked results from multiple search engines
4. Synthesizes findings into response with citations

**User**: "How do I configure authentication in FastAPI?"

**AI Behavior**:
1. First checks knowledge base via `search_knowledge_base`
2. If insufficient, calls `web_search` for additional examples
3. Combines knowledge base and web results

## Manual Search Triggering

You can also explicitly request web searches:

- "Search the web for [topic]"
- "Look up [query]"
- "Find current information about [subject]"
- "What's the latest on [topic]?"

## Tool Parameters

The `web_search` tool accepts:

- **query** (required): Search query string
- **result_count** (optional, default: 10): Number of results (1-20)
- **categories** (optional): Filter by category (general, news, images, etc.)
- **engines** (optional): Filter by specific search engines

## Integration with Other Tools

The `web_search` tool works alongside other MCP tools:

### Combined Workflows

1. **Research Workflow**:
   - `web_search` → Find relevant URLs
   - `crawl_single_page` → Deep dive into specific pages
   - `ingest_documents` → Save to knowledge base

2. **Knowledge Enhancement**:
   - `search_knowledge_base` → Check existing knowledge
   - `web_search` → Find current/updated information
   - Synthesize both sources

3. **Deep Research**:
   - Multiple `web_search` calls with refined queries
   - `crawl_deep` for comprehensive coverage
   - `agent_query` for conversational synthesis

## Troubleshooting

### Tool Not Appearing

1. **Check MCP Server Connection**:
   ```bash
   curl http://lambda-server:8000/mcp/tools/list | grep web_search
   ```

2. **Verify Tool is Enabled**:
   - Open WebUI Admin Panel → Settings → External Tools
   - Ensure `web_search` is toggled on

3. **Check Lambda Server Logs**:
   ```bash
   docker logs lambda-server | grep web_search
   ```

### Search Not Working

1. **Verify SearXNG is Running**:
   ```bash
   docker ps | grep searxng
   curl http://searxng:8080/search?q=test&format=json
   ```

2. **Check Network Connectivity**:
   ```bash
   docker exec lambda-server ping -c 1 searxng
   ```

3. **Test API Endpoint**:
   ```bash
   curl -X POST http://lambda-server:8000/api/v1/searxng/search \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "result_count": 5}'
   ```

4. **Check Lambda Server Logs**:
   ```bash
   docker logs lambda-server | grep searxng
   ```

### AI Not Using Search Automatically

1. **Model Support**: Ensure your model supports function calling
   - Most modern models (GPT-4, Claude, Llama 3.1+, etc.) support it
   - Check model documentation

2. **Prompt Engineering**: The AI decides based on context
   - Be explicit: "Search for current information about..."
   - Ask about recent events or real-time data

3. **Tool Availability**: Verify tools are enabled and accessible
   - Check Open WebUI External Tools settings
   - Verify MCP server is connected

## Best Practices

### When to Use Web Search

✅ **Good Use Cases**:
- Current events and news
- Real-time data (stock prices, weather, etc.)
- Recent developments in technology
- Information not in knowledge base
- Verification of facts

❌ **Avoid For**:
- Static documentation (use knowledge base)
- Code examples (use `search_code_examples`)
- Internal knowledge (use `search_knowledge_base`)

### Optimizing Search Queries

- **Be specific**: "latest Python 3.12 features" vs "Python"
- **Use keywords**: Include important terms
- **Refine iteratively**: Start broad, then narrow down
- **Combine sources**: Use web search + knowledge base together

### Performance Tips

- **Result count**: Use 5-10 results for quick answers
- **Cache important results**: Use `crawl_single_page` to save to knowledge base
- **Batch related queries**: Group related searches together

## Advanced Configuration

### Environment Variables

Optional configuration in `.env`:

```bash
# SearXNG URL (default: http://searxng:8080)
SEARXNG_URL=http://searxng:8080
```

### Custom Search Categories

SearXNG supports category filtering:
- `general` - General web search
- `news` - News articles
- `images` - Image search
- `videos` - Video search
- `maps` - Map/location search

Example:
```
"Search for recent AI news" → web_search(query="recent AI news", categories="news")
```

## API Reference

### REST API Endpoint

**POST** `/api/v1/searxng/search`

**Request**:
```json
{
  "query": "latest AI developments",
  "result_count": 10,
  "categories": "general",
  "engines": ["google", "bing"]
}
```

**Response**:
```json
{
  "query": "latest AI developments",
  "success": true,
  "count": 10,
  "results": [
    {
      "title": "Article Title",
      "url": "https://example.com/article",
      "content": "Article snippet...",
      "engine": "google",
      "score": 0.95
    }
  ]
}
```

### MCP Tool

**Tool Name**: `web_search`

**Parameters**:
- `query` (str, required): Search query
- `result_count` (int, optional): Number of results (1-20, default: 10)
- `categories` (str, optional): Category filter
- `engines` (List[str], optional): Engine filter

## Related Documentation

- [MCP Integration Guide](./MCP_INTEGRATION.md) - Setting up MCP tools
- [Conversation Memory](./CONVERSATION_MEMORY.md) - Using conversation features
- [Implementation Summary](./IMPLEMENTATION_SUMMARY.md) - Technical details

## Support

For issues or questions:
1. Check logs: `docker logs lambda-server`
2. Verify services: `docker ps`
3. Test endpoints: Use curl commands above
4. Review MCP integration: See [MCP Integration Guide](./MCP_INTEGRATION.md)

