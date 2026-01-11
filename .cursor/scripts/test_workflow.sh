#!/bin/bash
# Full test workflow script for Deep Research Agent tests
#
# This script:
# 1. Runs test suite via run_deep_research_tests.py
# 2. Generates JSON report
# 3. Runs tracking script to update scratchpad
# 4. Displays summary
# 5. Prompts to update AGENTS.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LAMBDA_DIR="$PROJECT_ROOT/04-lambda"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deep Research Test Workflow${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in dry-run mode
DRY_RUN=false
COVERAGE=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}DRY RUN MODE${NC}"
    echo ""
fi

if [[ "$1" == "--coverage" ]] || [[ "$2" == "--coverage" ]]; then
    COVERAGE=true
fi

# Step 1: Run tests
echo -e "${BLUE}Step 1: Running tests...${NC}"
if [ "$DRY_RUN" = false ]; then
    cd "$LAMBDA_DIR"
    if [ "$COVERAGE" = true ]; then
        python "$SCRIPT_DIR/run_deep_research_tests.py" --coverage
    else
        python "$SCRIPT_DIR/run_deep_research_tests.py"
    fi
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -ne 0 ]; then
        echo -e "${RED}Tests failed with exit code $TEST_EXIT_CODE${NC}"
    else
        echo -e "${GREEN}✓ Tests completed${NC}"
    fi
else
    echo -e "${YELLOW}[DRY RUN] Would run: python run_deep_research_tests.py${NC}"
    TEST_EXIT_CODE=0
fi
echo ""

# Step 2: Parse results and track issues
echo -e "${BLUE}Step 2: Tracking issues...${NC}"
if [ "$DRY_RUN" = false ]; then
    RESULTS_FILE="$PROJECT_ROOT/.cursor/test_results/latest.json"
    if [ -f "$RESULTS_FILE" ]; then
        # Add issues from failures
        python "$SCRIPT_DIR/track_issues.py" --add "$RESULTS_FILE" || true
        
        # Update scratchpad
        python "$SCRIPT_DIR/track_test_debugging.py" \
            --results "$RESULTS_FILE" \
            --update-scratchpad \
            --add-issues || true
        
        echo -e "${GREEN}✓ Issues tracked and scratchpad updated${NC}"
    else
        echo -e "${YELLOW}Warning: Results file not found: $RESULTS_FILE${NC}"
    fi
else
    echo -e "${YELLOW}[DRY RUN] Would track issues and update scratchpad${NC}"
fi
echo ""

# Step 3: Display summary
echo -e "${BLUE}Step 3: Test Summary${NC}"
if [ "$DRY_RUN" = false ]; then
    RESULTS_FILE="$PROJECT_ROOT/.cursor/test_results/latest.json"
    if [ -f "$RESULTS_FILE" ]; then
        # Show issue summary
        python "$SCRIPT_DIR/track_issues.py" --summary || true
        echo ""
        
        # Show recent test run info
        if command -v jq &> /dev/null; then
            echo "Recent Test Run:"
            jq -r '.summary | "  Total: \(.total)\n  Passed: \(.passed)\n  Failed: \(.failed)\n  Errors: \(.error)"' "$RESULTS_FILE" || true
        fi
    fi
else
    echo -e "${YELLOW}[DRY RUN] Would display test summary${NC}"
fi
echo ""

# Step 4: Generate AGENTS.md summary
echo -e "${BLUE}Step 4: AGENTS.md Update${NC}"
if [ "$DRY_RUN" = false ]; then
    RESULTS_FILE="$PROJECT_ROOT/.cursor/test_results/latest.json"
    if [ -f "$RESULTS_FILE" ]; then
        echo "Generating summary for AGENTS.md..."
        python "$SCRIPT_DIR/track_test_debugging.py" \
            --results "$RESULTS_FILE" \
            --generate-agents-summary || true
        echo ""
        echo -e "${YELLOW}Review the summary above and update AGENTS.md if needed.${NC}"
    fi
else
    echo -e "${YELLOW}[DRY RUN] Would generate AGENTS.md summary${NC}"
fi
echo ""

# Final status
if [ "$DRY_RUN" = false ] && [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Workflow completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
elif [ "$DRY_RUN" = false ]; then
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Workflow completed with test failures${NC}"
    echo -e "${RED}========================================${NC}"
    exit $TEST_EXIT_CODE
else
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Dry run completed${NC}"
    echo -e "${YELLOW}========================================${NC}"
    exit 0
fi
