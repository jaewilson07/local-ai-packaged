# Workflows Documentation

This document describes the key workflows in the local-ai-packaged infrastructure, including high-level overviews and detailed step-by-step flows.

## High-Level Workflows

### Document Ingestion Workflow
**Purpose**: Add documents to the knowledge base for RAG search  
**Components**: Lambda server, MongoDB, Ollama  
**Use Cases**: Adding PDFs, web pages, markdown files to searchable knowledge base

### RAG Search Workflow
**Purpose**: Search knowledge base and generate answers using LLM  
**Components**: Open WebUI/Lambda, MongoDB, Ollama  
**Use Cases**: Answering questions using ingested documents

### Conversation Memory Workflow
**Purpose**: Store and search past conversations  
**Components**: Open WebUI, PostgreSQL, Lambda server, MongoDB  
**Use Cases**: Making conversations searchable, topic classification

### Multi-Agent Orchestration Workflow
**Purpose**: Coordinate multiple AI agents in conversations  
**Components**: Lambda server, Persona system, MongoDB  
**Use Cases**: Complex conversations with multiple personas

### Discord Bot Workflow
**Purpose**: Automatically upload photos to Immich and notify users  
**Components**: Discord bot, Immich, PostgreSQL  
**Use Cases**: Event photo management, face detection notifications

### Calendar Integration Workflow
**Purpose**: Extract events from web content and add to Google Calendar  
**Components**: Lambda server, Crawl4AI, Google Calendar API  
**Use Cases**: Automatically adding events from websites to calendar

### N8N Workflow Automation
**Purpose**: Automate workflows using n8n with Lambda MCP tools  
**Components**: n8n, Lambda server, various services  
**Use Cases**: Automated data processing, webhook responses, scheduled tasks

## Detailed Workflow Documentation

### 1. Document Ingestion Workflow

#### Purpose
Ingest documents (PDFs, web pages, markdown, etc.) into the MongoDB RAG knowledge base for semantic and text search.

#### Components
- **Lambda Server**: Document processing and ingestion
- **MongoDB**: Document storage with vector embeddings
- **Ollama**: Embedding generation

#### Step-by-Step Flow

1. **Document Upload** (REST API):
   ```bash
   POST /api/v1/rag/ingest
   Content-Type: multipart/form-data
   files: [file1.pdf, file2.docx]
   ```

2. **Document Processing**:
   - Lambda receives file upload
   - Docling processes document (extracts text, structure)
   - Document converted to text format

3. **Chunking**:
   - Text split into chunks (default: 1000 chars, 200 overlap)
   - Chunks preserve context across boundaries

4. **Embedding Generation**:
   - Each chunk sent to Ollama for embedding
   - Embedding model: `nomic-embed-text` (768 dimensions)
   - Embeddings stored with chunks

5. **Storage**:
   - Chunks + embeddings stored in MongoDB
   - Metadata stored: source, chunk index, timestamps
   - Full-text index created for text search

6. **Response**:
   ```json
   {
     "success": true,
     "documents_processed": 2,
     "chunks_created": 45,
     "document_ids": ["doc1", "doc2"]
   }
   ```

#### API Endpoints

**REST API**:
- `POST /api/v1/rag/ingest` - Upload and ingest documents
  - Request: `multipart/form-data` with `files` field
  - Response: Ingestion status and statistics

**MCP Tool**:
- `ingest_documents(file_paths, clean_before)` - Note: Files must be on server filesystem

#### Configuration

Environment variables:
- `MONGODB_URI` - MongoDB connection string
- `MONGODB_DATABASE` - Database name (default: `rag_db`)
- `EMBEDDING_PROVIDER` - Embedding provider (default: `ollama`)
- `EMBEDDING_MODEL` - Embedding model (default: `nomic-embed-text`)

#### Example

```bash
# Upload PDF document
curl -X POST http://lambda-server:8000/api/v1/rag/ingest \
  -F "files=@document.pdf"

# Response
{
  "success": true,
  "documents_processed": 1,
  "chunks_created": 23,
  "document_ids": ["507f1f77bcf86cd799439011"]
}
```

---

### 2. RAG Search Workflow

