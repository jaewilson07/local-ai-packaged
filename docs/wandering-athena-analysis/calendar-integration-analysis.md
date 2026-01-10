# Calendar Integration - Analysis

## Overview

The calendar integration from wandering-athena provides Google Calendar sync capabilities with event CRUD operations, duplicate prevention, sync state tracking, and integration with memory systems. It uses the Google Calendar API v3 and supports OAuth2 authentication.

## Current Implementation in wandering-athena

**Location**: `src/capabilities/calendar/`

### Key Components

1. **CalendarOrchestrator** (`orchestrator.py`)
   - Simple orchestrator for calendar operations
   - CRUD operations (create, read, update, delete)
   - No LangGraph subgraph (simple CRUD doesn't need it)

2. **GoogleCalendarSyncService** (`implementations/google_calendar.py`)
   - One-way sync to Google Calendar
   - Duplicate prevention using sync state tracking
   - Idempotent sync operations
   - Error handling and retry logic
   - Base32hex event ID generation
   - Calendar ID normalization (base64 decoding)

3. **Calendar Tools** (`tools.py`)
   - `upsert_calendar_event`: Create or update events
   - `_create_event`: Create new events
   - `_update_event`: Update existing events

4. **Protocols** (`protocols.py`)
   - `CalendarSync`: Protocol for swappable calendar backends
   - Supports different calendar providers

### Key Features

- **Google Calendar Integration**: Full CRUD operations via Google Calendar API v3
- **OAuth2 Authentication**: Supports credentials from files or environment variables
- **Duplicate Prevention**: Tracks sync state to prevent duplicate events
- **Sync State Tracking**: Stores sync state in database (Supabase)
- **Idempotent Operations**: Safe to retry failed operations
- **Event ID Management**: Custom base32hex event IDs for consistency
- **Calendar ID Support**: Handles base64-encoded calendar IDs from URLs
- **Error Handling**: Comprehensive error handling with retry logic

## Current State in local-ai-packaged

### Existing Systems

- **Memory Systems**: MongoDB and Neo4j exist
- **Lambda Stack**: FastAPI server with MCP support
- **Workflow Systems**: n8n exists for automation

### Missing Capabilities

- No calendar integration
- No event management capabilities
- No Google Calendar sync
- No event extraction from web content (separate feature)

## Integration Requirements

### Option 1: Add as Lambda Project

**Approach**: Create new project in `04-lambda/server/projects/calendar/`

**Pros**:
- Matches wandering-athena pattern
- Can expose via REST API and MCP
- Independent service management
- Can integrate with existing memory systems

**Cons**:
- Requires Google OAuth2 setup
- Needs database table for sync state

**Implementation Steps**:
1. Create `04-lambda/server/projects/calendar/` directory
2. Port GoogleCalendarSyncService
3. Create CalendarOrchestrator (simplified, no LangGraph)
4. Create calendar store implementations (MongoDB, Supabase)
5. Add REST API endpoints
6. Add MCP tools
7. Create database schema for sync state
8. Add OAuth2 authentication flow

### Option 2: Integrate with n8n

**Approach**: Use n8n for calendar operations

**Pros**:
- Leverages existing n8n infrastructure
- Visual workflow builder
- Already has Google Calendar nodes

**Cons**:
- Less programmatic control
- Different pattern from wandering-athena

## Dependencies

### Required Python Packages

```python
# Google Calendar API
google-api-python-client>=2.0.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=1.0.0

# Core (already in local-ai-packaged)
pydantic>=2.0.0        # State models
motor>=3.0.0          # MongoDB async driver (if using MongoDB for sync state)
```

### Google OAuth2 Setup

- **Credentials**: OAuth2 client credentials from Google Cloud Console
- **Scopes**: `https://www.googleapis.com/auth/calendar`
- **Token Storage**: OAuth2 token file or environment variable
- **Database**: Table for sync state tracking (calendar_sync_state)

## Code Reference

### Key Functions from wandering-athena

```python
# Sync event to Google Calendar
result = await sync_service.sync_event_to_google_calendar(
    user_id="user123",
    persona_id="persona1",
    local_event_id="event_123",
    event_data={
        "summary": "Meeting",
        "start": "2024-01-01T10:00:00",
        "end": "2024-01-01T11:00:00",
        "location": "Office",
    },
    calendar_id="primary",
)

# Upsert event (create or update)
result = await upsert_calendar_event(
    sync_service=sync_service,
    user_id="user123",
    persona_id="persona1",
    local_event_id="event_123",
    event_data=event_data,
)

# List events
events = await sync_service.list_events(
    user_id="user123",
    calendar_id="primary",
    start_time="2024-01-01T00:00:00",
    end_time="2024-01-31T23:59:59",
)
```

## Integration Points

### With Existing Services

1. **Lambda Stack** (`04-lambda/`)
   - Can add as new project
   - Can expose via REST API
   - Can expose via MCP tools
   - Can integrate with existing memory systems

2. **Memory Systems** (`04-lambda/server/projects/mongo_rag/`)
   - Can store sync state in MongoDB
   - Can use Supabase for sync state (if available)
   - Can integrate with existing fact storage

3. **Event Extraction** (separate feature)
   - Can integrate with calendar system
   - Can automatically create events from extracted data

4. **n8n** (`03-apps/n8n/`)
   - Can trigger calendar operations from workflows
   - Can use calendar events as workflow triggers

## Database Schema

### Sync State Table

```sql
CREATE TABLE calendar_sync_state (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    local_event_id TEXT NOT NULL,
    gcal_event_id TEXT,
    gcal_calendar_id TEXT,
    sync_status TEXT NOT NULL, -- 'pending', 'synced', 'failed', 'skipped'
    event_summary TEXT,
    event_start_time TIMESTAMP,
    event_end_time TIMESTAMP,
    event_location TEXT,
    event_data JSONB,
    sync_error TEXT,
    last_sync_attempt TIMESTAMP,
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, persona_id, local_event_id)
);
```

## Recommended Approach

**Phase 1**: Add as Lambda project
- Create `04-lambda/server/projects/calendar/`
- Port GoogleCalendarSyncService
- Create CalendarOrchestrator
- Create MongoDB sync state store
- Add REST API endpoints
- Add MCP tools

**Phase 2**: OAuth2 Setup
- Add OAuth2 authentication flow
- Support credentials from environment variables
- Add token refresh logic

**Phase 3**: Integration
- Integrate with event extraction
- Add n8n workflow integration
- Add webhook support

## Implementation Checklist

- [ ] Create project directory structure
- [ ] Port GoogleCalendarSyncService
- [ ] Create CalendarOrchestrator
- [ ] Create sync state store (MongoDB or Supabase)
- [ ] Create database schema for sync state
- [ ] Add OAuth2 authentication
- [ ] Add REST API endpoints
- [ ] Add MCP tool definitions
- [ ] Add environment variables for Google credentials
- [ ] Create documentation
- [ ] Add tests
- [ ] Update README

## Notes

- Google Calendar API requires OAuth2 authentication
- Sync state tracking prevents duplicate events
- Custom event IDs (base32hex) ensure consistency
- Calendar IDs from URLs may be base64-encoded and need normalization
- Duplicate detection checks summary and start time
- Sync state can be stored in MongoDB or Supabase
- Supports multiple calendars per user
- Error handling includes retry logic for robustness
- Can integrate with event extraction for automatic event creation
