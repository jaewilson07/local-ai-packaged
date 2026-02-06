"""Google Calendar class implementations."""

# Re-export GoogleAuth from google_drive for convenience
# Use GoogleAuth with scopes=GoogleAuth.CALENDAR_SCOPES for Calendar operations
from app.services.external.google_drive.classes.google_auth import GoogleAuth

from .exceptions import (
    GoogleCalendarAuthError,
    GoogleCalendarConflictError,
    GoogleCalendarException,
    GoogleCalendarNotFoundError,
    GoogleCalendarQuotaError,
)
from .google_calendar import GoogleCalendar

__all__ = [
    "GoogleAuth",
    "GoogleCalendar",
    "GoogleCalendarAuthError",
    "GoogleCalendarConflictError",
    "GoogleCalendarException",
    "GoogleCalendarNotFoundError",
    "GoogleCalendarQuotaError",
]
