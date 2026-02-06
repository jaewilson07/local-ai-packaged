"""Google Calendar service module."""

from .classes import GoogleAuth, GoogleCalendar
from .classes.exceptions import (
    GoogleCalendarAuthError,
    GoogleCalendarConflictError,
    GoogleCalendarException,
    GoogleCalendarNotFoundError,
    GoogleCalendarQuotaError,
)
from .models import CalendarEvent, CalendarEventData, SyncState
from .service import GoogleCalendarService

__all__ = [
    # Core classes
    "GoogleCalendar",
    "GoogleAuth",  # Use with scopes=GoogleAuth.CALENDAR_SCOPES for Calendar
    "GoogleCalendarService",
    # Models
    "CalendarEvent",
    "CalendarEventData",
    "SyncState",
    # Exceptions
    "GoogleCalendarException",
    "GoogleCalendarAuthError",
    "GoogleCalendarNotFoundError",
    "GoogleCalendarConflictError",
    "GoogleCalendarQuotaError",
]
