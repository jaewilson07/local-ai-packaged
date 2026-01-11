"""Manual test script for Immich API connectivity.

This script can be run independently to test Immich API connection:
    python -m tests.manual.test_immich_connection
"""

import asyncio
import sys
from pathlib import Path

# Add bot directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.config import config
from bot.immich_client import ImmichClient


async def test_immich_connection():
    """Test Immich API connectivity."""
    print("=" * 60)
    print("Testing Immich API Connection")
    print("=" * 60)

    # Check configuration
    if not config.IMMICH_API_KEY:
        print("❌ ERROR: IMMICH_API_KEY not set in environment")
        return False

    if not config.IMMICH_SERVER_URL:
        print("❌ ERROR: IMMICH_SERVER_URL not set in environment")
        return False

    print(f"✓ Immich Server URL: {config.IMMICH_SERVER_URL}")
    print(f"✓ API Key: {config.IMMICH_API_KEY[:10]}...")
    print()

    # Create client
    client = ImmichClient()

    try:
        # Test 1: Search for people (simple GET request)
        print("Test 1: Searching for people...")
        people = await client.search_people("")
        print(f"✓ Found {len(people)} people in Immich")
        print()

        # Test 2: List assets
        print("Test 2: Listing recent assets...")
        from datetime import datetime, timedelta

        since = datetime.utcnow() - timedelta(days=1)
        assets = await client.list_new_assets(since)
        print(f"✓ Found {len(assets)} assets updated in last 24 hours")
        print()

        # Test 3: Get asset info (if assets exist)
        if assets:
            print("Test 3: Getting asset information...")
            asset_id = assets[0]["id"]
            asset_info = await client.get_asset_info(asset_id)
            print(f"✓ Retrieved asset info for {asset_id}")
            print(f"  Type: {asset_info.get('type', 'N/A')}")
            print()

            # Test 4: Get asset faces
            print("Test 4: Checking for face detections...")
            faces = await client.get_asset_faces(asset_id)
            print(f"✓ Found {len(faces)} faces in asset")
            if faces:
                print(f"  Person IDs: {[f.get('personId') for f in faces]}")
            print()

        print("=" * 60)
        print("✅ All Immich connection tests passed!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e!s}")
        print()
        print("Troubleshooting:")
        print("1. Verify IMMICH_SERVER_URL is correct")
        print("2. Verify IMMICH_API_KEY is valid")
        print("3. Check if Immich server is running")
        print("4. Check network connectivity")
        return False


async def test_immich_upload():
    """Test Immich asset upload (optional)."""
    print("=" * 60)
    print("Testing Immich Asset Upload")
    print("=" * 60)

    client = ImmichClient()

    # Create a small test image (1x1 pixel PNG)
    test_image_data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    try:
        print("Uploading test image...")
        result = await client.upload_asset(
            file_data=test_image_data,
            filename="test_upload.png",
            description="Test upload from Discord bot test script",
        )
        print("✅ Upload successful!")
        print(f"  Asset ID: {result.get('id', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Upload failed: {type(e).__name__}: {e!s}")
        return False


async def main():
    """Main entry point."""
    print()
    success = await test_immich_connection()
    print()

    # Ask if user wants to test upload
    if success and "--upload" in sys.argv:
        await test_immich_upload()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
