"""High-level Google Calendar service facade."""

import logging

from services.external.google_drive.classes.google_auth import GoogleAuth

from .classes import GoogleCalendar
from .classes.exceptions import GoogleCalendarException
from .models import CalendarEvent, CalendarEventData

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """High-level service for Google Calendar operations.

    Provides a simplified interface for common calendar operations with
    proper error handling and logging.
    """

    def __init__(
        self,
        credentials_json: str | None = None,
        token_json: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        default_calendar_id: str = "primary",
    ):
        """
        Initialize the Google Calendar service.

        Args:
            credentials_json: OAuth client configuration JSON
            token_json: Serialized token JSON
            client_id: OAuth client ID (alternative to JSON)
            client_secret: OAuth client secret (alternative to JSON)
            default_calendar_id: Default calendar ID to use
        """
        self.default_calendar_id = default_calendar_id

        try:
            # Use GoogleAuth with CALENDAR_SCOPES for Calendar operations
            self._auth = GoogleAuth(
                credentials_json=credentials_json,
                token_json=token_json,
                client_id=client_id,
                client_secret=client_secret,
                scopes=GoogleAuth.CALENDAR_SCOPES,
            )
            self._client = GoogleCalendar(self._auth)
            self._initialized = True
            logger.info("google_calendar_service_initialized")
        except Exception as e:
            logger.warning(f"google_calendar_service_init_failed: {e}")
            self._initialized = False
            self._auth = None
            self._client = None

    @property
    def is_initialized(self) -> bool:
        """Check if the service is properly initialized."""
        return self._initialized

    @property
    def client(self) -> GoogleCalendar:
        """Get the underlying Google Calendar client."""
        if not self._initialized:
            raise GoogleCalendarException(
                "Google Calendar service not initialized. Check credentials."
            )
        return self._client

    async def create_event(
        self,
        event_data: CalendarEventData,
        calendar_id: str | None = None,
    ) -> CalendarEvent:
        """
        Create a new calendar event.

        Args:
            event_data: Event data to create
            calendar_id: Calendar ID (uses default if not provided)

        Returns:
            Created CalendarEvent

        Raises:
            GoogleCalendarException: If creation fails
        """
        cal_id = calendar_id or self.default_calendar_id

        logger.info(
            "creating_calendar_event",
            extra={"summary": event_data.summary, "calendar_id": cal_id},
        )

        result = self.client.create_event(
            calendar_id=cal_id,
            summary=event_data.summary,
            start=event_data.start,
            end=event_data.end,
            description=event_data.description,
            location=event_data.location,
            timezone=event_data.timezone,
            attendees=event_data.attendees,
        )

        event = CalendarEvent.from_google_event(result)
        logger.info(
            "calendar_event_created",
            extra={"event_id": event.id, "summary": event.summary},
        )

        return event

    async def update_event(
        self,
        event_id: str,
        event_data: CalendarEventData | None = None,
        calendar_id: str | None = None,
        **kwargs,
    ) -> CalendarEvent:
        """
        Update an existing calendar event.

        Args:
            event_id: Google Calendar event ID
            event_data: Event data to update (optional)
            calendar_id: Calendar ID (uses default if not provided)
            **kwargs: Individual fields to update

        Returns:
            Updated CalendarEvent

        Raises:
            GoogleCalendarNotFoundError: If event not found
            GoogleCalendarException: If update fails
        """
        cal_id = calendar_id or self.default_calendar_id

        logger.info(
            "updating_calendar_event",
            extra={"event_id": event_id, "calendar_id": cal_id},
        )

        update_kwargs = {}
        if event_data:
            update_kwargs.update(
                summary=event_data.summary,
                start=event_data.start,
                end=event_data.end,
                description=event_data.description,
                location=event_data.location,
                timezone=event_data.timezone,
                attendees=event_data.attendees,
            )
        update_kwargs.update(kwargs)

        result = self.client.update_event(
            calendar_id=cal_id,
            event_id=event_id,
            **update_kwargs,
        )

        event = CalendarEvent.from_google_event(result)
        logger.info(
            "calendar_event_updated",
            extra={"event_id": event.id, "summary": event.summary},
        )

        return event

    async def delete_event(
        self,
        event_id: str,
        calendar_id: str | None = None,
    ) -> None:
        """
        Delete a calendar event.

        Args:
            event_id: Google Calendar event ID
            calendar_id: Calendar ID (uses default if not provided)

        Raises:
            GoogleCalendarNotFoundError: If event not found
            GoogleCalendarException: If deletion fails
        """
        cal_id = calendar_id or self.default_calendar_id

        logger.info(
            "deleting_calendar_event",
            extra={"event_id": event_id, "calendar_id": cal_id},
        )

        self.client.delete_event(calendar_id=cal_id, event_id=event_id)

        logger.info("calendar_event_deleted", extra={"event_id": event_id})

    async def get_event(
        self,
        event_id: str,
        calendar_id: str | None = None,
    ) -> CalendarEvent:
        """
        Get a single event by ID.

        Args:
            event_id: Google Calendar event ID
            calendar_id: Calendar ID (uses default if not provided)

        Returns:
            CalendarEvent

        Raises:
            GoogleCalendarNotFoundError: If event not found
            GoogleCalendarException: If retrieval fails
        """
        cal_id = calendar_id or self.default_calendar_id

        result = self.client.get_event(calendar_id=cal_id, event_id=event_id)
        return CalendarEvent.from_google_event(result)

    async def list_events(
        self,
        calendar_id: str | None = None,
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 10,
        query: str | None = None,
    ) -> list[CalendarEvent]:
        """
        List calendar events.

        Args:
            calendar_id: Calendar ID (uses default if not provided)
            time_min: Start of time range (ISO format)
            time_max: End of time range (ISO format)
            max_results: Maximum number of events to return
            query: Free text search query

        Returns:
            List of CalendarEvents

        Raises:
            GoogleCalendarException: If listing fails
        """
        cal_id = calendar_id or self.default_calendar_id

        logger.info(
            "listing_calendar_events",
            extra={
                "calendar_id": cal_id,
                "time_min": time_min,
                "time_max": time_max,
                "max_results": max_results,
            },
        )

        results = self.client.list_events(
            calendar_id=cal_id,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            query=query,
        )

        events = [CalendarEvent.from_google_event(e) for e in results]
        logger.info("calendar_events_listed", extra={"count": len(events)})

        return events


__all__ = ["GoogleCalendarService"]
