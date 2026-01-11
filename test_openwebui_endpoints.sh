#!/bin/bash

# Test Open WebUI API endpoints that are called on startup
# This helps identify which endpoint might be returning null/undefined

echo "Testing Open WebUI API endpoints..."
echo ""

# Test endpoints that are commonly called on page load
ENDPOINTS=(
    "/api/config"
    "/api/version"
    "/api/v1/configs"
    "/api/v1/configs/banners"
    "/api/v1/auths/"
    "/api/v1/users/user/settings"
    "/api/v1/tools/"
    "/api/models"
    "/api/usage"
)

for endpoint in "${ENDPOINTS[@]}"; do
    echo "Testing: $endpoint"
    RESPONSE=$(docker exec open-webui sh -c "curl -s -w '\n%{http_code}' http://localhost:8080$endpoint 2>&1" | tail -1)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(docker exec open-webui sh -c "curl -s http://localhost:8080$endpoint 2>&1" | head -5)
    
    echo "  HTTP Code: $HTTP_CODE"
    
    # Check if response is valid JSON
    if echo "$BODY" | grep -q "^{"; then
        # Check if it's null or empty object
        if echo "$BODY" | grep -q "^null$\|^\[\]$"; then
            echo "  ⚠️  WARNING: Response is null or empty array"
        elif echo "$BODY" | grep -q "^{}$"; then
            echo "  ⚠️  WARNING: Response is empty object"
        else
            echo "  ✓ Valid JSON response"
        fi
    elif echo "$BODY" | grep -q "^<!doctype html>"; then
        echo "  ⚠️  WARNING: Response is HTML (not JSON)"
    else
        echo "  Response preview: $(echo "$BODY" | head -1 | cut -c1-50)..."
    fi
    echo ""
done

echo "Note: Some endpoints require authentication and will return 401/403"
echo "The issue is likely with an endpoint that returns null/undefined when it should return an object"
