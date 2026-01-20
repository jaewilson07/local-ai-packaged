# Agent Patterns

Common patterns for implementing Pydantic AI agents in this project.

## Naming Conventions

1. **Dependencies MUST end with "Deps"**: `AgentDeps`, `RAGDeps`, `ValidationDeps`
2. **Response models MUST end with "Response"**: `SearchResponse`, `AnalysisResponse`
3. **Agent instances**: `rag_agent`, `validation_agent` (descriptive, snake_case)

## Pattern 1: RAG Agent

Knowledge retrieval with search tools:

```python
from pydantic_ai import Agent, RunContext
from shared.llm import get_llm_model

RAG_SYSTEM_PROMPT = """You are a knowledge assistant with access to a document database.

When answering questions:
1. Search the knowledge base for relevant information
2. Use the most relevant results to form your answer
3. Always cite your sources
4. If no relevant information is found, say so clearly
"""

rag_agent = Agent(
    get_llm_model(),
    deps_type=RAGDependencies,
    system_prompt=RAG_SYSTEM_PROMPT
)

@rag_agent.tool
async def search_knowledge_base(
    ctx: RunContext[RAGDependencies],
    query: str,
    match_count: int = 5,
    search_type: str = "hybrid",
) -> str:
    """
    Search the knowledge base for relevant information.

    Args:
        ctx: Agent context
        query: Search query
        match_count: Number of results (default: 5)
        search_type: "semantic", "text", or "hybrid"
    """
    deps = ctx.deps

    if search_type == "hybrid":
        results = await deps.hybrid_search(query, match_count)
    elif search_type == "semantic":
        results = await deps.semantic_search(query, match_count)
    else:
        results = await deps.text_search(query, match_count)

    if not results:
        return "No relevant documents found."

    formatted = [f"Found {len(results)} documents:\n"]
    for i, r in enumerate(results, 1):
        formatted.append(f"\n[{i}] {r.title} (relevance: {r.score:.2f})")
        formatted.append(r.content[:500])

    return "\n".join(formatted)
```

## Pattern 2: Task Agent with Structured Output

Agent that returns structured data:

```python
from pydantic import BaseModel, Field

class TaskAnalysis(BaseModel):
    """Structured output for task analysis."""
    summary: str = Field(..., description="Brief summary of the task")
    complexity: str = Field(..., description="low, medium, or high")
    estimated_steps: int = Field(..., ge=1)
    dependencies: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

task_agent = Agent(
    get_llm_model(),
    deps_type=TaskDependencies,
    output_type=TaskAnalysis,  # Enforce structured output
    system_prompt="""Analyze tasks and provide structured assessments.
    Consider complexity, dependencies, and potential risks."""
)

# Usage
async def analyze_task(description: str) -> TaskAnalysis:
    deps = TaskDependencies.from_settings()
    await deps.initialize()
    try:
        result = await task_agent.run(description, deps=deps)
        return result.data  # Returns TaskAnalysis instance
    finally:
        await deps.cleanup()
```

## Pattern 3: Conversation Agent with History

Agent that maintains conversation context:

```python
from pydantic_ai.messages import ModelMessage

CONVERSATION_PROMPT = """You are a helpful assistant engaged in a conversation.
Maintain context from previous messages and provide coherent responses."""

conversation_agent = Agent(
    get_llm_model(),
    deps_type=ConversationDependencies,
    system_prompt=CONVERSATION_PROMPT
)

class ConversationManager:
    """Manages conversation state and history."""

    def __init__(self):
        self.history: dict[str, list[ModelMessage]] = {}

    async def chat(
        self,
        session_id: str,
        message: str,
        user_email: str,
    ) -> str:
        """Process a chat message with history."""

        # Get or create history
        history = self.history.get(session_id, [])

        deps = ConversationDependencies.from_settings(
            user_email=user_email,
            session_id=session_id,
        )
        await deps.initialize()

        try:
            result = await conversation_agent.run(
                message,
                deps=deps,
                message_history=history,
            )

            # Update history
            self.history[session_id] = result.all_messages()

            return result.data
        finally:
            await deps.cleanup()
```

