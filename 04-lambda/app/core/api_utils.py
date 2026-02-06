"""API utility classes for FastAPI endpoints.

This module provides utilities for working with dependencies in API endpoints.
"""

import logging
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DependencyContext:
    """
    Async context manager for initializing and cleaning up dependencies.

    This provides a simple way to use dependencies that require async
    initialization and cleanup in API endpoints.

    Usage:
        async with DependencyContext(MyDependencies) as deps:
            # deps is initialized and ready to use
            result = await deps.some_method()
        # deps.cleanup() is automatically called

    Args:
        deps_class: A dependency class that has:
            - A constructor that accepts no arguments (or uses from_settings())
            - An async initialize() method
            - An async cleanup() method
    """

    def __init__(self, deps_class: type[T], **kwargs):
        """
        Initialize the context manager.

        Args:
            deps_class: The dependency class to instantiate
            **kwargs: Optional keyword arguments passed to from_settings() or constructor
        """
        self.deps_class = deps_class
        self.kwargs = kwargs
        self.deps: T | None = None

    async def __aenter__(self) -> T:
        """Initialize dependencies and return them."""
        # Try from_settings() first, fall back to direct instantiation
        if hasattr(self.deps_class, "from_settings"):
            self.deps = self.deps_class.from_settings(**self.kwargs)
        else:
            self.deps = self.deps_class(**self.kwargs)

        # Initialize if the method exists
        if hasattr(self.deps, "initialize"):
            await self.deps.initialize()

        return self.deps

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up dependencies."""
        if self.deps and hasattr(self.deps, "cleanup"):
            try:
                await self.deps.cleanup()
            except Exception as e:
                logger.warning(f"Error during dependency cleanup: {e}")

        return False  # Don't suppress exceptions
