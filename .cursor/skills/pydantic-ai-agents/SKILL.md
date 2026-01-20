---
name: pydantic-ai-agents
description: Guide Pydantic AI agent development with tool definitions, dependencies, and LangGraph integration. Use when building AI agents, defining agent tools, creating RunContext dependencies, integrating with LangGraph workflows, or when the user asks about agent patterns, structured outputs, or agent testing.
---

# Pydantic AI Agents

Best practices for building AI agents using Pydantic AI, following this project's established patterns.

## Naming Conventions

1. **Dependencies MUST end with "Deps"**: `AgentDeps`, `CaptionValidationDeps`, `RouletteDeps`
2. **Response models MUST end with "Response"**: `CaptionValidationResponse`, `DecisionResponse`, `SearchResponse`
3. **Agent instances**: `caption_validation_agent`, `decision_agent` (descriptive, snake_case)

## Agent Architecture Overview

```
src/capability/{domain}/{capability_name}/
├── models.py                 # Pydantic models (Deps and Response)
├── agents/
│   └── {agent_name}_agent.py # Agent implementation
├── graphs/
│   └── {name}_graph.py       # LangGraph implementation (if needed)
└── workflows.py              # Convenience functions that call agent or graph
```

**Refactoring note**: Plan folder structures first, then incrementally move code.

## Model Factory Functions

Use the shared `get_agent_model()` utility for consistent model configuration:

```python
from shared.llm import get_llm_model
# or for capability-specific models:
from src.capability.shared.model_factory import get_agent_model
from pydantic_ai.models.openai import OpenAIChatModel

def _get_my_model() -> OpenAIChatModel:
    """Factory function to get the model for this agent."""
    return get_agent_model("MY_CAPABILITY")
```

**Key Points:**
- Use shared `get_agent_model()` utility
- Capability name matches settings suffix
- Factory functions allow runtime model selection

## Agent Definition Pattern

Create agents following the pattern in `04-lambda/src/capabilities/`:

```python
from pydantic_ai import Agent, RunContext
from shared.llm import get_llm_model
from .dependencies import MyDeps  # Ends with "Deps"
from .prompts import SYSTEM_PROMPT

# Create the agent with typed dependencies
my_agent = Agent(
    get_llm_model(),        # Use shared LLM utility
    deps_type=MyDeps,       # Type-safe dependencies
    output_type=MyResponse, # Optional: structured output
    retries=3,              # Optional: retry on failure
    system_prompt=SYSTEM_PROMPT
)

@my_agent.tool
async def my_tool(
    ctx: RunContext[MyDependencies],
    query: str,
    limit: int = 10,
) -> str:
    """
    Tool description for the LLM to understand when to use this tool.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        limit: Maximum results to return

    Returns:
        Formatted results as string
    """
    deps = ctx.deps  # Access initialized dependencies

    try:
        results = await deps.service.search(query, limit=limit)
        return format_results(results)
    except Exception as e:
        return f"Error: {e!s}"
```

## Dependencies Pattern

Use dataclass-based dependencies that inherit from `BaseDependencies`. **Names MUST end with "Deps"**:

```python
from dataclasses import dataclass, field
from typing import Any, Optional
from shared.dependencies import BaseDependencies

@dataclass
class MyAgentDeps(BaseDependencies):
    """Runtime dependencies for my agent."""

    # External clients
    mongo_client: AsyncMongoClient | None = None
    db: Any | None = None
    openai_client: openai.AsyncOpenAI | None = None
    http_client: httpx.AsyncClient | None = None

    # Configuration
    settings: Any | None = None
    api_key: str | None = None
    log_prompts: bool = False

    # User context for data isolation
    current_user_id: str | None = None
    current_user_email: str | None = None
    is_admin: bool = False

    # Session state
    session_id: str | None = None
    query_history: list = field(default_factory=list)

    @classmethod
    def from_settings(
        cls,
        http_client: Optional[httpx.AsyncClient] = None,
        user_id: str | None = None,
        user_email: str | None = None,
        log_prompts: Optional[bool] = None,
        **kwargs
    ) -> "MyAgentDeps":
        """Create dependencies from application settings."""
        if http_client is None:
            http_client = httpx.AsyncClient()
        return cls(
            http_client=http_client,
            current_user_id=user_id,
            current_user_email=user_email,
            api_key=kwargs.get("api_key") or settings.API_KEY,
            log_prompts=log_prompts if log_prompts is not None else settings.LOG_PROMPTS,
            **kwargs
        )

    async def initialize(self) -> None:
        """Initialize external connections."""
        if not self.mongo_client:
            self.mongo_client = AsyncMongoClient(config.mongodb_uri)
            self.db = self.mongo_client[config.mongodb_database]
            await self.mongo_client.admin.command("ping")

        if not self.openai_client:
            self.openai_client = openai.AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
            )

    async def cleanup(self) -> None:
        """Clean up external connections."""
        if self.mongo_client:
            await self.mongo_client.close()
            self.mongo_client = None
```

