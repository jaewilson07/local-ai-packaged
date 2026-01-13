#!/usr/bin/env python3
"""
Sample ComfyUI API Call
This script demonstrates how to generate an image using the ComfyUI API wrapper
"""

import json
import sys
import time

import requests

# Configuration
BASE_URL = "http://localhost:8188"
API_BASE = f"{BASE_URL}/ai-dock/api"
API_PAYLOAD = f"{API_BASE}/payload"
API_RESULT = f"{API_BASE}/result"

# Default credentials (from docker-compose.yaml)
# Set these in your .env file or modify here
WEB_USER = "user"
WEB_PASSWORD = "password"

# Create a session and authenticate to get cookie
session = requests.Session()


# First, authenticate to get session cookie
def authenticate_session():
    """Authenticate and get session cookie"""
    login_url = f"{BASE_URL}/login"
    try:
        # Get login page first to get any CSRF tokens if needed
        response = session.get(login_url, timeout=5)

        # Submit login credentials
        login_data = {"user": WEB_USER, "password": WEB_PASSWORD}
        response = session.post(login_url, data=login_data, timeout=5, allow_redirects=True)

        if response.status_code in [200, 302]:
            print("✅ Authenticated successfully")
            return True
        print(f"⚠️  Authentication returned status: {response.status_code}")
        return False
    except Exception as e:
        print(f"⚠️  Authentication error: {e}")
        # Try basic auth as fallback
        session.auth = (WEB_USER, WEB_PASSWORD)
        return True


# Authenticate
authenticate_session()


def create_sample_payload():
    """
    Create a sample payload for text-to-image generation
    This uses the RawWorkflow handler with a simple workflow
    """
    payload = {
        "input": {
            "request_id": "",  # Will be auto-generated if empty
            "modifier": "",  # Empty means RawWorkflow
            "modifications": {},
            "workflow_json": {
                "3": {
                    "inputs": {
                        "seed": 12345,
                        "steps": 20,
                        "cfg": 8,
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "denoise": 1,
                        "model": ["4", 0],
                        "positive": ["6", 0],
                        "negative": ["7", 0],
                        "latent_image": ["5", 0],
                    },
                    "class_type": "KSampler",
                },
                "4": {
                    "inputs": {"ckpt_name": "v1-5-pruned-emaonly.ckpt"},
                    "class_type": "CheckpointLoaderSimple",
                },
                "5": {
                    "inputs": {"width": 512, "height": 512, "batch_size": 1},
                    "class_type": "EmptyLatentImage",
                },
                "6": {
                    "inputs": {
                        "text": "a beautiful landscape with mountains and a lake, sunset, highly detailed",
                        "clip": ["4", 1],
                    },
                    "class_type": "CLIPTextEncode",
                },
                "7": {
                    "inputs": {"text": "blurry, low quality, distorted", "clip": ["4", 1]},
                    "class_type": "CLIPTextEncode",
                },
                "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
                "9": {
                    "inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]},
                    "class_type": "SaveImage",
                },
            },
            "s3": {
                "access_key_id": "",
                "secret_access_key": "",
                "endpoint_url": "",
                "bucket_name": "",
            },
            "webhook": {"url": "", "extra_params": {}},
        }
    }
    return payload


def submit_job(payload):
    """Submit a job to the API"""
    print("=" * 60)
    print("Submitting job to ComfyUI API...")
    print("=" * 60)

    try:
        response = session.post(
            API_PAYLOAD, json=payload, headers={"Content-Type": "application/json"}, timeout=30
        )

        if response.status_code == 202:
            result = response.json()
            request_id = result.get("id")
            print("✅ Job submitted successfully!")
            print(f"   Request ID: {request_id}")
            print(f"   Status: {result.get('status', 'pending')}")
            return request_id
        if response.status_code == 401:
            print("❌ Authentication failed!")
            print("   Please check your WEB_USER and WEB_PASSWORD credentials")
            print("   These should match your docker-compose.yaml or .env file")
            return None
        if response.status_code == 422:
            print("❌ Validation error - payload format is incorrect")
            print(f"   Response: {response.text}")
            return None
        print(f"❌ Failed to submit job (status: {response.status_code})")
        print(f"   Response: {response.text}")
        return None

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is the container running?")
        print(f"   URL: {API_PAYLOAD}")
        return None
    except Exception as e:
        print(f"❌ Error submitting job: {e}")
        return None


def check_result(request_id, max_wait=300):
    """Poll for job result"""
    print("\n" + "=" * 60)
    print(f"Checking job status (Request ID: {request_id})")
    print("=" * 60)

    start_time = time.time()
    check_interval = 2  # Check every 2 seconds

    while time.time() - start_time < max_wait:
        try:
            response = session.get(f"{API_RESULT}/{request_id}", timeout=10)

            if response.status_code == 200:
                result = response.json()
                status = result.get("status", "unknown")
                message = result.get("message", "")

                print(f"   Status: {status} - {message}")

                if status == "completed":
                    print("\n✅ Job completed successfully!")
                    if "outputs" in result:
                        print(f"   Outputs: {json.dumps(result['outputs'], indent=2)}")
                    return result
                if status == "failed":
                    print(f"\n❌ Job failed: {message}")
                    return result
                if status in ["pending", "processing"]:
                    # Continue polling
                    time.sleep(check_interval)
                    continue
                print(f"\n⚠️  Unknown status: {status}")
                time.sleep(check_interval)
                continue

            if response.status_code == 404:
                print("⚠️  Request ID not found. Job may still be processing...")
                time.sleep(check_interval)
                continue
            print(f"⚠️  Unexpected status code: {response.status_code}")
            time.sleep(check_interval)
            continue

        except Exception as e:
            print(f"⚠️  Error checking result: {e}")
            time.sleep(check_interval)
            continue

    print(f"\n⏱️  Timeout waiting for result (waited {max_wait} seconds)")
    return None


def main():
    print("\n" + "=" * 60)
    print("ComfyUI API Sample - Image Generation")
    print("=" * 60 + "\n")

    # Authenticate first
    print("Authenticating...")
    if not authenticate_session():
        print("⚠️  Authentication may have failed, but continuing...")

    # Create payload
    payload = create_sample_payload()

    print("\n📋 Payload structure:")
    print(json.dumps(payload, indent=2))

    # Submit job
    request_id = submit_job(payload)
    if not request_id:
        print("\n❌ Failed to submit job. Exiting.")
        sys.exit(1)

    # Wait for result
    result = check_result(request_id)

    if result and result.get("status") == "completed":
        print("\n" + "=" * 60)
        print("✅ Success! Image generation completed")
        print("=" * 60)
        print("\nThe generated image should be in the ComfyUI output directory:")
        print("   Container: /opt/ComfyUI/output/")
        print("   Host: ./workspace/storage/output/")
        print("\nTo check the result programmatically, use:")
        print(f"   GET {API_RESULT}/{request_id}")
        return 0
    print("\n❌ Job did not complete successfully")
    return 1


if __name__ == "__main__":
    sys.exit(main())
