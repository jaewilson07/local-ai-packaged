# MCP Function Design Best Practices

## Overview

This document outlines best practices for designing Model Context Protocol (MCP) functions in the Lambda server. MCP functions enable AI agents and coding assistants to interact with our services through a standardized protocol.

## What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI assistants to discover and call tools/functions provided by servers. It allows AI models to:

- Discover available capabilities
- Call functions with structured parameters
- Receive structured responses
- Handle errors gracefully

## Core Principles

### 1. Dual Interface Pattern

**Every REST endpoint should have a corresponding MCP tool.**

This ensures:
- Consistency between REST and MCP interfaces
- Code reuse (MCP tools call REST endpoints internally)
- Single source of truth for business logic
- Easier maintenance and testing

**Pattern:**
```python
# REST endpoint (server/api/project.py)
@router.post("/endpoint")
async def endpoint(request: RequestModel):
    """REST endpoint implementation."""
    # Business logic here
    return ResponseModel(...)

# MCP tool (server/mcp/server.py)
elif tool == "tool_name":
    from server.api.project import endpoint
    from server.projects.project.models import RequestModel
    result = await endpoint(RequestModel(**args))
    return {"content": [{"type": "text", "text": str(result.dict())}]}
```

### 2. Single Responsibility

Each MCP function should do one thing well:

✅ **Good:**
- `crawl_single_page` - Crawls one page
- `crawl_deep` - Crawls multiple pages recursively
- `search_knowledge_base` - Searches the knowledge base

❌ **Bad:**
- `crawl_and_search` - Does too much
- `do_everything` - Violates single responsibility

### 3. Stateless Operations

MCP functions should be stateless and idempotent when possible:

- No session state between calls
- Same inputs produce same outputs
- Safe to retry on failure
- No side effects beyond intended operations

**Exception:** Operations that are inherently stateful (e.g., creating resources) should clearly document this.

### 4. Clear Naming Conventions

**Function Names:**
- Use `snake_case`
- Be descriptive and action-oriented
- Start with a verb: `crawl_`, `search_`, `ingest_`, `query_`
- Avoid abbreviations unless widely understood

✅ **Good:**
- `crawl_single_page`
- `search_knowledge_base`
- `ingest_documents`

❌ **Bad:**
- `crawl1`
- `search`
- `ing`

## Function Design

### Parameter Design

**Required vs Optional:**
- Mark parameters as required only when absolutely necessary
- Provide sensible defaults for optional parameters
- Document parameter ranges and constraints

**Example:**
```python
{
    "name": "crawl_deep",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Starting URL for deep crawl"
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum crawl depth",
                "default": 3,
                "minimum": 1,
                "maximum": 10
            },
            "allowed_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of allowed domains (exact match)"
            }
        },
        "required": ["url", "max_depth"]
    }
}
```

### Type Validation

Always use proper JSON Schema types:
- `string` for text
- `integer` for numbers
- `boolean` for true/false
- `array` for lists
- `object` for nested structures

Include validation constraints:
- `minimum`/`maximum` for numbers
- `enum` for restricted values
- `pattern` for string formats (if needed)

### Default Values

Provide sensible defaults that work for most use cases:

```python
{
    "chunk_size": {
        "type": "integer",
        "description": "Chunk size for document splitting",
        "default": 1000  # Works well for most documents
    }
}
```

## Schema Design

### JSON Schema Best Practices

**Property Descriptions:**
- Always include a `description` field
- Explain what the parameter does, not just its type
- Mention constraints and valid ranges
- Provide examples when helpful

**Example:**
```python
{
    "url": {
        "type": "string",
        "description": "URL to crawl. Must be a valid HTTP/HTTPS URL."
    },
    "max_depth": {
        "type": "integer",
        "description": "Maximum crawl depth. Range: 1-10. Depth 1 = starting page only, Depth 2 = starting page + 1 level of links.",
        "minimum": 1,
        "maximum": 10,
        "default": 3
    }
}
```

### Enum Values

