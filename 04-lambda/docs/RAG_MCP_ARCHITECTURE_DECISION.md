# RAG MCP Tools Architecture Decision

## Decision Date
2024-12-19

## Context

The Lambda server provides multiple RAG (Retrieval-Augmented Generation) capabilities:
- **MongoDB RAG**: Vector-based document search and retrieval
- **Graphiti RAG**: Graph-based knowledge graph operations
- **Crawl4AI RAG**: Web crawling with automatic ingestion

Each capability has distinct use cases, parameters, and backend systems. The question arose: should we have separate MCP tools for each RAG capability, or a unified router tool that intelligently routes to the appropriate backend?

## Current Architecture

We currently have **separate MCP tools for each RAG capability**:

### MongoDB RAG Tools (5 tools)
- `search_knowledge_base` - Vector/text/hybrid search
- `agent_query` - Conversational RAG agent
- `search_code_examples` - Code example search
- `get_available_sources` - List crawled sources
- `ingest_documents` - Document ingestion

### Graphiti RAG Tools (4 tools)
- `search_graphiti` - Knowledge graph search
- `parse_github_repository` - Repository parsing
- `check_ai_script_hallucinations` - Script validation
- `query_knowledge_graph` - Cypher queries

### Crawl4AI RAG Tools (2 tools)
- `crawl_single_page` - Single page crawl
- `crawl_deep` - Deep recursive crawl

**Total: 11 RAG-specific tools** (plus 31 other tools for N8N, Calendar, Persona, etc.)

## Decision

**Keep the current separate tools approach.**

## Rationale

### 1. MCP Best Practices
The Model Context Protocol encourages specific, discoverable tools. Our current structure follows this pattern:
- Each tool has a clear, single responsibility
- Tool descriptions clearly state capabilities
- Parameters are optimized for each use case

### 2. Better UX for LLMs
Modern LLMs (Claude, GPT-4) excel at tool selection when tools are well-described:
- Clear tool names indicate purpose (`search_knowledge_base` vs `search_graphiti`)
- Specific parameters match use cases
- No need for intermediate routing layer

### 3. Progressive Disclosure
We already have `search_tools` for discovering tools, which addresses the "too many tools" concern:
- Agents can search for relevant tools by description
- Tools are organized by project/category
- Reduces cognitive load when selecting tools

### 4. Maintainability
Separate tools make it easier to:
- Add new capabilities without affecting existing ones
- Modify parameters for specific use cases
- Debug issues (clear separation of concerns)
- Test functionality independently

### 5. Flexibility
Users can compose tools in creative ways:
- `crawl_deep` → `search_knowledge_base` → `extract_events_from_content`
- `parse_github_repository` → `check_ai_script_hallucinations`
- `search_knowledge_base` + `search_graphiti` for combined results

### 6. Performance
- No router latency (direct tool calls)
- No additional LLM calls to determine routing
- Tools can be called in parallel when appropriate

## Alternatives Considered

### Option 1: Unified Router Tool ❌

**Pros:**
- Single entry point for RAG operations
- Router agent could intelligently route to backends
- Could combine results from multiple RAG systems

**Cons:**
- Adds complexity (router agent needs maintenance and testing)
- Less explicit (harder to understand available capabilities)
- Harder discovery (can't see all capabilities without calling router)
- Router latency (extra LLM call to determine routing)
- Less flexible (can't easily use multiple tools in sequence)
- Generic parameters (would need to support all parameter types)

**Decision:** Rejected - benefits don't outweigh the costs.

### Option 2: Hybrid Approach (Optional Future Enhancement)

**Add a `rag_search_unified` tool** that:
- Routes internally to appropriate backend (MongoDB/Graphiti)
- Combines results from multiple sources
- Keeps existing specialized tools available

**Pros:**
- Provides convenience layer for common use cases
- Doesn't remove existing specialized tools
- Users can choose based on their needs

**Cons:**
- Adds another tool to maintain
- May cause confusion about which tool to use

**Decision:** Deferred - can be added later if there's clear user demand.

## Implementation Status

✅ **Current implementation matches this decision:**
- All RAG capabilities have dedicated MCP tools
- Tools are well-documented with clear descriptions
- Parameters are optimized for each use case
- Progressive disclosure via `search_tools` is implemented
- Tools are organized by project in code and documentation

## Related Documentation

- [MCP Troubleshooting Skill](../../.cursor/skills/mcp-troubleshooting/SKILL.md) - MCP connection guide
- [RAG Functionality Documentation](./RAG_FUNCTIONALITY.md) - RAG system details
- [Lambda AGENTS.md](../AGENTS.md) - MCP tool design guidelines

## Future Considerations

If we see patterns where users frequently:
1. Need to combine results from multiple RAG systems
2. Struggle to choose between similar tools
3. Request a "smart search" that routes automatically

Then we should reconsider adding a unified router tool as an **optional convenience layer** alongside existing specialized tools.

## Conclusion

The current architecture of separate, specialized MCP tools for each RAG capability is the optimal approach. It follows MCP best practices, provides better UX for LLMs, and maintains flexibility for future enhancements.
