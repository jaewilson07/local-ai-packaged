# Enhanced Knowledge RAG System - Analysis

## Overview

The enhanced knowledge RAG system from wandering-athena provides sophisticated retrieval capabilities including query decomposition, document grading, citation extraction, result synthesis, query rewriting, and enhanced retrieval with fallback mechanisms. It uses LangGraph for orchestration and integrates with memory systems.

## Current Implementation in wandering-athena

**Location**: `src/capabilities/knowledge/`

### Key Components

1. **KnowledgeOrchestrator** (`orchestrator.py`)
   - LangGraph-based knowledge subgraph
   - Enhanced RAG flow with query decomposition
   - Document grading and relevance scoring
   - Citation extraction
   - Result synthesis from multiple sub-queries
   - Query rewriting for better retrieval
   - Tool registry system

2. **Enhanced Retriever** (`nodes/retrieve.py`)
   - Vector search support
   - Metadata extraction
   - Deduplication
   - Support for both memory and vector stores

3. **Query Decomposition** (`nodes/decompose.py`)
   - Breaks complex questions into sub-queries
   - Uses LLM to identify when decomposition is needed

4. **Document Grading** (`nodes/grade.py`)
   - Relevance scoring for retrieved documents
   - Filters low-quality results
   - Uses LLM for semantic relevance

5. **Citation Extraction** (`nodes/citations.py`)
   - Extracts citations from documents
   - Formats citations with metadata
   - Tracks source information

6. **Result Synthesis** (`nodes/synthesize.py`)
   - Combines results from multiple sub-queries
   - Uses LLM to synthesize coherent answers

7. **Query Rewriting** (`nodes/rewrite.py`)
   - Rewrites queries for better retrieval
   - Handles ambiguous or unclear queries

8. **Tool Registry** (`tools.py`)
   - Centralized tool registration
   - Tool discovery and execution
   - Dependency management

9. **Web Crawling** (`actions/crawler.py`)
   - Deep crawl support
   - Content relevance checking
   - Memory caching

10. **Event Extraction** (`actions/event_extractor.py`)
    - Extracts events from web content
    - Parses event details (title, date, time, location, instructor)
    - Integration with calendar system

## Current State in local-ai-packaged

### Existing RAG Systems

- **MongoDB RAG** (`04-lambda/src/capabilities/retrieval/mongo_rag/`)
  - Basic hybrid search (semantic + text)
  - Document ingestion
  - Conversational agent
  - Code example extraction
  - Uses Pydantic AI for agents

- **Graphiti RAG** (`04-lambda/src/capabilities/retrieval/graphiti_rag/`)
  - Graph-based search
  - Temporal fact storage
  - GitHub repository parsing
  - Knowledge graph querying

### Missing Capabilities

- No query decomposition
- No document grading or relevance scoring
- No citation extraction system
- No result synthesis from multiple queries
- No query rewriting
- No enhanced retriever with fallback mechanisms
- No tool registry system
- No event extraction from web content
- No web crawling integration (though crawl4ai exists via MCP)

## Integration Requirements

### Option 1: Enhance Existing MongoDB RAG

**Approach**: Add enhanced features to existing `mongo_rag` project

**Pros**:
- Leverages existing infrastructure
- Unified RAG system
- Can reuse existing MongoDB setup

**Cons**:
- May complicate existing code
- Need to adapt LangGraph patterns to Pydantic AI

**Implementation Steps**:
1. Add query decomposition to agent
2. Add document grading after retrieval
3. Add citation extraction
4. Add result synthesis
5. Add query rewriting
6. Enhance retriever with fallback mechanisms
7. Add tool registry system

### Option 2: Create Enhanced RAG Project

**Approach**: Create new project `enhanced_rag` that uses existing RAG systems

**Pros**:
- Clean separation
- Can orchestrate multiple RAG systems
- Easier to maintain

**Cons**:
- More complex architecture
- May duplicate some functionality

### Option 3: Hybrid Approach

**Approach**: Enhance existing projects and add orchestration layer

**Pros**:
- Best of both worlds
- Incremental enhancement
- Maintains existing functionality

**Cons**:
- More work
- Need careful integration

## Dependencies

### Required Python Packages

```python
# Core (already in local-ai-packaged)
pydantic-ai>=0.1.0     # Agent framework
motor>=3.0.0          # MongoDB async driver

# Optional (for LangGraph patterns)
langgraph>=0.1.0       # If using LangGraph orchestrator
langchain-core>=0.1.0  # Document models

# Web crawling (already exists via MCP)
crawl4ai>=0.3.0       # Web crawling (via MCP in local-ai-packaged)
```

## Code Reference

### Key Patterns from wandering-athena

```python
# Query decomposition
sub_queries = await decompose_query_node(state)

# Document grading
graded_docs = await grade_documents_node(state)

# Citation extraction
citations = await extract_citations_node(state)

# Result synthesis
synthesized = await synthesize_results_node(state)

# Query rewriting
rewritten = await rewrite_query_node(state)

# Enhanced retrieval
documents, doc_strings = enhanced_retriever.retrieve(
    user_id, persona_id, query, limit
)
```

## Integration Points

### With Existing Services

1. **MongoDB RAG** (`04-lambda/src/capabilities/retrieval/mongo_rag/`)
   - Can enhance retrieval with grading
   - Can add query decomposition
   - Can add citation extraction
   - Can add result synthesis

2. **Graphiti RAG** (`04-lambda/src/capabilities/retrieval/graphiti_rag/`)
   - Can add enhanced retrieval
   - Can add query decomposition
   - Can integrate with knowledge graph

3. **Crawl4AI RAG** (`04-lambda/src/workflows/ingestion/crawl4ai_rag/`)
   - Can add web crawling integration
   - Can add event extraction
   - Can enhance with tool registry

4. **Memory Systems**
   - Can integrate with existing memory stores
   - Can use for enhanced retrieval
   - Can store citations

## Recommended Approach

**Phase 1**: Enhance MongoDB RAG
- Add query decomposition
- Add document grading
- Add citation extraction
- Enhance retriever

**Phase 2**: Add Advanced Features
- Add result synthesis
- Add query rewriting
- Add tool registry
- Add event extraction

**Phase 3**: Integration
- Integrate with Graphiti RAG
- Integrate with crawl4ai RAG
- Add orchestration layer

## Implementation Checklist

- [ ] Add query decomposition to MongoDB RAG agent
- [ ] Add document grading after retrieval
- [ ] Add citation extraction
- [ ] Add result synthesis for multi-query results
- [ ] Add query rewriting
- [ ] Enhance retriever with fallback mechanisms
- [ ] Create tool registry system
- [ ] Add event extraction tool
- [ ] Integrate web crawling (via existing crawl4ai MCP)
- [ ] Add REST API endpoints for new features
- [ ] Add MCP tool definitions
- [ ] Create documentation
- [ ] Add tests
- [ ] Update README

## Notes

- Enhanced RAG uses LangGraph in wandering-athena, but local-ai-packaged uses Pydantic AI
- Need to adapt orchestrator pattern to Pydantic AI agent pattern
- Query decomposition requires LLM calls - consider cost/performance
- Document grading improves retrieval quality but adds latency
- Citation extraction enhances answer quality and trustworthiness
- Result synthesis is valuable for complex multi-part questions
- Query rewriting helps with ambiguous queries
- Tool registry enables extensible knowledge tools
- Event extraction enables calendar integration
- Web crawling integration already exists via crawl4ai MCP
