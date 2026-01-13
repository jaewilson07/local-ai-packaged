#!/usr/bin/env python3
"""
Validate ComfyUI API Configuration
Checks if APIs are enabled and accessible
"""

import json
import sys

import requests

# Configuration
BASE_URL = "http://localhost:8188"
API_BASE = f"{BASE_URL}/ai-dock/api"
API_DOCS = f"{API_BASE}/docs"
API_PAYLOAD = f"{API_BASE}/payload"
API_QUEUE_INFO = f"{API_BASE}/queue-info"

# Default credentials (from docker-compose.yaml)
WEB_USER = "user"
WEB_PASSWORD = "password"


def check_service_status():
    """Check if ComfyUI service is running"""
    print("=" * 60)
    print("1. Checking ComfyUI Service Status")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}", timeout=5)
        if response.status_code == 200:
            print("✅ ComfyUI web interface is accessible")
            return True
        print(f"⚠️  ComfyUI returned status code: {response.status_code}")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to ComfyUI. Is the container running?")
        print(f"   Expected URL: {BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ Error checking ComfyUI: {e}")
        return False


def check_api_docs():
    """Check if API documentation is accessible"""
    print("\n" + "=" * 60)
    print("2. Checking API Documentation Endpoint")
    print("=" * 60)

    try:
        # Try without auth first
        response = requests.get(API_DOCS, timeout=5)
        if response.status_code == 200:
            print("✅ API documentation is accessible (no auth required)")
            print(f"   URL: {API_DOCS}")
            return True, None
        if response.status_code == 401:
            print("⚠️  API requires authentication")
            return False, "auth_required"
        print(f"⚠️  API docs returned status code: {response.status_code}")
        return False, None
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API wrapper service")
        print(f"   Expected URL: {API_DOCS}")
        print("   Make sure the API wrapper service is running in supervisor")
        return False, None
    except Exception as e:
        print(f"❌ Error checking API docs: {e}")
        return False, None


def check_api_with_auth():
    """Check API with authentication"""
    print("\n" + "=" * 60)
    print("3. Checking API with Authentication")
    print("=" * 60)

    session = requests.Session()
    session.auth = (WEB_USER, WEB_PASSWORD)

    try:
        response = session.get(API_DOCS, timeout=5)
        if response.status_code == 200:
            print("✅ API is accessible with authentication")
            print(f"   Using credentials: {WEB_USER} / {WEB_PASSWORD}")
            return True, session
        print(f"⚠️  API returned status code: {response.status_code}")
        return False, None
    except Exception as e:
        print(f"❌ Error checking API with auth: {e}")
        return False, None


def check_comfyui_api():
    """Check if ComfyUI native API is accessible"""
    print("\n" + "=" * 60)
    print("4. Checking ComfyUI Native API")
    print("=" * 60)

    try:
        # Check queue endpoint
        response = requests.get(f"{BASE_URL}/queue", timeout=5)
        if response.status_code == 200:
            try:
                queue_data = response.json()
                print("✅ ComfyUI native API is accessible")
                print(f"   Running jobs: {len(queue_data.get('running', []))}")
                print(f"   Pending jobs: {len(queue_data.get('pending', []))}")
                return True
            except json.JSONDecodeError:
                # Response might be HTML or empty
                if response.text.strip():
                    print("⚠️  ComfyUI API returned non-JSON response")
                    print(f"   Response preview: {response.text[:100]}...")
                else:
                    print("⚠️  ComfyUI API returned empty response")
                return False
        else:
            print(f"⚠️  ComfyUI API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to ComfyUI API")
        return False
    except Exception as e:
        print(f"❌ Error checking ComfyUI API: {e}")
        return False


def check_api_wrapper_endpoint(session=None):
    """Check if API wrapper payload endpoint exists"""
    print("\n" + "=" * 60)
    print("5. Checking API Wrapper Payload Endpoint")
    print("=" * 60)

    try:
        # Try to get OpenAPI schema to verify endpoint exists
        if session:
            response = session.get(f"{API_BASE}/openapi.json", timeout=5)
        else:
            response = requests.get(f"{API_BASE}/openapi.json", timeout=5)

        if response.status_code == 200:
            try:
                schema = response.json()
                paths = schema.get("paths", {})
                if "/payload" in paths:
                    print("✅ API wrapper payload endpoint is available")
                    print(f"   Endpoint: POST {API_PAYLOAD}")
                    return True
                print("⚠️  API wrapper endpoint not found in schema")
                print(f"   Available paths: {list(paths.keys())}")
                return False
            except json.JSONDecodeError:
                print("⚠️  API returned non-JSON response")
                print(f"   Response preview: {response.text[:200]}...")
                return False
        elif response.status_code == 404:
            # Try checking if the service is running by checking docs
            print("⚠️  OpenAPI schema not found, but API docs are accessible")
            print("   API wrapper service may be starting up")
            print(f"   Try accessing: {API_DOCS}")
            return False
        else:
            print(f"⚠️  Could not fetch API schema (status: {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API wrapper service")
        print("   Make sure the API wrapper service is running:")
        print("   docker exec -it comfyui-supervisor-1 supervisorctl status comfyui_api_wrapper")
        return False
    except Exception as e:
        print(f"❌ Error checking API wrapper endpoint: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("ComfyUI API Validation Script")
    print("=" * 60 + "\n")

    # Check 1: Service status
    service_ok = check_service_status()
    if not service_ok:
        print("\n❌ ComfyUI service is not running. Please start the container first.")
        sys.exit(1)

    # Check 2: API docs
    _api_docs_ok, auth_status = check_api_docs()

    # Check 3: Try with auth if needed
    session = None
    if auth_status == "auth_required":
        api_ok, session = check_api_with_auth()
        if not api_ok:
            print("\n⚠️  API may require different credentials. Check your .env file.")

    # Check 4: ComfyUI native API
    comfyui_api_ok = check_comfyui_api()

    # Check 5: API wrapper endpoint
    wrapper_ok = check_api_wrapper_endpoint(session)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"ComfyUI Service:      {'✅ OK' if service_ok else '❌ FAILED'}")
    print(f"ComfyUI Native API:   {'✅ OK' if comfyui_api_ok else '❌ FAILED'}")
    print(f"API Wrapper Service:  {'✅ OK' if wrapper_ok else '❌ FAILED'}")
    print(
        f"Authentication:       {'🔒 Required' if auth_status == 'auth_required' else '🔓 Not Required'}"
    )

    if service_ok and comfyui_api_ok and wrapper_ok:
        print("\n✅ All API services are enabled and accessible!")
        print(f"\n📚 API Documentation: {API_DOCS}")
        print(f"📤 API Payload Endpoint: POST {API_PAYLOAD}")
        return 0
    print("\n⚠️  Some services are not accessible. Check the errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
