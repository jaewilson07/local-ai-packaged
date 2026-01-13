# YouTube RAG Samples

Sample scripts demonstrating the YouTube RAG functionality for ingesting YouTube videos into the MongoDB RAG knowledge base.

## Prerequisites

1. Ensure the Lambda server is running with MongoDB available
2. Install dependencies: `youtube-transcript-api` and `yt-dlp`

```bash
pip install youtube-transcript-api yt-dlp
```

## Sample Scripts

### `ingest_video.py`

Demonstrates ingesting a YouTube video into the RAG knowledge base.

**Basic Usage:**

```bash
# Get metadata only (no ingestion)
python sample/youtube_rag/ingest_video.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --metadata-only

# Basic ingestion with chapter extraction
python sample/youtube_rag/ingest_video.py --url "https://youtu.be/VIDEO_ID"

# Full extraction with entities, topics, and key moments (requires OPENAI_API_KEY)
python sample/youtube_rag/ingest_video.py \
    --url "https://www.youtube.com/watch?v=VIDEO_ID" \
    --extract-entities \
    --extract-topics \
    --extract-key-moments
```

**Options:**
- `--url`: YouTube video URL (supports various formats)
- `--metadata-only`: Only fetch metadata, don't ingest
- `--extract-entities`: Use LLM to extract named entities (slower)
- `--extract-topics`: Use LLM to classify video topics
- `--extract-key-moments`: Use LLM to identify key moments

## Supported URL Formats

The YouTube client supports multiple URL formats:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- `https://m.youtube.com/watch?v=VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`

## Output

After ingestion, you can search for the video content using the standard RAG search tools:

```python
# Search for specific content
result = await search_knowledge_base(
    query="Your search query",
    search_type="hybrid"
)

# Search only YouTube videos
result = await search_youtube_videos(
    query="Your search query",
    channel_filter="Channel Name"  # Optional
)
```

## Environment Variables

- `MONGODB_URI`: MongoDB connection string (default: `mongodb://mongodb:27017`)
- `MONGODB_DATABASE`: Database name (default: `rag`)
- `YOUTUBE_TRANSCRIPT_LANGUAGE`: Default transcript language (default: `en`)
- `OPENAI_API_KEY`: Required for LLM-based extraction (entities, topics, key moments)
