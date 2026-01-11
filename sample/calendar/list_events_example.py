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
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

from server.projects.calendar.dependencies import CalendarDeps
from server.projects.calendar.agent import list_calendar_events_tool
from server.projects.shared.context_helpers import create_run_context
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """List calendar events."""
    # Example user ID
    user_id = "user_123"
    
    # Time range for events (next 7 days)
    now = datetime.now()
    start_time = now.isoformat()
    end_time = (now + timedelta(days=7)).isoformat()
    
    print("="*80)
    print("Calendar - List Events Example")
    print("="*80)
    print()
    print("This example demonstrates listing Google Calendar events")
    print("with time range filtering.")
    print()
    print(f"User ID: {user_id}")
    print(f"Time range: {start_time} to {end_time}")
    print()
    
    # Initialize dependencies
    deps = CalendarDeps.from_settings()
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
            timezone="America/Los_Angeles"
        )
        
        # Display results
        print("\n" + "="*80)
        print("CALENDAR EVENTS")
        print("="*80)
        print(result)
        print("="*80)
        
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
                    if event.get('location'):
                        print(f"  Location: {event.get('location')}")
                    if event.get('description'):
                        desc = event.get('description', '')[:100]
                        print(f"  Description: {desc}...")
                    print()
            else:
                print(f"\n⚠️  Failed to list events: {result_data.get('error', 'Unknown error')}")
        except json.JSONDecodeError:
            # Result might not be JSON if there's an error
            print(f"\n⚠️  Could not parse result as JSON")
        
        print("="*80)
        print("✅ Calendar event listing completed!")
        print("="*80)
        
    except Exception as e:
        logger.exception(f"❌ Error listing calendar events: {e}")
        print(f"\n❌ Fatal error: {e}")
        print("\nNote: Make sure Google Calendar OAuth2 credentials are configured.")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
