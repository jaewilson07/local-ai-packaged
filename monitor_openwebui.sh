#!/bin/bash

# Real-time monitoring script for Open WebUI
# Shows logs, database status, and API health

echo "=========================================="
echo "Open WebUI Monitoring Dashboard"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to check database tables
check_db_tables() {
    echo -e "\n${YELLOW}=== Database Tables Check ===${NC}"
    TABLES=$(docker exec supabase-db psql -U postgres -d postgres -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';" 2>&1 | grep -v "^$" | wc -l)
    if [ "$TABLES" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $TABLES tables${NC}"
        docker exec supabase-db psql -U postgres -d postgres -c "\dt" 2>&1 | grep -E "public|table" | head -20
    else
        echo -e "${RED}✗ No tables found - database may not be initialized${NC}"
    fi
}

# Function to check Open WebUI health
check_health() {
    echo -e "\n${YELLOW}=== Open WebUI Health ===${NC}"
    HEALTH=$(docker exec open-webui curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null || echo "000")
    if [ "$HEALTH" = "200" ]; then
        echo -e "${GREEN}✓ Health endpoint: HTTP $HEALTH${NC}"
    else
        echo -e "${RED}✗ Health endpoint: HTTP $HEALTH${NC}"
    fi
}

# Function to check database connection
check_db_connection() {
    echo -e "\n${YELLOW}=== Database Connection ===${NC}"
    if docker exec open-webui sh -c "nc -z supabase-db 5432" 2>/dev/null; then
        echo -e "${GREEN}✓ Network connectivity OK${NC}"
    else
        echo -e "${RED}✗ Network connectivity FAILED${NC}"
    fi

    if docker exec supabase-db pg_isready -U postgres >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
    else
        echo -e "${RED}✗ PostgreSQL is NOT ready${NC}"
    fi
}

# Initial checks
check_db_connection
check_health
check_db_tables

echo -e "\n${YELLOW}=== Live Logs (last 20 lines, updating every 5 seconds) ===${NC}"
echo ""

# Monitor logs
while true; do
    clear
    echo "=========================================="
    echo "Open WebUI Monitoring Dashboard"
    echo "=========================================="
    echo "Last update: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    check_db_connection
    check_health
    check_db_tables

    echo -e "\n${YELLOW}=== Recent Logs (last 20 lines) ===${NC}"
    docker logs open-webui --tail 20 2>&1 | tail -20

    echo ""
    echo "Press Ctrl+C to stop..."
    sleep 5
done
