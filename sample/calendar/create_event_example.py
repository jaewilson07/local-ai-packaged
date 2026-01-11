#!/usr/bin/env python3
"""Create calendar event example using Calendar project.

This example demonstrates how to create a Google Calendar event using
the Calendar project's sync service, which automatically tracks sync state
to prevent duplicates.

UPSERT Behavior:
The sync service automatically prevents duplicates by checking sync state.
If you call create_calendar_event_tool() multiple times with the same
local_event_id, user_id, and persona_id, the event will be UPDATED instead
of creating a duplicate. This ensures you always have exactly one event
per local_event_id, even if the creation function is called multiple times.

The sync state is tracked in MongoDB using the combination of:
- user_id
- persona_id
- local_event_id

This triple forms a unique key, so different users or personas can have
events with the same local_event_id without conflicts.

Prerequisites:
- MongoDB running (for sync state tracking)
- Google Calendar OAuth2 credentials configured
- Environment variables configured (MONGODB_URI, GOOGLE_CALENDAR_CREDENTIALS_PATH, etc.)
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))  # Add project root for sample.shared imports
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging

from sample.shared.auth_helpers import (
    get_cloudflare_email,
    require_cloudflare_email,
    get_mongodb_credentials,
)
from server.projects.calendar.agent import create_calendar_event_tool
from server.projects.calendar.dependencies import CalendarDeps
from server.projects.shared.context_helpers import create_run_context

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Create calendar events."""
    # Get user email from environment (for MongoDB auth)
    try:
        user_email = require_cloudflare_email()
        print(f"Using Cloudflare email: {user_email}")
    except ValueError as e:
        print(f"⚠️  Warning: {e}")
        print("Continuing with service account MongoDB connection...")
        user_email = None
    
    # Get MongoDB credentials from Supabase if user email is available
    mongodb_username = None
    mongodb_password = None
    if user_email:
        try:
            mongodb_username, mongodb_password = await get_mongodb_credentials(user_email)
            if mongodb_username and mongodb_password:
                print(f"✅ Found MongoDB credentials for user: {user_email}")
            else:
                print(f"⚠️  No MongoDB credentials found for user: {user_email}")
                print("   Falling back to service account connection...")
        except Exception as e:
            print(f"⚠️  Failed to get MongoDB credentials: {e}")
            print("   Falling back to service account connection...")
    
    # Example user and persona IDs (using email as user_id if available)
    user_id = user_email or "user_123"
    persona_id = "persona_456"

    # Example events to create
    now = datetime.now()
    events = [
        {
            "local_event_id": f"event_{int(now.timestamp())}_1",
            "summary": "Team Meeting",
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
            "description": "Weekly team sync meeting",
            "location": "Conference Room A",
        },
        {
            "local_event_id": f"event_{int(now.timestamp())}_2",
            "summary": "Project Review",
            "start": (now + timedelta(days=1)).isoformat(),
            "end": (now + timedelta(days=1, hours=1)).isoformat(),
            "description": "Quarterly project review and planning",
            "location": "Virtual",
        },
    ]

    print("=" * 80)
    print("Calendar - Create Event Example")
    print("=" * 80)
    print()
    print("This example demonstrates creating Google Calendar events")
    print("with automatic sync state tracking to prevent duplicates.")
    print()
    print(f"User ID: {user_id}")
    print(f"Persona ID: {persona_id}")
    print()

    # Initialize dependencies with user MongoDB credentials if available
    deps = CalendarDeps.from_settings(
        mongodb_username=mongodb_username,
        mongodb_password=mongodb_password,
    )
    await deps.initialize()

    try:
        # Create run context for tools
        ctx = create_run_context(deps)

        # Create each event
        for i, event_data in enumerate(events, 1):
            print(f"\n{'=' * 80}")
            print(f"Event {i}: {event_data['summary']}")
            print("=" * 80)

            logger.info(f"Creating calendar event: {event_data['summary']}")

            # Create event using agent tool
            result = await create_calendar_event_tool(
                ctx=ctx,
                user_id=user_id,
                persona_id=persona_id,
                local_event_id=event_data["local_event_id"],
                summary=event_data["summary"],
                start=event_data["start"],
                end=event_data["end"],
                description=event_data.get("description"),
                location=event_data.get("location"),
                timezone="America/Los_Angeles",
                calendar_id="primary",
            )

            print(f"\nResult: {result}")
            print()

        print("=" * 80)
        print("✅ Calendar event creation completed!")
        print("=" * 80)
        print()
        print("UPSERT Behavior:")
        print("  - Sync state is automatically tracked in MongoDB")
        print("  - If you run this again with the same local_event_id,")
        print("    user_id, and persona_id, the event will be UPDATED")
        print("    instead of creating a duplicate")
        print("  - The sync service checks for existing sync state before")
        print("    creating, ensuring exactly one event per local_event_id")
        print()
        print("To verify UPSERT behavior:")
        print("  1. Run this script once - event will be created")
        print("  2. Run this script again with the same local_event_id")
        print("  3. Check the result - it should show 'update' action")
        print("  4. Check Google Calendar - you should see only ONE event")
        print("=" * 80)

    except Exception as e:
        logger.exception(f"❌ Error creating calendar event: {e}")
        print(f"\n❌ Fatal error: {e}")
        print("\nNote: Make sure Google Calendar OAuth2 credentials are configured.")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
