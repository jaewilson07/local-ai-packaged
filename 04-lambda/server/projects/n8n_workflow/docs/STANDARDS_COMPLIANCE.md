# N8n Workflow Agent - Standards Compliance

This document confirms that the N8n Workflow agent implementation follows the **Pydantic AI Agent Implementation Standard** and **Lambda Stack Agent Rules**.

## Standards Compliance Checklist

### ✅ Naming Conventions

- **Dependencies**: `N8nWorkflowDeps` (ends with "Deps") ✓
- **Response Models**: All end with "Response" ✓
  - `WorkflowResponse`
  - `ListWorkflowsResponse`
  - `ExecuteWorkflowResponse`
- **Agent Instance**: `n8n_workflow_agent` (descriptive, snake_case) ✓

### ✅ File Structure

```
server/projects/n8n_workflow/
├── __init__.py          # Package marker
├── config.py            # Project-specific configuration
├── dependencies.py      # N8nWorkflowDeps class
├── agent.py             # Agent definition
├── tools.py             # Agent tools
├── prompts.py           # System prompts
├── models.py            # Pydantic models
└── docs/                # Documentation
    ├── ENHANCEMENT_RESEARCH.md
    ├── IMPLEMENTATION_SUMMARY.md
    └── STANDARDS_COMPLIANCE.md
```

### ✅ Dependencies Pattern

**File**: `dependencies.py`

```python
@dataclass
class N8nWorkflowDeps:
    """Runtime dependencies for N8n workflow agent."""
    http_client: Optional[httpx.AsyncClient] = None
    n8n_api_url: str = field(default_factory=lambda: config.n8n_api_url)
    n8n_api_key: Optional[str] = field(default_factory=lambda: config.n8n_api_key)
    session_id: Optional[str] = None
    
    @classmethod
    def from_settings(cls, ...) -> "N8nWorkflowDeps":
        """Create dependencies from application settings."""
        return cls(...)
    
    async def initialize(self) -> None:
        """Initialize external connections."""
        ...
    
    async def cleanup(self) -> None:
        """Clean up external connections."""
        ...
```

**Compliance**: ✓
- Uses `@dataclass`
- Has `from_settings()` classmethod
- Includes `initialize()` and `cleanup()` methods
- Focused on runtime context, not static configuration

### ✅ Response Models Pattern

**File**: `models.py`

All response models follow the standard:
- Use `BaseModel`
- Use `Field()` for validation and descriptions
- Use `default_factory` for mutable defaults
- End with "Response"

**Examples**:
- `WorkflowResponse`
- `ListWorkflowsResponse`
- `ExecuteWorkflowResponse`

### ✅ Model Factory Function

**File**: `agent.py`

```python
def _get_n8n_workflow_model(model_choice: Optional[str] = None) -> OpenAIModel:
    """Factory function to get the model for N8n workflow agent."""
    llm_choice = model_choice or config.llm_model
    base_url = config.llm_base_url
    api_key = config.llm_api_key
    
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIModel(llm_choice, provider=provider)
```

**Compliance**: ✓
- Named with `_get_` prefix
- Returns configured model
- Supports optional overrides

### ✅ System Prompts

**File**: `prompts.py`

```python
N8N_WORKFLOW_SYSTEM_PROMPT = """You are an expert N8n workflow automation assistant..."""
```

**Compliance**: ✓
- Declared separately as a string
- Passed to Agent constructor
- Comprehensive and well-documented

### ✅ Agent Definition

**File**: `agent.py`

```python
n8n_workflow_agent = Agent(
    _get_n8n_workflow_model(),
    deps_type=StateDeps[N8nWorkflowState],
    system_prompt=N8N_WORKFLOW_SYSTEM_PROMPT
)
```

**Compliance**: ✓
- Module-level agent (not class wrapper)
- Uses factory function for model
- Uses `StateDeps` for AGUI support
- System prompt declared separately

### ✅ Tools Pattern

**File**: `agent.py` (tool wrappers) and `tools.py` (implementation)

**Tool Wrapper Pattern** (for StateDeps compatibility):
```python
@n8n_workflow_agent.tool
async def create_workflow_tool(
    ctx: RunContext[StateDeps[N8nWorkflowState]],
    name: str,
    ...
) -> str:
    """Tool description."""
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    
    class DepsWrapper:
        def __init__(self, deps):
            self.deps = deps
    
    deps_ctx = DepsWrapper(deps)
    try:
        return await create_workflow(deps_ctx, ...)
    finally:
        await deps.cleanup()
```

