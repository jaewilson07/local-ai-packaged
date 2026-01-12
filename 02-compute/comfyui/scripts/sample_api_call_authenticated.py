#!/usr/bin/env python3
"""
Sample ComfyUI API Call with Proper Authentication
This script uses Bearer token or Basic auth to access the API through Caddy
"""

import base64
import json
import subprocess
import sys
import time

import requests

# Configuration
BASE_URL = "http://localhost:8188"
API_BASE = f"{BASE_URL}/ai-dock/api"
API_PAYLOAD = f"{API_BASE}/payload"
API_RESULT = f"{API_BASE}/result"

# Default credentials (from docker-compose.yaml)
WEB_USER = "user"
WEB_PASSWORD = "password"


def get_auth_token():
    """Try to get WEB_TOKEN from container, or generate from password"""
    try:
        # Try to get WEB_TOKEN from container environment
        result = subprocess.run(
            ["docker", "exec", "comfyui-supervisor-1", "env"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in result.stdout.split("\n"):
            if line.startswith("WEB_TOKEN="):
                return line.split("=", 1)[1]
    except (subprocess.SubprocessError, OSError, IndexError):
        pass

    # Fallback: generate base64 encoded password (used as token)
    return base64.b64encode(WEB_PASSWORD.encode()).decode()


def create_sample_payload():
    """Create a sample payload for text-to-image generation"""
    payload = {
        "input": {
            "request_id": "",
            "modifier": "",
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


def submit_job_with_auth(payload, auth_token):
    """Submit a job to the API using Bearer token authentication"""
    print("=" * 60)
    print("Submitting job to ComfyUI API with Bearer token...")
    print("=" * 60)

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {auth_token}"}

    try:
        response = requests.post(API_PAYLOAD, json=payload, headers=headers, timeout=30)

        if response.status_code == 202:
            result = response.json()
            request_id = result.get("id")
            print("✅ Job submitted successfully!")
            print(f"   Request ID: {request_id}")
            print(f"   Status: {result.get('status', 'pending')}")
            return request_id
        elif response.status_code == 401:
            print("❌ Authentication failed!")
            print("   Trying with Basic auth instead...")
            # Try Basic auth as fallback
            return submit_job_with_basic_auth(payload)
        elif response.status_code == 422:
            print("❌ Validation error - payload format is incorrect")
            print(f"   Response: {response.text[:200]}")
            return None
        else:
            print(f"❌ Failed to submit job (status: {response.status_code})")
            print(f"   Response: {response.text[:200]}")
            return None

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is the container running?")
        print(f"   URL: {API_PAYLOAD}")
        return None
    except Exception as e:
        print(f"❌ Error submitting job: {e}")
        return None


def submit_job_with_basic_auth(payload):
    """Submit a job using Basic authentication"""
    print("\nTrying Basic authentication...")

    # Encode credentials for Basic auth
    credentials = base64.b64encode(f"{WEB_USER}:{WEB_PASSWORD}".encode()).decode()

    headers = {"Content-Type": "application/json", "Authorization": f"Basic {credentials}"}

    try:
        response = requests.post(API_PAYLOAD, json=payload, headers=headers, timeout=30)

        if response.status_code == 202:
            result = response.json()
            request_id = result.get("id")
            print("✅ Job submitted successfully with Basic auth!")
            print(f"   Request ID: {request_id}")
            return request_id
        else:
            print(f"❌ Basic auth also failed (status: {response.status_code})")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Error with Basic auth: {e}")
        return None


def check_result(request_id, auth_token, max_wait=300):
    """Poll for job result using authentication"""
    print("\n" + "=" * 60)
    print(f"Checking job status (Request ID: {request_id})")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {auth_token}"}

    start_time = time.time()
    check_interval = 2

    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{API_RESULT}/{request_id}", headers=headers, timeout=10)

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
                elif status == "failed":
                    print(f"\n❌ Job failed: {message}")
                    return result
                elif status in ["pending", "processing"]:
                    time.sleep(check_interval)
                    continue
                else:
                    print(f"\n⚠️  Unknown status: {status}")
                    time.sleep(check_interval)
                    continue

            elif response.status_code == 404:
                print("⚠️  Request ID not found. Job may still be processing...")
                time.sleep(check_interval)
                continue
            else:
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
    print("ComfyUI API Sample - With Proper Authentication")
    print("=" * 60 + "\n")

    # Get auth token
    print("Getting authentication token...")
    auth_token = get_auth_token()
    print(f"✅ Using auth token: {auth_token[:20]}...")

    # Create payload
    payload = create_sample_payload()

    # Submit job
    request_id = submit_job_with_auth(payload, auth_token)
    if not request_id:
        print("\n❌ Failed to submit job. Exiting.")
        sys.exit(1)

    # Wait for result
    result = check_result(request_id, auth_token)

    if result and result.get("status") == "completed":
        print("\n" + "=" * 60)
        print("✅ Success! Image generation completed")
        print("=" * 60)
        print("\nThe generated image should be in the ComfyUI output directory:")
        print("   Container: /opt/ComfyUI/output/")
        print("   Host: ./workspace/storage/output/")
        return 0
    else:
        print("\n❌ Job did not complete successfully")
        return 1


if __name__ == "__main__":
    sys.exit(main())