Use enums for restricted choices:

```python
{
    "search_type": {
        "type": "string",
        "enum": ["semantic", "text", "hybrid"],
        "description": "Type of search to perform. 'semantic' uses vector embeddings, 'text' uses keyword matching, 'hybrid' combines both.",
        "default": "hybrid"
    }
}
```

### Validation Rules

Include validation in both:
1. **JSON Schema** (for MCP client validation)
2. **Pydantic models** (for server-side validation)

This provides defense in depth and better error messages.

## Error Handling

### Granular Error Handling

MCP tools should use granular error handling to differentiate error types and provide specific, actionable error messages:

```python
from pydantic import ValidationError
from fastapi import HTTPException
from pymongo.errors import ConnectionFailure, OperationFailure

try:
    result = await endpoint(RequestModel(**args))
    return {"content": [{"type": "json", "text": json.dumps(result.dict(), indent=2)}]}
except ValidationError as e:
    # Pydantic validation errors - provide detailed field-level errors
    error_details = "; ".join([
        f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
        for err in e.errors()
    ])
    logger.warning(f"mcp_validation_error: {tool}", extra={"errors": e.errors()})
    return {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": f"Invalid parameters: {error_details}",
            "details": e.errors()
        }
    }
except HTTPException as e:
    # FastAPI HTTP exceptions - preserve status code and detail
    logger.warning(f"mcp_http_error: {tool}", extra={"status_code": e.status_code, "detail": e.detail})
    return {
        "error": {
            "code": "HTTP_ERROR",
            "message": e.detail,
            "status_code": e.status_code
        }
    }
except (ConnectionFailure, OperationFailure) as e:
    # Database connection/operation errors
    logger.error(f"mcp_database_error: {tool}", extra={"error": str(e)})
    return {
        "error": {
            "code": "DATABASE_ERROR",
            "message": "Database operation failed",
            "details": str(e)
        }
    }
except Exception as e:
    # Unexpected errors - log full exception
    logger.exception(f"mcp_tool_error: {tool}")
    return {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": str(e)
        }
    }
```

### Error Response Format

All errors follow a consistent structured format:

```python
{
    "error": {
        "code": "ERROR_CODE",      # Machine-readable error code
        "message": "Human-readable error message",
        "details": "Additional context or error details",
        "status_code": 500         # Optional: HTTP status code if applicable
    }
}
```

### Error Codes

Standard error codes used across all MCP tools:

- `VALIDATION_ERROR`: Invalid input parameters (Pydantic validation failed)
- `HTTP_ERROR`: HTTP operation failed (from FastAPI HTTPException)
- `DATABASE_ERROR`: Database connection or operation failed
- `INTERNAL_ERROR`: Unexpected server error
- `UNKNOWN_TOOL`: Tool name not recognized
- `INVALID_REQUEST`: Malformed request (missing required fields)
- `NOT_IMPLEMENTED`: Feature not available via MCP

### Error Categories

**Validation Errors:**
- Invalid parameter types
- Missing required parameters
- Out-of-range values
- Invalid formats
- **Response**: `VALIDATION_ERROR` with detailed field-level errors

**Operation Errors:**
- Network failures
- Database connection issues
- External service unavailability
- Resource not found
- **Response**: `HTTP_ERROR` or `DATABASE_ERROR` with specific details

**System Errors:**
- Internal server errors
- Unexpected exceptions
- Configuration issues
- **Response**: `INTERNAL_ERROR` with logged exception details

### Graceful Degradation

When possible, provide partial results or fallbacks:

```python
# If hybrid search fails, try semantic-only
try:
    results = await hybrid_search(...)
except:
    logger.warning("Hybrid search failed, falling back to semantic")
    results = await semantic_search(...)
```

## Response Formatting

### MCP Response Structure

MCP responses follow this structure:

```python
{
    "content": [
        {
            "type": "text" | "json",
            "text": "Response content as string"
        }
    ]
}
```

### Content Types

