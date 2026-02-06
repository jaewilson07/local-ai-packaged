"""Core protocols and interfaces for layer boundaries.

This module defines the contracts that each layer must adhere to,
ensuring proper separation of concerns and loose coupling.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable


# =============================================================================
# Lifecycle Protocols - Standard initialization/cleanup patterns
# =============================================================================


@runtime_checkable
class Initializable(Protocol):
    """Protocol for components that require async initialization."""

    async def initialize(self) -> None:
        """Initialize the component (connect to databases, load config, etc.)."""
        ...


@runtime_checkable
class Cleanable(Protocol):
    """Protocol for components that require cleanup."""

    async def cleanup(self) -> None:
        """Cleanup resources (close connections, flush buffers, etc.)."""
        ...


class ManagedResource(Protocol):
    """Protocol for resources with full lifecycle management."""

    async def initialize(self) -> None:
        """Initialize the resource."""
        ...

    async def cleanup(self) -> None:
        """Cleanup the resource."""
        ...

    async def health_check(self) -> bool:
        """Check if resource is healthy."""
        ...


# =============================================================================
# Service Layer Protocols - Dumb pipes for external I/O
# =============================================================================


@runtime_checkable
class DatabaseService(Protocol):
    """Protocol for database service adapters."""

    async def connect(self) -> None:
        """Establish database connection."""
        ...

    async def disconnect(self) -> None:
        """Close database connection."""
        ...

    async def health_check(self) -> bool:
        """Check database connectivity."""
        ...


@runtime_checkable
class CacheService(Protocol):
    """Protocol for caching service adapters."""

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache with optional TTL."""
        ...

    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        ...

    async def clear(self) -> None:
        """Clear all cache entries."""
        ...


@runtime_checkable
class StorageService(Protocol):
    """Protocol for object storage service adapters."""

    async def upload(self, key: str, data: bytes, metadata: dict[str, Any] | None = None) -> str:
        """Upload object to storage."""
        ...

    async def download(self, key: str) -> bytes:
        """Download object from storage."""
        ...

    async def delete(self, key: str) -> None:
        """Delete object from storage."""
        ...

    async def list_objects(self, prefix: str = "") -> list[str]:
        """List objects with optional prefix filter."""
        ...


@runtime_checkable
class MessageService(Protocol):
    """Protocol for message queue service adapters."""

    async def publish(self, topic: str, message: Any) -> None:
        """Publish message to topic."""
        ...

    async def subscribe(self, topic: str, callback: Any) -> None:
        """Subscribe to topic with callback."""
        ...


# =============================================================================
# Capability Layer Protocols - Business logic interfaces
# =============================================================================


@runtime_checkable
class CapabilityDependencies(Protocol):
    """Protocol for capability dependency containers."""

    @classmethod
    def from_settings(cls, **kwargs) -> "CapabilityDependencies":
        """Create dependencies from settings."""
        ...

    async def initialize(self) -> None:
        """Initialize all dependencies."""
        ...

    async def cleanup(self) -> None:
        """Cleanup all dependencies."""
        ...


@runtime_checkable
class Agent(Protocol):
    """Protocol for AI agents."""

    async def run(self, prompt: str, **kwargs) -> Any:
        """Execute agent with prompt."""
        ...


# =============================================================================
# Data Store Protocols - Repository patterns
# =============================================================================


@runtime_checkable
class Repository(Protocol):
    """Generic repository protocol for data access."""

    async def get(self, id: str) -> Any | None:
        """Get entity by ID."""
        ...

    async def list(self, **filters) -> list[Any]:
        """List entities with optional filters."""
        ...

    async def create(self, entity: Any) -> str:
        """Create entity and return ID."""
        ...

    async def update(self, id: str, entity: Any) -> None:
        """Update entity by ID."""
        ...

    async def delete(self, id: str) -> None:
        """Delete entity by ID."""
        ...


@runtime_checkable
class SearchableRepository(Repository, Protocol):
    """Repository with search capabilities."""

    async def search(self, query: str, **kwargs) -> list[Any]:
        """Search entities by query."""
        ...


# =============================================================================
# Authentication & Authorization Protocols
# =============================================================================


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol for authentication providers."""

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate authentication token and return user info."""
        ...

    async def get_user_permissions(self, user_id: str) -> list[str]:
        """Get user permissions."""
        ...


@runtime_checkable
class UserProvisioner(Protocol):
    """Protocol for just-in-time user provisioning."""

    async def provision_user(self, email: str, **metadata) -> dict[str, Any]:
        """Provision user in system."""
        ...

    async def user_exists(self, email: str) -> bool:
        """Check if user exists."""
        ...


# =============================================================================
# Workflow Protocols - Orchestration interfaces
# =============================================================================


@runtime_checkable
class Workflow(Protocol):
    """Protocol for workflow orchestrators."""

    async def execute(self, **inputs) -> Any:
        """Execute workflow with inputs."""
        ...

    async def validate(self, **inputs) -> bool:
        """Validate workflow inputs."""
        ...


@runtime_checkable
class StatefulWorkflow(Workflow, Protocol):
    """Protocol for workflows that maintain state."""

    async def get_state(self) -> dict[str, Any]:
        """Get current workflow state."""
        ...

    async def restore_state(self, state: dict[str, Any]) -> None:
        """Restore workflow from state."""
        ...


# =============================================================================
# Event & Messaging Protocols
# =============================================================================


@runtime_checkable
class EventPublisher(Protocol):
    """Protocol for event publishers."""

    async def publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish domain event."""
        ...


@runtime_checkable
class EventSubscriber(Protocol):
    """Protocol for event subscribers."""

    async def subscribe(self, event_type: str) -> None:
        """Subscribe to event type."""
        ...

    async def handle_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Handle received event."""
        ...


# =============================================================================
# Configuration Protocols
# =============================================================================


@runtime_checkable
class ConfigProvider(Protocol):
    """Protocol for configuration providers."""

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        ...

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        ...

    def reload(self) -> None:
        """Reload configuration from source."""
        ...