#### Purpose
Search the knowledge base using semantic and text search, then generate answers using LLM with retrieved context.

#### Components
- **Open WebUI/Lambda**: Query interface
- **MongoDB**: Knowledge base search
- **Ollama**: Embedding generation and LLM inference

#### Step-by-Step Flow

1. **User Query**:
   - User asks question in Open WebUI or via API
   - Query: "What is authentication?"

2. **Query Processing**:
   - Lambda receives query
   - If using hybrid search: Generate query embedding via Ollama

3. **Knowledge Base Search**:
   - **Semantic Search**: Vector similarity search using query embedding
   - **Text Search**: Full-text keyword search
   - **Hybrid Search**: Combine results using Reciprocal Rank Fusion (RRF)
   - Top N chunks retrieved (default: 5)

4. **Context Assembly**:
   - Retrieved chunks assembled into context
   - Metadata included (source, relevance score)

5. **LLM Generation**:
   - Context + query sent to Ollama
   - LLM model: `llama3.2` (default)
   - LLM generates answer using retrieved context

6. **Response**:
   ```json
   {
     "query": "What is authentication?",
     "response": "Authentication is the process of verifying...",
     "sources": [
       {"chunk": "...", "source": "document.pdf", "score": 0.95}
     ]
   }
   ```

#### API Endpoints

**REST API**:
- `POST /api/v1/rag/search` - Search knowledge base
  - Request: `{"query": "text", "search_type": "hybrid", "match_count": 5}`
  - Response: Search results with chunks and metadata

- `POST /api/v1/rag/agent` - Conversational agent query
  - Request: `{"query": "question"}`
  - Response: Natural language answer with sources

**MCP Tools**:
- `search_knowledge_base(query, match_count, search_type)` - Search knowledge base
- `agent_query(query)` - Conversational agent query

#### Search Types

- **Semantic**: Vector similarity search (best for conceptual queries)
- **Text**: Keyword matching (best for exact terms)
- **Hybrid**: Combines both using RRF (recommended)

#### Example

```bash
# Search knowledge base
curl -X POST http://lambda-server:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication",
    "search_type": "hybrid",
    "match_count": 5
  }'

# Agent query
curl -X POST http://lambda-server:8000/api/v1/rag/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "How does OAuth work?"}'
```

---

### 3. Conversation Memory Workflow

#### Purpose
Store conversations in PostgreSQL, export to MongoDB RAG for searchability, and classify by topics.

#### Components
- **Open WebUI**: Conversation interface
- **PostgreSQL**: Conversation storage
- **Lambda Server**: Export and topic classification
- **MongoDB**: Searchable conversation storage

#### Step-by-Step Flow

1. **Conversation Storage**:
   - User chats in Open WebUI
   - Messages stored in PostgreSQL (Supabase)
   - Metadata: user_id, conversation_id, timestamps

2. **Export to RAG** (Optional):
   - User or system triggers export
   - Lambda fetches conversation from PostgreSQL
   - Conversation formatted as document
   - Chunked and embedded
   - Stored in MongoDB RAG

3. **Topic Classification**:
   - LLM analyzes conversation
   - Generates 3-5 topic tags
   - Topics stored with conversation metadata

4. **Search Conversations**:
   - User searches by query or topic
   - Lambda searches MongoDB RAG
   - Returns matching conversations

#### API Endpoints

**REST API**:
- `POST /api/v1/openwebui/export` - Export single conversation
- `POST /api/v1/openwebui/export/batch` - Export multiple conversations
- `GET /api/v1/openwebui/conversations` - List conversations
- `GET /api/v1/openwebui/conversations/{id}` - Get specific conversation

**MCP Tools**:
- `export_openwebui_conversation(conversation_id, messages, ...)` - Export conversation
- `classify_conversation_topics(conversation_id, messages, ...)` - Classify topics
- `search_conversations(query, match_count, ...)` - Search conversations

#### Example

```bash
# Export conversation
curl -X POST http://lambda-server:8000/api/v1/openwebui/export \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv123",
    "messages": [...],
    "user_id": "user456"
  }'

# Classify topics
curl -X POST http://lambda-server:8000/api/v1/openwebui/topics/classify \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv123",
    "messages": [...]
  }'
```

