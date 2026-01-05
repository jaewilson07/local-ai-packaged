#!/bin/bash
# Get authentication token for ComfyUI API access

CONTAINER_NAME="comfyui-supervisor-1"

echo "============================================================"
echo "ComfyUI API Authentication Token"
echo "============================================================"
echo ""

# Get actual tokens from container environment
WEB_TOKEN=$(docker exec $CONTAINER_NAME bash -c 'source /opt/ai-dock/etc/environment.sh && echo $WEB_TOKEN' 2>/dev/null)
WEB_PASSWORD_B64=$(docker exec $CONTAINER_NAME bash -c 'source /opt/ai-dock/etc/environment.sh && echo $WEB_PASSWORD_B64' 2>/dev/null)

# Get user/password for reference
WEB_PASSWORD=$(docker exec $CONTAINER_NAME env | grep "^WEB_PASSWORD=" | cut -d= -f2)
WEB_USER=$(docker exec $CONTAINER_NAME env | grep "^WEB_USER=" | cut -d= -f2)

if [ -z "$WEB_PASSWORD" ]; then
    WEB_PASSWORD="password"
fi

if [ -z "$WEB_USER" ]; then
    WEB_USER="user"
fi

# Generate base64 encoded "user:password" for Basic auth (if needed)
BASIC_AUTH=$(echo -n "$WEB_USER:$WEB_PASSWORD" | base64)

echo "📋 Authentication Information:"
echo "   Username: $WEB_USER"
echo "   Password: $WEB_PASSWORD"
echo ""
echo "🔑 Tokens for API Authentication:"
echo ""
if [ -n "$WEB_TOKEN" ]; then
    echo "1. WEB_TOKEN (for Bearer token - RECOMMENDED):"
    echo "   $WEB_TOKEN"
    echo ""
fi
if [ -n "$WEB_PASSWORD_B64" ]; then
    echo "2. WEB_PASSWORD_B64 (for Bearer token or query parameter):"
    echo "   $WEB_PASSWORD_B64"
    echo ""
fi
echo "3. Basic Auth Token (user:password base64 - fallback):"
echo "   $BASIC_AUTH"
echo ""
echo "============================================================"
echo "Usage Examples:"
echo "============================================================"
echo ""
if [ -n "$WEB_TOKEN" ]; then
    echo "Bearer Token with WEB_TOKEN (RECOMMENDED):"
    echo "  curl -H \"Authorization: Bearer $WEB_TOKEN\" \\"
    echo "    -X POST \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -d @payload.json \\"
    echo "    http://localhost:8188/ai-dock/api/payload"
    echo ""
fi
if [ -n "$WEB_PASSWORD_B64" ]; then
    echo "Bearer Token with WEB_PASSWORD_B64:"
    echo "  curl -H \"Authorization: Bearer $WEB_PASSWORD_B64\" \\"
    echo "    -X POST \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -d @payload.json \\"
    echo "    http://localhost:8188/ai-dock/api/payload"
    echo ""
fi
echo "Basic Auth (Authorization Header):"
echo "  curl -H \"Authorization: Basic $BASIC_AUTH\" \\"
echo "    -X POST \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d @payload.json \\"
echo "    http://localhost:8188/ai-dock/api/payload"
echo ""
if [ -n "$WEB_TOKEN" ]; then
    echo "Query Parameter (with WEB_TOKEN):"
    echo "  curl -X POST \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -d @payload.json \\"
    echo "    \"http://localhost:8188/ai-dock/api/payload?token=$WEB_TOKEN\""
elif [ -n "$WEB_PASSWORD_B64" ]; then
    echo "Query Parameter (with WEB_PASSWORD_B64):"
    echo "  curl -X POST \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -d @payload.json \\"
    echo "    \"http://localhost:8188/ai-dock/api/payload?token=$WEB_PASSWORD_B64\""
fi
echo ""
echo "============================================================"
echo ""
echo "💾 To save token to environment variable:"
if [ -n "$WEB_TOKEN" ]; then
    echo "   export API_TOKEN=\"$WEB_TOKEN\""
fi
if [ -n "$WEB_PASSWORD_B64" ]; then
    echo "   export API_PASSWORD_B64=\"$WEB_PASSWORD_B64\""
fi
echo "   export API_BASIC_AUTH=\"$BASIC_AUTH\""
echo ""