## Pattern 4: Multi-Tool Agent

Agent with multiple specialized tools:

```python
MULTI_TOOL_PROMPT = """You are an assistant with multiple capabilities:
- Search documents for information
- Create calendar events
- Send notifications

Choose the appropriate tool based on the user's request."""

multi_agent = Agent(
    get_llm_model(),
    deps_type=MultiToolDependencies,
    system_prompt=MULTI_TOOL_PROMPT
)

@multi_agent.tool
async def search_documents(
    ctx: RunContext[MultiToolDependencies],
    query: str,
) -> str:
    """Search for documents matching the query."""
    return await ctx.deps.document_service.search(query)

@multi_agent.tool
async def create_calendar_event(
    ctx: RunContext[MultiToolDependencies],
    title: str,
    start_time: str,
    duration_minutes: int = 60,
) -> str:
    """Create a calendar event."""
    event = await ctx.deps.calendar_service.create_event(
        title=title,
        start_time=start_time,
        duration=duration_minutes,
    )
    return f"Created event: {event.title} at {event.start_time}"

@multi_agent.tool
async def send_notification(
    ctx: RunContext[MultiToolDependencies],
    recipient: str,
    message: str,
) -> str:
    """Send a notification to a user."""
    await ctx.deps.notification_service.send(recipient, message)
    return f"Notification sent to {recipient}"
```

## Pattern 5: Agent with External API

Agent that calls external services:

```python
@dataclass
class APIDependencies(BaseDependencies):
    """Dependencies for API-calling agent."""

    http_client: httpx.AsyncClient | None = None
    api_base_url: str = ""
    api_key: str = ""

    async def initialize(self) -> None:
        if not self.http_client:
            self.http_client = httpx.AsyncClient(
                base_url=self.api_base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30.0,
            )

    async def cleanup(self) -> None:
        if self.http_client:
            await self.http_client.aclose()

api_agent = Agent(
    get_llm_model(),
    deps_type=APIDependencies,
    system_prompt="You can query external APIs for data."
)

@api_agent.tool
async def query_api(
    ctx: RunContext[APIDependencies],
    endpoint: str,
    params: dict | None = None,
) -> str:
    """Query an external API endpoint."""
    try:
        response = await ctx.deps.http_client.get(
            endpoint,
            params=params or {},
        )
        response.raise_for_status()
        data = response.json()
        return f"API Response: {data}"
    except httpx.HTTPStatusError as e:
        return f"API Error: {e.response.status_code}"
    except Exception as e:
        return f"Error querying API: {e}"
```

## Pattern 6: Validation Agent

Agent that validates and transforms data:

```python
from pydantic import BaseModel, ValidationError

class ValidatedData(BaseModel):
    """Validated and normalized data."""
    name: str
    email: str
    phone: str | None = None
    is_valid: bool = True
    errors: list[str] = []

validation_agent = Agent(
    get_llm_model(),
    deps_type=ValidationDependencies,
    output_type=ValidatedData,
    system_prompt="""Validate and normalize input data.
    Extract name, email, and phone from the input.
    Report any validation errors found."""
)

@validation_agent.tool
async def lookup_email_domain(
    ctx: RunContext[ValidationDependencies],
    domain: str,
) -> str:
    """Check if an email domain is valid."""
    # Use DNS or API to validate domain
    is_valid = await ctx.deps.validate_domain(domain)
    return f"Domain {domain} is {'valid' if is_valid else 'invalid'}"
```

## Pattern 7: Retry and Error Recovery

Agent with built-in retry logic:

```python
from pydantic_ai import ModelRetry

@my_agent.tool(retries=3)
async def unreliable_operation(
    ctx: RunContext[MyDependencies],
    data: str,
) -> str:
    """Operation that may fail and need retries."""
    try:
        result = await ctx.deps.service.process(data)
        return result
    except TemporaryError as e:
        # Signal retry to the agent
        raise ModelRetry(f"Temporary failure: {e}. Retrying...")
    except PermanentError as e:
        # Don't retry permanent errors
        return f"Operation failed permanently: {e}"
```

