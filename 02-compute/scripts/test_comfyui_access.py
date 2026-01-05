#!/usr/bin/env python3
"""
Test ComfyUI Access Configuration

Tests both local and remote access patterns to verify Cloudflare Access setup.
"""

import os
import sys
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.comfyui_api_client import get_comfyui_client


def test_local_access():
    """Test local access (should work without authentication)"""
    print("=" * 60)
    print("Test 1: Local Access (localhost:8188)")
    print("=" * 60)
    
    try:
        session = get_comfyui_client("http://localhost:8188")
        response = session.get("http://localhost:8188", timeout=5)
        
        if response.status_code == 200:
            print("✅ Local access works (no authentication needed)")
            return True
        else:
            print(f"⚠️  Local access returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to localhost:8188")
        print("   Is ComfyUI container running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_remote_access_with_token():
    """Test remote access with service token"""
    print("\n" + "=" * 60)
    print("Test 2: Remote Access with Service Token")
    print("=" * 60)
    
    token = os.getenv("COMFYUI_ACCESS_TOKEN")
    if not token:
        print("⚠️  COMFYUI_ACCESS_TOKEN not set - skipping remote test")
        print("   Set it with: export COMFYUI_ACCESS_TOKEN=your-token")
        return None
    
    try:
        session = get_comfyui_client("https://comfyui.datacrew.space")
        # Try a simple endpoint
        response = session.get("https://comfyui.datacrew.space", timeout=10)
        
        if response.status_code == 200:
            print("✅ Remote access works with service token")
            return True
        elif response.status_code == 403:
            print("❌ Access denied (403 Forbidden)")
            print("   Possible issues:")
            print("   1. Service token is incorrect")
            print("   2. Token not added to Access policy")
            print("   3. Cloudflare Access not configured")
            return False
        elif response.status_code == 401:
            print("❌ Authentication failed (401)")
            print("   Check service token configuration")
            return False
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except requests.exceptions.SSLError:
        print("⚠️  SSL error - check domain configuration")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to comfyui.datacrew.space")
        print("   Check Cloudflare Tunnel is running")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_remote_access_without_token():
    """Test remote access without token (should fail)"""
    print("\n" + "=" * 60)
    print("Test 3: Remote Access without Token (Should Fail)")
    print("=" * 60)
    
    # Temporarily unset token
    original_token = os.environ.pop("COMFYUI_ACCESS_TOKEN", None)
    
    try:
        session = get_comfyui_client("https://comfyui.datacrew.space")
        print("❌ Should have raised ValueError - token validation failed")
        return False
    except ValueError:
        print("✅ Correctly requires token for remote access")
        return True
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")
        return False
    finally:
        # Restore token
        if original_token:
            os.environ["COMFYUI_ACCESS_TOKEN"] = original_token


def test_helper_function():
    """Test the helper function itself"""
    print("\n" + "=" * 60)
    print("Test 4: Helper Function Validation")
    print("=" * 60)
    
    try:
        # Test local client
        local_client = get_comfyui_client("http://localhost:8188")
        assert "CF-Access-Token" not in local_client.headers, "Local should not have token"
        print("✅ Local client created correctly (no token)")
        
        # Test remote client (should require token)
        token = os.getenv("COMFYUI_ACCESS_TOKEN")
        if token:
            remote_client = get_comfyui_client("https://comfyui.datacrew.space")
            assert "CF-Access-Token" in remote_client.headers, "Remote should have token"
            print("✅ Remote client created correctly (with token)")
        else:
            try:
                get_comfyui_client("https://comfyui.datacrew.space")
                print("❌ Should have required token")
                return False
            except ValueError:
                print("✅ Remote client correctly requires token")
        
        return True
    except Exception as e:
        print(f"❌ Error testing helper function: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("ComfyUI Access Configuration Test")
    print("=" * 60 + "\n")
    
    results = {
        "local_access": test_local_access(),
        "helper_function": test_helper_function(),
        "remote_without_token": test_remote_access_without_token(),
        "remote_with_token": test_remote_access_with_token(),
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{test_name:30} {status}")
    
    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)
    
    if not results.get("remote_with_token"):
        print("\n⚠️  Remote access not working. Complete these steps:")
        print("1. Set up Cloudflare Access in dashboard")
        print("2. Create service token")
        print("3. Set COMFYUI_ACCESS_TOKEN environment variable")
        print("\nSee: 00-infrastructure/docs/cloudflare/comfyui-access-implementation.md")
    else:
        print("\n✅ All tests passed!")
        print("Cloudflare Access is configured correctly.")
    
    if results.get("local_access"):
        print("\n✅ Local access works - existing scripts unaffected")


if __name__ == "__main__":
    main()



