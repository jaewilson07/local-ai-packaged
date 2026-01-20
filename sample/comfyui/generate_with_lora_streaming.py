#!/usr/bin/env python3
"""Sample script demonstrating streaming progress for LoRA image generation.

This script shows how to:
1. Submit an image generation request with LoRA
2. Stream progress updates via SSE (Server-Sent Events)
3. Watch images progressively appear in Immich

Prerequisites:
- Lambda server running (locally or via api.datacrew.space)
- ComfyUI service running with Z-Image-Turbo model
- A workflow template stored in the database with _metadata.parameter_overrides
- Authentication: LAMBDA_API_TOKEN or CF_ACCESS_JWT for external access

Usage:
    # Using public API (requires API token or Cloudflare JWT):
    python sample/comfyui/generate_with_lora_streaming.py

    # Using localhost (for local development):
    API_BASE_URL=http://localhost:8000 python sample/comfyui/generate_with_lora_streaming.py

    # With custom workflow ID:
    WORKFLOW_ID=<uuid> python sample/comfyui/generate_with_lora_streaming.py

    # Use a different LoRA:
    CHARACTER_LORA=my_lora.safetensors python sample/comfyui/generate_with_lora_streaming.py

Environment Variables:
    API_BASE_URL     - API endpoint (default: https://api.datacrew.space)
    LAMBDA_API_TOKEN - API token for authentication (preferred)
    CF_ACCESS_JWT    - Cloudflare Access JWT (alternative auth)
    WORKFLOW_ID      - Use a specific workflow UUID
    CHARACTER_LORA   - LoRA filename (default: alix_character_lora_zit.safetensors)
    PROMPT           - Custom prompt text
    BATCH_SIZE       - Number of images to generate (default: 5)
    USE_SSE          - Use SSE streaming (default: true)
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

# Add project root to path for sample.shared imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sample.shared.auth_helpers import (  # noqa: E402
    get_auth_headers,
    get_cloudflare_email,
)

# Default to public API endpoint
DEFAULT_API_URL = "https://api.datacrew.space"

# Path to the workflow template
WORKFLOW_TEMPLATE_PATH = Path(__file__).parent / "workflows" / "z_image_turbo_lora_template.json"


def get_api_base_url() -> str:
    """Get API base URL, defaulting to public endpoint."""
    return os.getenv("API_BASE_URL", DEFAULT_API_URL)


# Status emoji mapping for visual feedback
STATUS_EMOJI = {
    "pending": "⏳",
    "rewriting_prompt": "✍️",
    "submitting": "📤",
    "running": "🔄",
    "generating": "🎨",
    "uploading": "☁️",
    "completed": "✅",
    "failed": "❌",
}


def print_status_update(status_data: dict) -> None:
    """Print a formatted status update."""
    status = status_data.get("status", "unknown")
    emoji = STATUS_EMOJI.get(status, "❓")
    progress_message = status_data.get("progress_message", "")
    images_completed = status_data.get("images_completed", 0)
    images_total = status_data.get("images_total")

    # Build progress bar if we have image counts
    progress_bar = ""
    if images_total and images_total > 0:
        filled = int((images_completed / images_total) * 20)
        progress_bar = f" [{'█' * filled}{'░' * (20 - filled)}] {images_completed}/{images_total}"

    print(f"  {emoji} {status.upper()}: {progress_message}{progress_bar}")

    # Show optimized prompt if available
    if status_data.get("optimized_prompt") and status == "rewriting_prompt":
        prompt_preview = status_data["optimized_prompt"][:100] + "..."
        print(f"     Optimized: {prompt_preview}")

    # Show Immich assets as they appear
    immich_ids = status_data.get("immich_asset_ids", [])
    if immich_ids:
        print(f"     📸 Immich: {len(immich_ids)} image(s) uploaded")


def stream_generation_progress(
    api_base_url: str,
    headers: dict[str, str],
    run_id: str,
    timeout: float = 600.0,
) -> dict | None:
    """
    Stream generation progress via SSE.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers
        run_id: Workflow run UUID
        timeout: Maximum time to wait in seconds

    Returns:
        Final status data or None if error
    """
    url = f"{api_base_url}/api/v1/comfyui/runs/{run_id}/stream"

    print(f"\n📡 Streaming progress from: {url}")
    print("-" * 60)

    final_status = None

    try:
        # Use httpx for SSE support
        with httpx.Client(timeout=timeout) as client:
            with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line:
                        continue

                    # SSE format: "data: {json}"
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        try:
                            status_data = json.loads(data_str)
                            final_status = status_data

                            # Check for error
                            if "error" in status_data:
                                print(f"  ❌ Error: {status_data['error']}")
                                return None

                            print_status_update(status_data)

                            # Check for terminal state
                            if status_data.get("status") in ("completed", "failed"):
                                break

                        except json.JSONDecodeError:
                            print(f"  ⚠️ Invalid JSON: {data_str}")

    except httpx.ConnectError:
        print(f"  ❌ Connection Error: Cannot connect to {url}")
        print("     Make sure the Lambda server is running.")
        return None
    except httpx.HTTPStatusError as e:
        print(f"  ❌ HTTP Error: {e.response.status_code}")
        try:
            error_detail = e.response.json()
            print(f"     Detail: {error_detail}")
        except (ValueError, json.JSONDecodeError):
            print(f"     Response: {e.response.text}")
        return None

    print("-" * 60)
    return final_status


def poll_generation_progress(
    api_base_url: str,
    headers: dict[str, str],
    run_id: str,
    max_wait: float = 600.0,
    poll_interval: float = 2.0,
) -> dict | None:
    """
    Poll generation progress (fallback if SSE doesn't work).

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers
        run_id: Workflow run UUID
        max_wait: Maximum time to wait in seconds
        poll_interval: Seconds between polls

    Returns:
        Final status data or None if error
    """
    url = f"{api_base_url}/api/v1/comfyui/runs/{run_id}"

    print(f"\n📊 Polling progress from: {url}")
    print(f"   (Poll interval: {poll_interval}s, Max wait: {max_wait}s)")
    print("-" * 60)

    start_time = time.time()
    last_status = None

    while True:
        elapsed = time.time() - start_time

        if elapsed > max_wait:
            print(f"  ⏱️ Timeout after {max_wait}s")
            return None

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()

                status_data = response.json()
                current_status = (
                    status_data.get("status"),
                    status_data.get("progress_message"),
                    status_data.get("images_completed"),
                )

                # Only print if status changed
                if current_status != last_status:
                    last_status = current_status
                    print_status_update(status_data)

                # Check for terminal state
                if status_data.get("status") in ("completed", "failed"):
                    print("-" * 60)
                    return status_data

                time.sleep(poll_interval)

        except httpx.ConnectError:
            print(f"  ❌ Connection Error: Cannot connect to {url}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"  ❌ HTTP Error: {e.response.status_code}")
            return None


def submit_generation_request(
    api_base_url: str,
    headers: dict[str, str],
    workflow_id: str,
    prompt: str,
    character_lora: str,
    batch_size: int = 1,
    optimize_prompt: bool = True,
) -> dict | None:
    """
    Submit a LoRA image generation request.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers
        workflow_id: Workflow template UUID
        prompt: User prompt for image generation
        character_lora: LoRA filename for the character
        batch_size: Number of images to generate
        optimize_prompt: Whether to optimize prompt with AI

    Returns:
        Initial run data with run_id, or None if error
    """
    url = f"{api_base_url}/api/v1/comfyui/generate-with-lora"

    payload = {
        "workflow_id": workflow_id,
        "prompt": prompt,
        "character_lora": character_lora,
        "batch_size": batch_size,
        "optimize_prompt": optimize_prompt,
        "upload_to_immich": True,
    }

    print("🚀 Submitting generation request...")
    print(f"   URL: {url}")
    print(f"   Prompt: {prompt[:80]}...")
    print(f"   LoRA: {character_lora}")
    print(f"   Batch size: {batch_size}")
    print(f"   Optimize prompt: {optimize_prompt}")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                json=payload,
            )

            # Expect 202 Accepted
            if response.status_code == 202:
                result = response.json()
                run_id = result.get("id")
                status = result.get("status")
                print("\n   ✅ Request accepted!")
                print(f"   Run ID: {run_id}")
                print(f"   Initial status: {status}")
                return result

            # Handle other status codes
            response.raise_for_status()
            return response.json()

    except httpx.ConnectError:
        print(f"\n   ❌ Connection Error: Cannot connect to {url}")
        print("      Make sure the Lambda server is running.")
        return None
    except httpx.HTTPStatusError as e:
        print(f"\n   ❌ HTTP Error: {e.response.status_code}")
        try:
            error_detail = e.response.json()
            print(f"      Detail: {error_detail}")
        except (ValueError, json.JSONDecodeError):
            print(f"      Response: {e.response.text}")
        return None


def display_final_results(status_data: dict) -> None:
    """Display final generation results."""
    print("\n" + "=" * 60)
    print("🎉 GENERATION RESULTS")
    print("=" * 60)

    status = status_data.get("status")
    print(f"Status: {STATUS_EMOJI.get(status, '❓')} {status.upper()}")

    if status == "completed":
        # Show optimized prompt
        optimized_prompt = status_data.get("optimized_prompt")
        if optimized_prompt:
            print(f"\n📝 Optimized Prompt:\n   {optimized_prompt}")

        # Show output images
        output_images = status_data.get("output_images", [])
        if output_images:
            print(f"\n🖼️  Generated {len(output_images)} image(s):")
            for i, img in enumerate(output_images, 1):
                print(f"   {i}. {img}")

        # Show MinIO paths
        minio_paths = status_data.get("minio_paths", [])
        if minio_paths:
            print(f"\n💾 MinIO Storage ({len(minio_paths)} file(s)):")
            for i, path in enumerate(minio_paths, 1):
                print(f"   {i}. {path}")

        # Show Immich assets
        immich_ids = status_data.get("immich_asset_ids", [])
        if immich_ids:
            print(f"\n📸 Immich Assets ({len(immich_ids)} asset(s)):")
            for i, asset_id in enumerate(immich_ids, 1):
                print(f"   {i}. {asset_id}")
            print("\n   💡 Images should now be visible in your Immich library!")

    elif status == "failed":
        error_msg = status_data.get("error_message", "Unknown error")
        print(f"\n❌ Error: {error_msg}")

    # Metadata
    print("\n📋 Metadata:")
    print(f"   Run ID: {status_data.get('id')}")
    print(f"   Workflow ID: {status_data.get('workflow_id')}")
    print(f"   Started: {status_data.get('started_at')}")
    print(f"   Completed: {status_data.get('completed_at', 'N/A')}")

    print("=" * 60)


def load_workflow_template() -> dict[str, Any] | None:
    """Load the Z-Image-Turbo LoRA workflow template from file."""
    if not WORKFLOW_TEMPLATE_PATH.exists():
        print(f"   ❌ Workflow template not found: {WORKFLOW_TEMPLATE_PATH}")
        return None

    try:
        with open(WORKFLOW_TEMPLATE_PATH) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"   ❌ Invalid JSON in workflow template: {e}")
        return None


def create_workflow_from_template(
    api_base_url: str,
    headers: dict[str, str],
    workflow_json: dict[str, Any],
) -> str | None:
    """Create a new workflow from the template."""
    url = f"{api_base_url}/api/v1/comfyui/workflows"

    # Extract metadata
    metadata = workflow_json.get("_metadata", {})
    name = metadata.get("name", "Z-Image-Turbo LoRA Template")
    description = metadata.get("description", "Workflow for generate-with-lora API")

    payload = {
        "name": name,
        "description": description,
        "workflow_json": workflow_json,
        "is_public": False,
        "tags": ["z-image-turbo", "lora", "template"],
    }

    print(f"   📝 Creating workflow: {name}")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                headers={**headers, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            wf_id = result.get("id")
            print(f"   ✅ Workflow created: {wf_id}")
            return wf_id

    except httpx.HTTPStatusError as e:
        print(f"   ❌ HTTP Error: {e.response.status_code}")
        try:
            error_detail = e.response.json()
            print(f"      Detail: {error_detail}")
        except (ValueError, json.JSONDecodeError):
            print(f"      Response: {e.response.text}")
        return None


def get_or_create_workflow(
    api_base_url: str,
    headers: dict[str, str],
) -> str | None:
    """
    Get workflow ID from environment, find existing, or create from template.

    Returns:
        Workflow UUID string or None if not found/created
    """
    # Check for explicit workflow ID
    workflow_id = os.getenv("WORKFLOW_ID")
    if workflow_id:
        try:
            UUID(workflow_id)  # Validate it's a valid UUID
            print(f"\n📋 Using workflow from WORKFLOW_ID: {workflow_id}")
            return workflow_id
        except ValueError:
            print(f"⚠️ Invalid WORKFLOW_ID: {workflow_id}")

    # Try to find an existing Z-Image-Turbo LoRA workflow
    print("\n🔍 Looking for existing workflows...")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{api_base_url}/api/v1/comfyui/workflows",
                headers=headers,
                params={"per_page": 50},
            )
            response.raise_for_status()

            result = response.json()
            workflows = result.get("workflows", [])

            # Look for a workflow with the right parameter_overrides for generate-with-lora
            for wf in workflows:
                name = wf.get("name", "").lower()
                workflow_json = wf.get("workflow_json", {})
                metadata = workflow_json.get("_metadata", {})
                overrides = metadata.get("parameter_overrides", {})

                # Check if this workflow has the required overrides for generate-with-lora
                has_lora_overrides = (
                    "positive_prompt" in overrides
                    or "character_lora" in overrides
                    or ("z-image" in name and "lora" in name)
                )

                if has_lora_overrides:
                    wf_id = wf.get("id")
                    print(f"   ✅ Found compatible workflow: {wf.get('name')} (ID: {wf_id})")
                    return wf_id

            print("   ⚠️ No compatible workflow found with generate-with-lora overrides")

    except httpx.HTTPStatusError as e:
        print(f"   ❌ HTTP Error: {e.response.status_code}")
    except httpx.ConnectError:
        # If using internal Docker URL, suggest localhost
        if "lambda-server" in api_base_url:
            print(f"   ❌ Connection Error: Cannot connect to {api_base_url}")
            print("      You're running outside Docker. Try:")
            print("      API_BASE_URL=http://localhost:8000 python \\")
            print("        sample/comfyui/generate_with_lora_streaming.py")
        else:
            print(f"   ❌ Connection Error: Cannot connect to {api_base_url}")
            print("      Make sure the Lambda server is running.")
        return None

    # Create workflow from template
    print("\n📦 Creating workflow from template...")
    workflow_template = load_workflow_template()
    if not workflow_template:
        return None

    return create_workflow_from_template(api_base_url, headers, workflow_template)


def get_auth_method_description(headers: dict[str, str]) -> str:
    """Get a human-readable description of the auth method being used."""
    if "Authorization" in headers:
        return "API Token (Bearer)"
    elif "Cf-Access-Jwt-Assertion" in headers:
        return "Cloudflare Access JWT"
    elif "X-User-Email" in headers:
        return "Internal Network (X-User-Email)"
    return "None (may fail on external endpoints)"


def main():
    """Main function."""
    # Configuration
    api_base_url = get_api_base_url()

    try:
        headers = get_auth_headers()
    except ValueError as e:
        print("=" * 60)
        print("❌ Authentication Error")
        print("=" * 60)
        print(f"\n{e}")
        print("\nTo authenticate with the public API:")
        print("  1. Set LAMBDA_API_TOKEN in your .env file, or")
        print("  2. Set CF_ACCESS_JWT from browser cookies")
        print("\nFor local development:")
        print("  API_BASE_URL=http://localhost:8000 python \\")
        print("    sample/comfyui/generate_with_lora_streaming.py")
        sys.exit(1)

    cloudflare_email = get_cloudflare_email()
    auth_method = get_auth_method_description(headers)

    # Generation parameters (can be overridden via environment variables)
    prompt = os.getenv(
        "PROMPT",
        "generate 5 handheld selfies of Alix walking around the streets of barcelona "
        "in a short miniskirt. her suggestive smile is very flirty and intimate",
    )
    character_lora = os.getenv("CHARACTER_LORA", "alix_character_lora_zit.safetensors")
    batch_size = int(os.getenv("BATCH_SIZE", "5"))  # Generate 5 images by default

    # Header
    print("=" * 60)
    print("🎨 LoRA Image Generation with Streaming Progress")
    print("=" * 60)
    print(f"API Base URL: {api_base_url}")
    print(f"Auth Method: {auth_method}")
    if cloudflare_email:
        print(f"User Email: {cloudflare_email}")
    print(f"Character LoRA: {character_lora}")
    print(f"Batch Size: {batch_size}")
    print("=" * 60)

    # Step 1: Get or find a workflow
    workflow_id = get_or_create_workflow(api_base_url, headers)
    if not workflow_id:
        print("\n❌ No workflow available. Exiting.")
        sys.exit(1)

    print(f"\n📋 Using workflow: {workflow_id}")

    # Step 2: Submit generation request
    run_data = submit_generation_request(
        api_base_url=api_base_url,
        headers=headers,
        workflow_id=workflow_id,
        prompt=prompt,
        character_lora=character_lora,
        batch_size=batch_size,
        optimize_prompt=True,
    )

    if not run_data:
        print("\n❌ Failed to submit generation request. Exiting.")
        sys.exit(1)

    run_id = run_data.get("id")

    # Step 3: Stream progress
    print("\n" + "=" * 60)
    print("📡 STREAMING PROGRESS")
    print("=" * 60)

    # Try SSE streaming first, fall back to polling
    use_sse = os.getenv("USE_SSE", "true").lower() == "true"

    if use_sse:
        print("Using Server-Sent Events (SSE) for real-time updates...")
        final_status = stream_generation_progress(
            api_base_url=api_base_url,
            headers=headers,
            run_id=run_id,
            timeout=600.0,  # 10 minutes
        )

        # If SSE failed, fall back to polling
        if final_status is None:
            print("\n⚠️ SSE streaming failed, falling back to polling...")
            final_status = poll_generation_progress(
                api_base_url=api_base_url,
                headers=headers,
                run_id=run_id,
                max_wait=600.0,
                poll_interval=2.0,
            )
    else:
        print("Using polling for progress updates (set USE_SSE=true for SSE)...")
        final_status = poll_generation_progress(
            api_base_url=api_base_url,
            headers=headers,
            run_id=run_id,
            max_wait=600.0,
            poll_interval=2.0,
        )

    if not final_status:
        print("\n❌ Failed to get final status. Check Lambda server logs.")
        sys.exit(1)

    # Step 4: Display final results
    display_final_results(final_status)

    # Exit code based on status
    if final_status.get("status") == "completed":
        print("\n✅ Generation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Generation did not complete successfully.")
        sys.exit(1)


if __name__ == "__main__":
    main()
