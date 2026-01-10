# Persona/Character Management System - Analysis

## Overview

The persona management system from wandering-athena provides sophisticated character/persona management with mood tracking, relationship management, conversation context tracking, and dynamic voice instruction generation. It uses LangGraph for orchestration and supports multiple persona stores.

## Current Implementation in wandering-athena

**Location**: `src/capabilities/persona/`

### Key Components

1. **PersonaOrchestrator** (`orchestrator.py`)
   - LangGraph-based persona state management
   - Mood tracking and updates
   - Relationship state management
   - Conversation context tracking
   - Voice instruction generation

2. **PersonaServiceAgent** (`agent.py`)
   - Pydantic AI wrapper for persona orchestrator
   - High-level API for persona operations
   - Voice instruction generation
   - Interaction recording

3. **State Models** (`state.py`)
   - `Personality`: Base personality definition (identity, behavior, preferences)
   - `MoodState`: Current emotional state (emotion, intensity)
   - `RelationshipState`: User relationship (affection, trust, interaction count)
   - `ConversationContext`: Conversation mode and depth
   - `PersonaState`: Complete stateful persona representation
   - `PersonaSubgraphState`: LangGraph state model

4. **Protocols** (`protocols.py`)
   - `PersonaStore`: Protocol for swappable persona backends
   - Supports multiple storage implementations

5. **Actions** (`actions/`)
   - `track_mood.py`: Mood tracking from interactions
   - `track_relationship.py`: Relationship updates from interactions
   - `track_context.py`: Conversation context updates

### Key Features

- **Personality Profiles**: JSON-based personality definitions with identity, behavior, and preferences
- **Mood Tracking**: Dynamic emotional state based on interactions
- **Relationship Management**: Affection scores, trust levels, interaction counts
- **Conversation Context**: Mode (deep_empathy, casual_chat, storytelling, etc.) and depth level
- **Voice Instructions**: Dynamic style instructions generated from current state
- **Interaction Recording**: Automatic state updates from user-bot interactions
- **Multiple Persona Support**: Different personas for different interfaces (CLI, Discord)

## Current State in local-ai-packaged

### Existing Systems

- **Memory Systems**: Basic memory exists in MongoDB and Neo4j
- **Agent Systems**: Pydantic AI agents exist in `04-lambda/server/projects/`
- **Graphiti RAG**: Knowledge graph system exists

### Missing Capabilities

- No persona/character management system
- No mood or relationship tracking
- No conversation context tracking
- No dynamic voice instruction generation
- No personality profile management

## Integration Requirements

### Option 1: Add as Lambda Project

**Approach**: Create new project in `04-lambda/server/projects/persona/`

**Pros**:
- Matches wandering-athena pattern
- Can expose via REST API and MCP
- Independent service management
- Can integrate with existing memory systems

**Cons**:
- Requires LangGraph (if using orchestrator pattern)
- May need adaptation to Pydantic AI pattern (local-ai-packaged uses Pydantic AI, not LangGraph)

**Implementation Steps**:
1. Create `04-lambda/server/projects/persona/` directory
2. Port state models and protocols
3. Adapt orchestrator to Pydantic AI pattern (or use LangGraph if available)
4. Create persona store implementations (MongoDB, Neo4j, file-based)
5. Add REST API endpoints
6. Add MCP tools
7. Integrate with existing memory systems

### Option 2: Integrate with Existing Memory Systems

**Approach**: Extend existing memory systems with persona capabilities

**Pros**:
- Leverages existing infrastructure
- Unified data storage
- Simpler architecture

**Cons**:
- May complicate existing memory systems
- Less modular

## Dependencies

### Required Python Packages

```python
# Core
pydantic>=2.0.0        # State models (already in local-ai-packaged)
pydantic-ai>=0.1.0     # Agent framework (already in local-ai-packaged)

# Optional (for LangGraph orchestrator)
langgraph>=0.1.0       # If using LangGraph pattern
langchain-core>=0.1.0  # If using LangGraph

# Storage
motor>=3.0.0          # MongoDB async driver (already in local-ai-packaged)
neo4j>=5.0.0          # Neo4j driver (already in local-ai-packaged)
```

### Storage Requirements

- **Personality Profiles**: JSON files or database storage
- **Mood State**: Per user-persona pair, timestamped
- **Relationship State**: Per user-persona pair, with scores and counts
- **Conversation Context**: Per user-persona pair, current mode and depth

## Code Reference

### Key Classes from wandering-athena

```python
# Personality definition
personality = Personality(
    id="jarvis",
    name="Jarvis",
    byline="Your helpful AI assistant",
    identity=["intelligent", "helpful", "professional"],
    behavior=["responds clearly", "provides detailed explanations"],
    seed_preferences=SeedPreferences(
        communication_style="friendly and helpful",
        formality="balanced",
    ),
)

# Voice instruction generation
orchestrator = PersonaOrchestrator(persona_store=store)
result = await orchestrator.execute({
    "user_id": "user123",
    "persona_id": "jarvis",
    "query": "get_voice_instructions",
})

# Interaction recording
await orchestrator.execute({
    "user_id": "user123",
    "persona_id": "jarvis",
    "query": "record_interaction",
    "user_message": "Hello!",
    "bot_response": "Hi there!",
})
```

## Integration Points

### With Existing Services

1. **Memory Systems** (`04-lambda/server/projects/mongo_rag/`, `graphiti_rag/`)
   - Can store persona state in MongoDB
   - Can use Neo4j for relationship graphs
   - Can integrate with existing fact storage

2. **Lambda Stack** (`04-lambda/`)
   - Can add as new project
   - Can expose via REST API
   - Can expose via MCP tools
   - Can integrate with existing agent systems

3. **Agent Systems**
   - Can enhance existing Pydantic AI agents with persona awareness
   - Can inject voice instructions into system prompts
   - Can track interactions automatically

## Recommended Approach

**Phase 1**: Add as Lambda project with Pydantic AI adaptation
- Create `04-lambda/server/projects/persona/`
- Port state models (Personality, MoodState, RelationshipState, etc.)
- Create Pydantic AI agent (adapt from LangGraph orchestrator)
- Create MongoDB persona store implementation
- Add REST API endpoints
- Add MCP tools

**Phase 2**: Integration
- Integrate with existing memory systems
- Add automatic interaction tracking
- Add voice instruction injection to agents

**Phase 3**: Advanced features
- Add Neo4j relationship graph
- Add personality profile management UI
- Add mood/relationship visualization

## Implementation Checklist

- [ ] Create project directory structure
- [ ] Port state models (Personality, MoodState, RelationshipState, etc.)
- [ ] Create PersonaStore protocol
- [ ] Create MongoDB persona store implementation
- [ ] Create Pydantic AI agent (adapt from LangGraph orchestrator)
- [ ] Port mood tracking actions
- [ ] Port relationship tracking actions
- [ ] Port context tracking actions
- [ ] Add REST API endpoints
- [ ] Add MCP tool definitions
- [ ] Integrate with existing memory systems
- [ ] Add environment variables for configuration
- [ ] Create documentation
- [ ] Add tests
- [ ] Update README

## Notes

- Persona system uses LangGraph in wandering-athena, but local-ai-packaged uses Pydantic AI
- Need to adapt orchestrator pattern to Pydantic AI agent pattern
- Can use existing MongoDB/Neo4j infrastructure for storage
- Voice instructions are generated dynamically based on current state
- Mood and relationship tracking requires LLM analysis of interactions
- Consider using existing agent systems for mood/relationship analysis
- Personality profiles can be stored as JSON files or in database
- Multiple personas can be active simultaneously (one per interface)