**Key Points:**
- Use `@dataclass` for dependencies
- Include `from_settings()` classmethod
- Keep focused on runtime context, not static configuration

## Tool Definition Best Practices

### 1. Clear Docstrings

The LLM reads tool docstrings to decide when to use them:

```python
@my_agent.tool
async def search_knowledge_base(
    ctx: RunContext[MyDependencies],
    query: str,
    search_type: str = "hybrid",
) -> str:
    """
    Search the knowledge base for relevant information.

    Use this tool when:
    - User asks questions about documented topics
    - Looking up facts or procedures
    - Finding related content

    Args:
        ctx: Agent runtime context
        query: Natural language search query
        search_type: "semantic", "text", or "hybrid" (default: hybrid)

    Returns:
        Formatted search results with sources
    """
```

### 2. Error Handling

Always return user-friendly error messages:

```python
@my_agent.tool
async def process_data(
    ctx: RunContext[MyDependencies],
    data_id: str,
) -> str:
    """Process data by ID."""
    try:
        deps = ctx.deps
        result = await deps.service.process(data_id)

        if not result:
            return f"No data found for ID: {data_id}"

        return f"Processed successfully: {result.summary}"

    except ConnectionError:
        return "Error: Unable to connect to the service. Please try again."
    except Exception as e:
        return f"Error processing data: {e!s}"
```

### 3. Typed Parameters with Field

Use Pydantic Field for parameter metadata:

```python
from pydantic import Field

@my_agent.tool
async def create_item(
    ctx: RunContext[MyDependencies],
    name: str = Field(..., description="Item name", min_length=1),
    category: str = Field("default", description="Item category"),
    tags: list[str] = Field(default_factory=list, description="Optional tags"),
) -> str:
    """Create a new item."""
```

## Running Agents

### Basic Usage

```python
async def run_agent_query(query: str, user_email: str) -> str:
    """Run agent with user context."""
    deps = MyDependencies.from_settings(user_email=user_email)
    await deps.initialize()

    try:
        result = await my_agent.run(query, deps=deps)
        return result.data
    finally:
        await deps.cleanup()
```

### With Message History

```python
from pydantic_ai.messages import ModelMessage

async def run_with_history(
    query: str,
    history: list[ModelMessage],
    deps: MyDependencies,
) -> tuple[str, list[ModelMessage]]:
    """Run agent with conversation history."""
    result = await my_agent.run(
        query,
        deps=deps,
        message_history=history,
    )
    return result.data, result.all_messages()
```

### Streaming Responses

```python
async def stream_response(query: str, deps: MyDependencies):
    """Stream agent response."""
    async with my_agent.run_stream(query, deps=deps) as stream:
        async for chunk in stream.stream_text():
            yield chunk
```

## Structured Output

Define output types with Pydantic models. **Response models MUST end with "Response"**:

```python
from pydantic import BaseModel, Field

class AnalysisResponse(BaseModel):
    """Structured analysis output."""
    summary: str = Field(..., description="Brief summary")
    key_points: list[str] = Field(..., description="Main takeaways")
    confidence: float = Field(..., ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=list)

# Agent with structured output
analysis_agent = Agent(
    get_llm_model(),
    deps_type=AnalysisDeps,
    output_type=AnalysisResponse,  # Enforce structured output
    retries=3,                     # Retry on validation failure
    system_prompt="Analyze the given content..."
)
```

**Key Points:**
- Response models MUST end with "Response"
- Use `Field()` for validation and descriptions
- Use `default_factory` for mutable defaults

## Output Validators

Validate and potentially modify agent output before returning:

```python
from pydantic_ai import ModelRetry

@my_agent.output_validator
async def validate_output(
    ctx: RunContext[MyAgentDeps],
    output: MyResponse
) -> MyResponse:
    """
    Validate and potentially modify the agent's output.

    Raises:
        ModelRetry: If validation fails and agent should retry
    """
    # Validation via external service
    validation_response = await ctx.deps.http_client.post(
        'https://example.com/validate',
        headers={'Authorization': f'Bearer {ctx.deps.api_key}'},
        params={'query': output.message},
    )
    if validation_response.status_code == 400:
        raise ModelRetry(f'Invalid response: {validation_response.text}')
    validation_response.raise_for_status()

    # Simple validation
    if output.confidence < 0.5:
        raise ModelRetry('Confidence too low, please provide more detail')

    return output
```

**Key Points:**
- Parameters: `ctx: RunContext[DepsType]`, `output: ResponseType`
- Can modify output or raise `ModelRetry` to force retry
- Use for quality checks, external validation, post-processing

