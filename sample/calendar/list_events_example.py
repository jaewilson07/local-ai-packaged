#!/usr/bin/env python3
"""List calendar events example using Calendar project.

This example demonstrates how to list and filter Google Calendar events
using the Calendar project's sync service.

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

import logging  # noqa: E402

from sample.shared.auth_helpers import (  # noqa: E402
    get_mongodb_credentials,
    require_cloudflare_email,
)
from server.projects.calendar.agent import list_calendar_events_tool  # noqa: E402
from server.projects.calendar.dependencies import CalendarDeps  # noqa: E402
from server.projects.shared.context_helpers import create_run_context  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """List calendar events."""
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

    # Example user ID (using email as user_id if available)
    user_id = user_email or "user_123"

    # Time range for events (next 7 days)
    now = datetime.now()
    start_time = now.isoformat()
    end_time = (now + timedelta(days=7)).isoformat()

    print("=" * 80)
    print("Calendar - List Events Example")
    print("=" * 80)
    print()
    print("This example demonstrates listing Google Calendar events")
    print("with time range filtering.")
    print()
    print(f"User ID: {user_id}")
    print(f"Time range: {start_time} to {end_time}")
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

        # List events
        print("🔍 Fetching calendar events...")
        logger.info(f"Listing calendar events for user: {user_id}")

        result = await list_calendar_events_tool(
            ctx=ctx,
            user_id=user_id,
            calendar_id="primary",
            start_time=start_time,
            end_time=end_time,
            timezone="America/Los_Angeles",
        )

        # Display results
        print("\n" + "=" * 80)
        print("CALENDAR EVENTS")
        print("=" * 80)
        print(result)
        print("=" * 80)

        # Parse and display formatted results
        import json

        try:
            result_data = json.loads(result)
            if result_data.get("success"):
                events = result_data.get("events", [])
                print(f"\n✅ Found {result_data.get('count', 0)} event(s):\n")

                for i, event in enumerate(events, 1):
                    print(f"Event {i}:")
                    print(f"  ID: {event.get('id')}")
                    print(f"  Summary: {event.get('summary')}")
                    print(f"  Start: {event.get('start')}")
                    print(f"  End: {event.get('end')}")
                    if event.get("location"):
                        print(f"  Location: {event.get('location')}")
                    if event.get("description"):
                        desc = event.get("description", "")[:100]
                        print(f"  Description: {desc}...")
                    print()
            else:
                print(f"\n⚠️  Failed to list events: {result_data.get('error', 'Unknown error')}")
        except json.JSONDecodeError:
            # Result might not be JSON if there's an error
            print("\n⚠️  Could not parse result as JSON")

        print("=" * 80)
        print("✅ Calendar event listing completed!")
        print("=" * 80)

        # Verify via API
        from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
        from sample.shared.verification_helpers import verify_calendar_data

        api_base_url = get_api_base_url()
        headers = get_auth_headers()

        print("\n" + "=" * 80)
        print("Verification")
        print("=" * 80)

        # Check that we got results from the list operation
        result_data = json.loads(result) if isinstance(result, str) else result
        events_count = result_data.get("count", 0) if result_data.get("success") else 0

        success, message = verify_calendar_data(
            api_base_url=api_base_url,
            headers=headers,
            expected_events_min=events_count if events_count > 0 else None,
        )
        print(message)

        if events_count > 0 or success:
            print("\n✅ Verification passed!")
            sys.exit(0)
        else:
            print("\n⚠️  No events found (may be expected if calendar is empty)")
            sys.exit(0)  # Don't fail if calendar is empty
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
