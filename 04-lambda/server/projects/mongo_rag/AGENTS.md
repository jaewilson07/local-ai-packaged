# MongoDB RAG Project - AGENTS.md

> **Override**: This file extends [../../AGENTS.md](../../AGENTS.md). Project-specific rules take precedence.

## Component Identity

- **Project**: `mongo_rag`
- **Location**: `04-lambda/server/projects/mongo_rag/`
- **Purpose**: Enhanced RAG (Retrieval-Augmented Generation) with MongoDB vector search, memory tools, knowledge graph integration, and advanced query processing
- **Dependencies**: MongoDB (01-data), Ollama (02-compute), Neo4j (01-data, optional for graph operations)
- **Agent**: `rag_agent` (Pydantic AI agent with StateDeps)

## Architecture & Patterns

### File Organization

```
mongo_rag/
├── agent.py              # Main RAG agent definition
├── config.py             # Project-specific configuration
├── dependencies.py       # AgentDependencies (MongoDB, OpenAI client)
├── models.py             # Pydantic request/response models
├── prompts.py           # System prompts
├── tools.py             # Core search tools (semantic, text, hybrid)
├── tools_code.py        # Code example extraction tools
├── memory_models.py     # Memory data models (Message, Fact, WebContent)
├── memory_store.py      # MongoDB memory store implementation
├── memory_tools.py      # Memory tools interface
├── nodes/               # Enhanced RAG processing nodes
│   ├── decompose.py     # Query decomposition
│   ├── grade.py         # Document grading/relevance filtering
│   ├── citations.py     # Citation extraction
│   ├── synthesize.py    # Result synthesis from multiple queries
│   └── rewrite.py       # Query rewriting
├── ingestion/           # Document ingestion pipeline
├── reranking/           # Cross-encoder reranking (optional)
├── extraction/          # Entity extraction (optional)
└── neo4j_client.py      # Neo4j knowledge graph client
```

### Key Patterns

**DO's:**
- ✅ **Use AgentDependencies**: Always initialize and cleanup dependencies in try/finally blocks
  ```python
  deps = AgentDependencies()
  await deps.initialize()
  try:
      # Use deps.db, deps.openai_client, etc.
  finally:
      await deps.cleanup()
  ```

- ✅ **Search Strategies**: Use hybrid search by default (semantic + text with RRF)
  ```python
  # In tools.py
  results = await hybrid_search(ctx, query, match_count=5)
  ```

- ✅ **Enhanced RAG**: Use `enhanced_search` tool for complex queries (decomposition, grading, citations)
  ```python
  # In agent.py
  @rag_agent.tool
  async def enhanced_search(ctx, query, use_decomposition=True, use_grading=True)
  ```

- ✅ **Memory Operations**: Use MemoryTools for message/fact/web content storage
  ```python
  memory_tools = MemoryTools(deps=deps)
  memory_tools.record_message(user_id, persona_id, content, role)
  ```

- ✅ **Vector Search**: Use MongoDB `$vectorSearch` aggregation stage
  ```python
  pipeline = [{
      "$vectorSearch": {
          "index": config.mongodb_vector_index,
          "queryVector": embedding,
          "path": "embedding",
          "numCandidates": 100,
          "limit": match_count
      }
  }]
  ```

**DON'Ts:**
- ❌ **Don't hardcode collection names**: Use `config.mongodb_collection_documents` and `config.mongodb_collection_chunks`
- ❌ **Don't skip cleanup**: Always call `await deps.cleanup()` in finally blocks
- ❌ **Don't use synchronous MongoDB operations**: All operations must be async
- ❌ **Don't bypass memory tools**: Use `MemoryTools` interface, not direct MongoDB access
- ❌ **Don't ignore errors in node processing**: Log warnings but continue with fallback behavior

### Code Examples

**Agent Tool Pattern** (from `agent.py`):
```python
@rag_agent.tool
async def search_knowledge_base(
    ctx: RunContext[StateDeps[RAGState]],
    query: str,
    match_count: Optional[int] = 5
) -> str:
    """Search knowledge base using hybrid search."""
    deps = AgentDependencies()
    await deps.initialize()
    try:
        # Create wrapper for context
        class DepsWrapper:
            def __init__(self, deps):
                self.deps = deps
        wrapper = DepsWrapper(deps)
        
        results = await hybrid_search(ctx=wrapper, query=query, match_count=match_count)
        # Format results...
    finally:
        await deps.cleanup()
```

