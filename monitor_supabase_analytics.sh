#!/bin/bash

# Real-time monitoring for supabase-analytics
# Shows health status, logs, and database connectivity

echo "=========================================="
echo "Supabase Analytics Monitor"
echo "=========================================="
echo "Press Ctrl+C to stop"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to get health status
get_health() {
    docker inspect supabase-analytics --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown"
}

# Function to check health endpoint
check_endpoint() {
    docker exec supabase-analytics curl -s http://localhost:4000/health 2>/dev/null | grep -q '"status":"ok"' && echo "ok" || echo "error"
}

# Initial status
echo "Starting monitoring..."
echo ""

while true; do
    clear
    echo "=========================================="
    echo "Supabase Analytics Monitor"
    echo "=========================================="
    echo "Last update: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # Container status
    if docker ps --format "{{.Names}}" | grep -q "^supabase-analytics$"; then
        STATUS=$(docker inspect supabase-analytics --format='{{.State.Status}}')
        HEALTH=$(get_health)
        UPTIME=$(docker inspect supabase-analytics --format='{{.State.StartedAt}}' | xargs -I {} date -d {} +%s 2>/dev/null || echo "0")
        NOW=$(date +%s)
        RUNTIME=$((NOW - UPTIME))

        echo "Container Status:"
        echo "  Status: $STATUS"
        if [ "$HEALTH" = "healthy" ]; then
            echo -e "  Health: ${GREEN}$HEALTH${NC}"
        elif [ "$HEALTH" = "starting" ]; then
            echo -e "  Health: ${YELLOW}$HEALTH${NC}"
        else
            echo -e "  Health: ${RED}$HEALTH${NC}"
        fi
        echo "  Uptime: $((RUNTIME / 60)) minutes"
        echo ""

        # Health endpoint
        ENDPOINT_STATUS=$(check_endpoint)
        echo "Health Endpoint:"
        if [ "$ENDPOINT_STATUS" = "ok" ]; then
            echo -e "  Status: ${GREEN}OK${NC}"
            RESPONSE=$(docker exec supabase-analytics curl -s http://localhost:4000/health 2>/dev/null | python3 -m json.tool 2>/dev/null | head -5 || echo "Response received")
            echo "  Response: $RESPONSE"
        else
            echo -e "  Status: ${RED}ERROR${NC}"
        fi
        echo ""

        # Database check
        echo "Database:"
        if docker exec supabase-db psql -U postgres -c "\l" 2>/dev/null | grep -q "_supabase"; then
            echo -e "  _supabase database: ${GREEN}exists${NC}"
        else
            echo -e "  _supabase database: ${RED}missing${NC}"
        fi

        TABLE_COUNT=$(docker exec supabase-db psql -U supabase_admin -d _supabase -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '_analytics';" 2>/dev/null | tr -d ' ')
        if [ ! -z "$TABLE_COUNT" ] && [ "$TABLE_COUNT" != "0" ]; then
            echo -e "  Tables in _analytics: ${GREEN}$TABLE_COUNT${NC}"
        else
            echo -e "  Tables in _analytics: ${YELLOW}0${NC}"
        fi
        echo ""

        # Recent logs
        echo "Recent Logs (last 10 lines):"
        docker logs supabase-analytics --tail 10 2>&1 | tail -10 | sed 's/^/  /'
        echo ""

        # Error count
        ERROR_COUNT=$(docker logs supabase-analytics --tail 50 2>&1 | grep -i "error\|fatal" | wc -l)
        if [ "$ERROR_COUNT" -gt 0 ]; then
            echo -e "${YELLOW}⚠ Recent errors: $ERROR_COUNT${NC}"
            docker logs supabase-analytics --tail 50 2>&1 | grep -i "error\|fatal" | tail -3 | sed 's/^/  /'
        fi

    else
        echo -e "${RED}Container not running!${NC}"
    fi

    echo ""
    echo "Press Ctrl+C to stop..."
    sleep 5
done
