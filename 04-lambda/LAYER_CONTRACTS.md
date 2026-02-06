## Layer Contracts & Interface Design

This document defines the contracts and interfaces at each layer boundary, ensuring proper separation of concerns, cohesion, and orthogonal design.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Interfaces Layer (Triggers)                 │
│  Protocol: HTTP requests/MCP calls → Capability calls   │
│  Contract: Parse input, call capability, format output  │
│  NO BUSINESS LOGIC                                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│            Workflows Layer (Orchestration)               │
│  Protocol: Coordinate multiple capabilities             │
│  Contract: State management, capability composition     │
│  ORCHESTRATION ONLY - delegate atomic operations        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│          Capabilities Layer (Business Logic)             │
│  Protocol: Atomic operations with dependencies          │
│  Contract: Implement business rules, use services       │
│  SOURCE OF TRUTH for domain logic                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│             Services Layer (Dumb Pipes)                  │
│  Protocol: I/O operations only                          │
│  Contract: Connect, execute, return raw data            │
│  NO BUSINESS LOGIC - pure I/O                           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                Core Layer (Foundation)                   │
│  Protocol: Shared utilities, base classes, protocols    │
│  Contract: No dependencies on other layers              │
│  FOUNDATION - used by all layers above                  │
└─────────────────────────────────────────────────────────┘
```

## Core Layer Contracts

### Base Protocols

All components must implement lifecycle protocols:

```python
from app.core.protocols import Initializable, Cleanable

class MyComponent(Initializable, Cleanable):
    async def initialize(self) -> None:
        """Setup connections, load config."""
        pass
    
    async def cleanup(self) -> None:
        """Close connections, flush data."""
        pass
```

### Service Protocol

All service adapters must inherit from base service:

```python
from app.core.services import BaseService

class MyExternalService(BaseService):
    async def _initialize(self) -> None:
        """Service-specific initialization."""
        pass
    
    async def _cleanup(self) -> None:
        """Service-specific cleanup."""
        pass
    
    async def _health_check(self) -> bool:
        """Service-specific health check."""
        return self._connected
```

### Capability Protocol

All capability dependencies must inherit from BaseDependencies:

```python
from dataclasses import dataclass
from app.core.capabilities import BaseDependencies, MongoDBMixin

@dataclass
class MyCapabilityDeps(BaseDependencies, MongoDBMixin):
    """Dependencies for my capability."""
    
    @classmethod
    def from_settings(cls, **kwargs) -> "MyCapabilityDeps":
        """Create from settings."""
        return cls(
            mongodb_uri=kwargs.get("mongodb_uri"),
            mongodb_database=kwargs.get("mongodb_database", "default")
        )
    
    async def initialize(self) -> None:
        """Initialize all dependencies."""
        await self.initialize_mongodb()
    
    async def cleanup(self) -> None:
        """Cleanup all dependencies."""
        await self.cleanup_mongodb()
```

## Service Layer Contracts

### Contract Requirements

Services MUST:
1. Inherit from appropriate base class (`BaseDatabaseService`, `BaseStorageService`, etc.)
2. Implement lifecycle methods (`_initialize`, `_cleanup`, `_health_check`)
3. Contain ONLY I/O operations
4. Return raw, unprocessed data
5. NOT contain business logic
6. NOT make business decisions

### Example: Database Service

```python
from app.core.services import BaseDatabaseService
from app.core.protocols import DatabaseService

