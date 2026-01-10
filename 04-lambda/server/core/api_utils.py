"""Shared REST API utilities for dependency management and error handling.

Provides context managers and decorators to standardize the try/except/finally
pattern used across all REST API endpoints, reducing boilerplate.
"""

from functools import wraps
from typing import TypeVar, Callable, Any, Optional, Type
from fastapi import HTTPException
import logging

from server.projects.shared.dependencies import BaseDependencies

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseDependencies)


def with_dependencies(
    deps_class: Type[T],
    deps_kwargs: Optional[dict] = None,
    raise_on_error: bool = True
):
    """
    Decorator to manage dependency lifecycle in REST API endpoints.
    
    Automatically handles:
    - Dependency initialization
    - Cleanup in finally block
    - Error handling and logging
    
    Args:
        deps_class: Dependency class (must have from_settings(), initialize(), cleanup())
        deps_kwargs: Optional kwargs to pass to from_settings()
        raise_on_error: Whether to raise HTTPException on errors (default: True)
    
    Example:
        from server.core.api_utils import with_dependencies
        from server.projects.persona.dependencies import PersonaDeps
        
        @router.post("/get-voice")
        @with_dependencies(PersonaDeps)
        async def get_voice_instructions_endpoint(
            request: GetVoiceInstructionsRequest,
            deps: PersonaDeps
        ):
            # deps is already initialized
            instructions = await get_voice_instructions(deps, ...)
            return VoiceInstructionsResponse(...)
            # deps.cleanup() is called automatically
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create dependencies
            deps_kwargs_final = deps_kwargs or {}
            deps = deps_class.from_settings(**deps_kwargs_final)
            
            try:
                # Initialize dependencies
                await deps.initialize()
                
                # Inject deps into kwargs if function expects it
                import inspect
                sig = inspect.signature(func)
                # Check if function has 'deps' parameter (not in *args or **kwargs)
                params = list(sig.parameters.values())
                for param in params:
                    if param.name == 'deps':
                        kwargs['deps'] = deps
                        break
                
                # Call the function
                return await func(*args, **kwargs)
                
            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise
            except Exception as e:
                logger.exception(f"Error in {func.__name__}: {e}")
                if raise_on_error:
                    raise HTTPException(status_code=500, detail=str(e))
                raise
            finally:
                # Always cleanup
                try:
                    await deps.cleanup()
                except Exception as cleanup_error:
                    logger.warning(f"Error during cleanup in {func.__name__}: {cleanup_error}")
        
        return wrapper
    return decorator


class DependencyContext:
    """
    Context manager for dependency lifecycle management.
    
    Alternative to decorator pattern, useful when you need more control
    or when using dependencies outside of FastAPI endpoints.
    
    Example:
        from server.core.api_utils import DependencyContext
        from server.projects.persona.dependencies import PersonaDeps
        
        async with DependencyContext(PersonaDeps) as deps:
            instructions = await get_voice_instructions(deps, ...)
    """
    
    def __init__(
        self,
        deps_class: Type[T],
        deps_kwargs: Optional[dict] = None
    ):
        """
        Initialize dependency context.
        
        Args:
            deps_class: Dependency class
            deps_kwargs: Optional kwargs for from_settings()
        """
        self.deps_class = deps_class
        self.deps_kwargs = deps_kwargs or {}
        self.deps: Optional[T] = None
    
    async def __aenter__(self) -> T:
        """Initialize and return dependencies."""
        self.deps = self.deps_class.from_settings(**self.deps_kwargs)
        await self.deps.initialize()
        return self.deps
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup dependencies."""
        if self.deps:
            try:
                await self.deps.cleanup()
            except Exception as e:
                logger.warning(f"Error during dependency cleanup: {e}")
