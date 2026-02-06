"""Google Calendar specific exceptions."""


class GoogleCalendarException(Exception):
    """Base exception for Google Calendar operations."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class GoogleCalendarAuthError(GoogleCalendarException):
    """Authentication or authorization error."""


class GoogleCalendarNotFoundError(GoogleCalendarException):
    """Calendar or event not found."""


class GoogleCalendarConflictError(GoogleCalendarException):
    """Event conflict (duplicate or version mismatch)."""


class GoogleCalendarQuotaError(GoogleCalendarException):
    """API quota exceeded."""


__all__ = [
    "GoogleCalendarAuthError",
    "GoogleCalendarConflictError",
    "GoogleCalendarException",
    "GoogleCalendarNotFoundError",
    "GoogleCalendarQuotaError",
]
