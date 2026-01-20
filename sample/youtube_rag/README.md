# YouTube RAG Samples

Sample scripts demonstrating YouTube video ingestion into the RAG knowledge base with Graphiti temporal episode support.

## Quick Start - Full Pipeline Demo

Run the complete pipeline in one command:

```bash
python sample/youtube_rag/full_pipeline_demo.py --url "https://www.youtube.com/watch?v=A3DKwLORVe4"
```

This demonstrates all three success criteria:
1. **Transcript Extraction**: Extracts and saves the full transcript with timestamps
2. **Graphiti Episodes**: Creates temporal episodes for the knowledge graph  
3. **Q&A Session**: Answers 5 questions about the video content

Output files are saved to `sample/youtube_rag/output/`.

## Features

- **Transcript Extraction**: Extract transcripts from YouTube videos with timestamps
- **MongoDB RAG**: Store video content as searchable chunks with embeddings
- **Graphiti Integration**: Create temporal episodes for smart time-based queries
- **Entity Extraction**: Extract named entities using LLM (optional)
- **Topic Classification**: Classify video topics using LLM (optional)

## Prerequisites

1. **MongoDB** running and accessible
2. **Neo4j** running (for Graphiti features)
3. **Ollama** with `qwen3-embedding:4b` model (for embeddings)
4. **YouTube dependencies** installed:

```bash
pip install youtube-transcript-api yt-dlp
```

## Sample Scripts

### 1. Ingest Video (`ingest_video.py`)

Ingest a YouTube video into the RAG knowledge base.

```bash
# Basic ingestion with transcript and chapters
python sample/youtube_rag/ingest_video.py --url "https://www.youtube.com/watch?v=A3DKwLORVe4"

# Get transcript only (no ingestion)
python sample/youtube_rag/ingest_video.py --url "https://youtube.com/watch?v=A3DKwLORVe4" --transcript-only

# Get metadata only
python sample/youtube_rag/ingest_video.py --url "https://youtube.com/watch?v=A3DKwLORVe4" --metadata-only

# Full extraction with LLM (requires OPENAI_API_KEY)
python sample/youtube_rag/ingest_video.py --url "https://youtube.com/watch?v=A3DKwLORVe4" \
  --extract-entities --extract-topics --extract-key-moments
```

### 2. Extract Graphiti Nodes (`extract_graphiti_nodes.py`)

View the temporal episodes and entities stored in Graphiti.

```bash
# List all YouTube episodes in Graphiti
python sample/youtube_rag/extract_graphiti_nodes.py

# List episodes for a specific video
python sample/youtube_rag/extract_graphiti_nodes.py --video-id A3DKwLORVe4

# Search knowledge graph
python sample/youtube_rag/extract_graphiti_nodes.py --query "machine learning"

# Extract entities and relationships for a video
python sample/youtube_rag/extract_graphiti_nodes.py --video-id A3DKwLORVe4 --entities
```

### 3. Q&A with Graphiti RAG (`graphiti_qa.py`)

Ask questions about ingested YouTube videos using the knowledge graph.

```bash
# Run predefined Q&A test suite
python sample/youtube_rag/graphiti_qa.py

# Q&A for specific video
python sample/youtube_rag/graphiti_qa.py --video-id A3DKwLORVe4

# Interactive Q&A mode
python sample/youtube_rag/graphiti_qa.py --interactive

# Use MongoDB RAG instead of Graphiti
python sample/youtube_rag/graphiti_qa.py --mongodb
```

## Success Criteria

After running the samples, you should have:

1. **Transcript Extract**: A complete transcript of the video with timestamps
2. **Graphiti Nodes**: Temporal episodes created in Neo4j (overview, chapters, key moments)
3. **Q&A Results**: 5 questions answered using the knowledge graph

## Example Output

The sample scripts generate output files in the `sample/youtube_rag/output/` directory.

### Transcript Extract (`transcript_A3DKwLORVe4.txt`)

```
[00:00] Hey folks, it's Sydney from LinkChain
[00:02] and I'm super excited to chat with you
[00:04] today about a specific application of
[00:06] context engineering and that is design
[00:08] decisions when building a multi-agent
[00:10] system with a sub agent architecture.
...
```

### Graphiti Episodes (`graphiti_episodes_A3DKwLORVe4.json`)

```json
[
  {
    "name": "youtube:A3DKwLORVe4:overview",
    "type": "overview",
    "description": "YouTube: LangChain",
    "reference_time": "2026-01-18T16:10:00.454887",
    "content_preview": "[00:00] Hey folks, it's Sydney from LinkChain..."
  },
  {
    "name": "youtube:A3DKwLORVe4:transcript",
    "type": "transcript",
    "description": "Full transcript: Building with Subagents: Design Decisions",
    "reference_time": "2026-01-18T16:10:00.454902"
  }
]
```

### Q&A Results (`qa_results_A3DKwLORVe4.json`)

```json
[
  {
    "question": "What is the main topic of this video?",
    "answer": "The video 'Building with Subagents: Design Decisions' by LangChain discusses building with subagents and the design decisions involved in multi-agent systems.",
    "source": "transcript_search"
  },
  {
    "question": "What architecture pattern is being discussed?",
    "answer": "The video discusses the subagent (also called supervisor) architecture, where a main agent delegates tasks to sub-agents in parallel and combines their results.",
    "source": "transcript_search"
  },
  {
    "question": "What are the key design decisions mentioned?",
    "answer": "Key design decisions mentioned:\n• Synchronous vs asynchronous sub-agent invocation\n• Tool design: single dispatch tool vs tool-per-subagent\n• Context engineering strategies",
    "source": "transcript_search"
  },
  {
    "question": "Who is the presenter and what company are they from?",
    "answer": "The presenter is Sydney from LangChain.",
    "source": "transcript_search"
  },
  {
    "question": "What are the benefits of the subagent pattern?",
    "answer": "The video discusses the subagent (also called supervisor) architecture, where a main agent delegates tasks to sub-agents in parallel and combines their results.",
    "source": "transcript_search"
  }
]
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb://mongodb:27017` |
| `NEO4J_URI` | Neo4j connection URI | `bolt://neo4j:7687` |
| `NEO4J_PASSWORD` | Neo4j password | Required |
| `OPENAI_API_KEY` | OpenAI API key (for entity extraction) | Optional |
| `USE_GRAPHITI` | Enable Graphiti integration | `true` |

## Troubleshooting

### "youtube-transcript-api not installed"

```bash
pip install youtube-transcript-api yt-dlp
```

### "MongoDB connection failed"

Ensure MongoDB is running and accessible. For local development with Docker:

```bash
# Check if MongoDB is running
docker ps | grep mongodb

# Start MongoDB if needed
cd 01-data/mongodb && docker compose up -d
```

### "Graphiti not initialized"

Ensure Neo4j is running and configured:

```bash
# Check Neo4j status
docker ps | grep neo4j

# Set required environment variables
export NEO4J_URI=bolt://localhost:7687
export NEO4J_PASSWORD=your_password
```

### "No transcript available"

Some videos don't have transcripts (private videos, age-restricted, etc.). Try a different video.
