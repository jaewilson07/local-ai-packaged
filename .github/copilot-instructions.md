# GitHub Copilot Instructions for local-ai-packaged

> **Note**: These instructions align with `.cursorrules` and `AGENTS.md`. When in doubt, refer to `AGENTS.md` as the source of truth.

> **Multi-Editor Support**: Both GitHub Copilot and Cursor AI read AGENTS.md files as the universal source of truth. These instructions are a summarized version for Copilot's context window.

## Core Principles

- Follow the patterns established in `AGENTS.md`
- Prefer loud errors over silent failures (fail fast)
- Use stack-based Docker Compose architecture
- Enforce data isolation and authentication patterns

## Sample Files

- Create sample files in the `sample/` directory
- Sample capability tests go in `sample/capability/`
- Keep sample files self-contained and well-documented
- Use sample files for testing, demonstration, and learning purposes

## Code Style Standards

### Python
- Use Python 3.10+ features
- Black formatting (line-length: 100)
- Ruff linting (target: py310)
- Use type hints for function signatures

### YAML
- 2-space indentation
- Consistent service naming in Docker Compose files

### Shell
- POSIX-compliant when possible
- Use `#!/bin/bash` for bash-specific features

## Project Structure

### Stack Organization
Services are organized into numbered stacks with explicit dependencies:

1. **00-infrastructure**: Foundation services (cloudflared, caddy, redis)
2. **01-data**: Data stores (supabase, qdrant, neo4j, mongodb, minio)
3. **02-compute**: AI compute (ollama, comfyui)
4. **03-apps**: Application layer (n8n, flowise, open-webui, etc.)
5. **04-lambda**: FastAPI server with MCP and REST APIs

Each stack uses its own Docker Compose project name but shares the `ai-network` for inter-service communication.

## Exception Handling

### Never Do This
```python
# WRONG: Naked exception
try:
    risky_operation()
except:
    pass

# WRONG: Catching Exception
try:
    risky_operation()
except Exception as e:
    pass
```

### Do This Instead
```python
# CORRECT: Catch specific exceptions
from server.core.exceptions import MongoDBException, ValidationException

try:
    risky_operation()
except MongoDBException as e:
    logger.error(f"MongoDB operation failed: {e}")
    raise
except ValidationException as e:
    return {"error": str(e)}
```

### Structured Exception Layer
- Base: `BaseProjectException` from `server.core.exceptions`
- Service-specific: `MongoDBException`, `LLMException`, `ConfigurationException`
- Domain-specific: `ValidationException`, `NotFoundException`

### When to Create New Exceptions
- Create service-specific exceptions (e.g., `SupabaseException`, `Neo4jException`) inheriting from `BaseProjectException`
- Create capability-specific exceptions (e.g., `WorkflowException`, `RAGException`) for domain logic
- Include relevant context (operation, resource, model) in exception initialization

### API Exception Handling Pattern
```python
from server.core.error_handling import handle_project_errors

@router.get("/endpoint")
@handle_project_errors()
async def endpoint(user: User = Depends(get_current_user)):
    # Let exceptions propagate to framework-level handlers
    result = await service.operation()
    return result
```

## Authentication Patterns

### FastAPI Dependency Pattern
```python
from server.projects.auth.dependencies import get_current_user
from server.projects.auth.models import User

@router.get("/protected")
async def protected_endpoint(user: User = Depends(get_current_user)):
    # User is automatically validated and provisioned
    return {"message": f"Hello {user.email}!"}
```

### Data Isolation
- Regular users: Filter queries by `user.email` or `user.uid`
- Admin users: Bypass filtering (check with `AuthService.is_admin()`)
- Storage layers:
  - **Supabase**: Filter by `owner_email` field
  - **Neo4j**: Use user anchoring: `MATCH (u:User {email: $email})`
  - **MinIO**: Filter by `user-{uuid}/` prefix
  - **MongoDB**: Filter by `user_id` or `user_email` fields

## Docker Compose Patterns

### Service Definition
```yaml
x-service-name: &service-name
  image: image:tag
  container_name: service-name
  restart: unless-stopped
  networks:
    - default  # ai-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://127.0.0.1:PORT/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

### Volume Paths
- MUST use full paths from project root (e.g., `./03-apps/flowise/data`)
- Never use relative paths from service folder

### Health Checks
- Use `127.0.0.1` instead of `localhost` to avoid IPv6 issues
- Use `nc -z 127.0.0.1 PORT` for TCP port checks when `curl`/`wget` unavailable
- Use HTTP checks when service has HTTP endpoints

## Common Mistakes to Avoid

1. **Port Conflicts**: Use environment variables, not hardcoded ports
2. **Network Isolation**: All services must use `ai-network`
3. **Volume Paths**: Use full paths from project root
4. **Profile Mismatch**: Ensure GPU profile services match `--profile` flag
5. **Secret Exposure**: Never commit `.env` files or hardcode secrets
6. **Health Check Tools**: Use `127.0.0.1` instead of `localhost`
7. **Environment Variables**: Use `env_file: - ../../.env` for root `.env` file
8. **Service Dependencies**: Use `service_started` instead of `service_healthy` when appropriate
9. **One-Time Services**: Use `restart: "no"` for import/init services that run once and exit

## Testing Patterns

### Pydantic AI RunContext
Use `create_run_context()` helper for consistent RunContext creation:

```python
from server.projects.shared.context_helpers import create_run_context

deps = AgentDependencies()
await deps.initialize()

try:
    ctx = create_run_context(deps)
    results = await semantic_search(ctx, query="test")
finally:
    await deps.cleanup()
```

### When to Use Each Pattern
- **`agent.run(deps=deps)`**: Testing full agent workflow
- **`create_run_context()` + direct tool calls**: Testing individual tools

## Sample Script Authentication

Use shared helpers from `sample/shared/auth_helpers.py`:

```python
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers, get_cloudflare_email

api_base_url = get_api_base_url()  # Defaults to internal network
headers = get_auth_headers()  # Empty for internal, JWT for external
cloudflare_email = get_cloudflare_email()  # From .env file
```

## Database Migrations

- Migrations in `01-data/supabase/migrations/` are automatically applied during Lambda startup
- Core tables validated on every startup (e.g., `profiles`)
- Never manually delete core tables - they will be recreated but data will be lost
- All migrations use `CREATE TABLE IF NOT EXISTS` for idempotency

## Reference Documentation

- **Root**: `AGENTS.md` (Universal Constitution - source of truth)
- **Stack-level**: Each stack has `AGENTS.md` with stack-specific rules
- **Lambda capabilities**: `04-lambda/src/capabilities/*/AGENTS.md` for capability-specific patterns
- **Lambda workflows**: `04-lambda/src/workflows/*/AGENTS.md` for workflow-specific patterns
- **Auth system**: `04-lambda/src/services/auth/README.md`
