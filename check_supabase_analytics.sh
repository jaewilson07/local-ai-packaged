#!/bin/bash

# Comprehensive health check for supabase-analytics
# This script verifies all components needed for analytics to work

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "Supabase Analytics Health Check"
echo "=========================================="
echo ""

# Check 1: Container status
echo "1. Checking container status..."
if docker ps --format "{{.Names}}" | grep -q "^supabase-analytics$"; then
    STATUS=$(docker inspect supabase-analytics --format='{{.State.Status}}')
    HEALTH=$(docker inspect supabase-analytics --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-healthcheck")
    
    if [ "$STATUS" = "running" ]; then
        echo -e "${GREEN}✓ Container is running${NC}"
    else
        echo -e "${RED}✗ Container status: $STATUS${NC}"
        exit 1
    fi
    
    if [ "$HEALTH" = "healthy" ]; then
        echo -e "${GREEN}✓ Health check: $HEALTH${NC}"
    elif [ "$HEALTH" = "starting" ]; then
        echo -e "${YELLOW}⚠ Health check: $HEALTH (still starting)${NC}"
    else
        echo -e "${RED}✗ Health check: $HEALTH${NC}"
    fi
else
    echo -e "${RED}✗ Container not found${NC}"
    exit 1
fi
echo ""

# Check 2: Health endpoint
echo "2. Checking health endpoint..."
HEALTH_RESPONSE=$(docker exec supabase-analytics curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/health 2>/dev/null || echo "000")
if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ Health endpoint: HTTP $HEALTH_RESPONSE${NC}"
    HEALTH_BODY=$(docker exec supabase-analytics curl -s http://localhost:4000/health 2>/dev/null)
    if echo "$HEALTH_BODY" | grep -q '"status":"ok"'; then
        echo -e "${GREEN}✓ Health status: OK${NC}"
    else
        echo -e "${YELLOW}⚠ Health response: $HEALTH_BODY${NC}"
    fi
else
    echo -e "${RED}✗ Health endpoint: HTTP $HEALTH_RESPONSE${NC}"
fi
echo ""

# Check 3: Database connection
echo "3. Checking database connection..."
if docker exec supabase-db psql -U postgres -c "\l" 2>/dev/null | grep -q "_supabase"; then
    echo -e "${GREEN}✓ _supabase database exists${NC}"
else
    echo -e "${RED}✗ _supabase database not found${NC}"
    echo "  Creating database..."
    docker exec supabase-db psql -U postgres -c 'CREATE DATABASE "_supabase" WITH OWNER supabase_admin;' 2>/dev/null || true
fi

# Check schema
SCHEMA_CHECK=$(docker exec supabase-db psql -U supabase_admin -d _supabase -t -c "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = '_analytics';" 2>/dev/null | tr -d ' ')
if [ "$SCHEMA_CHECK" = "1" ]; then
    echo -e "${GREEN}✓ _analytics schema exists${NC}"
else
    echo -e "${YELLOW}⚠ _analytics schema not found, creating...${NC}"
    docker exec supabase-db psql -U supabase_admin -d _supabase -c "CREATE SCHEMA IF NOT EXISTS _analytics;" 2>/dev/null || true
fi
echo ""

# Check 4: Network connectivity
echo "4. Checking network connectivity..."
if docker exec supabase-analytics sh -c "nc -z supabase-db 5432" 2>/dev/null; then
    echo -e "${GREEN}✓ Can reach PostgreSQL${NC}"
else
    echo -e "${RED}✗ Cannot reach PostgreSQL${NC}"
fi
echo ""

# Check 5: Recent errors
echo "5. Checking for recent errors..."
ERROR_COUNT=$(docker logs supabase-analytics --tail 100 2>&1 | grep -i "error\|fatal\|exception" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ No recent errors found${NC}"
else
    echo -e "${YELLOW}⚠ Found $ERROR_COUNT recent errors${NC}"
    echo "  Recent errors:"
    docker logs supabase-analytics --tail 100 2>&1 | grep -i "error\|fatal\|exception" | tail -5 | sed 's/^/    /'
fi
echo ""

# Check 6: Environment variables
echo "6. Checking critical environment variables..."
ENV_VARS=("DB_HOSTNAME" "DB_DATABASE" "DB_SCHEMA" "POSTGRES_BACKEND_URL")
MISSING=0
for var in "${ENV_VARS[@]}"; do
    VALUE=$(docker exec supabase-analytics printenv "$var" 2>/dev/null || echo "")
    if [ -z "$VALUE" ]; then
        echo -e "${RED}✗ $var not set${NC}"
        MISSING=$((MISSING + 1))
    else
        echo -e "${GREEN}✓ $var is set${NC}"
    fi
done
echo ""

# Summary
echo "=========================================="
echo "Summary"
echo "=========================================="
if [ "$HEALTH" = "healthy" ] && [ "$HEALTH_RESPONSE" = "200" ] && [ "$MISSING" -eq 0 ]; then
    echo -e "${GREEN}✓ Supabase Analytics is healthy!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Supabase Analytics needs attention${NC}"
    echo ""
    echo "To fix issues:"
    echo "1. Check logs: docker logs supabase-analytics --tail 100"
    echo "2. Restart container: docker restart supabase-analytics"
    echo "3. Verify database: docker exec supabase-db psql -U postgres -c '\\l'"
    exit 1
fi

