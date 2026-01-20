# Microservices Layer Consolidation Plan

## Executive Summary

After analyzing the `04-lambda/src` codebase, I identified significant redundancy across three main layers:
- **Services Layer** (14 services)
- **Capabilities Layer** (6 capabilities with 10+ sub-capabilities)
- **Workflows Layer** (6 workflows)

This plan outlines a phased approach to consolidate redundant code, standardize patterns, and reduce maintenance burden while preserving functionality.

---

## 1. High-Priority Consolidations

### 1.1 Google OAuth Consolidation (CRITICAL - 90% Duplicate Code)

**Current State:**
- `services/external/google_drive/classes/google_auth.py` - `GoogleAuth` class
- `services/external/google_calendar/classes/google_calendar_auth.py` - `GoogleCalendarAuth` class

These classes are **~90% identical**:
- Same `_load_credentials_from_json()` method
- Same `_load_credentials_from_separate()` method
- Same `refresh_if_needed()` method
- Only differences: default scopes, env var names, exception types

**Proposed Solution:**
Create a shared `GoogleOAuthBase` class:

```
services/external/google/
├── __init__.py
├── auth/
│   ├── __init__.py
│   ├── base.py           # GoogleOAuthBase class
│   └── exceptions.py     # Shared Google auth exceptions
├── calendar/             # Move from google_calendar/
└── drive/                # Move from google_drive/
```

**Implementation:**

```python
# services/external/google/auth/base.py
class GoogleOAuthBase:
    """Base class for Google OAuth authentication."""

    DEFAULT_SCOPES: list[str] = []  # Override in subclasses

    # Common env var patterns
    CREDENTIALS_ENV_VAR: str = "GOOGLE_CREDENTIALS"
    TOKEN_ENV_VAR: str = "GOOGLE_TOKEN"

    def __init__(
        self,
        credentials_json: str | None = None,
        token_json: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
    ):
        self.scopes = scopes or self.DEFAULT_SCOPES
        # ... shared initialization logic ...

    def _load_credentials_from_json(self) -> Credentials: ...
    def _load_credentials_from_separate(self) -> Credentials: ...
    def get_credentials(self) -> Credentials: ...
    def refresh_if_needed(self) -> None: ...

# services/external/google/drive/auth.py
class GoogleDriveAuth(GoogleOAuthBase):
    DEFAULT_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
    CREDENTIALS_ENV_VAR = "GDOC_CLIENT"
    TOKEN_ENV_VAR = "GDOC_TOKEN"

# services/external/google/calendar/auth.py
class GoogleCalendarAuth(GoogleOAuthBase):
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events"
    ]
    CREDENTIALS_ENV_VAR = "GOOGLE_CALENDAR_CREDENTIALS"
    TOKEN_ENV_VAR = "GOOGLE_CALENDAR_TOKEN"
```

**Files to Modify:**
- Create: `services/external/google/auth/base.py`
- Modify: `services/external/google_drive/classes/google_auth.py` → inherit from base
- Modify: `services/external/google_calendar/classes/google_calendar_auth.py` → inherit from base
- Update all imports in dependent files

**Estimated Code Reduction:** ~100 lines

---

### 1.2 Password Generation Utility (MEDIUM - Exact Duplicate)

**Current State:**
Three separate implementations of `_generate_password()`:

| Location | Characters | Length |
|----------|-----------|--------|
| `services/external/immich/client.py:42` | `ascii_letters + digits` | 32 |
| `services/auth/services/immich_service.py:42` | `ascii_letters + digits` | 32 |
| `services/database/mongodb/client.py:39` | `ascii_letters + digits + !@#$%^&*` | 32 |

**Proposed Solution:**
Create a shared security utility:

```python
# shared/security.py
import secrets
import string

def generate_secure_password(
    length: int = 32,
    include_special: bool = False,
    special_chars: str = "!@#$%^&*"
) -> str:
    """Generate a cryptographically secure random password."""
    alphabet = string.ascii_letters + string.digits
    if include_special:
        alphabet += special_chars
    return "".join(secrets.choice(alphabet) for _ in range(length))
```

**Files to Modify:**
- Create: `shared/security.py`
- Modify: `services/external/immich/client.py` → import and use
- Modify: `services/auth/services/immich_service.py` → import and use
- Modify: `services/database/mongodb/client.py` → import and use

**Estimated Code Reduction:** ~30 lines

---

### 1.3 Duplicate Immich Client (HIGH - Entire File Duplicate)

**Current State:**
- `services/external/immich/client.py` - `ImmichService` class (~150 lines)
- `services/auth/services/immich_service.py` - Identical `ImmichService` class (~150 lines)

