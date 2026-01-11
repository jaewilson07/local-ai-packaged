# Event Extraction Tool - Analysis

## Overview

The event extraction tool from wandering-athena extracts event information from web content, parses event details (title, date, time, location, instructor), and integrates with the calendar system. It's implemented as a knowledge tool that runs after web crawling.

## Current Implementation in wandering-athena

**Location**: `src/capabilities/knowledge/actions/event_extractor.py`

### Key Components

1. **EventExtractionTool** (`event_extractor.py`)
   - Knowledge tool for event extraction
   - Extracts events from crawled content
   - Parses event details using regex (simplified)
   - Stores events in memory
   - Integrates with calendar system

### Key Features

- **Event Extraction**: Extracts events from web content
- **Detail Parsing**: Parses title, date, time, location, instructor
- **Memory Storage**: Stores extracted events as facts
- **Calendar Integration**: Can trigger calendar sync
- **Tool Registry**: Integrated with knowledge tool registry
- **Trigger Keywords**: Automatically runs on relevant queries

## Current State in local-ai-packaged

### Existing Systems

- **Crawl4AI RAG** (`04-lambda/server/projects/crawl4ai_rag/`)
  - Web crawling capabilities via MCP
  - No event extraction

- **Knowledge RAG Systems**: MongoDB RAG, Graphiti RAG
  - No event extraction capabilities

- **Calendar System**: Not yet implemented (separate feature)

### Missing Capabilities

- No event extraction from web content
- No event parsing (title, date, time, location, instructor)
- No web-to-calendar workflow
- No event validation and formatting

## Integration Requirements

### Option 1: Add to Knowledge RAG Systems

**Approach**: Add event extraction to existing MongoDB RAG or Graphiti RAG

**Pros**:
- Leverages existing infrastructure
- Can use existing web crawling
- Unified knowledge system

**Cons**:
- May complicate existing code
- Need to add parsing logic

**Implementation Steps**:
1. Add event extraction tool to knowledge RAG
2. Add event parsing logic
3. Integrate with calendar system (when available)
4. Add REST API endpoints
5. Add MCP tools

### Option 2: Create Event Extraction Project

**Approach**: Create new project `event_extraction` that works with knowledge RAG

**Pros**:
- Clean separation
- Can work with multiple RAG systems
- Easier to maintain

**Cons**:
- More complex architecture
- May duplicate some functionality

## Dependencies

### Required Python Packages

```python
# Core (already in local-ai-packaged)
pydantic>=2.0.0        # Event models
pydantic-ai>=0.1.0     # Agent framework (if using agent-based extraction)

# Optional (for LLM-based extraction)
openai>=1.0.0          # If using LLM for better extraction
```

## Code Reference

### Key Functions from wandering-athena

```python
# Event extraction tool
class EventExtractionTool(KnowledgeTool):
    def should_run(self, state, query):
        # Check for trigger keywords and crawled content
        return has_keyword and has_crawled_content

    async def execute(self, state):
        # Extract events from crawled content
        events = []
        for crawled_page in state.crawled_content:
            event_info = self._extract_event_info(
                crawled_page["content_markdown"],
                crawled_page["url"]
            )
            if event_info:
                events.append(event_info)

        # Store in memory
        for event in events:
            memory.remember_fact(
                user_id=state.user_id,
                persona_id=state.persona_id,
                fact=f"Event: {event['title']} at {event['location']} on {event['date']}",
                tags=["event", "calendar"],
            )

        return state

# Event parsing (simplified - use LLM in production)
def _extract_event_info(self, content, url):
    # Regex-based extraction (simplified)
    # In production, use LLM with structured output
    title_match = re.search(r"(?:title|event|class):\s*([^\n]+)", content)
    date_match = re.search(r"(?:date|when):\s*([^\n]+)", content)
    # ... etc
```

## Integration Points

### With Existing Services

1. **Crawl4AI RAG** (`04-lambda/server/projects/crawl4ai_rag/`)
   - Can add event extraction after crawling
   - Can use crawled content for extraction
   - Can integrate with knowledge base

2. **Knowledge RAG Systems** (`04-lambda/server/projects/mongo_rag/`, `graphiti_rag/`)
   - Can add event extraction tool
   - Can store events in knowledge base
   - Can search for events

3. **Calendar System** (when implemented)
   - Can automatically create events from extracted data
   - Can sync events to Google Calendar
   - Can validate event data

4. **Lambda Stack** (`04-lambda/`)
   - Can add as tool to existing agents
   - Can expose via REST API
   - Can expose via MCP tools

## Recommended Approach

**Phase 1**: Add to Knowledge RAG
- Add event extraction tool to MongoDB RAG or crawl4ai RAG
- Add event parsing logic (start with regex, upgrade to LLM)
- Store events in knowledge base
- Add REST API endpoints
- Add MCP tools

**Phase 2**: LLM-Based Extraction
- Upgrade to LLM-based extraction for better accuracy
- Use structured output for event parsing
- Add event validation

**Phase 3**: Calendar Integration
- Integrate with calendar system (when available)
- Add automatic event creation
- Add event sync to Google Calendar

## Implementation Checklist

- [ ] Add event extraction tool to knowledge RAG
- [ ] Add event parsing logic (regex-based initially)
- [ ] Create event data models (Pydantic)
- [ ] Add event storage in knowledge base
- [ ] Add REST API endpoints
- [ ] Add MCP tool definitions
- [ ] Upgrade to LLM-based extraction (optional)
- [ ] Add event validation
- [ ] Integrate with calendar system (when available)
- [ ] Create documentation
- [ ] Add tests
- [ ] Update README

## Notes

- Event extraction uses regex in wandering-athena (simplified)
- Production should use LLM with structured output for better accuracy
- Event extraction runs after web crawling
- Trigger keywords: "event", "calendar", "schedule", "sync calendar", "add to calendar"
- Events are stored as facts in memory
- Can integrate with calendar system for automatic event creation
- Event validation ensures data quality before calendar sync
- Consider using Pydantic models for event data structure
