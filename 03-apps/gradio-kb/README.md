# Gradio Knowledge Base

Interactive knowledge refinement system with RAG-powered chat and collaborative article editing.

## Overview

A split-screen Gradio UI where:
- **Left panel**: Article viewer with markdown rendering
- **Right panel**: Chat interface with RAG and web search

Users can:
1. Ask questions and get AI-generated answers with citations
2. Click citations to view source articles
3. Propose edits to improve articles
4. Track and manage their proposals

Article owners can:
1. Review proposed edits with diff view
2. Approve, reject, or request changes
3. Receive notifications about new proposals

## Features

- **RAG Search**: Semantic search across knowledge base
- **Web Search**: SearXNG integration for current information
- **Citation System**: Clickable citations that load articles
- **Version History**: Track all changes with full history
- **Approval Workflow**: Owner-gated edit proposals
- **Notifications**: In-app notifications for activity

## Running Locally

```bash
cd 03-apps/gradio-kb

# Install dependencies
pip install -r requirements.txt

# Set environment
export LAMBDA_API_URL=http://localhost:8000

# Run
python app.py
```

## Docker

The service is included in the apps stack:

```bash
# Build and run
docker compose -f 03-apps/docker-compose.yml up gradio-kb

# Or run entire stack
python start_services.py --stack apps
```

Access at: http://localhost:7860 (or https://kb.datacrew.space via tunnel)

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LAMBDA_API_URL` | `http://lambda-server:8000` | Lambda API endpoint |
| `GRADIO_SERVER_PORT` | `7860` | Gradio server port |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | Gradio server bind address |

## UI Components

### Article Viewer
- Markdown rendering with syntax highlighting
- Author/date/tags metadata display
- Version history access
- Edit proposal button

### Chat Interface
- Streaming chat responses
- Citation display with click-through
- Example questions
- Clear history

### Proposal System
- Side-by-side diff editor
- Change reason and sources
- Validation before submit
- Review queue for owners

## API Integration

The Gradio app communicates with these Lambda API endpoints:

- `/api/v1/kb/chat` - RAG-enhanced chat
- `/api/v1/kb/articles` - Article CRUD
- `/api/v1/kb/proposals` - Proposal management
- `/api/v1/kb/notifications` - Notification system
- `/api/v1/rag/search` - Knowledge base search
- `/api/v1/searxng/search` - Web search

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Gradio UI                          │
│  ┌─────────────────────┬─────────────────────────┐  │
│  │   Article Viewer    │    Chat Interface       │  │
│  │   ┌─────────────┐   │   ┌─────────────────┐   │  │
│  │   │  Markdown   │   │   │    Messages     │   │  │
│  │   │  Content    │   │   │    + Citations  │   │  │
│  │   └─────────────┘   │   └─────────────────┘   │  │
│  │   [Propose Edit]    │   [Ask a question...]   │  │
│  └─────────────────────┴─────────────────────────┘  │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP
                        ▼
┌─────────────────────────────────────────────────────┐
│               Lambda API Server                      │
│  /api/v1/kb/* endpoints                             │
│  ┌──────────┬──────────┬──────────┬──────────────┐  │
│  │ Articles │ Proposals│   Chat   │ Notifications │  │
│  └────┬─────┴────┬─────┴────┬─────┴──────┬───────┘  │
└───────┼──────────┼──────────┼────────────┼──────────┘
        │          │          │            │
        ▼          ▼          ▼            ▼
┌─────────────────────────────────────────────────────┐
│                    MongoDB                           │
│   articles | proposals | notifications              │
└─────────────────────────────────────────────────────┘
```

## Development

### Adding Components

Create new components in `components/`:

```python
# components/my_component.py
import gradio as gr

def create_my_component():
    with gr.Column() as container:
        # Your UI elements
        pass
    return {"container": container, ...}
```

### API Client Extensions

Add methods to `services/api_client.py`:

```python
async def my_new_endpoint(self, ...):
    client = await self._get_client()
    response = await client.post("/api/v1/kb/my-endpoint", json={...})
    response.raise_for_status()
    return response.json()
```

## Troubleshooting

### Chat not responding
- Check Lambda API is running: `curl http://localhost:8000/health`
- Check MongoDB connection in Lambda logs

### Articles not loading
- Verify article exists in MongoDB
- Check network connectivity between containers

### Proposals not saving
- Ensure user is authenticated
- Check proposal validation passes
