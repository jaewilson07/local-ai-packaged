#!/usr/bin/env python3
"""End-to-end test for API token authentication flow.

This script demonstrates the complete token authentication flow:
1. Generate a new API token using internal network auth (X-User-Email)
2. Use the token to make authenticated API calls
3. Verify the token info
4. Test the token with various endpoints
5. Optionally revoke the token

Usage:
    # Run with internal network auth (from host machine)
    API_BASE_URL=http://localhost:8000 CLOUDFLARE_EMAIL=your@email.com python test_token_flow.py

    # Or set CLOUDFLARE_EMAIL in .env file
    python test_token_flow.py

    # Skip token revocation to keep the token for future use
    python test_token_flow.py --keep-token

    # Test with an existing token
    LAMBDA_API_TOKEN=lat_xxx python test_token_flow.py --use-existing
"""

import argparse
import os
import sys
from pathlib import Path

# Add sample directory to path for shared imports
sample_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sample_dir.parent))

import requests

from sample.shared.auth_helpers import (
    get_cloudflare_email,
    print_auth_info,
)


def test_health(base_url: str) -> bool:
    """Test server health endpoint."""
    print("\n1. Testing server health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print(f"   ✓ Server healthy: {response.json()}")
            return True
        print(f"   ✗ Health check failed: {response.status_code}")
        return False
    except requests.RequestException as e:
        print(f"   ✗ Connection error: {e}")
        return False


def test_auth_with_email(base_url: str, email: str) -> dict | None:
    """Test authentication with X-User-Email header and generate token."""
    print("\n2. Testing internal network auth (X-User-Email)...")

    # First, get current user info
    headers = {"X-User-Email": email}
    try:
        response = requests.get(f"{base_url}/api/me", headers=headers, timeout=10)
        if response.status_code == 200:
            user_info = response.json()
            print(f"   ✓ Authenticated as: {user_info.get('email')}")
            print(f"   ✓ User ID: {user_info.get('id')}")
            print(f"   ✓ Role: {user_info.get('role', 'user')}")
            return user_info
        print(f"   ✗ Auth failed: {response.status_code} - {response.text}")
        return None
    except requests.RequestException as e:
        print(f"   ✗ Request error: {e}")
        return None


def generate_primary_token(base_url: str, email: str) -> str | None:
    """Generate a new primary API token."""
    print("\n3. Generating primary API token...")

    headers = {"X-User-Email": email}
    try:
        response = requests.post(f"{base_url}/api/me/token", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            print("   ✓ Token generated successfully!")
            print(f"   ✓ Token prefix: {token[:20]}..." if token else "   ✗ No token in response")
            print(f"   ✓ Created at: {data.get('created_at')}")
            return token
        print(f"   ✗ Token generation failed: {response.status_code} - {response.text}")
        return None
    except requests.RequestException as e:
        print(f"   ✗ Request error: {e}")
        return None


def generate_named_token(
    base_url: str, email: str, name: str, scopes: list | None = None
) -> str | None:
    """Generate a named API token."""
    print(f"\n   Generating named token '{name}'...")

    headers = {"X-User-Email": email, "Content-Type": "application/json"}
    payload = {"name": name}
    if scopes:
        payload["scopes"] = scopes

    try:
        response = requests.post(
            f"{base_url}/api/me/tokens",
            headers=headers,
            json=payload,
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            print(f"   ✓ Named token '{name}' generated!")
            print(f"   ✓ Token ID: {data.get('id')}")
            print(f"   ✓ Token prefix: {token[:20]}..." if token else "   ✗ No token in response")
            return token
        print(f"   ✗ Named token generation failed: {response.status_code} - {response.text}")
        return None
    except requests.RequestException as e:
        print(f"   ✗ Request error: {e}")
        return None


def test_token_auth(base_url: str, token: str) -> bool:
    """Test authentication using the API token."""
    print("\n4. Testing token authentication (Bearer token)...")

    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{base_url}/api/me", headers=headers, timeout=10)
        if response.status_code == 200:
            user_info = response.json()
            print("   ✓ Token auth successful!")
            print(f"   ✓ Authenticated as: {user_info.get('email')}")
            return True
        print(f"   ✗ Token auth failed: {response.status_code} - {response.text}")
        return False
    except requests.RequestException as e:
        print(f"   ✗ Request error: {e}")
        return False


def get_token_info(base_url: str, token: str) -> dict | None:
    """Get information about the current token."""
    print("\n5. Getting token info...")

    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{base_url}/api/me/token", headers=headers, timeout=10)
        if response.status_code == 200:
            info = response.json()
            print(f"   ✓ Token exists: {info.get('exists', False)}")
            print(f"   ✓ Created at: {info.get('created_at')}")
            return info
        print(f"   ✗ Token info failed: {response.status_code} - {response.text}")
        return None
    except requests.RequestException as e:
        print(f"   ✗ Request error: {e}")
        return None


def list_named_tokens(base_url: str, token: str) -> list | None:
    """List all named tokens for the user."""
    print("\n6. Listing named tokens...")

    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{base_url}/api/me/tokens", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Handle both list and dict responses
            if isinstance(data, dict):
                tokens = data.get("tokens", [])
                total = data.get("total", len(tokens))
            else:
                tokens = data
                total = len(tokens)
            print(f"   ✓ Found {total} named token(s)")
            for t in tokens:
                if isinstance(t, dict):
                    print(
                        f"      - {t.get('name')}: ID={t.get('id')}, created={t.get('created_at')}"
                    )
                else:
                    print(f"      - {t}")
            return tokens
        print(f"   ✗ List tokens failed: {response.status_code} - {response.text}")
        return None
    except requests.RequestException as e:
        print(f"   ✗ Request error: {e}")
        return None


def test_protected_endpoint(base_url: str, token: str) -> bool:
    """Test accessing a protected endpoint with the token."""
    print("\n7. Testing protected endpoint access...")

    headers = {"Authorization": f"Bearer {token}"}

    # Try to access ComfyUI workflows endpoint (if available)
    endpoints_to_try = [
        ("/api/v1/comfyui/workflows", "ComfyUI Workflows"),
        ("/api/v1/comfyui/loras", "ComfyUI LoRAs"),
        ("/api/v1/images/minio", "User Images (MinIO)"),
    ]

    success = False
    for endpoint, name in endpoints_to_try:
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else data.get("count", "N/A")
                print(f"   ✓ {name}: {count} items")
                success = True
            elif response.status_code == 404:
                print(f"   - {name}: endpoint not found (404)")
            else:
                print(f"   ✗ {name}: {response.status_code}")
        except requests.RequestException as e:
            print(f"   ✗ {name}: {e}")

    return success


def revoke_token(base_url: str, email: str) -> bool:
    """Revoke the primary API token."""
    print("\n8. Revoking primary token...")

    headers = {"X-User-Email": email}
    try:
        response = requests.delete(f"{base_url}/api/me/token", headers=headers, timeout=10)
        if response.status_code == 200:
            print("   ✓ Token revoked successfully")
            return True
        print(f"   ✗ Revoke failed: {response.status_code} - {response.text}")
        return False
    except requests.RequestException as e:
        print(f"   ✗ Request error: {e}")
        return False


def revoke_named_token(base_url: str, token: str, token_name: str) -> bool:
    """Revoke a named API token by name."""
    print(f"\n   Revoking named token '{token_name}'...")

    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.delete(
            f"{base_url}/api/me/tokens/name/{token_name}",
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            print(f"   ✓ Named token '{token_name}' revoked")
            return True
        print(f"   ✗ Revoke failed: {response.status_code} - {response.text}")
        return False
    except requests.RequestException as e:
        print(f"   ✗ Request error: {e}")
        return False


def test_token_no_longer_works(base_url: str, token: str) -> bool:
    """Verify that a revoked token no longer works."""
    print("\n9. Verifying token is revoked...")

    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{base_url}/api/me", headers=headers, timeout=10)
        if response.status_code == 401:
            print("   ✓ Token correctly rejected (401 Unauthorized)")
            return True
        if response.status_code == 200:
            print("   ✗ Token still works! Revocation may have failed.")
            return False
        print(f"   ? Unexpected status: {response.status_code}")
        return False
    except requests.RequestException as e:
        print(f"   ✗ Request error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test API token authentication flow")
    parser.add_argument(
        "--keep-token",
        action="store_true",
        help="Don't revoke the token after testing (keep for future use)",
    )
    parser.add_argument(
        "--use-existing",
        action="store_true",
        help="Use existing LAMBDA_API_TOKEN instead of generating a new one",
    )
    parser.add_argument(
        "--test-named",
        action="store_true",
        help="Also test named token creation/revocation",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("API Token Authentication Flow - End-to-End Test")
    print("=" * 60)

    # Print current auth config
    print("\nCurrent authentication configuration:")
    print_auth_info()

    # Get configuration
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    email = get_cloudflare_email()

    if not email:
        print("\n✗ ERROR: CLOUDFLARE_EMAIL not set!")
        print("  Set it in .env or export CLOUDFLARE_EMAIL=your@email.com")
        sys.exit(1)

    print("\nConfiguration:")
    print(f"  Base URL: {base_url}")
    print(f"  User Email: {email}")

    # Run tests
    results = []

    # Step 1: Health check
    results.append(("Health check", test_health(base_url)))

    if args.use_existing:
        # Use existing token
        token = os.getenv("LAMBDA_API_TOKEN")
        if not token:
            print("\n✗ ERROR: LAMBDA_API_TOKEN not set!")
            print("  Set it with: export LAMBDA_API_TOKEN=lat_xxx...")
            sys.exit(1)
        print(f"\nUsing existing token: {token[:20]}...")
    else:
        # Step 2: Test internal network auth
        user_info = test_auth_with_email(base_url, email)
        results.append(("Internal auth", user_info is not None))

        if not user_info:
            print("\n✗ Cannot proceed without authentication")
            sys.exit(1)

        # Step 3: Generate token
        token = generate_primary_token(base_url, email)
        results.append(("Token generation", token is not None))

        if not token:
            print("\n✗ Cannot proceed without a token")
            sys.exit(1)

    # Step 4: Test token auth
    results.append(("Token auth", test_token_auth(base_url, token)))

    # Step 5: Get token info
    token_info = get_token_info(base_url, token)
    results.append(("Token info", token_info is not None))

    # Step 6: List named tokens
    named_tokens = list_named_tokens(base_url, token)
    results.append(("List tokens", named_tokens is not None))

    # Step 7: Test protected endpoints
    results.append(("Protected endpoints", test_protected_endpoint(base_url, token)))

    # Optional: Test named tokens
    named_token = None
    if args.test_named:
        print("\n--- Testing Named Tokens ---")
        named_token = generate_named_token(base_url, email, "test-script-token", scopes=["read"])
        results.append(("Named token creation", named_token is not None))

        if named_token:
            results.append(("Named token auth", test_token_auth(base_url, named_token)))

    # Step 8: Revoke token (unless --keep-token)
    if not args.keep_token and not args.use_existing:
        # Clean up named token first
        if named_token:
            results.append(
                ("Named token revocation", revoke_named_token(base_url, token, "test-script-token"))
            )

        results.append(("Token revocation", revoke_token(base_url, email)))

        # Step 9: Verify token no longer works
        results.append(("Revocation verification", test_token_no_longer_works(base_url, token)))
    else:
        print("\n8. Skipping token revocation (--keep-token or --use-existing)")
        print("\n   ★ Your token for future use:")
        print(f"   export LAMBDA_API_TOKEN={token}")

    # Print summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Token authentication flow is working correctly.")
        return 0
    print("\n✗ Some tests failed. Check the output above for details.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