## System Prompts

### Static Prompts

```python
SYSTEM_PROMPT = """You are a helpful assistant with access to a knowledge base.

Your capabilities:
- Search for relevant information
- Provide accurate, sourced answers
- Explain complex topics clearly

Always cite your sources when using search results.
"""

my_agent = Agent(
    get_llm_model(),
    deps_type=MyDependencies,
    system_prompt=SYSTEM_PROMPT
)
```

### Dynamic Prompts

```python
@my_agent.system_prompt
async def dynamic_prompt(ctx: RunContext[MyDependencies]) -> str:
    """Generate prompt based on user context."""
    user_prefs = ctx.deps.user_preferences

    base_prompt = "You are a helpful assistant."

    if user_prefs.get("verbose"):
        base_prompt += " Provide detailed explanations."
    else:
        base_prompt += " Be concise."

    return base_prompt
```

## Testing Agents

### Testing Tools Directly

Use `create_run_context` helper to test tools without running the full agent:

```python
from shared.context_helpers import create_run_context

@pytest.mark.asyncio
async def test_search_tool(mock_dependencies):
    """Test tool in isolation."""
    await mock_dependencies.initialize()

    try:
        ctx = create_run_context(mock_dependencies)
        result = await search_knowledge_base(ctx, query="test query")

        assert "found" in result.lower() or "no results" in result.lower()
    finally:
        await mock_dependencies.cleanup()
```

### Testing Full Agent

```python
@pytest.mark.asyncio
async def test_agent_run(mock_dependencies):
    """Test full agent execution."""
    await mock_dependencies.initialize()

    try:
        result = await my_agent.run(
            "What is Python?",
            deps=mock_dependencies,
        )

        assert result.data  # Non-empty response
    finally:
        await mock_dependencies.cleanup()
```

### Mock Fixtures

```python
@pytest.fixture
def mock_dependencies():
    """Mock dependencies for testing."""
    deps = AsyncMock(spec=MyDependencies)
    deps.db = AsyncMock()
    deps.openai_client = create_mock_openai_client()
    deps.initialize = AsyncMock()
    deps.cleanup = AsyncMock()
    return deps
```

## Convenience Functions

Convenience functions wrap agent calls for simpler usage. They should:

- **Accept primitives** (str, dict, int, bool) as parameters
- **Return primitives or simple dicts** (not Pydantic models)
- **Create domain models and dependencies internally**
- **Live in the capability route/workflow file**, not the agent file

```python
# In capability route file (e.g., workflows.py), NOT in agent file
async def check_roulette(
    user_input: str,
    winning_number: int = 18,
    deps: Optional[RouletteDeps] = None
) -> dict:  # Returns dict, not RouletteResponse
    """Check if a customer has won at roulette."""
    if deps is None:
        async with httpx.AsyncClient() as client:
            deps = RouletteDeps.from_settings(
                http_client=client,
                winning_number=winning_number
            )
    result = await roulette_agent.run(user_input, deps=deps)
    return result.output.model_dump()  # Convert to dict
```

**Key Points:**
- Keep agent files focused on agent definition only
- Convenience functions handle dependency setup and cleanup
- Convert Pydantic outputs to dicts for external callers

## LangGraph Integration

For complex workflows requiring state management, branching, or multi-step orchestration, integrate with LangGraph. See [langgraph-integration.md](langgraph-integration.md) for detailed patterns.

## Deprecated Patterns

### Agent Class Wrapper

**Deprecated**: Use module-level agents instead. All functionality achievable with factory functions and `deps_type`.

```python
# ❌ Deprecated
class CapabilityAgent:
    def __init__(self):
        self._agent: Optional[Agent] = None
    # ...

# ✅ Preferred
capability_agent = Agent(...)
```

### Manual Model Factory

**Deprecated**: Use `get_agent_model()` from `src.capability.shared.model_factory` instead of manual implementation.

## Best Practices Summary

1. **Naming**: Dependencies end with "Deps", Responses end with "Response"
2. **Structure**: Module-level agents (class wrappers deprecated)
3. **Dependencies**: Dataclasses with `from_settings()` method
4. **Models**: Use `get_agent_model()` utility
5. **Prompts**: Declare separately (string/function), use functions for dynamic
6. **Tools**: First param `RunContext[DepsType]`, docstrings are important
7. **Validation**: Output validators for quality checks, raise `ModelRetry` to retry
8. **No Manual Schemas**: PydanticAI handles schema via `output_type`
9. **Type Safety**: Type hints everywhere
10. **Documentation**: Comprehensive docstrings

## Additional Resources

- [langgraph-integration.md](langgraph-integration.md) - StateGraph patterns, multi-agent workflows, and graph-based control flow
- [agent-patterns.md](agent-patterns.md) - Common agent implementations and patterns
