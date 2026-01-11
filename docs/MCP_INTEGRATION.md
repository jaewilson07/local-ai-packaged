# MCP Integration Guide

This guide explains how to use the Model Context Protocol (MCP) server provided by the Lambda server, including all available tools and integration examples.

## What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI assistants to discover and call tools/functions provided by servers. It allows AI models to:

- Discover available capabilities
- Call functions with structured parameters
- Receive structured responses
- Handle errors gracefully

## Lambda MCP Server Overview

The Lambda server provides a comprehensive MCP server with **40+ tools** organized into categories:

- **MongoDB RAG Tools**: Search, ingest, agent queries
- **Graphiti RAG Tools**: Knowledge graph operations
- **Crawl4AI Tools**: Web crawling and search
- **N8N Workflow Tools**: Workflow management
- **Open WebUI Tools**: Conversation export and search
- **Calendar Tools**: Google Calendar integration
- **Knowledge Extraction**: Event extraction from content
- **Persona Management**: Persona state and memory
- **Discord Character Tools**: Discord character management and engagement
- **Enhanced Search**: Advanced RAG with decomposition
- **Deep Research Tools**: Web search, page fetching, document parsing

## MCP Server Endpoints

### Base URL
- **Internal**: `http://lambda-server:8000/mcp`
- **External**: `http://localhost:8000/mcp` (if port exposed) or via Caddy reverse proxy

### Endpoints

**List Tools**:
```bash
POST /mcp/tools/list
```