## Pattern 8: Agent with Dynamic System Prompt

```python
base_agent = Agent(
    get_llm_model(),
    deps_type=DynamicPromptDependencies,
)

@base_agent.system_prompt
async def build_prompt(ctx: RunContext[DynamicPromptDependencies]) -> str:
    """Build system prompt based on user context."""

    user_prefs = ctx.deps.user_preferences
    role = ctx.deps.user_role

    prompt_parts = ["You are a helpful assistant."]

    # Add role-specific instructions
    if role == "developer":
        prompt_parts.append("Focus on technical accuracy and code examples.")
    elif role == "manager":
        prompt_parts.append("Focus on summaries and actionable insights.")

    # Add preference-based instructions
    if user_prefs.get("verbose"):
        prompt_parts.append("Provide detailed explanations.")
    if user_prefs.get("formal"):
        prompt_parts.append("Use formal language.")

    return "\n".join(prompt_parts)
```

## Pattern 9: Wrapper for Existing Tools

Wrap standalone tool functions into agent tools:

```python
# Existing standalone tools in tools.py
async def hybrid_search(ctx, query: str, match_count: int = 5) -> list[SearchResult]:
    """Standalone hybrid search function."""
    # ... implementation
    pass

# Wrap in agent
from shared.wrappers import DepsWrapper

@rag_agent.tool
async def search_knowledge_base(
    ctx: RunContext[RAGDependencies],
    query: str,
    match_count: int = 5,
) -> str:
    """Search the knowledge base using hybrid search."""

    # Create wrapper for standalone tools
    deps_ctx = DepsWrapper(ctx.deps)

    # Call standalone tool
    results = await hybrid_search(ctx=deps_ctx, query=query, match_count=match_count)

    # Format results for LLM
    if not results:
        return "No results found."

    return format_search_results(results)
```

## Pattern 10: Output Validator

Validate and potentially modify agent output before returning:

```python
from pydantic_ai import Agent, RunContext, ModelRetry

class ContentResponse(BaseModel):
    """Content generation response."""
    content: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    word_count: int

content_agent = Agent(
    get_llm_model(),
    deps_type=ContentDeps,
    output_type=ContentResponse,
    retries=3,
    system_prompt="Generate high-quality content."
)

@content_agent.output_validator
async def validate_content(
    ctx: RunContext[ContentDeps],
    output: ContentResponse
) -> ContentResponse:
    """
    Validate content quality before returning.

    Raises:
        ModelRetry: If validation fails and agent should retry
    """
    # Quality check via external service
    if ctx.deps.quality_service:
        score = await ctx.deps.quality_service.evaluate(output.content)
        if score < 0.7:
            raise ModelRetry(f'Content quality score {score} too low, improve the response')

    # Confidence check
    if output.confidence < 0.5:
        raise ModelRetry('Confidence too low, please provide more detail')

    # Word count validation
    actual_words = len(output.content.split())
    output.word_count = actual_words  # Update with actual count

    return output
```

**Key Points:**
- Parameters: `ctx: RunContext[DepsType]`, `output: ResponseType`
- Can modify output or raise `ModelRetry` to force retry
- Use for quality checks, external validation, post-processing

## Pattern 11: Usage Tracking

Track token usage and costs across agent calls:

```python
from pydantic_ai import Agent, RunUsage, UsageLimits

# Single agent with limits
result = await my_agent.run(
    prompt,
    deps=deps,
    usage_limits=UsageLimits(
        request_limit=5,
        total_tokens_limit=1000,
    ),
)
print(f"Usage: {result.usage()}")

# Multi-agent workflow with shared tracking
async def tracked_workflow(query: str) -> dict:
    """Workflow with usage tracking across multiple agents."""

    # Create shared usage tracker
    usage = RunUsage()
    usage_limits = UsageLimits(request_limit=15, total_tokens_limit=5000)

    # First agent
    result1 = await agent1.run(
        query,
        deps=deps1,
        usage=usage,  # Pass shared tracker
        usage_limits=usage_limits,
    )

    # Second agent
    result2 = await agent2.run(
        f"Process: {result1.data}",
        deps=deps2,
        usage=usage,  # Same tracker
        usage_limits=usage_limits,
    )

    # Total usage across all agents
    return {
        "result": result2.data,
        "total_tokens": usage.total_tokens,
        "total_requests": usage.requests,
    }
```

