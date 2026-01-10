# Advanced Memory Management - Analysis

## Overview

The advanced memory management system from wandering-athena provides sophisticated memory orchestration with LangGraph, web content storage, context window management, fact storage with semantic search, and multiple memory store implementations (SQLite, Supabase, Neo4j, Mem0).

## Current Implementation in wandering-athena

**Location**: `src/capabilities/memory/`

### Key Components

1. **MemoryOrchestrator** (`orchestrator.py`)
   - LangGraph-based memory subgraph
   - Memory retrieval and summarization
   - Recent message retrieval
   - Fact search

2. **MemoryTools** (`tools.py`)
   - High-level memory interface
   - Message recording
   - Context window management
   - Fact storage and search
   - Web content storage and retrieval

3. **MemoryStore Protocol** (`protocols.py`)
   - Protocol for swappable memory backends
   - Supports multiple implementations
   - Standardized interface

4. **State Models** (`state.py`)
   - `MemorySubgraphState`: LangGraph state model
   - Message and fact models

5. **Implementations** (`implementations/`)
   - Multiple memory store implementations
   - SQLite, Supabase, Neo4j, Mem0 support

### Key Features

- **Memory Orchestration**: LangGraph subgraph for memory operations
- **Context Window Management**: Recent message retrieval for context
- **Fact Storage**: Semantic search for facts
- **Web Content Storage**: Dedicated storage for web-scraped content
- **Multiple Backends**: SQLite, Supabase, Neo4j, Mem0 support
- **Chunking Support**: Automatic chunking for long content
- **Deduplication**: Prevents duplicate content storage

## Current State in local-ai-packaged

### Existing Memory Systems

- **MongoDB RAG** (`04-lambda/server/projects/mongo_rag/`)
  - Basic document storage
  - Hybrid search
  - No dedicated memory orchestration

- **Graphiti RAG** (`04-lambda/server/projects/graphiti_rag/`)
  - Knowledge graph storage
  - Temporal fact storage
  - No message storage

### Missing Capabilities

- No memory orchestration with LangGraph
- No web content storage (separate from documents)
- No context window management
- No recent message retrieval
- Limited memory store implementations
- No dedicated memory tools interface

## Integration Requirements

### Option 1: Enhance Existing Systems

**Approach**: Add memory capabilities to existing MongoDB RAG and Graphiti RAG

**Pros**:
- Leverages existing infrastructure
- Unified storage
- Simpler architecture

**Cons**:
- May complicate existing code
- Need to add new features

**Implementation Steps**:
1. Add message storage to MongoDB
2. Add context window management
3. Add web content storage
4. Enhance fact storage
5. Add memory orchestration

### Option 2: Create Memory Project

**Approach**: Create new project `memory` that orchestrates existing systems

**Pros**:
- Clean separation
- Can orchestrate multiple backends
- Easier to maintain

**Cons**:
- More complex architecture
- May duplicate some functionality

## Dependencies

### Required Python Packages

```python
# Core (already in local-ai-packaged)
pydantic>=2.0.0        # State models
motor>=3.0.0          # MongoDB async driver
neo4j>=5.0.0          # Neo4j driver (if using Neo4j)

# Optional (for LangGraph)
langgraph>=0.1.0       # If using LangGraph orchestrator
langchain-core>=0.1.0  # Document models

# Optional (for Mem0)
mem0ai>=0.1.0         # If using Mem0 backend
```

## Code Reference

### Key Functions from wandering-athena

```python
# Memory tools interface
memory = MemoryTools(store=store)

# Record messages
memory.record_user_message(user_id, persona_id, content, role="user")

# Get context window
messages = memory.get_context_window(user_id, persona_id, limit=20)

# Store facts
memory.remember_fact(user_id, persona_id, fact, tags=["tag1", "tag2"])

# Search facts
facts = memory.search_facts(user_id, persona_id, query, limit=10)

# Store web content
chunks = memory.add_web_content(
    user_id=user_id,
    persona_id=persona_id,
    content=content,
    source_url=url,
    source_title=title,
    chunk_size=1000,
    chunk_overlap=200,
)
```

## Integration Points

### With Existing Services

1. **MongoDB RAG** (`04-lambda/server/projects/mongo_rag/`)
   - Can add message storage
   - Can add web content storage
   - Can enhance fact storage

2. **Graphiti RAG** (`04-lambda/server/projects/graphiti_rag/`)
   - Can integrate with knowledge graph
   - Can store facts in graph
   - Can enhance temporal storage

3. **Lambda Stack** (`04-lambda/`)
   - Can add as new project
   - Can expose via REST API
   - Can expose via MCP tools

## Recommended Approach

**Phase 1**: Enhance MongoDB RAG
- Add message storage
- Add context window management
- Add web content storage
- Enhance fact storage

**Phase 2**: Add Memory Orchestration
- Create MemoryOrchestrator (adapt to Pydantic AI)
- Add memory tools interface
- Add REST API endpoints
- Add MCP tools

**Phase 3**: Integration
- Integrate with Graphiti RAG
- Add multiple backend support
- Add memory orchestration

## Implementation Checklist

- [ ] Add message storage to MongoDB
- [ ] Add context window management
- [ ] Add web content storage
- [ ] Enhance fact storage with semantic search
- [ ] Create MemoryTools interface
- [ ] Create MemoryOrchestrator (adapt to Pydantic AI)
- [ ] Add REST API endpoints
- [ ] Add MCP tool definitions
- [ ] Create documentation
- [ ] Add tests
- [ ] Update README

## Notes

- Memory orchestration uses LangGraph in wandering-athena, but local-ai-packaged uses Pydantic AI
- Need to adapt orchestrator pattern to Pydantic AI agent pattern
- Web content storage is separate from document storage
- Context window management improves conversation continuity
- Fact storage with semantic search enables better retrieval
- Multiple backend support provides flexibility
- Chunking support handles long content efficiently
- Deduplication prevents storage bloat