---

### 4. Multi-Agent Orchestration Workflow

#### Purpose
Coordinate multiple AI agents (personas) in complex conversations with memory and context management.

#### Components
- **Lambda Server**: Persona management and orchestration
- **MongoDB**: Persona state, facts, conversation history
- **Ollama**: LLM inference for personas

#### Step-by-Step Flow

1. **User Message**:
   - User sends message to persona
   - Message includes: `user_id`, `persona_id`, `content`

2. **Context Retrieval**:
   - Lambda retrieves persona state (mood, relationship, context)
   - Retrieves recent conversation history
   - Retrieves relevant facts about user/persona

3. **Orchestration**:
   - Lambda determines which agents to involve
   - Coordinates multi-agent conversation
   - Manages context sharing between agents

4. **Response Generation**:
   - LLM generates response using persona voice
   - Response considers mood, relationship, context
   - Response formatted with persona personality

5. **State Update**:
   - Conversation recorded
   - Persona mood/relationship updated if needed
   - Facts extracted and stored if relevant

#### API Endpoints

**MCP Tools**:
- `orchestrate_conversation(user_id, persona_id, message)` - Main orchestration
- `get_persona_state(user_id, persona_id)` - Get persona state
- `record_message(user_id, persona_id, content, role)` - Record message
- `get_context_window(user_id, persona_id, limit)` - Get conversation context
- `store_fact(user_id, persona_id, fact, tags)` - Store fact
- `search_facts(user_id, persona_id, query, limit)` - Search facts
- `update_persona_mood(user_id, persona_id, primary_emotion, intensity)` - Update mood

#### Example

```json
{
  "tool": "orchestrate_conversation",
  "arguments": {
    "user_id": "user123",
    "persona_id": "persona456",
    "message": "What should I work on today?"
  }
}
```

---

### 5. Discord Bot Workflow

#### Purpose
Automatically upload photos from Discord to Immich, map user faces, and send notifications.

#### Components
- **Discord Bot**: File handling and notifications
- **Immich**: Photo/video storage and face detection
- **PostgreSQL**: User-face mappings (SQLite in bot)

#### Step-by-Step Flow

1. **File Upload**:
   - User uploads photo to `#event-uploads` channel
   - Discord bot detects file attachment
   - Bot downloads file (max 25MB)

2. **Upload to Immich**:
   - Bot uploads file to Immich via REST API
   - Immich processes image (metadata extraction, face detection)
   - Immich returns asset ID

3. **Confirmation**:
   - Bot sends confirmation message in Discord
   - Message includes Immich link

4. **Face Mapping** (User Action):
   - User runs `/claim_face [SearchName]` command
   - Bot searches Immich for people matching name
   - User selects person from dropdown
   - Bot stores mapping: Discord user → Immich person

5. **Notification** (Background):
   - Bot polls Immich every 2 minutes for new assets
   - If new asset contains claimed face:
     - Bot sends DM to Discord user
     - DM includes thumbnail and Immich link

#### API Endpoints

**Discord Bot** (Internal):
- Slash commands: `/claim_face [SearchName]`
- Message handlers: File upload detection

**Immich API** (Used by Bot):
- `POST /api/asset/upload` - Upload asset
- `GET /api/person` - List people (filtered by name)
- `GET /api/asset` - List assets (with `updatedAfter` filter)
- `GET /api/asset/{id}/faces` - Get face detections

#### Example

```
User: [Uploads photo.jpg to #event-uploads]
Bot: ✅ Uploaded to Immich! View: https://immich.datacrew.space/library/asset123

User: /claim_face John
Bot: [Shows dropdown with matching people]
User: [Selects "John Doe"]
Bot: ✅ Face claimed! You'll receive notifications when detected.

[Later, when John is detected in new photo]
Bot: [DM] 👋 You were spotted in a new photo! [thumbnail] View: [link]
```

---

### 6. Calendar Integration Workflow

#### Purpose
Extract events from web content and automatically add them to Google Calendar.

#### Components
- **Lambda Server**: Event extraction and calendar management
- **Crawl4AI**: Web crawling
- **Google Calendar API**: Calendar event creation

