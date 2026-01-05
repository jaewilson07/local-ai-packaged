#!/bin/bash
# Sample ComfyUI API Call using curl
# This demonstrates how to generate an image using the ComfyUI API wrapper

# Configuration
BASE_URL="http://localhost:8188"
API_BASE="${BASE_URL}/ai-dock/api"
API_PAYLOAD="${API_BASE}/payload"
API_RESULT="${API_BASE}/result"

# Default credentials (from docker-compose.yaml)
WEB_USER="user"
WEB_PASSWORD="password"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "============================================================"
echo "ComfyUI API Sample - Image Generation (curl)"
echo "============================================================"
echo ""

# Create a simple payload JSON file
PAYLOAD_FILE=$(mktemp)
cat > "$PAYLOAD_FILE" << 'EOF'
{
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
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {
                    "ckpt_name": "v1-5-pruned-emaonly.ckpt"
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "text": "a beautiful landscape with mountains and a lake, sunset, highly detailed",
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": "blurry, low quality, distorted",
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        },
        "s3": {
            "access_key_id": "",
            "secret_access_key": "",
            "endpoint_url": "",
            "bucket_name": ""
        },
        "webhook": {
            "url": "",
            "extra_params": {}
        }
    }
}
EOF

echo -e "${BLUE}1. Submitting job to ComfyUI API...${NC}"
echo ""

# Submit the job
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -u "${WEB_USER}:${WEB_PASSWORD}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d @"$PAYLOAD_FILE" \
    "${API_PAYLOAD}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "202" ]; then
    echo -e "${GREEN}✅ Job submitted successfully!${NC}"
    REQUEST_ID=$(echo "$BODY" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    echo "   Request ID: $REQUEST_ID"
    echo ""
    
    echo -e "${BLUE}2. Polling for job result...${NC}"
    echo ""
    
    # Poll for result (max 5 minutes)
    MAX_WAIT=300
    ELAPSED=0
    CHECK_INTERVAL=2
    
    while [ $ELAPSED -lt $MAX_WAIT ]; do
        RESULT_RESPONSE=$(curl -s -w "\n%{http_code}" \
            -u "${WEB_USER}:${WEB_PASSWORD}" \
            "${API_RESULT}/${REQUEST_ID}")
        
        RESULT_HTTP_CODE=$(echo "$RESULT_RESPONSE" | tail -n1)
        RESULT_BODY=$(echo "$RESULT_RESPONSE" | sed '$d')
        
        if [ "$RESULT_HTTP_CODE" = "200" ]; then
            STATUS=$(echo "$RESULT_BODY" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
            MESSAGE=$(echo "$RESULT_BODY" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
            
            echo -e "   Status: ${YELLOW}${STATUS}${NC} - ${MESSAGE}"
            
            if [ "$STATUS" = "completed" ]; then
                echo ""
                echo -e "${GREEN}✅ Job completed successfully!${NC}"
                echo ""
                echo "The generated image should be in the ComfyUI output directory:"
                echo "   Container: /opt/ComfyUI/output/"
                echo "   Host: ./workspace/storage/output/"
                rm -f "$PAYLOAD_FILE"
                exit 0
            elif [ "$STATUS" = "failed" ]; then
                echo ""
                echo -e "${RED}❌ Job failed: ${MESSAGE}${NC}"
                rm -f "$PAYLOAD_FILE"
                exit 1
            fi
        fi
        
        sleep $CHECK_INTERVAL
        ELAPSED=$((ELAPSED + CHECK_INTERVAL))
    done
    
    echo ""
    echo -e "${YELLOW}⏱️  Timeout waiting for result${NC}"
    rm -f "$PAYLOAD_FILE"
    exit 1
    
elif [ "$HTTP_CODE" = "401" ]; then
    echo -e "${RED}❌ Authentication failed!${NC}"
    echo "   Please check your WEB_USER and WEB_PASSWORD credentials"
    rm -f "$PAYLOAD_FILE"
    exit 1
else
    echo -e "${RED}❌ Failed to submit job (HTTP $HTTP_CODE)${NC}"
    echo "   Response: $BODY"
    rm -f "$PAYLOAD_FILE"
    exit 1
fi


