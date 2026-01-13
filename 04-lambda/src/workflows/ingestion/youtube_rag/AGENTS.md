# YouTube RAG Project - AGENTS.md

> **Parent**: See [04-lambda/AGENTS.md](../../AGENTS.md) for Lambda stack conventions.

## Overview

The YouTube RAG project provides tools to ingest YouTube videos into the MongoDB RAG knowledge base. It extracts transcripts, metadata, chapters, and optionally uses LLM to extract entities, topics, and key moments.

## Architecture

```
youtube_rag/
├── __init__.py
├── AGENTS.md              # This file
├── config.py              # Configuration settings
├── dependencies.py        # YouTubeRAGDeps class
├── models.py              # Pydantic models
├── tools.py               # Core tool functions
├── services/
│   ├── __init__.py
│   ├── youtube_client.py  # YouTube API client
│   └── extractors/
│       ├── __init__.py
│       ├── chapters.py    # Chapter extraction
│       ├── entities.py    # Entity extraction (LLM)
│       └── topics.py      # Topic classification (LLM)
└── ingestion/
    ├── __init__.py
    └── adapter.py         # YouTubeContentIngester
```

## Key Components

### YouTubeClient (`services/youtube_client.py`)

Core client for extracting data from YouTube videos:
- Uses `youtube-transcript-api` for transcript extraction
- Uses `yt-dlp` for metadata and chapter extraction
- Supports multiple YouTube URL formats
- Handles language fallbacks for transcripts

### Extractors (`services/extractors/`)

LLM-powered knowledge extraction:
- **ChapterExtractor**: Extracts chapters from video description or YouTube API
- **EntityExtractor**: Extracts named entities (people, products, concepts) using LLM
- **TopicExtractor**: Classifies videos into topic categories

### YouTubeContentIngester (`ingestion/adapter.py`)

Bridges YouTube content to MongoDB RAG:
- Reuses chunking and embedding from `mongo_rag` project
- Supports chapter-based or standard text chunking
- Integrates with Graphiti for knowledge graph (optional)

## Data Flow

```
YouTube URL
    │
    ▼
┌─────────────────────┐
│   YouTubeClient     │
│  - Extract video ID │
│  - Get metadata     │
│  - Get transcript   │
│  - Get chapters     │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│   Extractors        │
│  (optional, LLM)    │
│  - Entities         │
│  - Topics           │
│  - Key moments      │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ YouTubeContentIngester│
│  - Chunk transcript │
│  - Generate embeddings│
│  - Store in MongoDB │
│  - Store in Graphiti│
└─────────────────────┘
```

## Storage Schema

Documents stored with `source_type: "youtube"`:

```python
{
    "_id": ObjectId,
    "title": "Video Title",
    "source": "https://youtube.com/watch?v=...",
    "content": "Full transcript with chapter markers...",
    "metadata": {
        "source_type": "youtube",
        "video_id": "VIDEO_ID",
        "channel_name": "Channel Name",
        "channel_id": "UC...",
        "upload_date": "20240115",
        "duration_seconds": 1234,
        "view_count": 50000,
        "like_count": 1200,
        "tags": ["tag1", "tag2"],
        "thumbnail_url": "https://...",
        "chapters": [
            {"title": "Intro", "start_time": 0, "end_time": 60},
            ...
        ],
        "entities": [
            {"name": "OpenAI", "type": "organization", "mentions": 5},
            ...
        ],
        "topics": ["AI/Machine Learning", "Programming"],
        "transcript_language": "en",
        "transcript_is_generated": false,
    },
    "created_at": datetime,
}
```

## MCP Tools

### `ingest_youtube_video`
Ingest a YouTube video into the knowledge base.

**Parameters:**
- `url` (required): YouTube video URL
- `extract_chapters`: Extract chapter markers (default: true)
- `extract_entities`: Use LLM to extract entities (default: false)
- `extract_topics`: Use LLM to classify topics (default: false)
- `extract_key_moments`: Use LLM to identify key moments (default: false)
- `chunk_by_chapters`: Chunk by chapters if available (default: true)
- `chunk_size`: Chunk size for splitting (default: 1000)
- `chunk_overlap`: Chunk overlap (default: 200)
- `preferred_language`: Preferred transcript language

### `get_youtube_metadata`
Get video metadata without ingesting.

**Parameters:**
- `url` (required): YouTube video URL
- `include_transcript`: Also fetch transcript (default: false)

### `search_youtube_videos`
Search ingested YouTube videos.

**Parameters:**
- `query` (required): Search query
- `match_count`: Number of results (default: 5)
- `search_type`: "semantic", "text", or "hybrid" (default: "hybrid")
- `channel_filter`: Filter by channel name

## REST API Endpoints

- `POST /api/v1/youtube/ingest` - Ingest a YouTube video
- `POST /api/v1/youtube/metadata` - Get video metadata
- `GET /api/v1/youtube/health` - Health check

## Configuration

Environment variables:
- `MONGODB_URI`: MongoDB connection string
- `MONGODB_DATABASE`: Database name (default: "rag")
- `YOUTUBE_TRANSCRIPT_LANGUAGE`: Default transcript language (default: "en")
- `YOUTUBE_FALLBACK_LANGUAGES`: Comma-separated fallback languages
- `YOUTUBE_LLM_MODEL`: Model for LLM extractors (default: "gpt-4o-mini")
- `OPENAI_API_KEY`: Required for LLM extractors
- `USE_GRAPHITI`: Enable Graphiti integration (default: true)

## Dependencies

- `youtube-transcript-api>=0.6.2` - Transcript extraction
- `yt-dlp>=2024.1.0` - Metadata and chapter extraction

## Chunking Strategies

### Chapter-Based Chunking (Default)
When chapters are available and `chunk_by_chapters=true`:
- Each chapter becomes a separate chunk
- Preserves semantic boundaries
- Chunks include chapter title in metadata

### Standard Chunking
When chapters unavailable or `chunk_by_chapters=false`:
- Uses standard text chunking from `mongo_rag`
- Respects `chunk_size` and `chunk_overlap` settings

## Knowledge Extraction Tiers

### Tier 1: Core (Always Extracted)
- Video metadata (title, channel, duration, views, etc.)
- Transcript with timestamps
- Chapter markers (if available from YouTube)

### Tier 2: Enhanced (Optional, LLM-powered)
- Entity extraction (people, organizations, products, concepts)
- Topic classification
- Key moments with timestamps
- Entity relationships

### Tier 3: Advanced (Future)
- Speaker diarization
- Visual scene detection
- OCR from video frames

## Error Handling

The project uses structured exceptions:
- `YouTubeClientError`: Base exception
- `VideoNotFoundError`: Video unavailable or private
- `TranscriptNotAvailableError`: No transcript available

All errors are captured and returned in the response's `errors` array.

## Search Hints

```bash
# Find YouTube RAG files
rg -l "youtube" 04-lambda/server/projects/youtube_rag/

# Find MCP tool registration
rg -n "ingest_youtube_video" 04-lambda/server/mcp/

# Find entity extraction
rg -n "extract_entities" 04-lambda/server/projects/youtube_rag/
```
