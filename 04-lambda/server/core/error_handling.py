"""Shared error handling decorators and utilities."""

import logging
from functools import wraps
from typing import Callable, Type, Any, Optional
from fastapi import HTTPException

from server.core.exceptions import (
    BaseProjectException,
    MongoDBException,
    LLMException,
    ValidationException,
    NotFoundException,
    ConfigurationException
)

logger = logging.getLogger(__name__)


def handle_project_errors(
    raise_as_http: bool = True,
    default_status_code: int = 500
):
    """
    Decorator to handle project-specific exceptions and convert them to HTTP exceptions.
    
    This decorator catches project-specific exceptions and converts them to
    appropriate HTTP exceptions for API endpoints.
    
    Args:
        raise_as_http: If True, convert exceptions to HTTPException (default: True)
        default_status_code: Default HTTP status code for unhandled exceptions
        
    Usage:
        ```python
        from server.core.error_handling import handle_project_errors
        
        @router.post("/endpoint")
        @handle_project_errors()
        async def my_endpoint():
            # If MongoDBException is raised, it becomes HTTPException with status 500
            # If NotFoundException is raised, it becomes HTTPException with status 404
            # etc.
            pass
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except NotFoundException as e:
                if raise_as_http:
                    raise HTTPException(status_code=e.status_code, detail=e.message)
                raise
            except ValidationException as e:
                if raise_as_http:
                    raise HTTPException(status_code=e.status_code, detail=e.message)
                raise
            except (MongoDBException, LLMException, ConfigurationException) as e:
                logger.exception(f"Error in {func.__name__}: {e.message}")
                if raise_as_http:
                    raise HTTPException(status_code=e.status_code, detail=e.message)
                raise
            except BaseProjectException as e:
                logger.exception(f"Project error in {func.__name__}: {e.message}")
                if raise_as_http:
                    raise HTTPException(status_code=e.status_code, detail=e.message)
                raise
            except HTTPException:
                raise  # Re-raise FastAPI HTTP exceptions directly
            except Exception as e:
                logger.exception(f"Unexpected error in {func.__name__}: {e}")
                if raise_as_http:
                    raise HTTPException(
                        status_code=default_status_code,
                        detail=f"Internal server error: {str(e)}"
                    )
                raise
        return wrapper
    return decorator


def handle_mongodb_errors(operation: str):
    """
    Decorator to wrap MongoDB operations with consistent error handling.
    
    Args:
        operation: Description of the operation (e.g., "fetching user", "inserting document")
        
    Usage:
        ```python
        from server.core.error_handling import handle_mongodb_errors
        
        @handle_mongodb_errors("fetching user profile")
        async def get_user_profile(user_id: str):
            # MongoDB errors are automatically converted to MongoDBException
            result = await db.users.find_one({"user_id": user_id})
            if not result:
                raise NotFoundException("user", user_id)
            return result
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Convert to MongoDBException if not already a project exception
                if not isinstance(e, BaseProjectException):
                    raise MongoDBException(
                        message=f"Failed {operation}: {str(e)}",
                        operation=operation,
                        details={"error_type": type(e).__name__}
                    )
                raise
        return wrapper
    return decorator


def handle_llm_errors(operation: str, model: Optional[str] = None):
    """
    Decorator to wrap LLM operations with consistent error handling.
    
    Args:
        operation: Description of the operation (e.g., "generating response", "creating embeddings")
        model: Optional LLM model name
        
    Usage:
        ```python
        from server.core.error_handling import handle_llm_errors
        
        @handle_llm_errors("generating response", model="llama3.2")
        async def generate_response(prompt: str):
            # LLM errors are automatically converted to LLMException
            response = await llm_client.chat.completions.create(...)
            return response
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Convert to LLMException if not already a project exception
                if not isinstance(e, BaseProjectException):
                    raise LLMException(
                        message=f"Failed {operation}: {str(e)}",
                        model=model,
                        operation=operation,
                        details={"error_type": type(e).__name__}
                    )
                raise
        return wrapper
    return decorator