These files are **functionally identical** - both handle Immich user provisioning.

**Proposed Solution:**
Delete one and consolidate:

1. Keep `services/external/immich/client.py` as the canonical implementation
2. Remove `services/auth/services/immich_service.py`
3. Update imports in `services/auth/services/auth_service.py`

**Files to Modify:**
- Delete: `services/auth/services/immich_service.py`
- Modify: `services/auth/services/__init__.py` → update exports
- Modify: `services/auth/services/auth_service.py` → import from `services.external.immich`

**Estimated Code Reduction:** ~150 lines

---

## 2. Configuration Standardization

### 2.1 Create BaseConfig Class

**Current State:**
26 different `*Config` classes with varying patterns:

| Pattern | Count | Examples |
|---------|-------|----------|
| Plain class with `global_settings` | 15 | `RAGConfig`, `PersonaConfig`, `CalendarConfig` |
| Pydantic `BaseSettings` | 4 | `SupabaseConfig`, `MinIOConfig`, `OpenWebUIExportConfig` |
| `@dataclass` | 2 | `YouTubeRAGConfig`, `ComfyUIConfig` |
| Pydantic model `class Config` | 6 | Nested in models |

**Proposed Solution:**
Create a standardized `BaseProjectConfig`:

```python
# shared/config.py
from server.config import settings as global_settings

class BaseProjectConfig:
    """Base configuration class for all projects."""

    # Common MongoDB settings
    mongodb_uri: str = global_settings.mongodb_uri
    mongodb_database: str = global_settings.mongodb_database

    # Common LLM settings
    llm_provider: str = global_settings.llm_provider
    llm_model: str = global_settings.llm_model
    llm_api_key: str = global_settings.llm_api_key
    llm_base_url: str = global_settings.llm_base_url

    # Common embedding settings  
    embedding_model: str = global_settings.embedding_model
    embedding_api_key: str = global_settings.embedding_api_key
    embedding_base_url: str = global_settings.embedding_base_url

    def __init__(self):
        """Allow subclasses to override defaults."""
        pass
```

**Migration Strategy:**
1. Create `BaseProjectConfig` in `shared/config.py`
2. Gradually migrate existing config classes to inherit from it
3. Remove duplicated property declarations

**Files to Modify (Phase 1 - New Base):**
- Create: `shared/config.py` with `BaseProjectConfig`

**Files to Modify (Phase 2 - Migration):**
- `capabilities/retrieval/mongo_rag/config.py` → inherit from `BaseProjectConfig`
- `capabilities/persona/persona_state/config.py` → inherit from `BaseProjectConfig`
- `capabilities/calendar/calendar_sync/config.py` → inherit from `BaseProjectConfig`
- `workflows/ingestion/crawl4ai_rag/config.py` → inherit from `BaseProjectConfig`
- `workflows/research/deep_research/config.py` → inherit from `BaseProjectConfig`
- ... (12 more config files)

**Estimated Code Reduction:** ~200 lines across 15+ files

---

## 3. Dependencies Standardization

### 3.1 Fix YouTubeRAGDeps (Non-Conforming)

**Current State:**
`YouTubeRAGDeps` does NOT inherit from `BaseDependencies`, making it inconsistent:

```python
# Current - doesn't inherit from BaseDependencies
@dataclass
class YouTubeRAGDeps:
    mongo_client: AsyncMongoClient | None = None
    # ... manual implementation of initialize/cleanup
```

**Proposed Solution:**
Refactor to use standard pattern:

```python
# workflows/ingestion/youtube_rag/dependencies.py
@dataclass
class YouTubeRAGDeps(BaseDependencies, MongoDBMixin):
    """Dependencies for YouTube RAG operations."""

    youtube_client: YouTubeClient | None = None
    openai_client: openai.AsyncOpenAI | None = None
    preferred_language: str = field(default_factory=lambda: config.default_transcript_language)
    skip_mongodb: bool = False

    async def initialize(self) -> None:
        if not self.skip_mongodb:
            await self.initialize_mongodb()

        if self.youtube_client is None:
            self.youtube_client = YouTubeClient(preferred_language=self.preferred_language)

        if self.openai_client is None and config.openai_api_key:
            self.openai_client = openai.AsyncOpenAI(...)

    async def cleanup(self) -> None:
        await self.cleanup_mongodb()

    @classmethod
    def from_settings(cls, **kwargs) -> "YouTubeRAGDeps":
        return cls(**kwargs)
```

**Files to Modify:**
- `workflows/ingestion/youtube_rag/dependencies.py`

---

### 3.2 Migrate AgentDependencies to Use Mixins

