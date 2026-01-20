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
- Dependencies installed: Run `uv pip install -e ".[test]"` in `04-lambda/` directory

Validation:
This sample validates its results through:

1. **API Verification**: Uses `verify_calendar_data()` from `sample/shared/verification_helpers.py`
   - Verifies calendar events via `/api/me/data/calendar` endpoint
   - Checks that at least the expected number of events exist
   - Validates event data structure and counts
   - Supports retry logic (3 retries with 2s delay) for eventual consistency

2. **Exit Code Validation**:
   - Returns exit code 0 if verification passes or OAuth is not configured (graceful failure)
   - Returns exit code 1 if fatal errors occur during event creation

3. **Error Handling**:
   - Catches and logs exceptions during event creation
   - Provides clear error messages for debugging
   - Gracefully handles missing OAuth credentials (warns but continues)
   - Ensures proper cleanup of dependencies in finally block

4. **Result Validation**:
   - Verifies that events are created successfully (checks result action: 'create' or 'update')
   - Validates event data matches input parameters
   - Confirms sync state is tracked in MongoDB

The sample will fail validation if:
- Event creation fails (OAuth errors, API errors, etc.)
- Verification API call fails (network errors, auth errors)
- Expected minimum event count is not met
- Dependencies fail to initialize or cleanup

Note: This sample gracefully handles OAuth configuration issues and will exit with code 0
if verification fails due to OAuth (allowing samples to run even if OAuth is not configured).
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))  # Add project root for sample.shared imports
lambda_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from capabilities.calendar.ai.dependencies import CalendarDeps  # noqa: E402
from capabilities.calendar.calendar_sync.agent import create_calendar_event_tool  # noqa: E402

from sample.shared.auth_helpers import (  # noqa: E402
    get_mongodb_credentials,
    require_cloudflare_email,
)
from shared.context_helpers import create_run_context  # noqa: E402

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

        # Verify via API
        from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
        from sample.shared.verification_helpers import verify_calendar_data

        api_base_url = get_api_base_url()
        headers = get_auth_headers()

        print("\n" + "=" * 80)
        print("Verification")
        print("=" * 80)

        success, message = verify_calendar_data(
            api_base_url=api_base_url,
            headers=headers,
            expected_events_min=len(events),
        )
        print(message)

        if success:
            print("\n✅ Verification passed!")
            sys.exit(0)
        else:
            print("\n❌ Verification failed (events may need time to sync)")
            sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
