# Conversation Orchestration - Analysis

## Overview

The conversation orchestration system from wandering-athena provides sophisticated LangGraph-based conversation flow with roleplay mode, tool orchestration, multi-stage planning, mode selection, and analysis nodes. It coordinates Memory, Knowledge, and Personality domains.

## Current Implementation in wandering-athena

**Location**: `src/capabilities/conversation/`

### Key Components

1. **ConversationOrchestrator** (`orchestrator.py`)
   - LangGraph-based conversation graph builder
   - Phase1 graph: ingest → tool_orchestrator → planner → responder → summary
   - Roleplay graph: ingest → analysis → tool_orchestrator → mode_selector → planner → responder → critic → safety → summary
   - Coordinates Memory, Knowledge, and Personality domains

2. **Nodes** (`nodes/`)
   - `ingest_node`: Process user input
   - `tool_orchestrator_node`: Route to tools or planner
   - `planner_node`: Generate response plan
   - `responder_node`: Generate response
   - `summary_node`: Summarize conversation
   - `roleplay.py`: Roleplay-specific nodes (analysis, mode_selector, critic, safety)

3. **Tool Orchestrator** (`nodes/tool_orchestrator.py`)
   - Routes between tool execution and planning
   - Determines when tools are needed
   - Coordinates tool execution

### Key Features

- **Multi-Stage Planning**: ingest → tool_orchestrator → planner → responder → summary
- **Tool Orchestration**: Automatic tool routing and execution
- **Roleplay Mode**: Enhanced graph with analysis, critic, and safety nodes
- **Mode Selection**: Different conversation modes (deep_empathy, casual_chat, storytelling, etc.)
- **Analysis Node**: Conversation understanding and analysis
- **Critic Node**: Response quality checking
- **Safety Node**: Content safety filtering

## Current State in local-ai-packaged

### Existing Agent Systems

- **MongoDB RAG Agent** (`04-lambda/src/capabilities/retrieval/mongo_rag/agent.py`)
  - Pydantic AI agent
  - Basic tool support
  - Simple conversation flow

- **Graphiti RAG Agent** (`04-lambda/src/capabilities/retrieval/graphiti_rag/agent.py`)
  - Pydantic AI agent
  - Knowledge graph tools
  - Simple conversation flow

### Missing Capabilities

- No sophisticated conversation orchestration
- No roleplay or multi-mode conversation support
- No tool orchestrator with routing logic
- No multi-stage planning
- No mode selector
- No analysis or critic nodes
- No safety filtering

## Integration Requirements

### Option 1: Enhance Existing Agents

**Approach**: Add orchestration features to existing Pydantic AI agents

**Pros**:
- Leverages existing infrastructure
- Maintains Pydantic AI pattern
- Simpler integration

**Cons**:
- Need to adapt LangGraph patterns to Pydantic AI
- May complicate existing code

**Implementation Steps**:
1. Add tool orchestrator to agents
2. Add multi-stage planning
3. Add mode selection
4. Add analysis and critic nodes (as tools or agent steps)
5. Add safety filtering

### Option 2: Create Conversation Project

**Approach**: Create new project `conversation` that orchestrates existing agents

**Pros**:
- Clean separation
- Can orchestrate multiple agents
- Easier to maintain

**Cons**:
- More complex architecture
- May duplicate some functionality

## Dependencies

### Required Python Packages

```python
# Core (already in local-ai-packaged)
pydantic-ai>=0.1.0     # Agent framework

# Optional (for LangGraph patterns)
langgraph>=0.1.0       # If using LangGraph orchestrator
langchain-core>=0.1.0  # If using LangGraph
```

## Code Reference

### Key Patterns from wandering-athena

```python
# Phase1 graph
graph.add_node("ingest", ingest_node)
graph.add_node("tool_orchestrator", tool_orchestrator_node)
graph.add_node("planner", planner_node)
graph.add_node("responder", responder_node)
graph.add_node("summary", summary_node)

# Roleplay graph
graph.add_node("analysis", roleplay_nodes.analysis_node)
graph.add_node("mode_selector", roleplay_nodes.mode_selector_node)
graph.add_node("critic", roleplay_nodes.critic_node)
graph.add_node("safety", roleplay_nodes.safety_node)
```

## Integration Points

### With Existing Services

1. **MongoDB RAG Agent** (`04-lambda/src/capabilities/retrieval/mongo_rag/`)
   - Can enhance with orchestration
   - Can add tool orchestrator
   - Can add multi-stage planning

2. **Graphiti RAG Agent** (`04-lambda/src/capabilities/retrieval/graphiti_rag/`)
   - Can enhance with orchestration
   - Can add mode selection
   - Can add analysis nodes

3. **Persona System** (if added)
   - Can integrate with conversation orchestration
   - Can use persona state for mode selection
   - Can use voice instructions

## Recommended Approach

**Phase 1**: Enhance Existing Agents
- Add tool orchestrator
- Add multi-stage planning
- Add mode selection (if persona system exists)

**Phase 2**: Add Advanced Features
- Add analysis nodes
- Add critic nodes
- Add safety filtering
- Add roleplay mode (if needed)

**Phase 3**: Integration
- Integrate with persona system
- Integrate with memory system
- Add orchestration layer

## Implementation Checklist

- [ ] Add tool orchestrator to agents
- [ ] Add multi-stage planning (ingest → planner → responder → summary)
- [ ] Add mode selection
- [ ] Add analysis nodes (as agent tools or steps)
- [ ] Add critic nodes (as agent tools or steps)
- [ ] Add safety filtering
- [ ] Add roleplay mode (optional)
- [ ] Integrate with persona system (if added)
- [ ] Add REST API endpoints
- [ ] Add MCP tool definitions
- [ ] Create documentation
- [ ] Add tests
- [ ] Update README

## Notes

- Conversation orchestration uses LangGraph in wandering-athena, but local-ai-packaged uses Pydantic AI
- Need to adapt orchestrator pattern to Pydantic AI agent pattern
- Tool orchestrator can be implemented as agent tool or separate service
- Multi-stage planning improves response quality
- Mode selection enables different conversation styles
- Analysis and critic nodes can be implemented as agent tools
- Safety filtering is important for production use
- Roleplay mode is optional and may not be needed for all use cases