## Pattern 12: Convenience Function

Wrap agent calls for simpler usage in route files:

```python
# In workflows.py or route file (NOT in agent file)
async def generate_caption(
    image_url: str,
    style: str = "descriptive",
    deps: CaptionDeps | None = None
) -> dict:  # Returns dict, not Pydantic model
    """
    Generate a caption for an image.

    Accepts primitives, returns dict (not Pydantic model).
    Creates dependencies internally if not provided.
    """
    if deps is None:
        deps = CaptionDeps.from_settings(style=style)

    await deps.initialize()
    try:
        result = await caption_agent.run(
            f"Generate a {style} caption for image: {image_url}",
            deps=deps,
        )
        # Convert Pydantic output to dict
        return result.output.model_dump()
    finally:
        await deps.cleanup()
```

**Key Points:**
- Accept primitives (str, dict, int, bool) as parameters
- Return primitives or simple dicts (not Pydantic models)
- Create domain models and dependencies internally
- Live in capability route/workflow file, NOT in agent file

## Common Dependencies Base

All dependency classes should follow this pattern. **Names MUST end with "Deps"**:

```python
from dataclasses import dataclass, field
from typing import Any, Optional
from shared.dependencies import BaseDependencies

@dataclass
class MyAgentDeps(BaseDependencies):
    """Runtime dependencies for MyAgent."""

    # External clients
    http_client: httpx.AsyncClient | None = None
    primary_service: Any | None = None
    secondary_service: Any | None = None

    # Configuration
    api_key: str | None = None
    log_prompts: bool = False

    # User context
    current_user_id: str | None = None
    current_user_email: str | None = None
    is_admin: bool = False

    # Session state
    session_id: str | None = None
    context: dict = field(default_factory=dict)

    @classmethod
    def from_settings(
        cls,
        http_client: Optional[httpx.AsyncClient] = None,
        log_prompts: Optional[bool] = None,
        **kwargs
    ) -> "MyAgentDeps":
        """Factory method to create dependencies from settings."""
        if http_client is None:
            http_client = httpx.AsyncClient()
        return cls(
            http_client=http_client,
            api_key=kwargs.get("api_key") or settings.API_KEY,
            log_prompts=log_prompts if log_prompts is not None else settings.LOG_PROMPTS,
            **kwargs
        )

    async def initialize(self) -> None:
        """Initialize services."""
        if not self.primary_service:
            self.primary_service = await create_primary_service()

    async def cleanup(self) -> None:
        """Cleanup services."""
        if self.primary_service:
            await self.primary_service.close()
        if self.http_client:
            await self.http_client.aclose()

## Deprecated Patterns

### Agent Class Wrapper

**Deprecated**: Use module-level agents instead.

```python
# ❌ Deprecated - Don't use class wrappers
class MyCapabilityAgent:
    def __init__(self):
        self._agent: Optional[Agent] = None

    def get_agent(self) -> Agent:
        if not self._agent:
            self._agent = Agent(...)
        return self._agent

# ✅ Preferred - Module-level agents
my_capability_agent = Agent(
    get_llm_model(),
    deps_type=MyCapabilityDeps,
    output_type=MyCapabilityResponse,
    system_prompt=MY_CAPABILITY_PROMPT
)
```

### Manual Model Factory

**Deprecated**: Use shared `get_agent_model()` utility.

```python
# ❌ Deprecated - Manual model creation
def create_model():
    return OpenAIChatModel(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4",
    )

# ✅ Preferred - Use shared utility
from src.capability.shared.model_factory import get_agent_model

def _get_my_model() -> OpenAIChatModel:
    return get_agent_model("MY_CAPABILITY")
```