**Call Tool**:
```bash
POST /mcp/tools/call
Content-Type: application/json
{
  "tool": "tool_name",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

## MCP Tools Catalog

### MongoDB RAG Tools

#### `search_knowledge_base`
Search the MongoDB RAG knowledge base using semantic, text, or hybrid search.

**Parameters**:
- `query` (str, required): Search query text
- `match_count` (int, 1-50, default: 5): Number of results
- `search_type` ("semantic" | "text" | "hybrid", default: "hybrid"): Search type

**Returns**: Search results with chunks, metadata, and relevance scores

**Example**:
```json
{
  "tool": "search_knowledge_base",
  "arguments": {
    "query": "authentication methods",
    "match_count": 10,
    "search_type": "hybrid"
  }
}
```

#### `agent_query`
Query the conversational RAG agent with natural language.

**Parameters**:
- `query` (str, required): Natural language question

**Returns**: Natural language response with synthesized information

**Example**:
```json
{
  "tool": "agent_query",
  "arguments": {
    "query": "How does OAuth 2.0 work?"
  }
}
```

#### `ingest_documents`
Ingest documents into the MongoDB RAG knowledge base.

**Note**: Files must be on server filesystem. Use REST API for file uploads.

**Parameters**:
- `file_paths` (List[str], required): Absolute file paths on server
- `clean_before` (bool, default: false): Delete existing documents before ingestion

**Returns**: Ingestion status

#### `search_code_examples`
Search for code examples in the knowledge base.

**Requires**: `USE_AGENTIC_RAG=true`

**Parameters**:
- `query` (str, required): Search query
- `match_count` (int, 1-50, default: 5): Number of results

**Returns**: Code snippets with summaries, language, and context

#### `get_available_sources`
Get all available data sources (domains/paths) that have been crawled.

**Parameters**: None

**Returns**: List of sources with summaries and statistics

### Graphiti RAG Tools

#### `search_graphiti`
Search the Graphiti knowledge graph for entities and relationships.

**Requires**: `USE_GRAPHITI=true`

**Parameters**:
- `query` (str, required): Search query
- `match_count` (int, default: 10): Number of results

**Returns**: Facts with temporal information and source metadata

#### `parse_github_repository`
Parse a GitHub repository into the Neo4j knowledge graph.

**Requires**: `USE_KNOWLEDGE_GRAPH=true`

**Parameters**:
- `repo_url` (str, required): GitHub repository URL (must end with .git)

**Returns**: Parse results with extracted classes, methods, functions

#### `check_ai_script_hallucinations`
Check an AI-generated Python script for hallucinations.

**Requires**: `USE_KNOWLEDGE_GRAPH=true`

**Parameters**:
- `script_path` (str, required): Absolute path to script on server

**Returns**: Validation results for imports, method calls, class instantiations

#### `query_knowledge_graph`
Query and explore the Neo4j knowledge graph.

**Requires**: `USE_KNOWLEDGE_GRAPH=true`

**Parameters**:
- `command` (str, required): Command to execute
  - `repos` - List repositories
  - `explore <repo>` - Explore repository structure
  - `classes [repo]` - List classes
  - `class <name>` - Get class details
  - `method <name> [class]` - Get method details
  - `query <cypher>` - Execute Cypher query

**Returns**: Query results based on command

### Crawl4AI Tools

#### `crawl_single_page`
Crawl a single web page and automatically ingest into MongoDB RAG.

**Parameters**:
- `url` (str, required): URL to crawl
- `chunk_size` (int, 100-5000, default: 1000): Chunk size
- `chunk_overlap` (int, 0-500, default: 200): Chunk overlap

**Returns**: Crawl results with automatic ingestion

#### `crawl_deep`
Deep crawl a website recursively and ingest all pages.

**Parameters**:
- `url` (str, required): Starting URL
- `max_depth` (int, 1-10, required): Maximum recursion depth
- `allowed_domains` (List[str], optional): Allowed domains
- `allowed_subdomains` (List[str], optional): Allowed subdomain prefixes
- `chunk_size` (int, default: 1000): Chunk size
- `chunk_overlap` (int, default: 200): Chunk overlap

**Returns**: Crawl results with all pages ingested

#### `web_search`
Search the web using SearXNG metasearch engine.

**Parameters**:
- `query` (str, required): Search query
- `result_count` (int, 1-20, default: 10): Number of results
- `categories` (str, optional): Filter by category
- `engines` (List[str], optional): Filter by search engines

**Returns**: Search results from multiple search engines

### N8N Workflow Tools

#### `create_n8n_workflow`
Create a new n8n workflow.

**Parameters**:
- `name` (str, required): Workflow name
- `nodes` (List[Dict], optional): Workflow nodes
- `connections` (Dict, optional): Node connections
- `active` (bool, default: false): Activate workflow
- `settings` (Dict, optional): Workflow settings

**Returns**: Created workflow details

#### `update_n8n_workflow`
Update an existing n8n workflow.

**Parameters**:
- `workflow_id` (str, required): Workflow ID
- `name` (str, optional): New name
- `nodes` (List[Dict], optional): New nodes
- `connections` (Dict, optional): New connections
- `active` (bool, optional): Activation status
- `settings` (Dict, optional): New settings

**Returns**: Updated workflow details

#### `delete_n8n_workflow`
Delete an n8n workflow permanently.

**Parameters**:
- `workflow_id` (str, required): Workflow ID

**Returns**: Deletion confirmation

#### `activate_n8n_workflow`
Activate or deactivate an n8n workflow.

**Parameters**:
- `workflow_id` (str, required): Workflow ID
- `active` (bool, required): Activation status

**Returns**: Activation status

#### `list_n8n_workflows`
List all n8n workflows.

**Parameters**:
- `active_only` (bool, default: false): Only return active workflows

**Returns**: List of workflows with IDs, names, and status

#### `execute_n8n_workflow`
Execute an n8n workflow manually.

**Parameters**:
- `workflow_id` (str, required): Workflow ID
- `input_data` (Dict, optional): Input data for workflow

**Returns**: Execution results

#### `scrape_event_to_calendar`
Scrape event from website and create Google Calendar event.

**Parameters**:
- `url` (str, required): Website URL
- `event_name_pattern` (str, optional): Event name pattern
- `calendar_id` (str, default: "primary"): Google Calendar ID
- `timezone` (str, default: "America/New_York"): Timezone
- `location_pattern` (str, optional): Location pattern
- `description_template` (str, optional): Description template
- `workflow_name` (str, default: "Scrape Event To Calendar"): n8n workflow name

**Returns**: Calendar event details

#### `discover_n8n_nodes`
Discover available n8n nodes via API.

**Parameters**:
- `category` (str, optional): Filter by category

**Returns**: List of available node types with descriptions

#### `search_n8n_knowledge_base`
Search the knowledge base for n8n-related information.

**Parameters**:
- `query` (str, required): Search query
- `match_count` (int, 1-50, default: 5): Number of results
- `search_type` ("semantic" | "text" | "hybrid", default: "hybrid"): Search type

**Returns**: Formatted search results

#### `search_n8n_node_examples`
Search for n8n node usage examples.

**Parameters**:
- `node_type` (str, optional): Filter by node type
- `query` (str, optional): Search query
- `match_count` (int, default: 5): Number of results

**Returns**: Formatted examples

### Open WebUI Tools

#### `export_openwebui_conversation`
Export an Open WebUI conversation to MongoDB RAG.

**Parameters**:
- `conversation_id` (str, required): Conversation ID
- `messages` (List[Dict], required): Conversation messages
- `user_id` (str, optional): User ID
- `title` (str, optional): Conversation title
- `topics` (List[str], optional): Conversation topics

**Returns**: Export results

#### `classify_conversation_topics`
Classify topics for an Open WebUI conversation.

**Parameters**:
- `conversation_id` (str, required): Conversation ID
- `messages` (List[Dict], required): Conversation messages
- `title` (str, optional): Conversation title
- `existing_topics` (List[str], optional): Existing topics

**Returns**: Classified topics (3-5 topics)

#### `search_conversations`
Search conversations in the RAG system.

**Parameters**:
- `query` (str, required): Search query
- `match_count` (int, 1-50, default: 5): Number of results
- `user_id` (str, optional): Filter by user ID
- `conversation_id` (str, optional): Filter by conversation ID
- `topics` (List[str], optional): Filter by topics

**Returns**: Search results filtered to Open WebUI conversations

### Calendar Tools

#### `create_calendar_event`
Create a Google Calendar event.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID
- `local_event_id` (str, required): Local event ID
- `summary` (str, required): Event summary
- `start_time` (str, required): Start time (ISO 8601)
- `end_time` (str, required): End time (ISO 8601)
- `description` (str, optional): Event description
- `location` (str, optional): Event location
- `calendar_id` (str, default: "primary"): Calendar ID

**Returns**: Created event details

#### `update_calendar_event`
Update an existing Google Calendar event.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID
- `local_event_id` (str, required): Local event ID
- `summary` (str, optional): New summary
- `start_time` (str, optional): New start time
- `end_time` (str, optional): New end time
- `description` (str, optional): New description
- `location` (str, optional): New location
- `calendar_id` (str, default: "primary"): Calendar ID

**Returns**: Updated event details

#### `delete_calendar_event`
Delete a Google Calendar event.

**Parameters**:
- `user_id` (str, required): User ID
- `event_id` (str, required): Calendar event ID
- `calendar_id` (str, default: "primary"): Calendar ID

**Returns**: Deletion confirmation

#### `list_calendar_events`
List Google Calendar events.

**Parameters**:
- `user_id` (str, required): User ID
- `calendar_id` (str, default: "primary"): Calendar ID
- `start_time` (str, optional): Start time filter (ISO 8601)
- `end_time` (str, optional): End time filter (ISO 8601)

**Returns**: List of events

### Knowledge Extraction Tools

#### `extract_events_from_content`
Extract events from web content.

**Parameters**:
- `content` (str, required): Content text
- `url` (str, optional): Source URL
- `use_llm` (bool, default: false): Use LLM for extraction

**Returns**: Extracted events with dates, times, locations

#### `extract_events_from_crawled`
Extract events from crawled pages.

**Parameters**:
- `crawled_pages` (List[Dict], required): Crawled page data
- `use_llm` (bool, default: false): Use LLM for extraction

**Returns**: Extracted events from multiple pages

### Persona Management Tools

#### `record_message`
Record message in conversation history.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID
- `content` (str, required): Message content
- `role` ("user" | "assistant", default: "user"): Message role

**Returns**: Recorded message details

#### `get_context_window`
Get recent conversation context.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID
- `limit` (int, default: 20): Number of messages

**Returns**: Recent messages for context

#### `store_fact`
Store fact about user/persona.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID
- `fact` (str, required): Fact text
- `tags` (List[str], optional): Tags

**Returns**: Stored fact details

#### `search_facts`
Search stored facts.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID
- `query` (str, required): Search query
- `limit` (int, default: 10): Number of results

**Returns**: Matching facts

#### `store_web_content`
Store web content for persona.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID
- `content` (str, required): Content text
- `source_url` (str, required): Source URL
- `tags` (List[str], optional): Tags

**Returns**: Stored content details

#### `get_persona_voice_instructions`
Get persona voice/personality instructions.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID

**Returns**: Voice instructions for LLM

#### `record_persona_interaction`
Record interaction with persona.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID
- `user_message` (str, required): User message
- `bot_response` (str, required): Bot response

**Returns**: Recorded interaction

#### `get_persona_state`
Get persona state (mood, relationship, context).

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID

**Returns**: Persona state including mood, relationship level, context

#### `update_persona_mood`
Update persona mood.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID
- `primary_emotion` (str, required): Primary emotion
- `intensity` (float, 0.0-1.0, required): Emotion intensity

**Returns**: Updated mood state

#### `orchestrate_conversation`
Orchestrate multi-agent conversation.

**Parameters**:
- `user_id` (str, required): User ID
- `persona_id` (str, required): Persona ID
- `message` (str, required): User message

**Returns**: Orchestrated conversation response

### Discord Character Tools

#### `add_discord_character`
Adds an AI character to a Discord channel.

**Parameters**:
- `channel_id` (str, required): Discord channel ID
- `persona_id` (str, required): Persona ID to add
- `name` (str, optional): Optional display name for the character
- `avatar_url` (str, optional): Optional avatar URL for the character

**Returns**: Character operation response with success status and character details

**Example**:
```json
{
  "tool": "add_discord_character",
  "arguments": {
    "channel_id": "123456789",
    "persona_id": "athena",
    "name": "Athena",
    "avatar_url": "https://example.com/athena.png"
  }
}
```

#### `remove_discord_character`
Removes an AI character from a Discord channel.

**Parameters**:
- `channel_id` (str, required): Discord channel ID
- `persona_id` (str, required): Persona ID to remove

**Returns**: Character operation response with success status

#### `list_discord_characters`
Lists all active AI characters in a Discord channel.

**Parameters**:
- `channel_id` (str, required): Discord channel ID

**Returns**: List of active characters with persona IDs, names, and active timestamps

#### `clear_discord_character_history`
Clears chat history for a Discord channel, optionally for a specific character.

**Parameters**:
- `channel_id` (str, required): Discord channel ID
- `persona_id` (str, optional): Optional persona ID to clear history for. If None, clears all history for the channel.

**Returns**: Character operation response with success status

#### `engage_discord_character`
Engages a character in conversation and returns its response.

**Parameters**:
- `channel_id` (str, required): Discord channel ID to engage in
- `persona_id` (str, required): Persona ID of the character to engage
- `user_id` (str, required): User ID initiating the engagement (can be system for random engagements)
- `message_content` (str, required): The message content to send to the character
- `message_context` (List[Dict], optional): Recent messages for context, each with 'author_id', 'author_name', 'content', 'timestamp', 'is_bot'

**Returns**: Character response with generated text

**Example**:
```json
{
  "tool": "engage_discord_character",
  "arguments": {
    "channel_id": "123456789",
    "persona_id": "athena",
    "user_id": "987654321",
    "message_content": "What's your opinion on courage?",
    "message_context": [
      {
        "author_id": "987654321",
        "author_name": "User",
        "content": "Hello!",
        "timestamp": "2024-01-01T12:00:00Z",
        "is_bot": false
      }
    ]
  }
}
```

### Deep Research Tools

#### `search_web`
Search the web using SearXNG metasearch engine.

**Parameters**:
- `query` (str, required): Search query string
- `engines` (List[str], optional): Optional list of search engine filters
- `result_count` (int, 1-20, default: 5): Number of results to return

**Returns**: Search results from multiple search engines

#### `fetch_page`
Fetch a single web page using Crawl4AI.

**Parameters**:
- `url` (str, required): URL to fetch (must be valid HTTP/HTTPS URL)

**Returns**: Page content as markdown along with metadata

#### `parse_document`
Parse a document using Docling and chunk it with HybridChunker.

**Parameters**:
- `content` (str, required): Raw content to parse (HTML, markdown, or plain text)
- `content_type` ("html" | "markdown" | "text", default: "html"): Content type hint for parsing

**Returns**: Structured chunks with metadata

### Enhanced Search Tools

#### `enhanced_search`
Enhanced RAG search with decomposition and grading.

**Parameters**:
- `query` (str, required): Search query
- `match_count` (int, default: 5): Number of results
- `use_decomposition` (bool, default: true): Use query decomposition
- `use_grading` (bool, default: true): Use result grading

**Returns**: Enhanced search results

## Integration Examples

### Open WebUI Integration

1. **Configure MCP Server**:
   - Go to Settings → Connections → MCP Servers
   - Add new server: `http://lambda-server:8000/mcp`
   - Tools will be automatically available in conversations

