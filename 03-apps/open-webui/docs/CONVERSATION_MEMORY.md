# Open WebUI Conversation Memory Guide

## Overview

This guide explains how to use the enhanced conversation memory features in Open WebUI, including persistent storage, topic classification, and RAG searchability.

**Note**: Open WebUI is configured with Google OAuth authentication. Users can sign in with their Google accounts, and conversations are associated with authenticated user accounts stored in PostgreSQL.

## Features

### 1. Persistent Conversation Storage

Open WebUI is configured to use PostgreSQL (Supabase) for persistent conversation storage. This ensures:
- Conversations are stored in a database, not just local files
- Conversations persist across container restarts
- Better performance and scalability
- Support for advanced queries and filtering

**Configuration**: Already configured in `docker-compose.yml` with PostgreSQL connection.

### 2. Topic Classification

Conversations are automatically classified into topics using LLM analysis. Topics help:
- Organize conversations by theme
- Filter and search conversations
- Group related discussions

**How it works**:
1. When a conversation is created/updated, the topic classifier analyzes the content
2. LLM suggests 3-5 relevant topics
3. Topics are stored in PostgreSQL and can be manually overridden

**API Endpoint**: `POST /api/v1/openwebui/classify`
- Input: Conversation ID, title, messages
- Output: Suggested topics with confidence scores

### 3. RAG Searchability

Conversations can be exported to the MongoDB RAG system, making them searchable via vector search alongside other documents.

**Export Process**:
1. Conversations are formatted as text documents
2. Content is chunked and embedded
3. Stored in MongoDB with metadata (user_id, conversation_id, topics)
4. Immediately searchable via RAG search endpoints

**API Endpoint**: `POST /api/v1/openwebui/export`
- Input: Conversation ID, messages, metadata, topics
- Output: Export status with document ID and chunks created

**Search Conversations**: Use RAG search with filters:
```json
{
  "query": "authentication setup",
  "source_type": "openwebui_conversation",
  "topics": ["authentication"],
  "user_id": "user_123"
}
```

## Usage

### Exporting Conversations

**Via REST API**:
```bash
curl -X POST http://lambda-server:8000/api/v1/openwebui/export \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_123",
    "user_id": "user_456",
    "title": "Discussion about authentication",
    "messages": [
      {"role": "user", "content": "How do I set up auth?"},
      {"role": "assistant", "content": "To set up authentication..."}
    ],
    "topics": ["authentication", "setup"]
  }'
```

**Via MCP Tool** (from Open WebUI):
- Tool: `export_openwebui_conversation`
- Automatically called when conversations are created/updated (if configured)

### Classifying Topics

**Via REST API**:
```bash
curl -X POST http://lambda-server:8000/api/v1/openwebui/classify \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_123",
    "title": "Discussion about authentication",
    "messages": [
      {"role": "user", "content": "How do I set up auth?"},
      {"role": "assistant", "content": "To set up authentication..."}
    ]
  }'
```

**Via MCP Tool**:
- Tool: `classify_conversation_topics`
- Returns suggested topics with reasoning

### Searching Conversations

**Via RAG Search API**:
```bash
curl -X POST http://lambda-server:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication",
    "source_type": "openwebui_conversation",
    "topics": ["authentication"],
    "search_type": "hybrid"
  }'
```

**Via MCP Tool**:
- Tool: `search_conversations`
- Filters results to only include conversations
- Supports filtering by user_id, conversation_id, topics

## Integration with Open WebUI

### Automatic Export (Future)

A background worker can be configured to:
1. Poll Open WebUI API for new conversations
2. Automatically classify topics
3. Export conversations to RAG system
4. Update conversation metadata in PostgreSQL

### Manual Export

Users can manually trigger exports via:
- Open WebUI custom functions
- REST API calls
- MCP tools from within conversations

## Configuration

### Environment Variables

In `03-apps/docker-compose.yml`, Open WebUI is configured with:
- `DB_TYPE=postgresdb` - Use PostgreSQL
- `DB_POSTGRESDB_HOST=supabase-db` - Database host
- `DB_POSTGRESDB_USER=postgres` - Database user
- `DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}` - Database password
- `DB_POSTGRESDB_DATABASE=postgres` - Database name

### Lambda Server Configuration

The Lambda server needs access to:
- MongoDB (for RAG storage)
- Ollama (for topic classification)
- Open WebUI API (for fetching conversations)

## Best Practices

1. **Topic Classification**: Run classification after conversations are complete for better accuracy
2. **Export Timing**: Export conversations periodically, not on every message (to avoid overhead)
3. **Search Filters**: Use topic filters to narrow search results
4. **Metadata**: Include relevant metadata (user_id, tags) for better filtering

## Troubleshooting

### Conversations Not Stored in PostgreSQL
- Check Open WebUI logs: `docker logs open-webui`
- Verify database connection: Check environment variables
- Test connection: `docker exec open-webui psql -h supabase-db -U postgres -d postgres`

### Topics Not Classified
- Check Lambda server logs: `docker logs lambda-server`
- Verify Ollama is running: `docker ps | grep ollama`
- Test classification endpoint directly

### Conversations Not Searchable
- Verify export was successful: Check export response
- Check MongoDB for documents: Query `documents` collection
- Verify embeddings were created: Check `chunks` collection has embeddings

## References

- [MCP Integration Guide](./MCP_INTEGRATION.md)
- [Auto Memory Research](./AUTO_MEMORY_RESEARCH.md)
- Lambda Server API: `04-lambda/docs/API_CLOUDFLARE_SETUP.md`
