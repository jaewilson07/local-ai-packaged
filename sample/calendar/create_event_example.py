#!/usr/bin/env python3
"""Create calendar event example using Calendar project.

This example demonstrates how to create a Google Calendar event using
the Calendar project's sync service, which automatically tracks sync state
to prevent duplicates.

Prerequisites:
- MongoDB running (for sync state tracking)
- Google Calendar OAuth2 credentials configured
- Environment variables configured (MONGODB_URI, GOOGLE_CALENDAR_CREDENTIALS_PATH, etc.)
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

from server.projects.calendar.dependencies import CalendarDeps
from server.projects.calendar.agent import create_calendar_event_tool
from server.projects.shared.context_helpers import create_run_context
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Create calendar events."""
    # Example user and persona IDs
    user_id = "user_123"
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
    
    print("="*80)
    print("Calendar - Create Event Example")
    print("="*80)
    print()
    print("This example demonstrates creating Google Calendar events")
    print("with automatic sync state tracking to prevent duplicates.")
    print()
    print(f"User ID: {user_id}")
    print(f"Persona ID: {persona_id}")
    print()
    
    # Initialize dependencies
    deps = CalendarDeps.from_settings()
    await deps.initialize()
    
    try:
        # Create run context for tools
        ctx = create_run_context(deps)
        
        # Create each event
        for i, event_data in enumerate(events, 1):
            print(f"\n{'='*80}")
            print(f"Event {i}: {event_data['summary']}")
            print("="*80)
            
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
                calendar_id="primary"
            )
            
            print(f"\nResult: {result}")
            print()
        
        print("="*80)
        print("✅ Calendar event creation completed!")
        print("="*80)
        print()
        print("Note: Sync state is automatically tracked in MongoDB.")
        print("      If you run this again with the same local_event_id,")
        print("      the event will be updated instead of duplicated.")
        print("="*80)
        
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