**Text Content (`"type": "text"`):**
- Use for simple string responses
- Natural language text
- Single-line or short responses
- Example: Agent query responses

```python
# Simple text response
return {
    "content": [{
        "type": "text",
        "text": result.response
    }]
}
```

**JSON Content (`"type": "json"`):**
- Use for structured data responses
- Complex objects with nested data
- Arrays of results
- Metadata-rich responses
- Example: Search results, crawl responses

```python
import json

# Structured data response
result = await endpoint(RequestModel(**args))
return {
    "content": [{
        "type": "json",
        "text": json.dumps(result.dict(), indent=2)
    }]
}
```

### Structured Data Handling

When returning complex data:

1. **Convert Pydantic models to dict**: `result.dict()`
2. **Serialize to JSON**: Use `json.dumps()` with proper formatting
3. **Use JSON content type**: Set `"type": "json"` for structured data
4. **Wrap in MCP content format**: Follow MCP response structure

**Best Practices:**
- Always use `json.dumps()` instead of `str(dict)` for structured data
- Use `indent=2` for readable JSON formatting
- Use `"type": "json"` for any response containing structured data
- Use `"type": "text"` only for simple string responses

**Example:**
```python
import json

# Structured response (crawl results, search results)
result = await crawl_single(CrawlSinglePageRequest(**args))
return {
    "content": [{
        "type": "json",
        "text": json.dumps(result.dict(), indent=2)
    }]
}

# Simple text response (agent query)
result = await agent(AgentRequest(**args))
return {
    "content": [{
        "type": "text",
        "text": result.response
    }]
}
```

### Error Response Format

Errors use a structured format (not content array):

```python
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": "Additional context"
    }
}
```

## Integration Patterns

### REST Endpoint → MCP Tool Mapping

**Pattern:**
1. Define REST endpoint with Pydantic request/response models
2. Register MCP tool in `list_tools()` with matching schema
3. In `call_tool()`, import and call REST endpoint function
4. Convert response to MCP format

**Example:**
```python
# 1. REST endpoint (server/api/crawl4ai_rag.py)
@router.post("/single", response_model=CrawlResponse)
async def crawl_single(request: CrawlSinglePageRequest):
    # Implementation
    return CrawlResponse(...)

# 2. MCP tool registration (server/mcp/server.py)
{
    "name": "crawl_single_page",
    "description": "Crawl a single web page and ingest into knowledge base",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to crawl"},
            "chunk_size": {"type": "integer", "default": 1000}
        },
        "required": ["url"]
    }
}

# 3. MCP tool execution (server/mcp/server.py)
elif tool == "crawl_single_page":
    from server.api.crawl4ai_rag import crawl_single
    from server.projects.crawl4ai_rag.models import CrawlSinglePageRequest
    result = await crawl_single(CrawlSinglePageRequest(**args))
    return {"content": [{"type": "text", "text": str(result.dict())}]}
```

### Reusing Business Logic

**Never duplicate business logic between REST and MCP.**

✅ **Good:** MCP calls REST endpoint
```python
# MCP tool calls REST endpoint
result = await crawl_single(CrawlSinglePageRequest(**args))
```

❌ **Bad:** Duplicated logic
```python
# MCP tool reimplements crawling logic
# (Don't do this - violates DRY principle)
```

### Avoiding Code Duplication

**Strategy:**
1. Business logic lives in project modules (`server/projects/{name}/`)
2. REST endpoints are thin wrappers that call project functions
3. MCP tools call REST endpoints (or project functions directly)
4. All validation happens in Pydantic models

## Testing

### Unit Testing MCP Tools

Test MCP tools by calling the underlying REST endpoints:

```python
async def test_crawl_single_page_mcp():
    # Test via REST endpoint (which MCP calls)
    request = CrawlSinglePageRequest(url="https://example.com")
    result = await crawl_single(request)
    assert result.success
    assert result.pages_crawled == 1
```

### Integration Testing

Test the full MCP flow:

