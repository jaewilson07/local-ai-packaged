# Knowledge Base Project - AGENTS.md

> AI-augmented, crowdsourced knowledge refinement system.

## Project Overview

The Knowledge Base project provides an interactive system for collaborative knowledge management:

- **Article Management**: CRUD operations for markdown articles with version history
- **Proposal Workflow**: Users can propose edits that require owner approval
- **RAG Integration**: Semantic search using MongoDB vector embeddings
- **Notification System**: In-app notifications for proposal activity

## Architecture

```
Gradio UI (03-apps/gradio-kb/)
    ↓ HTTP API
Lambda API (04-lambda/server/api/knowledge_base.py)
    ↓
Services Layer
    ├── ArticleService - CRUD, embedding generation, versioning
    ├── ProposalService - Edit proposals, approval workflow
    ├── ChatService - RAG-enhanced conversation
    └── NotificationService - In-app notifications
    ↓
MongoDB (knowledge_base database)
    ├── articles collection
    ├── proposals collection
    └── notifications collection
```

## Key Files

### Lambda API
- `server/api/knowledge_base.py` - REST API endpoints
- `server/projects/knowledge_base/models.py` - Pydantic models
- `server/projects/knowledge_base/config.py` - Configuration
- `server/projects/knowledge_base/services/` - Service layer

### Gradio UI
- `03-apps/gradio-kb/app.py` - Main Gradio application
- `03-apps/gradio-kb/components/` - UI components
- `03-apps/gradio-kb/services/api_client.py` - Lambda API client

## Data Models

### Article

```python
{
    "_id": ObjectId,
    "slug": "optimizing-magic-etl",
    "title": "Optimizing Performance of Magic ETL",
    "content": "# Markdown content...",
    "content_embedding": [0.1, 0.2, ...],  # Vector for RAG
    "author_email": "owner@example.com",
    "source_url": "https://original.source/...",
    "source_type": "manual|import|web_crawl|...",
    "tags": ["etl", "performance"],
    "version": 3,
    "version_history": [...],
    "created_at": datetime,
    "updated_at": datetime,
}
```

### Proposal

```python
{
    "_id": ObjectId,
    "article_id": "...",
    "proposer_email": "contributor@example.com",
    "original_content": "...",
    "proposed_content": "...",
    "change_reason": "Updated for new API version",
    "supporting_sources": ["https://..."],
    "status": "pending|under_review|approved|rejected|needs_revision",
    "reviewer_email": "owner@example.com",
    "reviewer_notes": "...",
}
```

## API Endpoints

### Articles
- `GET /api/v1/kb/articles` - List articles (paginated)
- `GET /api/v1/kb/articles/{id}` - Get article by ID
- `POST /api/v1/kb/articles` - Create article
- `PUT /api/v1/kb/articles/{id}` - Update article (owner only)
- `DELETE /api/v1/kb/articles/{id}` - Delete article (owner only)
- `POST /api/v1/kb/search` - Semantic search

### Proposals
- `GET /api/v1/kb/proposals/mine` - User's submitted proposals
- `GET /api/v1/kb/proposals/review` - Pending proposals for review
- `POST /api/v1/kb/proposals` - Submit proposal
- `POST /api/v1/kb/proposals/{id}/review` - Review proposal

### Chat
- `POST /api/v1/kb/chat` - RAG-enhanced chat query
- `POST /api/v1/kb/fetch-url` - Fetch URL content

### Notifications
- `GET /api/v1/kb/notifications` - Get user notifications
- `POST /api/v1/kb/notifications/{id}/read` - Mark as read

## Proposal Workflow

```
1. User views article, clicks "Propose Edit"
2. User modifies content, provides reason and sources
3. Proposal created with status=pending
4. Article owner notified
5. Owner reviews: approve | reject | request_changes
6. If approved: content updated, new version created, re-indexed
7. Proposer notified of decision
```

## Integration Points

- **MongoDB RAG**: Uses same embedding infrastructure as mongo_rag project
- **SearXNG**: Web search for supplementary context
- **Crawl4AI**: Fetch and parse external URLs
- **n8n**: Optional webhook for email notifications
- **Discord**: Optional webhook for team notifications

## Configuration

Environment variables:
- `MONGODB_URI` - MongoDB connection string
- `MONGODB_DATABASE` - Database name (default: knowledge_base)
- `OPENAI_API_KEY` - For embeddings
- `EMBEDDING_MODEL` - Embedding model (default: text-embedding-3-small)
- `LLM_MODEL` - Chat model (default: gpt-4o-mini)
- `SEARXNG_URL` - SearXNG instance URL

## MongoDB Indexes

Required indexes for the articles collection:

```javascript
// Vector search index (Atlas)
{
  "name": "article_vector_index",
  "definition": {
    "mappings": {
      "dynamic": true,
      "fields": {
        "content_embedding": {
          "type": "knnVector",
          "dimensions": 1536,
          "similarity": "cosine"
        }
      }
    }
  }
}

// Standard indexes
db.articles.createIndex({ "slug": 1 }, { unique: true })
db.articles.createIndex({ "author_email": 1 })
db.articles.createIndex({ "tags": 1 })
db.articles.createIndex({ "updated_at": -1 })

db.proposals.createIndex({ "article_id": 1, "status": 1 })
db.proposals.createIndex({ "proposer_email": 1 })

db.notifications.createIndex({ "user_email": 1, "read": 1 })
```

## Testing

```bash
# Test article creation
curl -X POST http://localhost:8000/api/v1/kb/articles \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Article", "content": "# Test\n\nHello world"}'

# Test search
curl -X POST http://localhost:8000/api/v1/kb/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to optimize", "match_count": 5}'

# Test chat
curl -X POST http://localhost:8000/api/v1/kb/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I optimize ETL?", "rag_results": []}'
```