class PostgreSQLService(BaseDatabaseService, DatabaseService):
    """PostgreSQL service adapter - DUMB PIPE ONLY."""
    
    def __init__(self, config: PostgreSQLConfig):
        super().__init__(config)
        self._pool = None
    
    async def _connect(self) -> None:
        """Establish connection pool."""
        self._pool = await asyncpg.create_pool(
            host=self.config.host,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password
        )
    
    async def _disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
    
    async def _health_check(self) -> bool:
        """Check database connectivity."""
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False
    
    # Service methods - ONLY I/O, NO LOGIC
    async def execute_query(self, query: str, *args) -> list[dict]:
        """Execute query and return raw results."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
```

### What Services MUST NOT Do

```python
# ❌ BAD - Business logic in service
class UserService(BaseDatabaseService):
    async def create_user_with_validation(self, email: str, name: str) -> User:
        # ❌ Validation is business logic!
        if not self._is_valid_email(email):
            raise ValueError("Invalid email")
        
        # ❌ Default value assignment is business logic!
        if not name:
            name = email.split("@")[0]
        
        await self.execute_query("INSERT INTO users ...", email, name)

# ✅ GOOD - Pure I/O
class UserService(BaseDatabaseService):
    async def insert_user(self, email: str, name: str) -> str:
        """Insert user and return ID - NO VALIDATION."""
        result = await self.execute_query(
            "INSERT INTO users (email, name) VALUES ($1, $2) RETURNING id",
            email,
            name
        )
        return result[0]["id"]
```

## Capability Layer Contracts

### Contract Requirements

Capabilities MUST:
1. Inherit from `BaseCapability` or use dependency dataclass pattern
2. Implement business logic and domain rules
3. Use services for I/O operations only
4. Be composable and reusable
5. Have clear, single responsibility
6. Use dependency injection

### Example: Capability with Business Logic

```python
from dataclasses import dataclass
from app.core.capabilities import BaseDependencies, MongoDBMixin
from app.services.email.email_service import EmailService

@dataclass
class UserRegistrationDeps(BaseDependencies, MongoDBMixin):
    """Dependencies for user registration capability."""
    email_service: EmailService | None = None
    
    @classmethod
    def from_settings(cls, **kwargs) -> "UserRegistrationDeps":
        return cls(
            mongodb_uri=kwargs["mongodb_uri"],
            mongodb_database=kwargs.get("database", "users"),
            email_service=EmailService(kwargs.get("email_config"))
        )
    
    async def initialize(self) -> None:
        await self.initialize_mongodb()
        await self.email_service.initialize()

class UserRegistrationCapability(BaseCapability[UserRegistrationDeps, str]):
    """Capability for registering new users - BUSINESS LOGIC HERE."""
    
    async def execute(self, email: str, name: str) -> str:
        """
        Register new user with validation and side effects.
        This is where business logic lives!
        """
        # ✅ BUSINESS LOGIC - Email validation
        if not self._is_valid_email(email):
            raise ValueError("Invalid email format")
        
        # ✅ BUSINESS LOGIC - Default name generation
        if not name:
            name = self._generate_default_name(email)
        
        # ✅ BUSINESS LOGIC - Check for duplicates
        existing = await self._check_existing_user(email)
        if existing:
            raise ValueError("User already exists")
        
        # ✅ Use service for I/O (no logic in service!)
        user_id = await self._create_user_record(email, name)
        
        # ✅ BUSINESS LOGIC - Send welcome email
        await self.deps.email_service.send_email(
            to=email,
            subject="Welcome!",
            body=self._generate_welcome_email(name)
        )
        
        return user_id
    
    def _is_valid_email(self, email: str) -> bool:
        """Business rule: email validation."""
        return "@" in email and "." in email.split("@")[1]
    
    def _generate_default_name(self, email: str) -> str:
        """Business rule: default name from email."""
        return email.split("@")[0].replace(".", " ").title()
    
    async def _check_existing_user(self, email: str) -> bool:
        """Check if user exists - uses service."""
        result = await self.deps.mongo_db.users.find_one({"email": email})
        return result is not None
    
    async def _create_user_record(self, email: str, name: str) -> str:
        """Create user record - uses service."""
        result = await self.deps.mongo_db.users.insert_one({
            "email": email,
            "name": name,
            "created_at": datetime.utcnow()
        })
        return str(result.inserted_id)
```

## Workflow Layer Contracts

### Contract Requirements

Workflows MUST:
1. Coordinate multiple capabilities
2. Manage state across operations
3. Handle error recovery and retries
4. Delegate atomic operations to capabilities
5. NOT duplicate capability logic

### Example: Workflow Orchestration

```python
from app.core.protocols import StatefulWorkflow

class UserOnboardingWorkflow(StatefulWorkflow):
    """
    Workflow that orchestrates multiple capabilities.
    NO BUSINESS LOGIC - only coordination!
    """
    
    def __init__(
        self,
        registration_capability: UserRegistrationCapability,
        profile_capability: UserProfileCapability,
        notification_capability: NotificationCapability
    ):
        self.registration = registration_capability
        self.profile = profile_capability
        self.notification = notification_capability
        self._state = {}
    
    async def execute(self, **inputs) -> dict:
        """
        Execute workflow - ORCHESTRATION ONLY.
        """
        email = inputs["email"]
        name = inputs.get("name", "")
        
        # Step 1: Register user (delegates to capability)
        user_id = await self.registration.execute(email=email, name=name)
        self._state["user_id"] = user_id
        
        # Step 2: Create profile (delegates to capability)
        await self.profile.execute(
            user_id=user_id,
            preferences=inputs.get("preferences", {})
        )
        self._state["profile_created"] = True
        
        # Step 3: Send notifications (delegates to capability)
        await self.notification.execute(
            user_id=user_id,
            type="onboarding_complete"
        )
        self._state["notifications_sent"] = True
        
        return {
            "user_id": user_id,
            "status": "complete",
            "steps_completed": len(self._state)
        }
    
    async def get_state(self) -> dict:
        """Return current workflow state."""
        return self._state.copy()
```

## Interface Layer Contracts

### Contract Requirements

Interfaces (HTTP/MCP) MUST:
1. Parse and validate input
2. Call capabilities/workflows
3. Format output
4. Handle HTTP-specific concerns (status codes, headers)
5. NOT contain business logic
6. NOT directly call services

### Example: HTTP Interface

```python
from fastapi import APIRouter, HTTPException, Depends
from app.services.auth.dependencies import get_current_user
from app.capabilities.user.registration import UserRegistrationCapability, UserRegistrationDeps

router = APIRouter()

@router.post("/users/register")
async def register_user(
    request: UserRegistrationRequest,
    user: User = Depends(get_current_user)
):
    """
    HTTP interface - THIN TRIGGER ONLY.
    """
    # ✅ Parse input (interface concern)
    email = request.email
    name = request.name
    
    # ✅ Create and initialize dependencies
    deps = UserRegistrationDeps.from_settings(
        mongodb_uri=os.getenv("MONGODB_URI"),
        database="users"
    )
    await deps.initialize()
    
    try:
        # ✅ Call capability (business logic is there!)
        capability = UserRegistrationCapability(deps)
        user_id = await capability.execute(email=email, name=name)
        
        # ✅ Format output (interface concern)
        return {
            "user_id": user_id,
            "email": email,
            "status": "registered"
        }
    
    except ValueError as e:
        # ✅ Handle HTTP error responses (interface concern)
        raise HTTPException(status_code=400, detail=str(e))
    
    finally:
        # ✅ Cleanup
        await deps.cleanup()
```

## Testing Contracts

### Unit Testing Services

```python
import pytest
from app.services.database.postgresql import PostgreSQLService

@pytest.mark.asyncio
async def test_postgresql_service_execute_query():
    """Test service I/O - NO BUSINESS LOGIC."""
    service = PostgreSQLService(test_config)
    await service.initialize()
    
    # Test raw I/O
    results = await service.execute_query("SELECT 1 as num")
    assert results == [{"num": 1}]
    
    await service.cleanup()
```

### Unit Testing Capabilities

```python
@pytest.mark.asyncio
async def test_user_registration_validates_email():
    """Test capability business logic."""
    deps = UserRegistrationDeps.from_settings(
        mongodb_uri="mock://",
        database="test"
    )
    capability = UserRegistrationCapability(deps)
    
    # Test business rule validation
    with pytest.raises(ValueError, match="Invalid email"):
        await capability.execute(email="invalid", name="Test")
```

### Integration Testing Workflows

```python
@pytest.mark.asyncio
async def test_user_onboarding_workflow():
    """Test workflow orchestration."""
    workflow = UserOnboardingWorkflow(
        registration_capability=mock_registration,
        profile_capability=mock_profile,
        notification_capability=mock_notification
    )
    
    result = await workflow.execute(
        email="test@example.com",
        name="Test User"
    )
    
    assert result["status"] == "complete"
    assert result["steps_completed"] == 3
```

## Summary of Layer Responsibilities

| Layer        | Responsibility | Business Logic | I/O Operations | Composition |
|--------------|----------------|----------------|----------------|-------------|
| Interfaces   | Parse/Format   | ❌ NO          | ❌ NO          | ❌ NO       |
| Workflows    | Orchestrate    | ❌ NO          | ❌ NO          | ✅ YES      |
| Capabilities | Domain Rules   | ✅ YES         | Via Services   | ✅ YES      |
| Services     | External I/O   | ❌ NO          | ✅ YES         | ❌ NO       |
| Core         | Foundation     | ❌ NO          | ❌ NO          | N/A         |

## Key Principles

1. **Single Responsibility**: Each layer has ONE job
2. **Dependency Direction**: Always depends downward (Interface → Workflow → Capability → Service → Core)
3. **No Skip Layers**: Interfaces cannot directly call Services
4. **Protocol-Driven**: Use protocols/ABCs at boundaries
5. **Testability**: Each layer can be tested in isolation
6. **Replaceability**: Services can be swapped without changing capabilities

## Violations to Avoid

❌ Business logic in services
❌ Services calling other services
❌ Interfaces calling services directly
❌ Workflows duplicating capability logic
❌ Capabilities without dependency injection
❌ Cross-layer circular dependencies
