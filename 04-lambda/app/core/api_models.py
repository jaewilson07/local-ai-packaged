"""Shared API models for error responses."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    BAD_REQUEST = "bad_request"
    CONFLICT = "conflict"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class APIError(BaseModel):
    """Standardized API error response model."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Any] = Field(None, description="Additional error details")
    code: ErrorCode = Field(ErrorCode.INTERNAL_ERROR, description="Standardized error code")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "details": None,
                "code": "internal_error",
            }
        }
