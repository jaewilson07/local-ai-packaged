#!/usr/bin/env python3
"""
ComfyUI API Client Helper

Provides authenticated API client for ComfyUI with automatic Cloudflare Access token handling.
Supports both local (localhost) and remote (domain-based) access patterns.
"""

import os

import requests


def get_comfyui_client(
    base_url: str | None = None, use_cloudflare_access: bool = True, timeout: int = 30
) -> requests.Session:
    """
    Get authenticated ComfyUI API client with proper authentication headers.

    Automatically handles:
    - Local access (localhost:8188) - no authentication needed
    - Remote access (comfyui.datacrew.space) - adds CF-Access-Token header

    Args:
        base_url: API base URL (defaults to COMFYUI_URL env var or localhost:8188)
        use_cloudflare_access: If True, add CF-Access-Token header for remote URLs
        timeout: Request timeout in seconds (default: 30)

    Returns:
        requests.Session configured with proper authentication

    Raises:
        ValueError: If remote URL is used but COMFYUI_ACCESS_TOKEN is not set

    Example:
        # Local access (no token needed)
        session = get_comfyui_client("http://localhost:8188")
        response = session.post("http://localhost:8188/ai-dock/api/payload", json=payload)

        # Remote access (requires token)
        session = get_comfyui_client("https://comfyui.datacrew.space")
        response = session.post("https://comfyui.datacrew.space/ai-dock/api/payload", json=payload)
    """
    session = requests.Session()
    session.timeout = timeout

    # Determine base URL
    if base_url is None:
        base_url = os.getenv("COMFYUI_URL", "http://localhost:8188")

    # Remove trailing slash for consistency
    base_url = base_url.rstrip("/")

    # Check if this is a remote URL that needs Cloudflare Access token
    is_remote = any(domain in base_url for domain in ["datacrew.space", "https://"])

    if is_remote and use_cloudflare_access:
        token = os.getenv("COMFYUI_ACCESS_TOKEN")
        if not token:
            raise ValueError(
                "COMFYUI_ACCESS_TOKEN environment variable is required for remote access. "
                "Set it in your .env file or export it before running the script.\n"
                "Get the token from: Cloudflare Zero Trust → Access → Service Tokens"
            )
        session.headers["CF-Access-Token"] = token

    # Set default headers
    if "Content-Type" not in session.headers:
        session.headers["Content-Type"] = "application/json"

    return session


def submit_comfyui_workflow(
    workflow_json: dict, base_url: str | None = None, api_endpoint: str = "/ai-dock/api/payload"
) -> str | None:
    """
    Submit a ComfyUI workflow and return the request ID.

    Args:
        workflow_json: ComfyUI workflow JSON payload
        base_url: API base URL (defaults to COMFYUI_URL env var or localhost:8188)
        api_endpoint: API endpoint path (default: /ai-dock/api/payload)

    Returns:
        Request ID if successful, None otherwise

    Example:
        workflow = {
            "input": {
                "workflow_json": {...}
            }
        }
        request_id = submit_comfyui_workflow(workflow)
    """
    session = get_comfyui_client(base_url)

    if base_url is None:
        base_url = os.getenv("COMFYUI_URL", "http://localhost:8188")
    base_url = base_url.rstrip("/")

    url = f"{base_url}{api_endpoint}"

    try:
        response = session.post(url, json=workflow_json)

        if response.status_code == 202:
            result = response.json()
            return result.get("id")
        if response.status_code == 401:
            print("❌ Authentication failed!")
            if "CF-Access-Token" in session.headers:
                print("   Check that COMFYUI_ACCESS_TOKEN is correct")
            else:
                print("   For remote access, set COMFYUI_ACCESS_TOKEN environment variable")
            return None
        if response.status_code == 403:
            print("❌ Access denied (403 Forbidden)")
            print("   This usually means:")
            print("   1. Cloudflare Access is blocking the request")
            print("   2. Service token is missing or invalid")
            print("   3. Access policy doesn't allow this token")
            return None
        print(f"❌ Failed to submit workflow (status: {response.status_code})")
        print(f"   Response: {response.text[:200]}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to ComfyUI API at {url}")
        print("   Is the service running?")
        return None
    except Exception as e:
        print(f"❌ Error submitting workflow: {e}")
        return None


def check_comfyui_result(
    request_id: str, base_url: str | None = None, api_endpoint: str = "/ai-dock/api/result"
) -> dict | None:
    """
    Check the status of a ComfyUI workflow execution.

    Args:
        request_id: Request ID returned from submit_comfyui_workflow
        base_url: API base URL (defaults to COMFYUI_URL env var or localhost:8188)
        api_endpoint: API endpoint path (default: /ai-dock/api/result)

    Returns:
        Result dictionary with status and outputs, None if error

    Example:
        result = check_comfyui_result(request_id)
        if result and result.get("status") == "completed":
            print("Workflow completed!")
    """
    session = get_comfyui_client(base_url)

    if base_url is None:
        base_url = os.getenv("COMFYUI_URL", "http://localhost:8188")
    base_url = base_url.rstrip("/")

    url = f"{base_url}{api_endpoint}/{request_id}"

    try:
        response = session.get(url)

        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            return None  # Request not found (may still be processing)
        print(f"⚠️  Unexpected status code: {response.status_code}")
        return None
    except Exception as e:
        print(f"⚠️  Error checking result: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    print("ComfyUI API Client Helper")
    print("=" * 60)
    print("\nThis module provides helper functions for ComfyUI API access.")
    print("\nExample usage:")
    print(
        """
    from utils.comfyui_api_client import get_comfyui_client, submit_comfyui_workflow

    # Local access (no token needed)
    session = get_comfyui_client("http://localhost:8188")

    # Remote access (requires COMFYUI_ACCESS_TOKEN env var)
    session = get_comfyui_client("https://comfyui.datacrew.space")

    # Submit workflow
    workflow = {"input": {"workflow_json": {...}}}
    request_id = submit_comfyui_workflow(workflow)
    """
    )
