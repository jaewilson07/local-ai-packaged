"""Base classes for capability layer components.

Capabilities are the SOURCE OF TRUTH for business logic.
They implement atomic operations that can be composed by workflows.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

# Type variables for generic base classes
TDeps = TypeVar("TDeps")
TResult = TypeVar("TResult")


@dataclass
class BaseDependencies(ABC):
    """Base class for capability dependencies.
    
    All capability dependencies should:
    - Use @dataclass decorator
    - Implement from_settings() classmethod
    - Implement initialize() and cleanup() methods
    - Store external service clients
    - NOT contain business logic
    """

    @classmethod
    @abstractmethod
    def from_settings(cls, **kwargs) -> "BaseDependencies":
        """
        Create dependencies from application settings.
        
        Args:
            **kwargs: Configuration parameters
            
        Returns:
            Initialized dependencies instance
        """
        pass

    async def initialize(self) -> None:
        """Initialize all dependencies (connections, clients, etc.)."""
        pass

    async def cleanup(self) -> None:
        """Cleanup all dependencies (close connections, etc.)."""
        pass


# Common dependency mixins for composition


@dataclass
class MongoDBMixin:
    """Mixin for MongoDB dependencies."""
    
    mongo_client: Any | None = None
    mongo_db: Any | None = None
    mongodb_uri: str = ""
    mongodb_database: str = "default"

    async def initialize_mongodb(self) -> None:
        """Initialize MongoDB connection."""
        if self.mongo_client is None:
            from pymongo import AsyncMongoClient
            self.mongo_client = AsyncMongoClient(
                self.mongodb_uri,
                serverSelectionTimeoutMS=5000
            )
            self.mongo_db = self.mongo_client[self.mongodb_database]
            # Verify connection
            await self.mongo_client.admin.command("ping")
            logger.info("MongoDB connection initialized")

    async def cleanup_mongodb(self) -> None:
        """Cleanup MongoDB connection."""
        if self.mongo_client is not None:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")


@dataclass
class OpenAIClientMixin:
    """Mixin for OpenAI client dependencies."""
    
    openai_client: Any | None = None
    openai_api_key: str = ""
    openai_base_url: str = ""

    async def initialize_openai(self) -> None:
        """Initialize OpenAI client."""
        if self.openai_client is None:
            import openai
            self.openai_client = openai.AsyncOpenAI(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url
            )
            logger.info("OpenAI client initialized")

    async def cleanup_openai(self) -> None:
        """Cleanup OpenAI client."""
        if self.openai_client is not None:
            await self.openai_client.close()
            logger.info("OpenAI client closed")


@dataclass
class Neo4jMixin:
    """Mixin for Neo4j dependencies."""
    
    neo4j_driver: Any | None = None
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    async def initialize_neo4j(self) -> None:
        """Initialize Neo4j driver."""
        if self.neo4j_driver is None:
            from neo4j import AsyncGraphDatabase
            self.neo4j_driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # Verify connection
            async with self.neo4j_driver.session() as session:
                await session.run("RETURN 1")
            logger.info("Neo4j driver initialized")

    async def cleanup_neo4j(self) -> None:
        """Cleanup Neo4j driver."""
        if self.neo4j_driver is not None:
            await self.neo4j_driver.close()
            logger.info("Neo4j driver closed")


@dataclass
class HTTPClientMixin:
    """Mixin for HTTP client dependencies."""
    
    http_client: Any | None = None

    async def initialize_http(self) -> None:
        """Initialize HTTP client."""
        if self.http_client is None:
            import httpx
            self.http_client = httpx.AsyncClient(timeout=30.0)
            logger.info("HTTP client initialized")

    async def cleanup_http(self) -> None:
        """Cleanup HTTP client."""
        if self.http_client is not None:
            await self.http_client.aclose()
            logger.info("HTTP client closed")


class BaseCapability(ABC, Generic[TDeps, TResult]):
    """Base class for atomic capability operations.
    
    Capabilities are atomic operations that:
    - Implement specific business logic
    - Use dependencies for external I/O
    - Can be composed by workflows
    - Return strongly-typed results
    """

    def __init__(self, deps: TDeps):
        """
        Initialize capability with dependencies.
        
        Args:
            deps: Capability dependencies
        """
        self.deps = deps

    @abstractmethod
    async def execute(self, **inputs) -> TResult:
        """
        Execute the capability.
        
        Args:
            **inputs: Capability inputs
            
        Returns:
            Capability result
        """
        pass

    async def validate(self, **inputs) -> bool:
        """
        Validate capability inputs.
        
        Args:
            **inputs: Capability inputs
            
        Returns:
            True if inputs are valid
        """
        return True


class BaseRepository(ABC, Generic[TResult]):
    """Base class for data repositories.
    
    Repositories provide data access abstraction and should:
    - Hide database-specific details
    - Implement CRUD operations
    - Support filtering and search
    - Handle data mapping/transformation
    """

    def __init__(self, client: Any):
        """
        Initialize repository.
        
        Args:
            client: Database client
        """
        self.client = client

    @abstractmethod
    async def get(self, id: str) -> TResult | None:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def list(self, **filters) -> list[TResult]:
        """List entities with optional filters."""
        pass

    @abstractmethod
    async def create(self, entity: TResult) -> str:
        """Create entity and return ID."""
        pass

    @abstractmethod
    async def update(self, id: str, entity: TResult) -> None:
        """Update entity by ID."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> None:
        """Delete entity by ID."""
        pass


class BaseStore(ABC, Generic[TResult]):
    """Base class for simple key-value stores.
    
    Stores provide simple persistence and should:
    - Support get/set operations
    - Handle serialization/deserialization
    - Provide optional TTL/expiration
    """

    @abstractmethod
    async def get(self, key: str) -> TResult | None:
        """Get value by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: TResult, ttl: int | None = None) -> None:
        """Set value with optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value by key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
