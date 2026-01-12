# Knowledge Project

Event extraction from web content using regex patterns and LLM-based extraction.

## Overview

This project provides capabilities for extracting structured event information from web content (HTML, markdown, or plain text). It supports both fast regex-based extraction and accurate LLM-based extraction.

## Features

- **Event Extraction**: Extract event details (title, date, time, location, instructor) from web content
- **Dual Extraction Modes**: 
  - Regex-based extraction (fast, pattern-based)
  - LLM-based extraction (accurate, semantic understanding)
- **Batch Processing**: Extract events from multiple crawled pages
- **Structured Output**: Returns structured event data with validation

## Architecture

This project follows the Service vs Capability Architecture pattern:

- **`config.py`**: Project-specific configuration (LLM settings)
- **`dependencies.py`**: `KnowledgeDeps` class inheriting from `BaseDependencies`
- **`tools.py`**: Core capability functions (`extract_events_from_content`, `extract_events_from_crawled_pages`)
- **`agent.py`**: `KnowledgeAgent` with agent tools for event extraction
- **`models.py`**: Pydantic models for request/response validation
- **REST API**: `server/api/knowledge.py` - REST endpoints using tools
- **MCP Tools**: Exposed via `fastmcp_server.py` for inter-agent communication

## API Endpoints

### Extract Events from Content
```
POST /api/v1/knowledge/extract-events
Content-Type: application/json

{
  "content": "<html>...</html>",
  "url": "https://example.com/events",
  "use_llm": false
}
```

### Extract Events from Crawled Pages
```
POST /api/v1/knowledge/extract-events-from-crawled
Content-Type: application/json

{
  "crawled_pages": [
    {"url": "https://example.com/page1", "content": "..."},
    {"url": "https://example.com/page2", "content": "..."}
  ],
  "use_llm": false
}
```

## Agent Tools

The `KnowledgeAgent` provides the following tools:

- `extract_events_from_content`: Extract events from web content
- `extract_events_from_crawled_pages`: Extract events from multiple crawled pages

## MCP Tools

The following MCP tools are available:

- `extract_events_from_content`: Extract events from web content
- `extract_events_from_crawled`: Extract events from multiple crawled pages

## Usage Examples

### Using Tools Directly

```python
from server.projects.knowledge.dependencies import KnowledgeDeps
from server.projects.knowledge.tools import extract_events_from_content
from server.projects.shared.context_helpers import create_run_context

deps = KnowledgeDeps.get_instance()
await deps.initialize()

try:
    ctx = create_run_context(deps)
    events = await extract_events_from_content(
        ctx=ctx,
        content="<html>...</html>",
        url="https://example.com/events",
        use_llm=False
    )
finally:
    await deps.cleanup()
```

### Using the Agent

```python
from server.projects.knowledge.agent import KnowledgeAgent

agent = KnowledgeAgent()
result = await agent.run(
    "Extract events from this content: <html>...</html>",
    deps=KnowledgeDeps.get_instance()
)
```

## Configuration

Environment variables:

- `LLM_API_KEY`: Optional API key for LLM-based extraction
- `LLM_BASE_URL`: LLM API base URL (default: `http://ollama:11434/v1`)
- `USE_LLM_FOR_EXTRACTION`: Use LLM by default (default: `false`)

## Integration

This project is used by:

- **Crawl4AI RAG**: Extracts events from crawled web pages
- **Future projects**: Any project needing event extraction from web content

## Dependencies

- `server.projects.shared.dependencies.BaseDependencies`: Base dependencies class
- `server.projects.knowledge.event_extractor.EventExtractor`: Core extraction logic
