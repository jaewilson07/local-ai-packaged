#!/usr/bin/env python3
"""Sample script to execute a ComfyUI workflow end-to-end.

This script demonstrates the complete workflow execution flow:
1. Create workflow in Supabase
2. Check if LoRA model exists
3. Execute workflow via API
4. Poll for completion
5. Display results

Prerequisites:
- Lambda server running and accessible
- ComfyUI service running
- CLOUDFLARE_EMAIL in .env (for user identification)
- For external API URLs: CF_ACCESS_JWT env var (optional, defaults to internal network)
"""

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

# The workflow JSON provided by the user
WORKFLOW_JSON = {
    "2": {
        "inputs": {
            "text": "worst quality, low quality, normal quality, lowres, blurry, distorted, grainy, plastic, waxy, 3D render, CGI, cartoon, doll-like, fake skin texture, oversaturated, flat lighting, unnatural shadows, artificial colors, bad anatomy, deformed, extra limbs, fused fingers, cloned face, asymmetrical, text, watermark, logo, signature, out of frame.",
            "clip": ["27", 1],
        },
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "CLIP Text Encode (Negative Prompt)"},
    },
    "3": {
        "inputs": {"strength": 0.4, "images": ["5", 0]},
        "class_type": "FastLaplacianSharpen",
        "_meta": {"title": "🌀 Fast Laplacian Sharpen"},
    },
    "5": {
        "inputs": {"samples": ["15", 0], "vae": ["9", 0]},
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode"},
    },
    "7": {
        "inputs": {"shift": 3, "model": ["25", 0]},
        "class_type": "ModelSamplingAuraFlow",
        "_meta": {"title": "ModelSamplingAuraFlow"},
    },
    "8": {
        "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2"},
        "class_type": "CLIPLoaderGGUF",
        "_meta": {"title": "CLIPLoader (GGUF)"},
    },
    "9": {
        "inputs": {"vae_name": "ae.safetensors"},
        "class_type": "VAELoader",
        "_meta": {"title": "Load VAE"},
    },
    "14": {
        "inputs": {
            "grain_intensity": 0.01,
            "saturation_mix": 0.3,
            "batch_size": 4,
            "images": ["3", 0],
        },
        "class_type": "FastFilmGrain",
        "_meta": {"title": "🎞️ Fast Film Grain"},
    },
    "15": {
        "inputs": {
            "seed": 434637170144726,
            "steps": 9,
            "cfg": 1,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1,
            "model": ["27", 0],
            "positive": ["16", 0],
            "negative": ["2", 0],
            "latent_image": ["24", 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler"},
    },
    "16": {
        "inputs": {
            "randomize_percent": 50,
            "strength": 20,
            "noise_insert": "noise on beginning steps",
            "steps_switchover_percent": 20,
            "seed": 835659019602924,
            "mask_starts_at": "beginning",
            "mask_percent": 0,
            "log_to_console": False,
            "conditioning": ["23", 0],
        },
        "class_type": "SeedVarianceEnhancer",
        "_meta": {"title": "SeedVarianceEnhancer"},
    },
    "21": {
        "inputs": {"filename_prefix": "ComfyUI", "images": ["14", 0]},
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image"},
    },
    "23": {
        "inputs": {
            "text": '"i wish you were here"\n\nStyle & Perspective: A candid, handheld smartphone selfie taken from a high angle by Alix, capturing a spontaneous, intimate moment. The frame is slightly tilted, showing her extended arm holding the phone.\n\nSubject & Expression: Alix is looking directly into the camera lens with a playful, mischievous "kissy face" smile and a wink, as if sending a private message to her boyfriend.\n\nAppearance & Details: She is wearing a casual ribbed white crop top and a dark pleated mini skirt. The bright afternoon sun catches her wind-blown hair, highlighting natural skin texture, visible pores, and a healthy glow.\n\nSetting & Background: The background is a bustling, sun-drenched street in Barcelona\'s Gothic Quarter, packed with blurred tourists, historic stone architecture, and a distant glimpse of a landmark like La Sagrada Familia.\n\nTechnical Quality: Shot on an iPhone front-facing camera. Natural daylight, slight wide-angle lens distortion, authentic film grain, sharp focus on her eyes and lips, shallow depth of field, unposed, real life texture, 4k resolution.',
            "clip": ["27", 1],
        },
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "prompt"},
    },
    "24": {
        "inputs": {"width": 512, "height": 768, "batch_size": 3},
        "class_type": "EmptySD3LatentImage",
        "_meta": {"title": "EmptySD3LatentImage"},
    },
    "25": {
        "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"},
        "class_type": "UNETLoader",
        "_meta": {"title": "Load Diffusion Model"},
    },
    "27": {
        "inputs": {
            "lora_name": "alix_character_lora_zit_merged_2000_3000.safetensors",
            "strength_model": 1,
            "strength_clip": 1,
            "model": ["7", 0],
            "clip": ["8", 0],
        },
        "class_type": "LoraLoader",
        "_meta": {"title": "Lora Loader"},
    },
    "28": {
        "inputs": {"filename_prefix": "raw", "images": ["5", 0]},
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image"},
    },
}


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
        headers: Authentication headers (from get_auth_headers())
        workflow_json: ComfyUI workflow JSON
        name: Workflow name
        description: Optional workflow description

    Returns:
        Workflow data or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/workflows"

    # Add Content-Type to headers
    headers = {**headers, "Content-Type": "application/json"}

    payload = {
        "name": name,
        "workflow_json": workflow_json,
        "is_public": False,
        "tags": ["sample", "alix-character"],
    }

    if description:
        payload["description"] = description

    print(f"Creating workflow: {name}")
    print(f"  URL: {url}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        print("  ✅ Workflow created!")
        print(f"     ID: {result.get('id')}")
        print(f"     Name: {result.get('name')}")

        return result

    except requests.exceptions.HTTPError as e:
        print(f"  ✗ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"     Detail: {error_detail}")
            except (ValueError, json.JSONDecodeError):
                print(f"     Response: {e.response.text}")
        return None


def check_lora_exists(api_base_url: str, headers: dict[str, str], lora_filename: str) -> bool:
    """
    Check if a LoRA model exists for the user.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers (from get_auth_headers())
        lora_filename: LoRA filename to check

    Returns:
        True if LoRA exists, False otherwise
    """
    url = f"{api_base_url}/api/v1/comfyui/loras"

    print(f"Checking for LoRA: {lora_filename}")

    try:
        response = requests.get(url, headers=headers, params={"limit": 1000})
        response.raise_for_status()

        result = response.json()
        models = result.get("models", [])

        # Check if any model matches the filename
        for model in models:
            if model.get("filename") == lora_filename:
                print(f"  ✅ LoRA found: {model.get('name')} (ID: {model.get('id')})")
                return True

        print(f"  ⚠️  LoRA not found: {lora_filename}")
        return False

    except requests.exceptions.ConnectionError:
        print(f"  ✗ Connection Error: Cannot connect to {url}")
        print("    Make sure the Lambda server is running.")
        return None

    except requests.exceptions.HTTPError as e:
        print(f"  ✗ HTTP Error: {e}")
        return False


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
        headers: Authentication headers (from get_auth_headers())
        workflow_id: Workflow UUID
        input_params: Optional input parameters to override workflow values

    Returns:
        Workflow run data or None if failed
    """
    url = f"{api_base_url}/api/v1/comfyui/workflows/{workflow_id}/run"

    # Add Content-Type to headers
    headers = {**headers, "Content-Type": "application/json"}

    payload = {}
    if input_params:
        payload["input_params"] = input_params

    print(f"Executing workflow: {workflow_id}")
    print(f"  URL: {url}")

    try:
        response = requests.post(url, headers=headers, json=payload if payload else None)
        response.raise_for_status()

        result = response.json()
        run_id = result.get("id")
        comfyui_request_id = result.get("comfyui_request_id")
        status = result.get("status")

        print("  ✅ Workflow execution started!")
        print(f"     Run ID: {run_id}")
        print(f"     ComfyUI Request ID: {comfyui_request_id}")
        print(f"     Status: {status}")

        return result

    except requests.exceptions.HTTPError as e:
        print(f"  ✗ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"     Detail: {error_detail}")
            except (ValueError, json.JSONDecodeError):
                print(f"     Response: {e.response.text}")
        return None


def poll_workflow_status(
    api_base_url: str,
    headers: dict[str, str],
    run_id: str,
    max_wait: int = 300,
    poll_interval: int = 5,
) -> dict[str, Any] | None:
    """
    Poll workflow status until completion or timeout.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers (from get_auth_headers())
        run_id: Workflow run UUID
        max_wait: Maximum time to wait in seconds (default: 300 = 5 minutes)
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
    print()

    while True:
        elapsed = time.time() - start_time

        if elapsed > max_wait:
            print(f"  ⏱️  Timeout after {max_wait}s")
            return None

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            result = response.json()
            status = result.get("status")

            # Only print status if it changed
            if status != last_status:
                print(f"  Status: {status} (elapsed: {int(elapsed)}s)")
                last_status = status

            # Check if completed
            if status == "completed":
                print("  ✅ Workflow completed!")
                return result
            if status == "failed":
                error_msg = result.get("error_message", "Unknown error")
                print(f"  ✗ Workflow failed: {error_msg}")
                return result
            if status in ("pending", "running"):
                # Still processing, wait and poll again
                time.sleep(poll_interval)
            else:
                print(f"  ⚠️  Unknown status: {status}")
                time.sleep(poll_interval)

        except requests.exceptions.HTTPError as e:
            print(f"  ✗ HTTP Error: {e}")
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"     Detail: {error_detail}")
                except (ValueError, json.JSONDecodeError):
                    print(f"     Response: {e.response.text}")
            return None
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return None


def display_results(run_data: dict[str, Any]):
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
                print(f"  {i}. {image_url}")
        else:
            print("\nNo output images found")

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

    input_params = run_data.get("input_params")
    if input_params:
        print(f"  Input Params: {json.dumps(input_params, indent=2)}")

    print("=" * 60)


def extract_lora_from_workflow(workflow_json: dict[str, Any]) -> str | None:
    """
    Extract LoRA filename from workflow JSON.

    Args:
        workflow_json: ComfyUI workflow JSON

    Returns:
        LoRA filename if found, None otherwise
    """
    for _node_id, node_data in workflow_json.items():
        if isinstance(node_data, dict):
            class_type = node_data.get("class_type")
            if class_type == "LoraLoader":
                inputs = node_data.get("inputs", {})
                lora_name = inputs.get("lora_name")
                if lora_name:
                    return lora_name
    return None


def verify_in_me_data(
    api_base_url: str,
    headers: dict[str, str],
    workflow_id: str | None = None,
    run_id: str | None = None,
) -> bool:
    """
    Verify that workflows and runs appear in /api/me/data.

    Args:
        api_base_url: Base URL of the API
        headers: Authentication headers (from get_auth_headers())
        workflow_id: Optional workflow ID to verify
        run_id: Optional run ID to verify

    Returns:
        True if data found in /api/me/data, False otherwise
    """
    url = f"{api_base_url}/api/me/data"

    print("\nVerifying data appears in /api/me/data...")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        result = response.json()
        rag_summary = result.get("rag", {})

        workflows_count = rag_summary.get("supabase_workflows", 0)
        runs_count = rag_summary.get("supabase_workflow_runs", 0)

        print(f"  Total workflows: {workflows_count}")
        print(f"  Total workflow runs: {runs_count}")

        if (workflow_id and workflows_count > 0) or workflows_count > 0:
            print("  ✅ Workflows found in /api/me/data")

        if (run_id and runs_count > 0) or runs_count > 0:
            print("  ✅ Workflow runs found in /api/me/data")

        return workflows_count > 0 or runs_count > 0

    except requests.exceptions.HTTPError as e:
        print(f"  ✗ HTTP Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"     Detail: {error_detail}")
            except (ValueError, json.JSONDecodeError):
                print(f"     Response: {e.response.text}")
        return False


def main():
    """Main function."""
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
        print("  (or http://localhost:8000 if running outside Docker)")
        return

    cloudflare_email = get_cloudflare_email()

    # Workflow configuration
    workflow_name = "Alix Character Image Generation"
    workflow_description = "Sample workflow for generating images with Alix character LoRA"

    print("=" * 60)
    print("ComfyUI Workflow Execution Sample")
    print("=" * 60)
    print(f"API Base URL: {api_base_url}")
    if cloudflare_email:
        print(f"User Email: {cloudflare_email}")
    if headers:
        print("Authentication: Using Cloudflare Access JWT")
    else:
        print("Authentication: Internal network (no auth required)")
    print(f"Workflow Name: {workflow_name}")
    print("=" * 60)
    print()

    # Step 1: Extract LoRA from workflow
    lora_filename = extract_lora_from_workflow(WORKFLOW_JSON)
    if lora_filename:
        print(f"📋 Workflow uses LoRA: {lora_filename}")
        print()

        # Step 2: Check if LoRA exists
        lora_exists = check_lora_exists(api_base_url, headers, lora_filename)
        print()

        if lora_exists is None:
            # Connection error
            print("❌ Cannot connect to server. Make sure Lambda server is running.")
            print("\n⚠️  Sample requires running services - exiting gracefully")
            sys.exit(0)

        if not lora_exists:
            print("⚠️  WARNING: LoRA model not found!")
            print(f"   The workflow requires: {lora_filename}")
            print("\n   To import the LoRA:")
            print("   1. If it's in Google Drive, use:")
            print("      python sample/comfyui/import_lora_from_google_drive.py")
            print("   2. Or use the API:")
            print("      python sample/comfyui/import_lora_via_api.py")
            print("   3. Or upload via API:")
            print("      POST /api/v1/comfyui/loras (multipart/form-data)")
            print("\n   The workflow will still execute, but may fail if ComfyUI")
            print("   cannot find the LoRA model.")
            print()
            # Non-interactive mode - skip if stdin is not a TTY
            if sys.stdin.isatty():
                response = input("Continue anyway? (y/n): ")
                if response.lower() != "y":
                    print("Aborted.")
                    return
            else:
                print("⚠️  Running non-interactively - continuing anyway")
            print()
    else:
        print("📋 No LoRA models found in workflow")
        print()

    # Step 3: Create workflow
    workflow = create_workflow(
        api_base_url=api_base_url,
        headers=headers,
        workflow_json=WORKFLOW_JSON,
        name=workflow_name,
        description=workflow_description,
    )

    if not workflow:
        print("\n❌ Failed to create workflow. Aborting.")
        sys.exit(1)

    workflow_id = workflow.get("id")
    print()

    # Step 4: Execute workflow
    run_data = execute_workflow(api_base_url=api_base_url, headers=headers, workflow_id=workflow_id)

    if not run_data:
        print("\n❌ Failed to execute workflow. Aborting.")
        sys.exit(1)

    run_id = run_data.get("id")
    print()

    # Step 5: Poll for completion
    final_run_data = poll_workflow_status(
        api_base_url=api_base_url,
        headers=headers,
        run_id=run_id,
        max_wait=600,  # 10 minutes for image generation
        poll_interval=5,
    )

    if not final_run_data:
        print("\n❌ Failed to get workflow status or timeout exceeded.")
        sys.exit(1)

    # Step 6: Display results
    display_results(final_run_data)

    # Step 7: Verify in /api/me/data
    workflow_id = final_run_data.get("workflow_id")
    run_id = final_run_data.get("id")

    from sample.shared.verification_helpers import verify_rag_data

    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    success, message = verify_rag_data(
        api_base_url=api_base_url,
        headers=headers,
        expected_workflows_min=1 if workflow_id else 0,
    )

    print(message)

    if success:
        print("\n✅ Sample execution and verification completed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n⚠️  Sample execution completed but verification failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
