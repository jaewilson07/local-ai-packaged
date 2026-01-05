# Open WebUI MCP Integration Guide

## Overview

Open WebUI has native support for Model Context Protocol (MCP) servers starting from version 0.6.31+. This guide explains how to connect Open WebUI to the Lambda MCP server.

## Prerequisites

- Open WebUI version 0.6.31 or later
- Lambda MCP server running and accessible
- Network connectivity between Open WebUI and Lambda server

## Configuration Steps

### Method 1: Admin Panel (Recommended)

1. **Access Admin Panel**
   - Log in to Open WebUI as an administrator
   - Navigate to **Settings** → **External Tools**

2. **Add MCP Server**
   - Click the **"+" (Add Server)** button
   - Set the following:
     - **Type**: `MCP (Streamable HTTP)`
     - **Server URL**: 
       - Internal (Docker): `http://lambda-server:8000/mcp`
       - External (via Caddy): `https://api.datacrew.space/mcp`
     - **Authentication**: Leave empty (or add API key if authentication is enabled)
   - Click **Save**

3. **Enable Tools**
   - After adding the server, enable specific tools from the list
   - Tools will appear in the chat interface when available

### Method 2: Configuration File

Create or edit `03-apps/open-webui/config/mcp-servers.json`:

```json
{
  "servers": [
    {
      "name": "Lambda MCP Server",
      "type": "mcp",
      "url": "http://lambda-server:8000/mcp",
      "enabled": true,
      "tools": [
        "search_knowledge_base",
        "ingest_documents",
        "agent_query",
        "crawl_single_page",
        "crawl_deep",
        "search_graphiti",
        "query_knowledge_graph"
      ]
    }
  ]
}
```

**Note**: Configuration via Admin Panel is preferred as it's more user-friendly and doesn't require file editing.

## Available MCP Tools

The Lambda MCP server provides the following tools:

### RAG Tools
- **search_knowledge_base** - Search the MongoDB RAG knowledge base
- **ingest_documents** - Ingest documents into the knowledge base
- **agent_query** - Conversational RAG agent
- **search_code_examples** - Search for code examples
- **get_available_sources** - Get list of available data sources

### Web Crawling Tools
- **crawl_single_page** - Crawl a single web page
- **crawl_deep** - Deep crawl multiple pages recursively

### Knowledge Graph Tools (if enabled)
- **search_graphiti** - Search Graphiti knowledge graph
- **parse_github_repository** - Parse GitHub repository into knowledge graph
- **check_ai_script_hallucinations** - Validate AI scripts for hallucinations
- **query_knowledge_graph** - Query the knowledge graph

### n8n Workflow Tools
- **create_n8n_workflow** - Create n8n workflow
- **update_n8n_workflow** - Update n8n workflow
- **delete_n8n_workflow** - Delete n8n workflow
- **activate_n8n_workflow** - Activate/deactivate n8n workflow
- **list_n8n_workflows** - List all n8n workflows
- **execute_n8n_workflow** - Execute n8n workflow

## Usage

Once configured, MCP tools will be available in Open WebUI:

1. **In Chat**: Tools are automatically called by the LLM when needed
2. **Manual Selection**: Some tools can be manually selected from the tools menu
3. **Function Calling**: The LLM will use tools based on the conversation context

## Troubleshooting

### Tools Not Appearing

1. **Check Server Status**: Verify Lambda server is running
   ```bash
   docker ps | grep lambda-server
   curl http://lambda-server:8000/health
   ```

2. **Check Network**: Ensure Open WebUI can reach Lambda server
   ```bash
   docker exec open-webui ping -c 1 lambda-server
   ```

3. **Check MCP Endpoint**: Verify MCP endpoint is accessible
   ```bash
   curl http://lambda-server:8000/mcp/tools/list
   ```

### Connection Errors

- **"Connection refused"**: Lambda server may not be running or not accessible
- **"Timeout"**: Network connectivity issue or server overloaded
- **"Authentication failed"**: Check if API key is required and correctly configured

### Tool Execution Errors

- Check Lambda server logs: `docker logs lambda-server`
- Verify tool parameters are correct
- Ensure required services (MongoDB, Ollama, etc.) are running

## Advanced Configuration

### Custom Tool Selection

You can enable/disable specific tools in the Admin Panel:
- Go to **Settings** → **External Tools**
- Select your MCP server
- Toggle individual tools on/off

### Multiple MCP Servers

Open WebUI supports multiple MCP servers:
- Add each server separately in the Admin Panel
- Tools from all enabled servers will be available
- Tools are identified by their unique names

## Integration with Other Features

### RAG Search Integration

MCP tools can be used alongside Open WebUI's built-in RAG features:
- Use `search_knowledge_base` to search your MongoDB RAG system
- Use `ingest_documents` to add documents to the knowledge base
- Use `agent_query` for conversational access to your knowledge base

### Conversation Export

MCP tools can trigger conversation exports:
- Use custom functions to export conversations
- Integrate with Lambda server's conversation export API

## References

- [Open WebUI MCP Documentation](https://docs.openwebui.com/features/plugin/tools/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- Lambda MCP Server: `04-lambda/server/mcp/AGENTS.md`