```python
async def test_mcp_tool_call():
    # Simulate MCP tool call
    args = {"url": "https://example.com"}
    result = await call_tool_mcp("crawl_single_page", args)
    assert "content" in result
    assert result["content"][0]["type"] == "text"
```

### Mock Strategies

Mock external dependencies:
- MongoDB connections
- HTTP requests (crawl4ai)
- LLM API calls
- File system operations

## Common Patterns

### CRUD Operations

**Create:**
```python
{
    "name": "create_resource",
    "description": "Create a new resource",
    "inputSchema": {
        "properties": {
            "name": {"type": "string"},
            "data": {"type": "object"}
        },
        "required": ["name"]
    }
}
```

**Read/Search:**
```python
{
    "name": "search_resources",
    "description": "Search for resources",
    "inputSchema": {
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10}
        },
        "required": ["query"]
    }
}
```

### Search Operations

Search functions should support:
- Query parameter (required)
- Limit/match_count (optional with default)
- Filter options (optional)
- Sort options (optional)

**Example:**
```python
{
    "name": "search_knowledge_base",
    "inputSchema": {
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "match_count": {"type": "integer", "default": 10},
            "search_type": {"type": "string", "enum": ["semantic", "text", "hybrid"], "default": "hybrid"}
        },
        "required": ["query"]
    }
}
```

### Async Operations

All MCP tools should be async:

```python
@app.post("/mcp/tools/call")
async def call_tool(request: Request):
    # All tool calls are async
    result = await endpoint(RequestModel(**args))
    return {"content": [{"type": "text", "text": str(result.dict())}]}
```

### File Handling Limitations

**MCP Limitation:** MCP doesn't support file uploads directly.

**Solutions:**
1. Require files to be on server filesystem
2. Accept file paths as parameters
3. Document that REST API should be used for file uploads

**Example:**
```python
elif tool == "ingest_documents":
    return {
        "error": "File ingestion via MCP requires files to be on server. "
                 "Use REST API POST /api/v1/rag/ingest for file uploads."
    }
```

## Available MCP Tools

The Lambda server provides the following MCP tools organized by project:

### MongoDB RAG Tools
- **`search_knowledge_base`** - Search the MongoDB RAG knowledge base using semantic, text, or hybrid search
- **`ingest_documents`** - Ingest documents into the MongoDB RAG knowledge base (files must be on server filesystem)
- **`agent_query`** - Query the conversational RAG agent with natural language
- **`search_code_examples`** - Search for code examples in the knowledge base (requires `USE_AGENTIC_RAG=true`)
- **`get_available_sources`** - Get all available sources (domains/paths) that have been crawled

### Graphiti RAG Tools
- **`search_graphiti`** - Search the Graphiti knowledge graph for entities and relationships (requires `USE_GRAPHITI=true`)
- **`parse_github_repository`** - Parse a GitHub repository into the Neo4j knowledge graph for code structure analysis (requires `USE_KNOWLEDGE_GRAPH=true`)
- **`check_ai_script_hallucinations`** - Check an AI-generated Python script for hallucinations using the knowledge graph (requires `USE_KNOWLEDGE_GRAPH=true`)
- **`query_knowledge_graph`** - Query and explore the Neo4j knowledge graph containing repository code structure (requires `USE_KNOWLEDGE_GRAPH=true`)

### Crawl4AI Tools
- **`crawl_single_page`** - Crawl a single web page and automatically ingest it into the MongoDB RAG knowledge base
- **`crawl_deep`** - Deep crawl a website recursively and ingest all discovered pages into MongoDB

### N8N Workflow Tools
- **`create_workflow`** - Create a new n8n workflow
- **`update_workflow`** - Update an existing n8n workflow

### System Tools
- **`search_tools`** - Search for MCP tools by name or description (progressive disclosure)
- **`list_directory`** - List files and directories in a given path
- **`read_file`** - Read the contents of a file

**Note**: Feature flags control availability of certain tools:
- `USE_GRAPHITI=true` enables Graphiti RAG tools
- `USE_KNOWLEDGE_GRAPH=true` enables knowledge graph tools
- `USE_AGENTIC_RAG=true` enables code example search

