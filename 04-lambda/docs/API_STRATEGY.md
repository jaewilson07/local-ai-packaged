# API Strategy Documentation

> Central documentation for Lambda server API routing standards, error handling, and capability/workflow integration.

## Related Documentation

- [Root AGENTS.md](../../AGENTS.md) - Project architecture and conventions
- [Lambda AGENTS.md](../AGENTS.md) - Lambda server patterns and guidelines
- [Auth README](../src/services/auth/README.md) - Authentication system documentation
- [FastAPI Skill](../../.cursor/skills/fastapi-development/SKILL.md) - FastAPI development best practices

## Route Standards

All API routes follow a consistent prefix pattern for organization and discoverability:

| Route Pattern | Description | Example |
|--------------|-------------|---------|
| `/api/v1/capabilities/{capability}/*` | Capability endpoints | `/api/v1/capabilities/persona/chat` |
| `/api/v1/workflows/{workflow}/*` | Workflow endpoints | `/api/v1/n8n/create` |
| `/api/v1/admin/*` | Admin endpoints | `/api/v1/admin/discord/config` |
| `/api/v1/data/*` | Data service health checks | `/api/v1/data/mongodb/health` |
| `/api/v1/rag/*` | RAG search endpoints | `/api/v1/rag/search` |
| `/api/v1/crawl/*` | Web crawling endpoints | `/api/v1/crawl/single` |

### Route Prefix Reference

#### Capabilities (`/api/v1/capabilities/`)

| Capability | Full Prefix | Endpoints |
|-----------|-------------|-----------|
| Persona | `/api/v1/capabilities/persona` | `/chat`, `/mood` |
| Calendar | `/api/v1/capabilities/calendar` | `/create`, `/update`, `/delete`, `/list` |
| Retrieval | `/api/v1/capabilities/retrieval` | `/search/vector`, `/search/graph` |
| Processing | `/api/v1/capabilities/processing` | `/classify-topics` |

#### Workflows

| Workflow | Full Prefix | Endpoints |
|----------|-------------|-----------|
| N8n | `/api/v1/n8n` | `/create`, `/update`, `/delete`, `/list`, `/activate`, `/execute` |
| Conversation | `/api/v1/conversation` | `/orchestrate` |
| Crawl4AI | `/api/v1/crawl` | `/single`, `/deep` |
| YouTube RAG | `/api/v1/youtube` | `/ingest`, `/metadata`, `/health` |

#### Data Services

| Service | Full Prefix | Endpoints |
|---------|-------------|-----------|
| MongoDB | `/api/v1/data/mongodb` | `/health` |
| Neo4j | `/api/v1/data/neo4j` | `/health` |

#### Admin

| Feature | Full Prefix | Endpoints |
|---------|-------------|-----------|
| Discord Bot | `/api/v1/admin/discord` | `/capabilities` (GET), `/config` (GET, PUT), `/config/capability/{name}` (POST, DELETE), `/config/capability/{name}/settings` (PUT) |

## Error Handling

### Standardized Response Models

All errors use the `APIError` model from `shared/api_models.py`:

```python
from shared.api_models import APIError, ErrorCode

# Error response structure
{
    "success": false,
    "error_code": "NOT_FOUND",  # ErrorCode enum value
    "message": "User not found: user_123",
    "details": {
        "resource_type": "user",
        "resource_id": "user_123"
    }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `BAD_REQUEST` | 400 | Malformed request |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | Dependency unavailable |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `LLM_ERROR` | 500 | LLM service error |
| `CONFIGURATION_ERROR` | 500 | Missing/invalid configuration |

### Exception Handling

The Lambda server includes a global exception handler that converts `BaseProjectError` subclasses to standardized `APIError` responses:

```python
from shared.exceptions import NotFoundException, ValidationException

# Raising exceptions automatically returns APIError responses
raise NotFoundException("User", user_id)  # Returns 404 with NOT_FOUND code
raise ValidationException("Invalid email format", field="email")  # Returns 400
```

### Success Responses

For generic success responses (not returning domain objects), use `APISuccess`:

```python
from shared.api_models import APISuccess

