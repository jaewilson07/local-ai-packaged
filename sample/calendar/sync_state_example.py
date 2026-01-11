#!/usr/bin/env python3
"""Sync state tracking example using Calendar project.

This example demonstrates how sync state tracking works in the Calendar project.
Sync state prevents duplicate events by tracking the mapping between local
event IDs and Google Calendar event IDs in MongoDB.

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
from server.projects.calendar.dependencies import CalendarDeps

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate sync state tracking."""
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
    local_event_id = f"sync_demo_{int(datetime.now().timestamp())}"

    print("=" * 80)
    print("Calendar - Sync State Tracking Example")
    print("=" * 80)
    print()
    print("This example demonstrates sync state tracking:")
    print("  - How sync state prevents duplicate events")
    print("  - How to check if an event is already synced")
    print("  - How sync state maps local_event_id to gcal_event_id")
    print()
    print(f"User ID: {user_id}")
    print(f"Persona ID: {persona_id}")
    print(f"Local Event ID: {local_event_id}")
    print()

    # Initialize dependencies with user MongoDB credentials if available
    deps = CalendarDeps.from_settings(
        mongodb_username=mongodb_username,
        mongodb_password=mongodb_password,
    )
    await deps.initialize()

    try:
        # Get sync store
        sync_store = deps.sync_store

        # 1. Check if event exists in sync state
        print("=" * 80)
        print("1. CHECKING SYNC STATE")
        print("=" * 80)

        existing_state = await sync_store.get_sync_state(
            user_id=user_id, persona_id=persona_id, local_event_id=local_event_id
        )

        if existing_state:
            print("✅ Sync state found:")
            print(f"   Local Event ID: {existing_state.get('local_event_id')}")
            print(f"   Google Calendar Event ID: {existing_state.get('gcal_event_id')}")
            print(f"   Sync Status: {existing_state.get('sync_status')}")
            print(f"   Last Synced: {existing_state.get('last_synced_at')}")
        else:
            print(f"ℹ️  No sync state found for local_event_id: {local_event_id}")
            print("   This means the event hasn't been synced yet.")
        print()

        # 2. Create sync state (simulating event creation)
        print("=" * 80)
        print("2. CREATING SYNC STATE")
        print("=" * 80)

        # Simulate creating an event and getting a Google Calendar event ID
        mock_gcal_event_id = f"gcal_{local_event_id}"

        await sync_store.save_sync_state(
            user_id=user_id,
            persona_id=persona_id,
            local_event_id=local_event_id,
            gcal_event_id=mock_gcal_event_id,
            sync_status="synced",
            event_data={
                "summary": "Sync State Demo Event",
                "start": datetime.now().isoformat(),
                "end": (datetime.now() + timedelta(hours=1)).isoformat(),
            },
            gcal_calendar_id="primary",
        )

        print("✅ Sync state created:")
        print(f"   Local Event ID: {local_event_id}")
        print(f"   Google Calendar Event ID: {mock_gcal_event_id}")
        print("   Sync Status: synced")
        print()

        # 3. Check sync state again
        print("=" * 80)
        print("3. VERIFYING SYNC STATE")
        print("=" * 80)

        updated_state = await sync_store.get_sync_state(
            user_id=user_id, persona_id=persona_id, local_event_id=local_event_id
        )

        if updated_state:
            print("✅ Sync state verified:")
            print(f"   Local Event ID: {updated_state.get('local_event_id')}")
            print(f"   Google Calendar Event ID: {updated_state.get('gcal_event_id')}")
            print(f"   Sync Status: {updated_state.get('sync_status')}")
            print(f"   Created At: {updated_state.get('created_at')}")
            print(f"   Updated At: {updated_state.get('updated_at')}")
        else:
            print("❌ Sync state not found (unexpected)")
        print()

        # 4. Demonstrate duplicate prevention
        print("=" * 80)
        print("4. DUPLICATE PREVENTION")
        print("=" * 80)
        print("If you try to create the same event again:")
        print("  1. Check sync state for local_event_id")
        print("  2. If found, update existing Google Calendar event")
        print("  3. If not found, create new Google Calendar event")
        print()
        print("This prevents duplicate events from being created.")
        print()

        print("=" * 80)
        print("✅ Sync state tracking demonstration completed!")
        print("=" * 80)
        print()
        print("Sync state is stored in MongoDB and persists across sessions.")
        print("The Calendar sync service automatically uses sync state to")
        print("prevent duplicates when creating or updating events.")
        print("=" * 80)

    except Exception as e:
        logger.exception(f"❌ Error during sync state demo: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
