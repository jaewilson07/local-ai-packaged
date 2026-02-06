"""Factory functions for creating capability dependencies.

Provides centralized dependency creation with consistent configuration.
"""

from typing import Any, Callable, TypeVar

from app.core.capabilities import BaseDependencies

TDeps = TypeVar("TDeps", bound=BaseDependencies)


def create_dependency_factory(deps_class: type[TDeps]) -> Callable[..., TDeps]:
    """
    Create a factory function for a specific dependency class.
    
    This is useful for FastAPI dependency injection where you need
    a callable that creates dependencies on demand.
    
    Args:
        deps_class: The dependency class to instantiate
        
    Returns:
        Factory function that creates dependency instances
        
    Examples:
        >>> from app.capabilities.retrieval.mongo_rag.dependencies import AgentDeps
        >>> 
        >>> # Create factory
        >>> get_deps = create_dependency_factory(AgentDeps)
        >>> 
        >>> # Use in FastAPI
        >>> @router.post("/endpoint")
        >>> async def endpoint(deps: AgentDeps = Depends(get_deps)):
        >>>     await deps.initialize()
        >>>     # ... use deps
        >>>     await deps.cleanup()
    """

    def factory(**kwargs: Any) -> TDeps:
        """Create and return dependency instance."""
        return deps_class.from_settings(**kwargs)

    return factory


async def initialize_deps(deps: BaseDependencies) -> BaseDependencies:
    """
    Initialize dependencies and return them.
    
    Helper function for use with FastAPI dependency injection.
    
    Args:
        deps: Dependencies to initialize
        
    Returns:
        Initialized dependencies
        
    Examples:
        >>> @router.post("/endpoint")
        >>> async def endpoint(
        >>>     deps: AgentDeps = Depends(initialize_deps)
        >>> ):
        >>>     # deps are already initialized
        >>>     result = await process(deps)
        >>>     await deps.cleanup()
        >>>     return result
    """
    await deps.initialize()
    return deps
