#!/bin/bash

# Open WebUI Diagnostic Script
# Checks service health, database connectivity, and API endpoints

set -e

echo "=========================================="
echo "Open WebUI Diagnostic Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in Docker environment
check_docker() {
    echo "1. Checking Docker environment..."
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker not found${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ Docker found${NC}"
    echo ""
}

# Check Open WebUI container status
check_openwebui_container() {
    echo "2. Checking Open WebUI container status..."
    if docker ps --format "{{.Names}}" | grep -q "^open-webui$"; then
        STATUS=$(docker inspect open-webui --format='{{.State.Status}}')
        HEALTH=$(docker inspect open-webui --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-healthcheck")
        echo -e "${GREEN}✓ Container is running${NC}"
        echo "  Status: $STATUS"
        echo "  Health: $HEALTH"

        # Check recent logs for errors
        echo ""
        echo "  Recent logs (last 20 lines):"
        docker logs open-webui --tail 20 2>&1 | grep -i "error\|exception\|timeout\|failed" || echo "  No obvious errors in recent logs"
    else
        echo -e "${RED}✗ Open WebUI container not running${NC}"
        echo "  Run: docker compose -p localai-apps up -d open-webui"
    fi
    echo ""
}

# Check PostgreSQL connection
check_postgres() {
    echo "3. Checking PostgreSQL connection..."
    if docker ps --format "{{.Names}}" | grep -q "supabase-db"; then
        echo -e "${GREEN}✓ PostgreSQL container found${NC}"

        # Test connection from Open WebUI container
        if docker ps --format "{{.Names}}" | grep -q "^open-webui$"; then
            echo "  Testing connection from Open WebUI container..."
            if docker exec open-webui sh -c "nc -z supabase-db 5432" 2>/dev/null; then
                echo -e "${GREEN}✓ Network connectivity to PostgreSQL OK${NC}"
            else
                echo -e "${RED}✗ Cannot reach PostgreSQL from Open WebUI${NC}"
            fi
        fi
    else
        echo -e "${RED}✗ PostgreSQL container not found${NC}"
        echo "  Expected container: supabase-db"
    fi
    echo ""
}

# Check Open WebUI health endpoint
check_health_endpoint() {
    echo "4. Checking Open WebUI health endpoint..."
    if docker ps --format "{{.Names}}" | grep -q "^open-webui$"; then
        HEALTH_RESPONSE=$(docker exec open-webui curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null || echo "000")
        if [ "$HEALTH_RESPONSE" = "200" ]; then
            echo -e "${GREEN}✓ Health endpoint responding (HTTP $HEALTH_RESPONSE)${NC}"
        else
            echo -e "${YELLOW}⚠ Health endpoint returned HTTP $HEALTH_RESPONSE${NC}"
        fi
    fi
    echo ""
}

# Check API endpoints
check_api_endpoints() {
    echo "5. Checking Open WebUI API endpoints..."
    if docker ps --format "{{.Names}}" | grep -q "^open-webui$"; then
        # Check if API is accessible
        API_RESPONSE=$(docker exec open-webui curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v1/configs 2>/dev/null || echo "000")
        if [ "$API_RESPONSE" = "200" ] || [ "$API_RESPONSE" = "401" ]; then
            echo -e "${GREEN}✓ API endpoint responding (HTTP $API_RESPONSE)${NC}"
        else
            echo -e "${YELLOW}⚠ API endpoint returned HTTP $API_RESPONSE${NC}"
        fi
    fi
    echo ""
}

# Check Caddy reverse proxy
check_caddy() {
    echo "6. Checking Caddy reverse proxy..."
    if docker ps --format "{{.Names}}" | grep -q "^caddy$"; then
        echo -e "${GREEN}✓ Caddy container found${NC}"

        # Check if Caddy can reach Open WebUI
        if docker exec caddy curl -s -o /dev/null -w "%{http_code}" http://open-webui:8080/health 2>/dev/null | grep -q "200"; then
            echo -e "${GREEN}✓ Caddy can reach Open WebUI${NC}"
        else
            echo -e "${RED}✗ Caddy cannot reach Open WebUI${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Caddy container not found${NC}"
    fi
    echo ""
}

# Check database query performance
check_db_performance() {
    echo "7. Checking database query performance..."
    if docker ps --format "{{.Names}}" | grep -q "supabase-db"; then
        echo "  Testing simple query..."
        START_TIME=$(date +%s%N)
        docker exec supabase-db psql -U postgres -d postgres -c "SELECT 1;" > /dev/null 2>&1
        END_TIME=$(date +%s%N)
        DURATION=$((($END_TIME - $START_TIME) / 1000000))

        if [ $DURATION -lt 100 ]; then
            echo -e "${GREEN}✓ Database query fast (${DURATION}ms)${NC}"
        elif [ $DURATION -lt 1000 ]; then
            echo -e "${YELLOW}⚠ Database query slow (${DURATION}ms)${NC}"
        else
            echo -e "${RED}✗ Database query very slow (${DURATION}ms)${NC}"
        fi

        # Check for large conversation tables
        echo "  Checking conversation table size..."
        CONV_COUNT=$(docker exec supabase-db psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM conversations;" 2>/dev/null | tr -d ' ' || echo "0")
        if [ "$CONV_COUNT" != "0" ] && [ ! -z "$CONV_COUNT" ]; then
            echo "  Conversations in database: $CONV_COUNT"
            if [ "$CONV_COUNT" -gt 1000 ]; then
                echo -e "${YELLOW}⚠ Large number of conversations may cause slow loading${NC}"
            fi
        fi
    fi
    echo ""
}

# Check network connectivity
check_network() {
    echo "8. Checking Docker network..."
    if docker network inspect ai-network &>/dev/null; then
        echo -e "${GREEN}✓ ai-network exists${NC}"

        # Check if Open WebUI is on the network
        if docker network inspect ai-network | grep -q "open-webui"; then
            echo -e "${GREEN}✓ Open WebUI is on ai-network${NC}"
        else
            echo -e "${RED}✗ Open WebUI not found on ai-network${NC}"
        fi

        # Check if PostgreSQL is on the network
        if docker network inspect ai-network | grep -q "supabase-db"; then
            echo -e "${GREEN}✓ PostgreSQL is on ai-network${NC}"
        else
            echo -e "${RED}✗ PostgreSQL not found on ai-network${NC}"
        fi
    else
        echo -e "${RED}✗ ai-network not found${NC}"
    fi
    echo ""
}

# Check environment variables
check_env_vars() {
    echo "9. Checking critical environment variables..."
    if docker ps --format "{{.Names}}" | grep -q "^open-webui$"; then
        DB_TYPE=$(docker exec open-webui printenv DB_TYPE 2>/dev/null || echo "not set")
        DB_HOST=$(docker exec open-webui printenv DB_POSTGRESDB_HOST 2>/dev/null || echo "not set")

        echo "  DB_TYPE: $DB_TYPE"
        echo "  DB_POSTGRESDB_HOST: $DB_HOST"

        if [ "$DB_TYPE" = "postgresdb" ] && [ "$DB_HOST" = "supabase-db" ]; then
            echo -e "${GREEN}✓ Database configuration looks correct${NC}"
        else
            echo -e "${YELLOW}⚠ Database configuration may be incorrect${NC}"
        fi
    fi
    echo ""
}

# Summary and recommendations
print_recommendations() {
    echo "=========================================="
    echo "Recommendations"
    echo "=========================================="
    echo ""
    echo "If chat conversations are spinning forever:"
    echo ""
    echo "1. Check browser console (F12) for errors:"
    echo "   - Look for failed API requests"
    echo "   - Check for CORS errors"
    echo "   - Look for WebSocket connection failures"
    echo ""
    echo "2. Check Open WebUI logs:"
    echo "   docker logs open-webui --tail 100 -f"
    echo ""
    echo "3. If you have many conversations, try:"
    echo "   - Clear browser cache"
    echo "   - Wait longer (5-15 minutes for large histories)"
    echo "   - Check database query performance"
    echo ""
    echo "4. Test API directly:"
    echo "   docker exec open-webui curl http://localhost:8080/api/v1/conversations"
    echo ""
    echo "5. Restart Open WebUI:"
    echo "   docker restart open-webui"
    echo ""
}

# Run all checks
main() {
    check_docker
    check_openwebui_container
    check_postgres
    check_health_endpoint
    check_api_endpoints
    check_caddy
    check_db_performance
    check_network
    check_env_vars
    print_recommendations
}

main

