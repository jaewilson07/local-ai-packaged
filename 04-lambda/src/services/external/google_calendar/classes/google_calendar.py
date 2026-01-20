"""Google Calendar API low-level wrapper."""

from datetime import datetime
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from services.external.google_drive.classes.google_auth import GoogleAuth

from .exceptions import (
    GoogleCalendarAuthError,
    GoogleCalendarConflictError,
    GoogleCalendarException,
    GoogleCalendarNotFoundError,
    GoogleCalendarQuotaError,
)


class GoogleCalendar:
    """Low-level wrapper for Google Calendar API operations.

    Provides direct access to Calendar API operations with proper error handling
    and credential management.
    """

    def __init__(self, authenticator: GoogleAuth):
        """
        Initialize API client with authenticated credentials.

        Args:
            authenticator: GoogleAuth instance (configured with CALENDAR_SCOPES)
        """
        self.authenticator = authenticator
        self._service = None

    @property
    def service(self):
        """Lazy-loaded Google Calendar API service client."""
        if self._service is None:
            self._service = build(
                "calendar", "v3", credentials=self.authenticator.get_credentials()
            )
        return self._service

    def refresh_credentials_if_needed(self) -> None:
        """Refresh OAuth credentials if they are expired."""
        self.authenticator.refresh_if_needed()

    def _handle_http_error(self, e: HttpError, operation: str, resource_id: str | None = None):
        """Convert HttpError to appropriate GoogleCalendarException."""
        status = e.resp.status
        if status == 401:
            raise GoogleCalendarAuthError(f"Authentication failed: {e}", e)
        if status == 403:
            if "quotaExceeded" in str(e) or "rateLimitExceeded" in str(e):
                raise GoogleCalendarQuotaError(f"API quota exceeded: {e}", e)
            raise GoogleCalendarAuthError(f"Access forbidden: {e}", e)
        if status == 404:
            raise GoogleCalendarNotFoundError(
                f"Resource not found{f': {resource_id}' if resource_id else ''}: {e}", e
            )
        if status == 409:
            raise GoogleCalendarConflictError(f"Conflict error: {e}", e)
        raise GoogleCalendarException(f"{operation} failed: {e}", e)

    def create_event(
        self,
        calendar_id: str,
        summary: str,
        start: str,
        end: str,
        description: str | None = None,
        location: str | None = None,
        timezone: str = "America/Los_Angeles",
        attendees: list[str] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a new calendar event.

        Args:
            calendar_id: Calendar ID (use "primary" for the primary calendar)
            summary: Event title/summary
            start: Start datetime (ISO format or datetime string)
            end: End datetime (ISO format or datetime string)
            description: Event description
            location: Event location
            timezone: Timezone for the event
            attendees: List of attendee email addresses
            **kwargs: Additional event properties

        Returns:
            Created event data from Google Calendar API

        Raises:
            GoogleCalendarException: If creation fails
        """
        self.refresh_credentials_if_needed()

        event_body = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": timezone},
            "end": {"dateTime": end, "timeZone": timezone},
        }

        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location
        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        # Merge any additional kwargs
        event_body.update(kwargs)

        try:
            return self.service.events().insert(calendarId=calendar_id, body=event_body).execute()
        except HttpError as e:
            self._handle_http_error(e, "Event creation")

    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        summary: str | None = None,
        start: str | None = None,
        end: str | None = None,
        description: str | None = None,
        location: str | None = None,
        timezone: str = "America/Los_Angeles",
        attendees: list[str] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Update an existing calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Google Calendar event ID
            summary: New event title (optional)
            start: New start datetime (optional)
            end: New end datetime (optional)
            description: New description (optional)
            location: New location (optional)
            timezone: Timezone for datetime fields
            attendees: New list of attendee emails (optional)
            **kwargs: Additional event properties to update

        Returns:
            Updated event data from Google Calendar API

        Raises:
            GoogleCalendarNotFoundError: If event not found
            GoogleCalendarException: If update fails
        """
        self.refresh_credentials_if_needed()

        try:
            # First, get the existing event
            existing = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()

            # Update only provided fields
            if summary is not None:
                existing["summary"] = summary
            if start is not None:
                existing["start"] = {"dateTime": start, "timeZone": timezone}
            if end is not None:
                existing["end"] = {"dateTime": end, "timeZone": timezone}
            if description is not None:
                existing["description"] = description
            if location is not None:
                existing["location"] = location
            if attendees is not None:
                existing["attendees"] = [{"email": email} for email in attendees]

            # Merge any additional kwargs
            existing.update(kwargs)

            return (
                self.service.events()
                .update(calendarId=calendar_id, eventId=event_id, body=existing)
                .execute()
            )
        except HttpError as e:
            self._handle_http_error(e, "Event update", event_id)

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        """
        Delete a calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Google Calendar event ID

        Raises:
            GoogleCalendarNotFoundError: If event not found
            GoogleCalendarException: If deletion fails
        """
        self.refresh_credentials_if_needed()

        try:
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        except HttpError as e:
            self._handle_http_error(e, "Event deletion", event_id)

    def get_event(self, calendar_id: str, event_id: str) -> dict[str, Any]:
        """
        Get a single event by ID.

        Args:
            calendar_id: Calendar ID
            event_id: Google Calendar event ID

        Returns:
            Event data from Google Calendar API

        Raises:
            GoogleCalendarNotFoundError: If event not found
            GoogleCalendarException: If retrieval fails
        """
        self.refresh_credentials_if_needed()

        try:
            return self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        except HttpError as e:
            self._handle_http_error(e, "Event retrieval", event_id)

    def list_events(
        self,
        calendar_id: str,
        time_min: str | datetime | None = None,
        time_max: str | datetime | None = None,
        max_results: int = 10,
        single_events: bool = True,
        order_by: str = "startTime",
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List calendar events within a time range.

        Args:
            calendar_id: Calendar ID
            time_min: Start of time range (ISO format or datetime)
            time_max: End of time range (ISO format or datetime)
            max_results: Maximum number of events to return
            single_events: Whether to expand recurring events
            order_by: Order by field ("startTime" or "updated")
            query: Free text search query

        Returns:
            List of event data dictionaries

        Raises:
            GoogleCalendarException: If listing fails
        """
        self.refresh_credentials_if_needed()

        # Convert datetime objects to ISO format strings
        if isinstance(time_min, datetime):
            time_min = time_min.isoformat()
        if isinstance(time_max, datetime):
            time_max = time_max.isoformat()

        try:
            kwargs = {
                "calendarId": calendar_id,
                "maxResults": max_results,
                "singleEvents": single_events,
                "orderBy": order_by,
            }

            if time_min:
                kwargs["timeMin"] = time_min
            if time_max:
                kwargs["timeMax"] = time_max
            if query:
                kwargs["q"] = query

            result = self.service.events().list(**kwargs).execute()
            return result.get("items", [])
        except HttpError as e:
            self._handle_http_error(e, "Event listing")

    def list_calendars(self) -> list[dict[str, Any]]:
        """
        List all calendars accessible to the user.

        Returns:
            List of calendar data dictionaries

        Raises:
            GoogleCalendarException: If listing fails
        """
        self.refresh_credentials_if_needed()

        try:
            result = self.service.calendarList().list().execute()
            return result.get("items", [])
        except HttpError as e:
            self._handle_http_error(e, "Calendar listing")


__all__ = ["GoogleCalendar"]