2. **Use in Conversation**:
   ```
   User: Search the knowledge base for "authentication"
   Assistant: [Calls search_knowledge_base tool automatically]
   ```

### Claude Desktop Integration

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "lambda-server": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Programmatic Usage (Python)

```python
import requests

# List available tools
response = requests.post("http://lambda-server:8000/mcp/tools/list")
tools = response.json()

# Call a tool
response = requests.post("http://lambda-server:8000/mcp/tools/call", json={
    "tool": "search_knowledge_base",
    "arguments": {
        "query": "authentication",
        "match_count": 5,
        "search_type": "hybrid"
    }
})
result = response.json()
```

### n8n Integration

**HTTP Request Node Configuration**:
- **URL**: `http://lambda-server:8000/mcp/tools/call`
- **Method**: POST
- **Body** (JSON):
  ```json
  {
    "tool": "search_knowledge_base",
    "arguments": {
      "query": "{{ $json.question }}",
      "search_type": "hybrid"
    }
  }
  ```

## Feature Flags

Some tools require feature flags to be enabled:

- `USE_GRAPHITI=true` - Enables Graphiti RAG tools
- `USE_KNOWLEDGE_GRAPH=true` - Enables knowledge graph tools
- `USE_AGENTIC_RAG=true` - Enables code example search
- `USE_CONTEXTUAL_EMBEDDINGS=false` - Contextual embeddings (optional)
- `USE_RERANKING=false` - Cross-encoder reranking (optional)

## Error Handling

MCP tools return structured errors:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "details": "Additional details"
  }
}
```

Common error codes:
- `VALIDATION_ERROR` - Invalid parameters
- `DATABASE_ERROR` - Database operation failed
- `NOT_FOUND` - Resource not found
- `NOT_IMPLEMENTED` - Feature not available
- `FEATURE_DISABLED` - Feature flag not enabled

## Best Practices

1. **Use Hybrid Search**: For most queries, use `search_type: "hybrid"` for best results
2. **Batch Operations**: When possible, batch multiple operations
3. **Error Handling**: Always check for errors in tool responses
4. **Feature Flags**: Check required feature flags before using tools
5. **File Uploads**: Use REST API for file uploads, not MCP tools

## Further Reading

- [Lambda Server README](../04-lambda/README.md) - Complete API reference
- [RAG MCP Architecture Decision](../04-lambda/docs/RAG_MCP_ARCHITECTURE_DECISION.md) - Architecture decision for RAG tools design
- [Workflows Documentation](WORKFLOWS.md) - Workflow examples using MCP tools
- [Architecture Documentation](ARCHITECTURE.md) - System architecture
- [Services Documentation](SERVICES.md) - Service catalog