## Examples

### Good MCP Function Example

```python
import json
from pydantic import ValidationError
from fastapi import HTTPException
from pymongo.errors import ConnectionFailure, OperationFailure

# Tool definition
{
    "name": "crawl_single_page",
    "description": "Crawl a single web page and ingest into knowledge base. The page is immediately searchable after ingestion.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to crawl. Must be a valid HTTP/HTTPS URL."
            },
            "chunk_size": {
                "type": "integer",
                "description": "Chunk size for document splitting. Range: 100-5000.",
                "default": 1000,
                "minimum": 100,
                "maximum": 5000
            },
            "chunk_overlap": {
                "type": "integer",
                "description": "Chunk overlap size. Range: 0-500.",
                "default": 200,
                "minimum": 0,
                "maximum": 500
            }
        },
        "required": ["url"]
    }
}

# Tool execution with comprehensive error handling
elif tool == "crawl_single_page":
    from server.api.crawl4ai_rag import crawl_single
    from server.projects.crawl4ai_rag.models import CrawlSinglePageRequest
    
    try:
        result = await crawl_single(CrawlSinglePageRequest(**args))
        # Use JSON type for structured data
        return {
            "content": [{
                "type": "json",
                "text": json.dumps(result.dict(), indent=2)
            }]
        }
    except ValidationError as e:
        # Granular validation error handling
        error_details = "; ".join([
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in e.errors()
        ])
        logger.warning(f"mcp_validation_error: crawl_single_page", extra={"errors": e.errors()})
        return {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"Invalid parameters: {error_details}",
                "details": e.errors()
            }
        }
    except HTTPException as e:
        logger.warning(f"mcp_http_error: crawl_single_page", extra={"status_code": e.status_code, "detail": e.detail})
        return {
            "error": {
                "code": "HTTP_ERROR",
                "message": e.detail,
                "status_code": e.status_code
            }
        }
    except (ConnectionFailure, OperationFailure) as e:
        logger.error(f"mcp_database_error: crawl_single_page", extra={"error": str(e)})
        return {
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Database operation failed",
                "details": str(e)
            }
        }
    except Exception as e:
        logger.exception(f"mcp_tool_error: crawl_single_page")
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": str(e)
            }
        }
```

### Anti-Patterns to Avoid

❌ **Bad: Duplicated Logic**
```python
# Don't reimplement business logic in MCP handler
elif tool == "crawl_single_page":
    # Reimplementing crawling here - BAD!
    crawler = AsyncWebCrawler()
    result = await crawler.arun(url=args["url"])
    # ... more duplicated code
```

✅ **Good: Call REST Endpoint**
```python
# Call existing REST endpoint - GOOD!
elif tool == "crawl_single_page":
    from server.api.crawl4ai_rag import crawl_single
    result = await crawl_single(CrawlSinglePageRequest(**args))
```

❌ **Bad: Vague Descriptions**
```python
{
    "name": "search",
    "description": "Search stuff"  # Too vague!
}
```

✅ **Good: Clear Descriptions**
```python
{
    "name": "search_knowledge_base",
    "description": "Search RAG knowledge base for relevant information using semantic, text, or hybrid search. Searches across all ingested documents and crawled web pages."
}
```

❌ **Bad: Missing Validation**
```python
{
    "max_depth": {
        "type": "integer"
    }
}
```

✅ **Good: Proper Validation**
```python
{
    "max_depth": {
        "type": "integer",
        "description": "Maximum crawl depth",
        "minimum": 1,
        "maximum": 10,
        "default": 3
    }
}
```

## Migration from REST to MCP

When adding MCP support to existing REST endpoints:

1. **Verify REST endpoint exists and works**
2. **Create MCP tool definition** in `list_tools()`
   - Match parameter names to REST request model
   - Include all required and optional parameters
   - Add proper descriptions and validation
