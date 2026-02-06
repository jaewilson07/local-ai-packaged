"""Error handling utilities for API endpoints."""

import functools
import logging
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def handle_project_errors():
    """
    Decorator to handle common project errors in API endpoints.

    Catches exceptions and converts them to appropriate HTTP responses.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise FastAPI HTTP exceptions as-is
                raise
            except ValueError as e:
                logger.warning(f"Validation error in {func.__name__}: {e}")
                raise HTTPException(status_code=400, detail=str(e)) from e
            except NotImplementedError as e:
                logger.warning(f"Not implemented in {func.__name__}: {e}")
                raise HTTPException(status_code=501, detail=str(e)) from e
            except Exception as e:
                logger.exception(f"Error in {func.__name__}: {e}")
                raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e

        return wrapper

    return decorator
