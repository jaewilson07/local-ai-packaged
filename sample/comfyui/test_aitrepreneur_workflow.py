#!/usr/bin/env python3
"""Test script for the aitrepreneur Z-Image-Turbo workflow.

This script demonstrates the complete workflow execution flow:
1. Load workflow from JSON file
2. Create workflow in Supabase via API
3. Execute workflow with custom prompt
4. Poll for completion
5. Verify images in MinIO
6. Verify images appear in user images API
7. Optionally verify in Immich

Prerequisites:
- Lambda server running and accessible
- ComfyUI service running with required models
- Required models downloaded:
  - z_image_turbo-Q8_0.gguf (UNET)
  - Qwen3-4B-Q6_K.gguf (CLIP) - from official Qwen/Qwen3-4B-GGUF repo
  - ae.safetensors (VAE)
- CLOUDFLARE_EMAIL in .env (for user identification)

Usage:
    python sample/comfyui/test_aitrepreneur_workflow.py
    python sample/comfyui/test_aitrepreneur_workflow.py --prompt "your custom prompt"
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Add project root to path for sample.shared imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sample.shared.auth_helpers import (  # noqa: E402
    get_api_base_url,
    get_auth_headers,
    get_cloudflare_email,
)


def load_workflow(workflow_path: Path) -> dict[str, Any]:
    """
    Load workflow JSON from file.

    Args:
        workflow_path: Path to workflow JSON file

    Returns:
        Workflow JSON dict
    """
    print(f"Loading workflow from: {workflow_path}")
    with open(workflow_path) as f:
        workflow = json.load(f)

    # Extract metadata if present
    metadata = workflow.get("_metadata", {})
    if metadata:
        print(f"  Name: {metadata.get('name', 'Unknown')}")
        print(f"  Description: {metadata.get('description', 'No description')}")
        print("  Required models:")
        for model_type, model_name in metadata.get("required_models", {}).items():
            print(f"    - {model_type}: {model_name}")

    return workflow


def create_workflow(
    api_base_url: str,
    headers: dict[str, str],
    workflow_json: dict[str, Any],
    name: str,
    description: str | None = None,
) -> dict[str, Any] | None:
    """
    Create a workflow in Supabase via API.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers
        workflow_json: ComfyUI workflow JSON
        name: Workflow name
        description: Optional workflow description

    Returns:
        Workflow data or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/workflows"
    headers = {**headers, "Content-Type": "application/json"}

    payload = {
        "name": name,
        "workflow_json": workflow_json,
        "is_public": False,
        "tags": ["sample", "z-image-turbo", "aitrepreneur"],
    }

    if description:
        payload["description"] = description

    print(f"\nCreating workflow: {name}")
    print(f"  URL: {url}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        print("  Workflow created!")
        print(f"     ID: {result.get('id')}")
        print(f"     Name: {result.get('name')}")

        return result

    except requests.exceptions.HTTPError as e:
        print(f"  HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"     Detail: {error_detail}")
            except (ValueError, json.JSONDecodeError):
                print(f"     Response: {e.response.text[:500]}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"  Cannot connect to {url}")
        print("    Make sure the Lambda server is running.")
        return None


def execute_workflow(
    api_base_url: str,
    headers: dict[str, str],
    workflow_id: str,
    input_params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Execute a workflow via API.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers
        workflow_id: Workflow UUID
        input_params: Optional input parameters to override workflow values

    Returns:
        Workflow run data or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/workflows/{workflow_id}/run"
    headers = {**headers, "Content-Type": "application/json"}

    payload = {}
    if input_params:
        payload["input_params"] = input_params

    print(f"\nExecuting workflow: {workflow_id}")
    if input_params:
        print(f"  Input params: {input_params}")

    try:
        response = requests.post(
            url, headers=headers, json=payload if payload else None, timeout=60
        )
        response.raise_for_status()

        result = response.json()
        print("  Workflow execution started!")
        print(f"     Run ID: {result.get('id')}")
        print(f"     Status: {result.get('status')}")
        print(f"     ComfyUI Request ID: {result.get('comfyui_request_id')}")

        return result

    except requests.exceptions.HTTPError as e:
        print(f"  HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"     Detail: {error_detail}")
            except (ValueError, json.JSONDecodeError):
                print(f"     Response: {e.response.text[:500]}")
        return None


def poll_workflow_status(
    api_base_url: str,
    headers: dict[str, str],
    run_id: str,
    max_wait: int = 600,
    poll_interval: int = 5,
) -> dict[str, Any] | None:
    """
    Poll workflow status until completion or timeout.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers
        run_id: Workflow run UUID
        max_wait: Maximum time to wait in seconds (default: 600 = 10 minutes)
        poll_interval: Seconds between polls (default: 5)

    Returns:
        Final workflow run data or None if error/timeout
    """
    url = f"{api_base_url}/api/v1/comfyui/runs/{run_id}"

    start_time = time.time()
    last_status = None

    print("\nPolling workflow status...")
    print(f"  Run ID: {run_id}")
    print(f"  Max wait: {max_wait}s, Poll interval: {poll_interval}s")

    while True:
        elapsed = time.time() - start_time

        if elapsed > max_wait:
            print(f"  Timeout after {max_wait}s")
            return None

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            status = result.get("status")

            # Only print status if it changed
            if status != last_status:
                print(f"  Status: {status} (elapsed: {int(elapsed)}s)")
                last_status = status

            # Check if completed
            if status == "completed":
                print("  Workflow completed!")
                return result
            if status == "failed":
                error_msg = result.get("error_message", "Unknown error")
                print(f"  Workflow failed: {error_msg}")
                return result
            if status in ("pending", "running"):
                # Still processing, wait and poll again
                time.sleep(poll_interval)
            else:
                print(f"  Unknown status: {status}")
                time.sleep(poll_interval)

        except requests.exceptions.HTTPError as e:
            print(f"  HTTP Error: {e}")
            return None
        except Exception as e:
            print(f"  Error: {e}")
            return None


def verify_minio_images(
    api_base_url: str,
    headers: dict[str, str],
) -> bool:
    """
    Verify images exist in MinIO via images API.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers

    Returns:
        True if images found, False otherwise
    """
    url = f"{api_base_url}/api/v1/images/comfyui"

    print("\nVerifying images in MinIO...")

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        result = response.json()
        images = result.get("images", [])
        total = result.get("total", 0)

        if total > 0:
            print(f"  Found {total} ComfyUI images in MinIO")
            for img in images[:5]:  # Show first 5
                print(f"    - {img.get('filename')}")
            if total > 5:
                print(f"    ... and {total - 5} more")
            return True
        print("  No ComfyUI images found in MinIO")
        return False

    except requests.exceptions.HTTPError as e:
        print(f"  HTTP Error: {e}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def verify_immich_images(
    api_base_url: str,
    headers: dict[str, str],
) -> bool:
    """
    Verify images exist in Immich via images API.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers

    Returns:
        True if images found, False otherwise
    """
    url = f"{api_base_url}/api/v1/images/immich"

    print("\nVerifying images in Immich...")

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 404:
            print("  Immich not configured for this user")
            return False

        response.raise_for_status()

        result = response.json()
        images = result.get("images", [])
        total = result.get("total", 0)

        if total > 0:
            print(f"  Found {total} images in Immich")
            for img in images[:5]:  # Show first 5
                print(f"    - {img.get('filename')}")
            if total > 5:
                print(f"    ... and {total - 5} more")
            return True
        print("  No images found in Immich")
        return False

    except requests.exceptions.HTTPError as e:
        print(f"  HTTP Error: {e}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def display_results(run_data: dict[str, Any]) -> None:
    """
    Display workflow execution results.

    Args:
        run_data: Workflow run data from API
    """
    print("\n" + "=" * 60)
    print("WORKFLOW EXECUTION RESULTS")
    print("=" * 60)

    status = run_data.get("status")
    print(f"Status: {status}")

    if status == "completed":
        output_images = run_data.get("output_images", [])
        if output_images:
            print(f"\nGenerated {len(output_images)} image(s):")
            for i, image_url in enumerate(output_images, 1):
                # Truncate long URLs
                display_url = image_url[:80] + "..." if len(image_url) > 80 else image_url
                print(f"  {i}. {display_url}")
        else:
            print("\n  No output images found")

        # Display MinIO storage paths
        minio_paths = run_data.get("minio_paths", [])
        if minio_paths:
            print(f"\nMinIO Storage ({len(minio_paths)} file(s)):")
            for i, path in enumerate(minio_paths, 1):
                print(f"  {i}. {path}")
        else:
            print("\nMinIO Storage: Not uploaded (check Lambda server logs)")

        # Display Immich asset IDs
        immich_asset_ids = run_data.get("immich_asset_ids", [])
        if immich_asset_ids:
            print(f"\nImmich Assets ({len(immich_asset_ids)} asset(s)):")
            for i, asset_id in enumerate(immich_asset_ids, 1):
                print(f"  {i}. {asset_id}")
        else:
            print("\nImmich Assets: Not uploaded (Immich may not be configured)")

    elif status == "failed":
        error_message = run_data.get("error_message")
        if error_message:
            print(f"\nError: {error_message}")
        else:
            print("\nWorkflow failed (no error message)")

    # Display metadata
    print("\nMetadata:")
    print(f"  Run ID: {run_data.get('id')}")
    print(f"  Workflow ID: {run_data.get('workflow_id')}")
    print(f"  ComfyUI Request ID: {run_data.get('comfyui_request_id')}")
    print(f"  Started: {run_data.get('started_at')}")
    print(f"  Completed: {run_data.get('completed_at', 'N/A')}")

    print("=" * 60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test the aitrepreneur Z-Image-Turbo workflow")
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Custom prompt to use (overrides workflow default)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Custom seed to use (overrides workflow default)",
    )
    parser.add_argument(
        "--workflow",
        type=str,
        default=None,
        help="Path to workflow JSON file (default: workflows/aitrepreneur_z_image_turbo.json)",
    )
    parser.add_argument(
        "--skip-immich",
        action="store_true",
        help="Skip Immich verification",
    )
    args = parser.parse_args()

    # Configuration
    try:
        api_base_url = get_api_base_url()
        headers = get_auth_headers()
    except ValueError as e:
        print("=" * 60)
        print("Authentication Error")
        print("=" * 60)
        print(f"\n{e}")
        print("\nTip: For local development, use internal network URL:")
        print("  export API_BASE_URL=http://lambda-server:8000")
        return 1

    cloudflare_email = get_cloudflare_email()

    # Determine workflow path
    if args.workflow:
        workflow_path = Path(args.workflow)
    else:
        workflow_path = Path(__file__).parent / "workflows" / "aitrepreneur_z_image_turbo.json"

    if not workflow_path.exists():
        print(f"Error: Workflow file not found: {workflow_path}")
        return 1

    # Print configuration
    print("=" * 60)
    print("Z-Image-Turbo Workflow Test")
    print("=" * 60)
    print(f"API Base URL: {api_base_url}")
    if cloudflare_email:
        print(f"User Email: {cloudflare_email}")
    if headers:
        print("Authentication: Using Cloudflare Access JWT")
    else:
        print("Authentication: Internal network (no auth required)")
    print(f"Workflow: {workflow_path}")
    if args.prompt:
        print(f"Custom Prompt: {args.prompt[:50]}...")
    if args.seed:
        print(f"Custom Seed: {args.seed}")
    print("=" * 60)

    # Step 1: Load workflow
    print("\n[Step 1/6] Loading workflow...")
    workflow_json = load_workflow(workflow_path)

    # Step 2: Create workflow via API
    print("\n[Step 2/6] Creating workflow in database...")
    metadata = workflow_json.get("_metadata", {})
    workflow = create_workflow(
        api_base_url=api_base_url,
        headers=headers,
        workflow_json=workflow_json,
        name=metadata.get("name", "Z-Image-Turbo Test"),
        description=metadata.get("description", "Test workflow execution"),
    )

    if not workflow:
        print("\nFailed to create workflow. Aborting.")
        return 1

    workflow_id = workflow.get("id")

    # Step 3: Execute workflow with optional custom prompt
    print("\n[Step 3/6] Executing workflow...")
    input_params = {}
    if args.prompt:
        input_params["prompt"] = args.prompt
    if args.seed:
        input_params["seed"] = args.seed

    run_data = execute_workflow(
        api_base_url=api_base_url,
        headers=headers,
        workflow_id=workflow_id,
        input_params=input_params if input_params else None,
    )

    if not run_data:
        print("\nFailed to execute workflow. Aborting.")
        return 1

    run_id = run_data.get("id")

    # Step 4: Poll for completion
    print("\n[Step 4/6] Waiting for completion...")
    final_run_data = poll_workflow_status(
        api_base_url=api_base_url,
        headers=headers,
        run_id=run_id,
        max_wait=600,  # 10 minutes for image generation
        poll_interval=5,
    )

    if not final_run_data:
        print("\nFailed to get workflow status or timeout exceeded.")
        return 1

    # Display results
    display_results(final_run_data)

    # Step 5: Verify images in MinIO
    print("\n[Step 5/6] Verifying images in MinIO...")
    minio_paths = final_run_data.get("minio_paths", [])
    if minio_paths:
        print(f"  SUCCESS: {len(minio_paths)} image(s) uploaded to MinIO")
        for path in minio_paths[:3]:  # Show first 3
            print(f"    - {path}")
        if len(minio_paths) > 3:
            print(f"    ... and {len(minio_paths) - 3} more")
        minio_verified = True
    else:
        print("  WARNING: No MinIO paths in run data (images may not have been uploaded)")
        # Fall back to API verification
        minio_verified = verify_minio_images(api_base_url, headers)

    # Step 6: Verify images in Immich (optional)
    immich_verified = False
    immich_asset_ids = final_run_data.get("immich_asset_ids", [])
    if not args.skip_immich:
        print("\n[Step 6/6] Verifying images in Immich...")
        if immich_asset_ids:
            print(f"  SUCCESS: {len(immich_asset_ids)} image(s) uploaded to Immich")
            for asset_id in immich_asset_ids[:3]:  # Show first 3
                print(f"    - {asset_id}")
            if len(immich_asset_ids) > 3:
                print(f"    ... and {len(immich_asset_ids) - 3} more")
            immich_verified = True
        else:
            print("  INFO: No Immich asset IDs (Immich may not be configured)")
            # Fall back to API verification
            immich_verified = verify_immich_images(api_base_url, headers)
    else:
        print("\n[Step 6/6] Skipping Immich verification...")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    status = final_run_data.get("status")
    output_images = final_run_data.get("output_images", [])

    print(f"Workflow Execution: {'PASSED' if status == 'completed' else 'FAILED'}")
    print(
        f"MinIO Storage: {'PASSED' if minio_verified else 'NOT VERIFIED'} ({len(minio_paths)} files)"
    )

    immich_status = (
        "SKIPPED" if args.skip_immich else ("PASSED" if immich_verified else "NOT CONFIGURED")
    )
    print(f"Immich Upload: {immich_status} ({len(immich_asset_ids)} assets)")

    print(f"\nGenerated Images: {len(output_images)}")

    if status == "completed" and minio_verified:
        print("\nTest completed successfully!")
        return 0
    print("\nTest completed with issues.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
