#!/usr/bin/env python3
"""
Sample ComfyUI API Call - Direct Container Access
This script runs the API call from inside the container to bypass Caddy authentication
"""

import json
import subprocess
import sys

# Payload
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
        "s3": {"access_key_id": "", "secret_access_key": "", "endpoint_url": "", "bucket_name": ""},
        "webhook": {"url": "", "extra_params": {}},
    }
}

print("=" * 60)
print("ComfyUI API Sample - Direct Container Access")
print("=" * 60)
print("\nSubmitting job via container...")

# Run curl inside the container
cmd = [
    "docker",
    "exec",
    "comfyui-supervisor-1",
    "curl",
    "-s",
    "-X",
    "POST",
    "http://127.0.0.1:38188/payload",
    "-H",
    "Content-Type: application/json",
    "-d",
    json.dumps(payload),
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)

    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            request_id = response.get("id")
            status = response.get("status")

            print("✅ Job submitted successfully!")
            print(f"   Request ID: {request_id}")
            print(f"   Status: {status}")
            print("\n📋 Full response:")
            print(json.dumps(response, indent=2))

            if request_id:
                print("\n🔍 To check the result, run:")
                print(
                    f"   docker exec comfyui-supervisor-1 curl -s http://127.0.0.1:38188/result/{request_id}"
                )

            sys.exit(0)
        except json.JSONDecodeError:
            print("❌ Invalid JSON response:")
            print(result.stdout)
            sys.exit(1)
    else:
        print(f"❌ Command failed with return code {result.returncode}")
        print(f"   Error: {result.stderr}")
        sys.exit(1)

except subprocess.TimeoutExpired:
    print("❌ Request timed out")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
