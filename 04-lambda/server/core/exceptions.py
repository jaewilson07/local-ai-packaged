"""Shared exception classes for consistent error handling across projects."""

from typing import Any


class BaseProjectException(Exception):
    """Base exception for all project-specific errors."""

    def __init__(self, message: str, status_code: int = 500, details: dict[str, Any] | None = None):
        """
        Initialize base project exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code (for API errors)
            details: Optional additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class MongoDBException(BaseProjectException):
    """Exception raised for MongoDB-related errors."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        collection: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize MongoDB exception.

        Args:
            message: Error message
            operation: MongoDB operation that failed (e.g., "insert", "find")
            collection: Collection name where error occurred
            details: Optional additional error details
        """
        super().__init__(message, status_code=500, details=details)
        self.operation = operation
        self.collection = collection


class LLMException(BaseProjectException):
    """Exception raised for LLM-related errors."""

    def __init__(
        self,
        message: str,
        model: str | None = None,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize LLM exception.

        Args:
            message: Error message
            model: LLM model name
            operation: LLM operation that failed (e.g., "chat", "embed")
            details: Optional additional error details
        """
        super().__init__(message, status_code=500, details=details)
        self.model = model
        self.operation = operation


class ValidationException(BaseProjectException):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize validation exception.

        Args:
            message: Error message
            field: Field name that failed validation
            value: Invalid value
            details: Optional additional error details
        """
        super().__init__(message, status_code=400, details=details)
        self.field = field
        self.value = value


class NotFoundException(BaseProjectException):
    """Exception raised when a resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize not found exception.

        Args:
            resource_type: Type of resource (e.g., "user", "document")
            resource_id: ID of the resource that was not found
            details: Optional additional error details
        """
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message, status_code=404, details=details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ConfigurationException(BaseProjectException):
    """Exception raised for configuration errors."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize configuration exception.

        Args:
            message: Error message
            config_key: Configuration key that is missing or invalid
            details: Optional additional error details
        """
        super().__init__(message, status_code=500, details=details)
        self.config_key = config_key