**Current State:**
`capabilities/retrieval/mongo_rag/dependencies.py` has 100+ lines of manual MongoDB initialization that duplicates `MongoDBMixin`:

```python
# Current - 100+ lines of manual MongoDB setup
class AgentDependencies(BaseDependencies):
    async def initialize(self) -> None:
        # Manual MongoDB URI building with user credentials
        # Manual client creation
        # Manual ping verification
        # ... 80+ lines
```

**Proposed Solution:**
Refactor to use `MongoDBMixin`:

```python
@dataclass
class AgentDependencies(BaseDependencies, MongoDBMixin, OpenAIClientMixin):
    """Dependencies for MongoDB RAG Agent."""

    graphiti_deps: GraphitiDeps | None = None
    # ... user context fields ...

    async def initialize(self) -> None:
        # Use mixin for MongoDB
        await self.initialize_mongodb()

        # Use mixin for OpenAI
        await self.initialize_openai_client()

        # Project-specific: Graphiti
        if graphiti_config.use_graphiti and not self.graphiti_deps:
            self.graphiti_deps = GraphitiDeps()
            await self.graphiti_deps.initialize()

    async def cleanup(self) -> None:
        await self.cleanup_mongodb()
        await self.cleanup_openai_clients()
        if self.graphiti_deps:
            await self.graphiti_deps.cleanup()
```

**Challenge:** The current implementation has user-based MongoDB authentication logic that needs to be preserved or moved to the mixin.

**Proposed Mixin Enhancement:**

```python
# server/dependencies.py - Enhanced MongoDBMixin
class MongoDBMixin:
    # ... existing code ...

    async def initialize_mongodb_with_user_auth(
        self,
        username: str | None = None,
        password: str | None = None,
        **kwargs
    ) -> None:
        """Initialize MongoDB with optional user-based authentication."""
        if username and password:
            # Build user-based connection string
            uri = self._build_user_connection_string(username, password)
        else:
            uri = self.mongodb_uri

        await self.initialize_mongodb(mongodb_uri=uri, **kwargs)
```

**Files to Modify:**
- `server/dependencies.py` - Add user auth support to `MongoDBMixin`
- `capabilities/retrieval/mongo_rag/dependencies.py` - Migrate to use mixins

**Estimated Code Reduction:** ~80 lines

---

## 4. Create New Mixins for Common Patterns

### 4.1 HTTPClientMixin

**Current State:**
Multiple workflows initialize `httpx.AsyncClient` with similar patterns:
- `workflows/automation/n8n_workflow/ai/dependencies.py`
- `workflows/ingestion/openwebui_export/dependencies.py`
- `workflows/research/deep_research/ai/dependencies.py`

**Proposed Solution:**

```python
# server/dependencies.py
class HTTPClientMixin:
    """Mixin for async HTTP client handling."""

    http_client: httpx.AsyncClient | None = None
    http_timeout: float = 30.0

    async def initialize_http_client(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        headers: dict | None = None,
    ) -> None:
        """Initialize async HTTP client."""
        if self.http_client:
            return

        self.http_client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout or self.http_timeout,
            headers=headers or {},
        )

    async def cleanup_http_client(self) -> None:
        """Clean up HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
```

**Files to Create:**
- Add `HTTPClientMixin` to `server/dependencies.py`

**Files to Modify:**
- `workflows/automation/n8n_workflow/ai/dependencies.py` → use mixin
- `workflows/ingestion/openwebui_export/dependencies.py` → use mixin
- `workflows/research/deep_research/ai/dependencies.py` → use mixin

---

### 4.2 Crawl4AIMixin

**Current State:**
Both `crawl4ai_rag` and `deep_research` initialize `AsyncWebCrawler` identically.

**Proposed Solution:**

```python
# server/dependencies.py
class Crawl4AIMixin:
    """Mixin for Crawl4AI web crawler handling."""

    crawler: Any | None = None  # AsyncWebCrawler

    async def initialize_crawler(self) -> None:
        """Initialize Crawl4AI crawler."""
        if self.crawler:
            return

        try:
            from crawl4ai import AsyncWebCrawler
            self.crawler = AsyncWebCrawler()
            await self.crawler.__aenter__()
        except ImportError:
            logger.warning("Crawl4AI not installed, crawler unavailable")

    async def cleanup_crawler(self) -> None:
        """Clean up crawler."""
        if self.crawler:
            await self.crawler.__aexit__(None, None, None)
            self.crawler = None
```

---

## 5. Router and API Standardization

### 5.1 Standardize Router Prefixes

**Current State (Inconsistent):**