**Tool Implementation Pattern** (in `tools.py`):
```python
async def create_workflow(
    ctx: RunContext[N8nWorkflowDeps],
    name: str,
    ...
) -> str:
    """Create a new N8n workflow."""
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()
    # ... implementation
```

**Compliance**: ✓
- First parameter: `RunContext[DepsType]`
- Comprehensive docstrings
- Access dependencies via `ctx.deps`
- Proper error handling and cleanup

### ✅ Configuration Management

**Three-Level Configuration**:

1. **Global Config** (`server/config.py`):
   - `n8n_api_url`
   - `n8n_api_key`

2. **Project Config** (`server/projects/n8n_workflow/config.py`):
   ```python
   class N8nWorkflowConfig:
       n8n_api_url: str = getattr(global_settings, 'n8n_api_url', 'http://n8n:5678/api/v1')
       n8n_api_key: Optional[str] = getattr(global_settings, 'n8n_api_key', None)
       llm_model: str = global_settings.llm_model
       ...
   ```

3. **Runtime Config** (via Dependencies):
   - `N8nWorkflowDeps.from_settings()`

**Compliance**: ✓
- Derives from global settings
- Project-specific overrides
- Runtime configuration via dependencies

### ✅ Error Handling

**Pattern**:
```python
try:
    result = await operation()
except HTTPStatusError as e:
    logger.error("operation_failed", extra={"error": str(e)})
    return error_message
except Exception as e:
    logger.exception("operation_error")
    return error_message
finally:
    await deps.cleanup()
```

**Compliance**: ✓
- Specific exception handling
- Structured logging with context
- Always cleanup in `finally` blocks

### ✅ REST API Design

**File**: `server/api/n8n_workflow.py`

**Pattern**:
```python
@router.post("/create", response_model=WorkflowResponse)
async def create_workflow_endpoint(request: CreateWorkflowRequest):
    """Create a new N8n workflow."""
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    try:
        # Business logic
        return WorkflowResponse(...)
    finally:
        await deps.cleanup()
```

**Compliance**: ✓
- Uses Pydantic models for request/response
- Proper dependency initialization/cleanup
- Error handling with HTTP exceptions

### ✅ MCP Server Integration

**File**: `server/mcp/server.py`

**Compliance**: ✓
- Tool definitions in `get_tool_definitions()`
- Tool handlers in `call_tool()`
- Calls REST endpoints internally (no code duplication)
- Proper error handling and validation

## Architecture Compliance

### ✅ Project Isolation
- Self-contained in `server/projects/n8n_workflow/`
- No cross-project dependencies
- Clean boundaries

### ✅ Dual Interface
- REST API endpoints at `/api/v1/n8n/*`
- MCP tools exposed via `/mcp/tools/*`
- Shared business logic

### ✅ Type Safety
- Pydantic models for all data structures
- Type hints throughout
- Validation at API boundaries

### ✅ Async First
- All I/O operations are async
- Proper async/await usage
- Async HTTP client (httpx)

## Deviations and Rationale

### StateDeps Pattern

**Deviation**: Agent uses `StateDeps[N8nWorkflowState]` but tools expect `N8nWorkflowDeps`.

**Rationale**: 
- Enables AGUI (Agent UI) support for interactive workflows
- Follows the same pattern as `mongo_rag` agent
- Tool wrappers bridge the gap cleanly
- Maintains compatibility with Pydantic AI's StateDeps system

**Implementation**: Tool wrappers create `DepsWrapper` instances to bridge `StateDeps` to `N8nWorkflowDeps`, matching the pattern used in `mongo_rag/agent.py`.

## Testing Recommendations

1. **Unit Tests**: Test dependencies, models, and tools independently
2. **Integration Tests**: Test REST API endpoints
3. **MCP Tests**: Test MCP tool execution
4. **E2E Tests**: Test full workflow creation flow

## Summary

The N8n Workflow agent implementation **fully complies** with:
- ✅ Pydantic AI Agent Implementation Standard
- ✅ Lambda Stack Agent Rules
- ✅ Project structure standards
- ✅ Configuration management patterns
- ✅ Error handling strategies
- ✅ Type safety requirements

The only intentional deviation (StateDeps pattern) is well-documented and follows established patterns in the codebase.

