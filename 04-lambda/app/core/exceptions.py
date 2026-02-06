"""Shared exception classes for the application."""


class BaseProjectError(Exception):
    """Base exception for all project errors."""

    pass


class ValidationException(BaseProjectError):
    """Raised when validation fails."""

    pass


class NotFoundException(BaseProjectError):
    """Raised when a resource is not found."""

    pass


class ConfigurationException(BaseProjectError):
    """Raised when configuration is invalid."""

    pass


class DatabaseException(BaseProjectError):
    """Raised when database operation fails."""

    pass


class MongoDBException(DatabaseException):
    """Raised when MongoDB operation fails."""

    pass


class LLMException(BaseProjectError):
    """Raised when LLM operation fails."""

    pass


class FileException(BaseProjectError):
    """Raised when file operation fails."""

    pass


class JSONException(BaseProjectError):
    """Raised when JSON parsing fails."""

    pass


class ParseException(BaseProjectError):
    """Raised when parsing fails."""

    pass