#### Step-by-Step Flow

1. **Web Crawl** (Optional):
   - User crawls website with events
   - Lambda crawls pages and extracts content

2. **Event Extraction**:
   - Lambda extracts events from content
   - Uses LLM for structured extraction (optional)
   - Extracts: title, date, time, location, description

3. **Calendar Event Creation**:
   - For each extracted event:
     - Lambda creates Google Calendar event
     - Event includes all extracted details
     - Returns calendar event ID

4. **Confirmation**:
   - Lambda returns list of created events
   - User can view events in Google Calendar

#### API Endpoints

**MCP Tools**:
- `scrape_event_to_calendar(url, event_name_pattern, ...)` - Scrape and create event
- `extract_events_from_content(content, url, use_llm)` - Extract events from text
- `extract_events_from_crawled(crawled_pages, use_llm)` - Extract from crawled pages
- `create_calendar_event(user_id, persona_id, local_event_id, summary, start_time, end_time, ...)` - Create event
- `list_calendar_events(user_id, calendar_id, start_time, end_time)` - List events

#### Example

```json
{
  "tool": "scrape_event_to_calendar",
  "arguments": {
    "url": "https://example.com/events",
    "event_name_pattern": "Workshop",
    "calendar_id": "primary",
    "timezone": "America/New_York"
  }
}
```

---

### 7. N8N Workflow Automation

#### Purpose
Automate workflows using n8n with Lambda MCP tools for RAG, knowledge graphs, and other operations.

#### Components
- **n8n**: Workflow automation platform
- **Lambda Server**: MCP tools and REST APIs
- **Various Services**: MongoDB, Neo4j, Ollama, etc.

#### Step-by-Step Flow

1. **Workflow Trigger**:
   - External trigger: webhook, schedule, file change, etc.
   - n8n workflow starts execution

2. **MCP Tool Call**:
   - n8n HTTP Request node calls Lambda MCP endpoint
   - Tool: `search_knowledge_base`, `create_calendar_event`, etc.
   - Lambda executes tool and returns result

3. **Data Processing**:
   - n8n processes tool result
   - Applies transformations, filters, etc.
   - Calls additional tools or services as needed

4. **Response**:
   - n8n sends response via webhook
   - Or stores result in database
   - Or triggers another workflow

#### API Endpoints

**Lambda MCP Endpoints** (Used by n8n):
- `POST /mcp/tools/list` - List available tools
- `POST /mcp/tools/call` - Execute MCP tool

**n8N Workflow Management** (MCP Tools):
- `create_n8n_workflow(name, nodes, connections, ...)` - Create workflow
- `update_n8n_workflow(workflow_id, ...)` - Update workflow
- `execute_n8n_workflow(workflow_id, input_data)` - Execute workflow

#### Example Workflow

**Trigger**: Webhook receives question  
**Steps**:
1. HTTP Request → Lambda MCP: `agent_query(question)`
2. Lambda searches knowledge base
3. Lambda generates answer
4. HTTP Request → Send answer via webhook

#### Example

```bash
# n8n HTTP Request node configuration
URL: http://lambda-server:8000/mcp/tools/call
Method: POST
Body (JSON):
{
  "tool": "search_knowledge_base",
  "arguments": {
    "query": "{{ $json.question }}",
    "search_type": "hybrid"
  }
}
```

---

## Workflow Integration Patterns

### Pattern 1: RAG-Enhanced Chat
1. User asks question
2. Search knowledge base
3. Generate answer with context
4. Return answer

### Pattern 2: Document → Search → Answer
1. Ingest document
2. User asks question
3. Search knowledge base
4. Generate answer

### Pattern 3: Web Crawl → Extract → Calendar
1. Crawl website
2. Extract events
3. Create calendar events
4. Notify user

### Pattern 4: Conversation → Export → Search
1. User chats
2. Export conversation
3. Classify topics
4. Search conversations later

## Further Reading

- [Architecture Documentation](ARCHITECTURE.md) - System architecture
- [Services Documentation](SERVICES.md) - Service catalog
- [MCP Integration](MCP_INTEGRATION.md) - MCP tools guide
- [Lambda Server README](../04-lambda/README.md) - API reference