3. **Add tool execution** in `call_tool()`
   - Import REST endpoint function
   - Import request model
   - Call endpoint with validated arguments
   - Convert response to MCP format
   - Add error handling
4. **Test both interfaces**
   - Test REST endpoint directly
   - Test MCP tool via `/mcp/tools/call`
   - Verify responses are equivalent

## Checklist for New MCP Functions

- [ ] Function name follows `snake_case` convention
- [ ] Description clearly explains what the function does
- [ ] All parameters have descriptions
- [ ] Required parameters are marked as `required`
- [ ] Optional parameters have sensible defaults
- [ ] Validation constraints are specified (min/max, enum, etc.)
- [ ] Tool calls corresponding REST endpoint (no code duplication)
- [ ] Error handling is implemented
- [ ] Response is properly formatted for MCP
- [ ] Function is tested (unit and/or integration)
- [ ] Documentation is updated

## Related Documentation

- [Lambda Stack AGENTS.md](../AGENTS.md) - Overall Lambda server architecture
- [MongoDB RAG Project](../projects/mongo_rag/) - RAG project implementation
- [Crawl4AI RAG Project](../projects/crawl4ai_rag/) - Web crawling implementation
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - FastAPI framework docs
- [MCP Specification](https://modelcontextprotocol.io) - Official MCP protocol docs

## Versioning Strategy

### Tool Versioning (Optional)

While not currently implemented, tools can include version metadata:

```python
{
    "name": "crawl_single_page",
    "description": "...",
    "version": "1.0.0",           # Semantic versioning
    "stability": "stable",         # stable | experimental | deprecated
    "inputSchema": {...}
}
```

**Stability Levels:**
- `stable`: Production-ready, API won't change
- `experimental`: New feature, may change
- `deprecated`: Will be removed in future version

**When to Version:**
- Breaking changes to tool behavior
- Schema changes that affect compatibility
- Major feature additions
- Deprecation announcements

**Current Status:**
- All tools are considered `stable` by default
- Versioning metadata can be added when needed
- Backward compatibility is maintained

## Security Considerations

### Input Validation

**Pydantic Models:**
- All MCP tool parameters are validated via Pydantic models
- Type checking, range validation, format validation
- Automatic error messages for invalid inputs

**Additional Validation:**
- Tool name validation (check exists before processing)
- Required parameter presence checks
- Schema compliance verification

### Authentication & Authorization

**Current Implementation:**
- MCP layer relies on FastAPI middleware for authentication
- No explicit auth checks in MCP handlers
- Security handled at REST endpoint level

**Future Enhancements:**
- API key validation for MCP tools
- Rate limiting per tool
- User context in tool calls
- Audit logging for sensitive operations

### Best Practices

1. **Never trust client input**: Always validate via Pydantic
2. **Log security events**: Log authentication failures, rate limit hits
3. **Sanitize error messages**: Don't expose internal details in production
4. **Rate limiting**: Consider per-tool rate limits for expensive operations
5. **Resource limits**: Enforce limits on crawl depth, search results, etc.

## Code Execution with MCP

### Overview

Following the pattern described in [Anthropic's code execution with MCP article](https://www.anthropic.com/engineering/code-execution-with-mcp), we generate Python modules that represent MCP tools as callable functions. This enables agents to discover and use tools via filesystem exploration instead of loading all tool definitions upfront, reducing token usage by up to 98.7%.

### Architecture

**Generated Structure:**
```
server/mcp/servers/
├── __init__.py
├── client.py              # Shared MCP client
├── mongo_rag/
│   ├── __init__.py        # Exports all tools
│   ├── search_knowledge_base.py
│   ├── ingest_documents.py
│   └── agent_query.py
└── crawl4ai_rag/
    ├── __init__.py
    ├── crawl_single_page.py
    └── crawl_deep.py
```

### How It Works

1. **Code Generation**: On FastAPI startup, `generate_all_servers()` reads tool definitions and generates Python modules
2. **Tool Discovery**: Agents explore the filesystem to find relevant tools
3. **Progressive Disclosure**: Agents load only the tool definitions they need
4. **Function Calls**: Agents import and call generated functions, which use the MCP client to make HTTP requests

### Example Generated Module

```python
# servers/mongo_rag/search_knowledge_base.py
"""Search the MongoDB RAG knowledge base using semantic, text, or hybrid search."""
from typing import Optional, List, Any, Literal
from server.mcp.servers.client import call_mcp_tool

async def search_knowledge_base(
    query: str,
    match_count: Optional[int] = 5,
    search_type: Optional[Literal["semantic", "text", "hybrid"]] = "hybrid"
) -> dict:
    """
    Search the MongoDB RAG knowledge base.
    
    Searches across all ingested documents including crawled web pages.
    Results are ranked by relevance and include metadata for filtering and context.
    
    Args:
        query: Search query text. Can be a question, phrase, or keywords.
        match_count: Number of results to return. Range: 1-50. Default: 5.
        search_type: Type of search to perform. Default: "hybrid".
    
    Returns:
        SearchResponse with query, results, and count.
    """
    return await call_mcp_tool(
        "search_knowledge_base",
        {
            "query": query,
            "match_count": match_count,
            "search_type": search_type
        }
    )
```

### Agent Usage Example

```python
# Agent can discover and use tools like this:
from server.mcp.servers.mongo_rag import search_knowledge_base
from server.mcp.servers.crawl4ai_rag import crawl_single_page

# Search the knowledge base
results = await search_knowledge_base(
    query="How do I connect to MongoDB?",
    match_count=5
)

# Crawl a page and it becomes searchable
crawl_result = await crawl_single_page(
    url="https://docs.example.com/getting-started"
)

# Search again - new content is now available
new_results = await search_knowledge_base(
    query="getting started",
    match_count=3
)
```

### Benefits

1. **Progressive Disclosure**: Agents load only needed tool definitions (98.7% token savings)
2. **Familiar Patterns**: Standard Python imports and function calls
3. **Better Composition**: Agents can write code that chains tools efficiently
4. **State Persistence**: Agents can save intermediate results to files
5. **Privacy**: Sensitive data can stay in execution environment

### Tool Discovery

Agents can discover tools using:

1. **Filesystem Exploration**: Use `list_directory` to explore `server/mcp/servers/`
2. **Search Tools**: Use `search_tools` to find tools by name or description
3. **Read Modules**: Use `read_file` to read generated Python modules

### Code Generation

Code is automatically generated on FastAPI startup. The generator:
- Reads tool definitions from `get_tool_definitions()`
- Groups tools by server/project (mongo_rag, crawl4ai_rag)
- Converts JSON Schema to Python type hints
- Generates proper docstrings and error handling

### MCP Client

The generated modules use `server.mcp.servers.client.call_mcp_tool()` which:
- Makes HTTP requests to `/mcp/tools/call` endpoint
- Handles error responses and raises appropriate exceptions
- Parses MCP response format (JSON or text content)
- Supports both httpx and aiohttp

## Summary

**Key Takeaways:**

1. **Dual Interface**: Every REST endpoint should have an MCP tool
2. **No Duplication**: MCP tools call REST endpoints, don't reimplement logic
3. **Clear Schemas**: Comprehensive descriptions and validation in JSON Schema
4. **Granular Error Handling**: Differentiate error types with structured error responses
5. **Proper Response Types**: Use `"type": "json"` for structured data, `"type": "text"` for simple responses
6. **Consistent Errors**: Standardized error response format with error codes
7. **Proper Types**: Use correct JSON Schema types with validation
8. **Code Execution**: Generate Python modules for progressive disclosure and token efficiency
9. **Async Everything**: All operations are async
10. **Test Both**: Test REST and MCP interfaces
11. **Security First**: Validate all inputs, log security events, sanitize errors

Following these practices ensures maintainable, consistent, secure, and reliable MCP functions that integrate seamlessly with our REST API infrastructure and enable efficient agent interactions through code execution.

