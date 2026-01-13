"""
Google Calendar One-Way Sync Service

Syncs local events to Google Calendar with duplicate prevention.
Tracks sync state using local_event_id and gcal_event_id.
Adapted from wandering-athena for MongoDB sync state storage.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Google Calendar API scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def generate_base32hex_id(local_event_id: str, max_length: int = 1024) -> str:
    """
    Generate a base32hex ID from local_event_id for Google Calendar.

    Google Calendar event IDs must be:
    - 5-1024 characters
    - Only lowercase letters a-v and digits 0-9 (base32hex alphabet)

    Args:
        local_event_id: The local event identifier
        max_length: Maximum length (default 1024, Google's limit)

    Returns:
        Base32hex encoded string suitable for Google Calendar event ID
    """
    # Create a hash of the local_event_id
    hash_bytes = hashlib.sha256(local_event_id.encode()).digest()

    # Convert to base32hex (RFC 4648 base32hex alphabet: 0-9, a-v)
    # This is a custom base32 encoding that uses 0-9 and a-v instead of A-Z
    base32hex_chars = "0123456789abcdefghijklmnopqrstuv"

    # Convert bytes to base32hex
    bits = 0
    value = 0
    result = []

    for byte in hash_bytes:
        value = (value << 8) | byte
        bits += 8

        while bits >= 5:
            result.append(base32hex_chars[(value >> (bits - 5)) & 0x1F])
            bits -= 5

    if bits > 0:
        result.append(base32hex_chars[(value << (5 - bits)) & 0x1F])

    event_id = "".join(result)

    # Ensure minimum length (Google requires 5 chars)
    if len(event_id) < 5:
        event_id = event_id.ljust(5, "0")

    # Truncate to max_length if needed
    return event_id[:max_length]


class GoogleCalendarSyncService:
    """
    Service for syncing local events to Google Calendar with duplicate prevention.

    This service:
    1. Tracks sync state in MongoDB (maps local_event_id to gcal_event_id)
    2. Prevents duplicate events by checking sync state before creating
    3. Updates existing events if sync state exists
    4. Handles OAuth2 authentication and token refresh
    5. Provides CRUD operations for calendar events

    Adapted from wandering-athena's GoogleCalendarSyncService for MongoDB storage.
    """

    def __init__(
        self,
        credentials_path: str,
        token_path: str,
        store: Any,  # PersonaStore protocol - MongoDB implementation
        default_calendar_id: str = "primary",
    ):
        """
        Initialize the Google Calendar sync service.

        Args:
            credentials_path: Path to OAuth2 credentials JSON file
            token_path: Path to store OAuth2 token
            store: Store implementation for sync state (MongoDB)
            default_calendar_id: Default Google Calendar ID (default: "primary")
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.store = store
        self.default_calendar_id = default_calendar_id
        self.service = None
        self._credentials = None

    def _get_credentials(self) -> Credentials:
        """
        Get valid OAuth2 credentials, refreshing if necessary.

        Returns:
            Valid Credentials object

        Raises:
            FileNotFoundError: If credentials file doesn't exist
            Exception: If authentication fails
        """
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Load existing token if available
        if self.token_path.exists():
            self._credentials = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        # Refresh token if expired
        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                self._save_token()
                return self._credentials
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}. Re-authenticating...")
                self._credentials = None

        # Authenticate if no valid credentials
        if not self._credentials or not self._credentials.valid:
            if not self.credentials_path.exists():
                raise FileNotFoundError(
                    f"Credentials file not found: {self.credentials_path}. "
                    "Please download OAuth2 credentials from Google Cloud Console."
                )

            flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
            self._credentials = flow.run_local_server(port=0)
            self._save_token()

        return self._credentials

    def _save_token(self) -> None:
        """Save OAuth2 token to file."""
        if self._credentials:
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with self.token_path.open("w") as token_file:
                token_file.write(self._credentials.to_json())
            logger.info(f"OAuth2 token saved to {self.token_path}")

    def _get_service(self):
        """Get or create Google Calendar API service."""
        if not self.service:
            credentials = self._get_credentials()
            self.service = build("calendar", "v3", credentials=credentials)
            logger.info("Google Calendar API service initialized")
        return self.service

    async def create_event(
        self,
        event_data: dict[str, Any],
        local_event_id: str | None = None,
        calendar_id: str | None = None,
        user_id: str | None = None,
        persona_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a calendar event, preventing duplicates.

        Args:
            event_data: Event data dictionary (summary, start, end, etc.)
            local_event_id: Unique local event identifier (for duplicate prevention)
            calendar_id: Google Calendar ID (default: self.default_calendar_id)
            user_id: Optional user ID for sync state tracking
            persona_id: Optional persona ID for sync state tracking

        Returns:
            Created Google Calendar event dictionary

        Raises:
            HttpError: If Google Calendar API call fails
        """
        calendar_id = calendar_id or self.default_calendar_id

        # Check for existing sync state if local_event_id and user context provided
        if local_event_id and user_id and persona_id:
            sync_state = await self.store.get_sync_state(
                user_id=user_id, persona_id=persona_id, local_event_id=local_event_id
            )

            if sync_state:
                # Event already synced - update instead
                logger.info(f"Event {local_event_id} already synced. Updating...")
                gcal_event_id = sync_state.get("google_event_id") or sync_state.get("gcal_event_id")
                if gcal_event_id:
                    return await self.update_event(
                        gcal_event_id,
                        event_data,
                        calendar_id=calendar_id,
                        user_id=user_id,
                        persona_id=persona_id,
                        local_event_id=local_event_id,
                    )
        elif local_event_id:
            # Fallback to old method for backward compatibility
            sync_state = await self.store.get_by_external_id(external_id=f"local:{local_event_id}")

            if sync_state:
                logger.info(f"Event {local_event_id} already synced. Updating...")
                gcal_event_id = sync_state.get("google_event_id") or sync_state.get("gcal_event_id")
                if gcal_event_id:
                    return await self.update_event(
                        gcal_event_id, event_data, calendar_id=calendar_id
                    )

        # Generate Google Calendar event ID if local_event_id provided
        if local_event_id:
            gcal_event_id = generate_base32hex_id(local_event_id)
            event_data["id"] = gcal_event_id

        # Create event via Google Calendar API
        service = self._get_service()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        event = await loop.run_in_executor(
            None, lambda: service.events().insert(calendarId=calendar_id, body=event_data).execute()
        )

        # Record sync state if local_event_id provided
        if local_event_id:
            if user_id and persona_id:
                # Use proper method with user context
                await self.store.save_sync_state(
                    user_id=user_id,
                    persona_id=persona_id,
                    local_event_id=local_event_id,
                    gcal_event_id=event["id"],
                    sync_status="synced",
                    event_data=event_data,
                    gcal_calendar_id=calendar_id,
                )
            else:
                # Fallback to old method for backward compatibility
                await self.store.record_sync_state(
                    external_id=f"local:{local_event_id}",
                    google_event_id=event["id"],
                    source_system="local",
                    metadata={"calendar_id": calendar_id},
                )
            logger.info(f"Event {local_event_id} synced to Google Calendar: {event['id']}")

        return event

    async def update_event(
        self,
        event_id: str,
        event_data: dict[str, Any],
        calendar_id: str | None = None,
        user_id: str | None = None,
        persona_id: str | None = None,
        local_event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing calendar event.

        Args:
            event_id: Google Calendar event ID
            event_data: Updated event data
            calendar_id: Google Calendar ID (default: self.default_calendar_id)
            user_id: Optional user ID for sync state tracking
            persona_id: Optional persona ID for sync state tracking
            local_event_id: Optional local event ID for sync state tracking

        Returns:
            Updated Google Calendar event dictionary
        """
        calendar_id = calendar_id or self.default_calendar_id
        service = self._get_service()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        event = await loop.run_in_executor(
            None,
            lambda: service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=event_data)
            .execute(),
        )

        # Update sync state if user context provided
        if user_id and persona_id and local_event_id:
            await self.store.save_sync_state(
                user_id=user_id,
                persona_id=persona_id,
                local_event_id=local_event_id,
                gcal_event_id=event_id,
                sync_status="synced",
                event_data=event_data,
                gcal_calendar_id=calendar_id,
            )

        logger.info(f"Event {event_id} updated in Google Calendar")
        return event

    async def delete_event(self, event_id: str, calendar_id: str | None = None) -> None:
        """
        Delete a calendar event.

        Args:
            event_id: Google Calendar event ID
            calendar_id: Google Calendar ID (default: self.default_calendar_id)
        """
        calendar_id = calendar_id or self.default_calendar_id
        service = self._get_service()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: service.events().delete(calendarId=calendar_id, eventId=event_id).execute(),
        )

        logger.info(f"Event {event_id} deleted from Google Calendar")

    async def list_events(
        self,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 10,
        calendar_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List calendar events.

        Args:
            time_min: Minimum time for events (default: now)
            time_max: Maximum time for events (default: now + 30 days)
            max_results: Maximum number of results (default: 10)
            calendar_id: Google Calendar ID (default: self.default_calendar_id)

        Returns:
            List of event dictionaries
        """
        calendar_id = calendar_id or self.default_calendar_id

        if time_min is None:
            time_min = datetime.utcnow()
        if time_max is None:
            time_max = time_min + timedelta(days=30)

        service = self._get_service()

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        events_result = await loop.run_in_executor(
            None,
            lambda: service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat() + "Z",
                timeMax=time_max.isoformat() + "Z",
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute(),
        )

        events = events_result.get("items", [])
        logger.info(f"Listed {len(events)} events from Google Calendar")
        return events

    async def sync_event_to_google_calendar(
        self,
        user_id: str,
        persona_id: str,
        local_event_id: str,
        event_data: dict[str, Any],
        calendar_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Sync a local event to Google Calendar with UPSERT logic.

        This method checks for existing sync state and either creates a new event
        or updates an existing one, preventing duplicates.

        Args:
            user_id: User ID
            persona_id: Persona ID
            local_event_id: Unique local event identifier
            event_data: Event data dictionary (summary, start, end, etc.)
            calendar_id: Google Calendar ID (default: self.default_calendar_id)

        Returns:
            Dict with:
            - success: bool
            - gcal_event_id: Google Calendar event ID
            - message: Status message
            - action: "create" or "update"
        """
        calendar_id = calendar_id or self.default_calendar_id

        try:
            # Check for existing sync state
            sync_state = await self.store.get_sync_state(
                user_id=user_id, persona_id=persona_id, local_event_id=local_event_id
            )

            if sync_state:
                # Event already synced - update instead
                gcal_event_id = sync_state.get("google_event_id") or sync_state.get("gcal_event_id")
                if gcal_event_id:
                    # Update existing event
                    updated_event = await self.update_event(
                        gcal_event_id,
                        event_data,
                        calendar_id=calendar_id,
                        user_id=user_id,
                        persona_id=persona_id,
                        local_event_id=local_event_id,
                    )

                    return {
                        "success": True,
                        "gcal_event_id": updated_event["id"],
                        "message": f"Event updated in Google Calendar (calendar: {calendar_id})",
                        "action": "update",
                    }
                # Sync state exists but no gcal_event_id - create new
                logger.warning(
                    f"Sync state exists for {local_event_id} but no gcal_event_id. Creating new event."
                )

            # Create new event
            created_event = await self.create_event(
                event_data=event_data,
                local_event_id=local_event_id,
                calendar_id=calendar_id,
                user_id=user_id,
                persona_id=persona_id,
            )

            return {
                "success": True,
                "gcal_event_id": created_event["id"],
                "message": f"Event created in Google Calendar (calendar: {calendar_id})",
                "action": "create",
            }

        except HttpError as e:
            error_msg = f"Google Calendar API error: {e}"
            logger.exception(error_msg)
            return {"success": False, "gcal_event_id": None, "message": error_msg, "action": None}
        except Exception as e:
            error_msg = f"Error syncing event to Google Calendar: {e!s}"
            logger.exception(error_msg)
            return {"success": False, "gcal_event_id": None, "message": error_msg, "action": None}

    async def get_sync_status(
        self,
        user_id: str,
        persona_id: str,
        local_event_id: str,
    ) -> dict[str, Any] | None:
        """
        Get sync status for a local event.

        Args:
            user_id: User ID
            persona_id: Persona ID
            local_event_id: Local event identifier

        Returns:
            Dict with sync state or None if not found
        """
        return await self.store.get_sync_state(
            user_id=user_id, persona_id=persona_id, local_event_id=local_event_id
        )

    async def get_synced_events_count(
        self,
        user_id: str,
        persona_id: str | None = None,
        calendar_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get count of synced events for a user.

        Args:
            user_id: User ID (required)
            persona_id: Optional persona ID filter
            calendar_id: Optional calendar ID filter

        Returns:
            Dict with:
            - total_events: Total count
            - events_by_calendar: Dict mapping calendar_id to count
            - calendars_count: Number of unique calendars
        """
        result = await self.store.count_events_by_user(
            user_id=user_id, persona_id=persona_id, calendar_id=calendar_id, sync_status="synced"
        )

        return {
            "total_events": result["total"],
            "events_by_calendar": result["by_calendar"],
            "calendars_count": result["calendars_count"],
        }