| Router | Prefix |
|--------|--------|
| `auth/router.py` | `/api/me` |
| `supabase/router.py` | `/supabase` |
| `preferences/router.py` | `/api/v1/preferences` |
| `mongodb/router.py` | `/api/v1/data/mongodb` |

**Proposed Standard:**
All routers should use `/api/v1/{service}` pattern:

| Router | Current | Proposed |
|--------|---------|----------|
| auth | `/api/me` | `/api/v1/auth/me` |
| supabase | `/supabase` | `/api/v1/data/supabase` |
| mongodb | `/api/v1/data/mongodb` | ✓ (already correct) |
| preferences | `/api/v1/preferences` | ✓ (already correct) |

**Implementation:**
This requires careful migration to avoid breaking clients. Consider:
1. Add new routes with standard prefixes
2. Deprecate old routes with redirect
3. Remove old routes after migration period

---

## 6. Naming Convention Standardization

### 6.1 Client vs Service Naming

**Current State (Inconsistent):**

| Type | Current Name | Pattern |
|------|--------------|---------|
| Database clients | `MongoDBClient`, `SupabaseClient` | `*Client` |
| External APIs | `ImmichService`, `GoogleCalendarService` | `*Service` |
| External APIs | `MinIOClient` | `*Client` |

**Proposed Convention:**
- `*Client` - Low-level API wrappers (direct API calls)
- `*Service` - High-level facades with business logic
- `*Store` - Data persistence layer

**Files to Rename (Optional - Breaking Change):**
- `MinIOClient` → `MinIOService` (it has business logic)
- Or: Keep as-is and document convention

---

## 7. Implementation Phases

### Phase 1: Quick Wins (1-2 days)
- [ ] Create `shared/security.py` with `generate_secure_password()`
- [ ] Delete duplicate `services/auth/services/immich_service.py`
- [ ] Create `GoogleOAuthBase` and migrate auth classes

### Phase 2: Dependencies Standardization (2-3 days)
- [ ] Add `HTTPClientMixin` and `Crawl4AIMixin` to `server/dependencies.py`
- [ ] Fix `YouTubeRAGDeps` to inherit from `BaseDependencies`
- [ ] Migrate `AgentDependencies` to use mixins

### Phase 3: Configuration Standardization (2-3 days)
- [ ] Create `BaseProjectConfig` in `shared/config.py`
- [ ] Migrate high-use config classes (mongo_rag, persona, calendar, crawl4ai)
- [ ] Migrate remaining config classes

### Phase 4: API Standardization (1-2 days)
- [ ] Document router prefix convention
- [ ] Create deprecation plan for non-standard routes
- [ ] Add redirect routes for backward compatibility

### Phase 5: Documentation and Cleanup (1 day)
- [ ] Update AGENTS.md with new patterns
- [ ] Add migration guide for developers
- [ ] Run full test suite

---

## 8. Estimated Impact

| Metric | Current | After Consolidation |
|--------|---------|---------------------|
| Lines of duplicate code | ~600 | ~0 |
| Config class variations | 4 patterns | 1 pattern |
| Dependencies patterns | 3 patterns | 1 pattern |
| Google auth implementations | 2 | 1 (+ 2 subclasses) |
| Password generation implementations | 3 | 1 |
| Immich service implementations | 2 | 1 |

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking imports | High | Keep old paths as re-exports during transition |
| Runtime behavior changes | Medium | Comprehensive testing before/after |
| Missing edge cases | Medium | Review all usages before consolidation |
| Config migration issues | Low | Gradual migration, one file at a time |

---

## 10. Files Changed Summary

### New Files
- `shared/security.py`
- `shared/config.py` (BaseProjectConfig)
- `services/external/google/auth/base.py`
- `services/external/google/auth/exceptions.py`

### Deleted Files
- `services/auth/services/immich_service.py`

### Modified Files (Major)
- `server/dependencies.py` - Add HTTPClientMixin, Crawl4AIMixin, enhance MongoDBMixin
- `services/external/google_drive/classes/google_auth.py` - Inherit from base
- `services/external/google_calendar/classes/google_calendar_auth.py` - Inherit from base
- `capabilities/retrieval/mongo_rag/dependencies.py` - Use mixins
- `workflows/ingestion/youtube_rag/dependencies.py` - Inherit from BaseDependencies

### Modified Files (Minor - Import Updates)
- 15+ config files to inherit from BaseProjectConfig
- 3+ files to use `generate_secure_password()`
- Import updates for Immich service consolidation

---

## 11. Success Criteria

1. **All tests pass** after consolidation
2. **No duplicate code** for identified patterns
3. **Consistent patterns** across all capabilities/workflows
4. **Documentation updated** to reflect new patterns
5. **No breaking changes** for external API consumers
