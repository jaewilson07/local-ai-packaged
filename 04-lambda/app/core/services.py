"""Base classes for service layer components.

Services are "dumb pipes" - they only perform I/O operations with external systems.
All business logic belongs in the capability layer.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Base class for all service adapters.
    
    Services must:
    - Only perform I/O operations
    - Contain NO business logic
    - Implement standard lifecycle methods
    - Handle connection management
    - Provide health checks
    """

    def __init__(self, config: Any = None):
        """
        Initialize service.
        
        Args:
            config: Service-specific configuration
        """
        self.config = config
        self._initialized = False
        self._connected = False

    async def initialize(self) -> None:
        """Initialize service resources."""
        if self._initialized:
            logger.warning(f"{self.__class__.__name__} already initialized")
            return
        
        await self._initialize()
        self._initialized = True
        logger.info(f"{self.__class__.__name__} initialized")

    async def cleanup(self) -> None:
        """Cleanup service resources."""
        if not self._initialized:
            return
        
        await self._cleanup()
        self._initialized = False
        self._connected = False
        logger.info(f"{self.__class__.__name__} cleaned up")

    async def health_check(self) -> bool:
        """Check if service is healthy."""
        if not self._initialized:
            return False
        return await self._health_check()

    @abstractmethod
    async def _initialize(self) -> None:
        """Subclass-specific initialization logic."""
        pass

    @abstractmethod
    async def _cleanup(self) -> None:
        """Subclass-specific cleanup logic."""
        pass

    @abstractmethod
    async def _health_check(self) -> bool:
        """Subclass-specific health check logic."""
        pass


class BaseDatabaseService(BaseService):
    """Base class for database service adapters."""

    async def connect(self) -> None:
        """Establish database connection."""
        if self._connected:
            logger.warning(f"{self.__class__.__name__} already connected")
            return
        
        await self._connect()
        self._connected = True
        logger.info(f"{self.__class__.__name__} connected")

    async def disconnect(self) -> None:
        """Close database connection."""
        if not self._connected:
            return
        
        await self._disconnect()
        self._connected = False
        logger.info(f"{self.__class__.__name__} disconnected")

    @abstractmethod
    async def _connect(self) -> None:
        """Subclass-specific connection logic."""
        pass

    @abstractmethod
    async def _disconnect(self) -> None:
        """Subclass-specific disconnection logic."""
        pass

    async def _initialize(self) -> None:
        """Initialize database service."""
        await self.connect()

    async def _cleanup(self) -> None:
        """Cleanup database service."""
        await self.disconnect()


class BaseStorageService(BaseService):
    """Base class for storage service adapters (S3, MinIO, etc.)."""

    @abstractmethod
    async def upload(self, key: str, data: bytes, metadata: dict[str, Any] | None = None) -> str:
        """
        Upload object to storage.
        
        Args:
            key: Object key/path
            data: Object data
            metadata: Optional metadata
            
        Returns:
            Object URL or ID
        """
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """
        Download object from storage.
        
        Args:
            key: Object key/path
            
        Returns:
            Object data
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete object from storage.
        
        Args:
            key: Object key/path
        """
        pass

    @abstractmethod
    async def list_objects(self, prefix: str = "") -> list[str]:
        """
        List objects with optional prefix filter.
        
        Args:
            prefix: Optional prefix filter
            
        Returns:
            List of object keys
        """
        pass


class BaseCacheService(BaseService):
    """Base class for caching service adapters (Redis, Memcached, etc.)."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional time-to-live in seconds
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass


class BaseAPIClient(BaseService):
    """Base class for external API clients."""

    def __init__(self, config: Any = None, base_url: str = "", api_key: str = ""):
        """
        Initialize API client.
        
        Args:
            config: Client configuration
            base_url: API base URL
            api_key: API authentication key
        """
        super().__init__(config)
        self.base_url = base_url
        self.api_key = api_key
        self._session = None

    @abstractmethod
    async def _create_session(self) -> Any:
        """Create HTTP session with proper headers/auth."""
        pass

    @abstractmethod
    async def _close_session(self) -> None:
        """Close HTTP session."""
        pass

    async def _initialize(self) -> None:
        """Initialize API client."""
        self._session = await self._create_session()

    async def _cleanup(self) -> None:
        """Cleanup API client."""
        await self._close_session()


class BaseMessageService(BaseService):
    """Base class for message queue service adapters."""

    @abstractmethod
    async def publish(self, topic: str, message: Any) -> None:
        """
        Publish message to topic.
        
        Args:
            topic: Topic/queue name
            message: Message payload
        """
        pass

    @abstractmethod
    async def subscribe(self, topic: str, callback: Any) -> None:
        """
        Subscribe to topic with callback.
        
        Args:
            topic: Topic/queue name
            callback: Message handler function
        """
        pass