return APISuccess(
    data={"items": [...], "count": 10},
    message="Successfully processed 10 items"
)
```

## Capability APIs

Each capability has its own AGENTS.md with detailed documentation:

- **[Calendar Sync](../src/capabilities/calendar/calendar_sync/AGENTS.md)** - Google Calendar integration and event synchronization
- **[MongoDB RAG](../src/capabilities/retrieval/mongo_rag/AGENTS.md)** - MongoDB-based RAG with vector search, memory tools, and knowledge graph
- **[Graphiti RAG](../src/capabilities/retrieval/graphiti_rag/AGENTS.md)** - Graph-based RAG using Graphiti and Neo4j
- **[Knowledge](../src/capabilities/knowledge_graph/knowledge/AGENTS.md)** - Event extraction from web content
- **[Knowledge Base](../src/capabilities/knowledge_graph/knowledge_base/AGENTS.md)** - Knowledge base article management
- **[OpenWebUI Topics](../src/capabilities/processing/openwebui_topics/AGENTS.md)** - Conversation topic classification using LLM
- **[Persona State](../src/capabilities/persona/persona_state/AGENTS.md)** - Persona mood, relationship, and context management
- **[Discord Characters](../src/capabilities/persona/discord_characters/AGENTS.md)** - Discord character management and interaction

## Workflow APIs

Workflows orchestrate multiple capabilities for complex operations:

- **[N8n Workflow](../src/workflows/automation/n8n_workflow/AGENTS.md)** - N8n workflow creation, execution, and management
- **[Conversation](../src/workflows/chat/conversation/AGENTS.md)** - Multi-agent conversation orchestration
- **[Crawl4AI RAG](../src/workflows/ingestion/crawl4ai_rag/AGENTS.md)** - Web crawling and automatic ingestion into MongoDB RAG
- **[OpenWebUI Export](../src/workflows/ingestion/openwebui_export/AGENTS.md)** - Export Open WebUI conversations to MongoDB RAG
- **[YouTube RAG](../src/workflows/ingestion/youtube_rag/AGENTS.md)** - YouTube video transcription and ingestion
- **[Deep Research](../src/workflows/research/deep_research/AGENTS.md)** - Deep research workflows with multi-step analysis

## Authentication

All API endpoints (except health checks) require authentication. Multiple methods are supported:

### Authentication Methods

| Method | Header | Use Case |
|--------|--------|----------|
| Cloudflare Access JWT | `Cf-Access-Jwt-Assertion: <JWT>` | Browser access via Cloudflare Access |
| API Token (Bearer) | `Authorization: Bearer lat_...` | Scripts, automation, Discord bot |
| Internal Network | `X-User-Email: user@example.com` | Docker services within `ai-network` |
| Dev Mode | None (uses `DEV_USER_EMAIL`) | Local development |

### Example Requests

```bash
# External requests with Cloudflare Access JWT
curl -X GET "https://api.datacrew.space/api/v1/capabilities/persona/chat" \
  -H "Cf-Access-Jwt-Assertion: <JWT_TOKEN>" \
  -H "Content-Type: application/json"

# External requests with API token
curl -X GET "https://api.datacrew.space/api/v1/auth/me" \
  -H "Authorization: Bearer lat_abc123..."

# Internal Docker network requests
curl -X GET "http://lambda-server:8000/api/v1/auth/me" \
  -H "X-User-Email: user@example.com"
```

### Auth Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/me` | GET | Get current user profile |
| `/api/v1/auth/me/token` | POST | Create/regenerate API token |
| `/api/v1/auth/me/token` | DELETE | Revoke API token |
| `/api/v1/auth/me/discord/link` | POST | Link Discord account |
| `/api/v1/auth/user/by-discord/{discord_user_id}` | GET | Lookup user by Discord ID (for bots) |

See [Auth README](../src/services/auth/README.md) for complete authentication documentation.

## Router Registration

Routers are registered directly in `main.py` to avoid circular import issues:

```python
# Example from main.py
from capabilities.persona.router import router as persona_router

app.include_router(
    persona_router,
    prefix="/api/v1/capabilities",
    tags=["capabilities", "persona"]
)
```

Router files should NOT include the base prefix (`/api/v1/capabilities/`) - only the capability-specific path:

```python
# In router.py - correct
@router.post("/persona/chat")

# In router.py - incorrect (prefix handled by main.py)
@router.post("/api/v1/capabilities/persona/chat")
```

## OpenAPI Documentation

The Lambda server provides interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs` (dark mode with toggle)
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`
- **MCP OpenAPI**: `http://localhost:8000/mcp/openapi.json` (for MCP tools)

## Best Practices

### Adding New Endpoints

1. Create router in capability/workflow directory
2. Import and register in `main.py` with appropriate prefix
3. Use `@handle_project_errors()` decorator or raise `BaseProjectError` subclasses
4. Document endpoint in router file with docstrings
5. Add cross-link to this document

### Testing Endpoints

Use the shared auth helpers for sample scripts:

```python
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers

api_base_url = get_api_base_url()
headers = get_auth_headers()

response = requests.post(
    f"{api_base_url}/api/v1/capabilities/persona/chat",
    headers=headers,
    json={"message": "Hello"}
)
```

### Error Handling

Always use standardized exceptions:

```python
from shared.exceptions import NotFoundException, ValidationException

def get_user(user_id: str):
    user = db.find_user(user_id)
    if not user:
        raise NotFoundException("User", user_id)
    return user
```

---

**Last Updated**: 2026-01-20
**Maintainer**: Lambda Server Team