**Memory Storage Pattern** (from `memory_store.py`):
```python
# Store message
message = MemoryMessage(user_id=user_id, persona_id=persona_id, role="user", content=content)
store.add_message(message)

# Get context window
messages = store.get_recent_messages(user_id, persona_id, limit=20)
```

**Query Decomposition Pattern** (from `nodes/decompose.py`):
```python
needs_decomp, sub_queries = await decompose_query(query, llm_client)
if needs_decomp:
    # Search each sub-query, then synthesize
    for sub_query in sub_queries:
        results = await hybrid_search(ctx, sub_query, match_count)
```

## Key Files & JIT Search

**Touch Points:**
- `agent.py:50` - `rag_agent` definition with tools
- `dependencies.py:17` - `AgentDependencies` class
- `tools.py:30` - `hybrid_search` function (main search entry point)
- `memory_store.py:14` - `MongoMemoryStore` implementation
- `nodes/decompose.py:12` - Query decomposition logic
- `nodes/grade.py:25` - Document grading logic

**Search Hints:**
```bash
# Find all RAG agent tools
rg -n "@rag_agent\.tool" 04-lambda/server/projects/mongo_rag/

# Find memory operations
rg -n "MemoryTools|MongoMemoryStore" 04-lambda/server/projects/mongo_rag/

# Find search implementations
rg -n "def (semantic|text|hybrid)_search" 04-lambda/server/projects/mongo_rag/

# Find enhanced RAG nodes
rg -n "def (decompose|grade|synthesize|rewrite)" 04-lambda/server/projects/mongo_rag/nodes/

# Find MongoDB vector search usage
rg -n "\$vectorSearch" 04-lambda/server/projects/mongo_rag/
```

## Testing & Validation

**Manual Testing:**
```bash
# Test search endpoint
curl -X POST http://lambda-server:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "search_type": "hybrid", "match_count": 5}'

# Test enhanced search
curl -X POST http://lambda-server:8000/api/v1/rag/enhanced-search \
  -H "Content-Type: application/json" \
  -d '{"query": "complex multi-part question", "use_decomposition": true}'

# Test memory operations
curl -X POST http://lambda-server:8000/api/v1/rag/memory/record \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user1", "persona_id": "persona1", "content": "Hello", "role": "user"}'
```

**Validation Strategy:**
- Verify MongoDB indexes exist: `db.chunks.getIndexes()`
- Check vector search returns results: Test with known document
- Validate memory storage: Record message, retrieve context window
- Test enhanced RAG: Complex query should decompose and synthesize

## Domain Dictionary

- **RAG**: Retrieval-Augmented Generation - combines vector search with LLM generation
- **Hybrid Search**: Combines semantic (vector) and text (keyword) search using Reciprocal Rank Fusion
- **Query Decomposition**: Breaking complex multi-part questions into focused sub-queries
- **Document Grading**: LLM-based relevance filtering to remove irrelevant documents
- **Context Window**: Recent messages retrieved for conversation continuity
- **Memory Store**: Persistent storage for messages, facts, and web content

## Integration Points

- **MongoDB**: Primary vector store and document storage (`mongodb:27017`)
- **Ollama**: LLM for agent responses and embeddings (`ollama:11434`)
- **Neo4j**: Optional knowledge graph for entity relationships (`neo4j:7687`)
- **REST API**: Endpoints in `server/api/mongo_rag.py`
- **MCP Tools**: Exposed via `server/mcp/fastmcp_server.py`

## Configuration

**Required Environment Variables:**
- `MONGODB_URI` - MongoDB connection string
- `MONGODB_DATABASE` - Database name
- `LLM_MODEL` - LLM model name (default: llama3.2)
- `LLM_BASE_URL` - LLM API base URL (default: http://ollama:11434/v1)
- `EMBEDDING_MODEL` - Embedding model (default: nomic-embed-text)

**Optional Feature Flags:**
- `USE_KNOWLEDGE_GRAPH` - Enable Neo4j graph operations
- `USE_RERANKING` - Enable cross-encoder reranking
- `USE_AGENTIC_RAG` - Enable code example extraction
