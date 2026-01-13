#!/bin/bash
# Fix ownership of all files in the project directory
# This script fixes files created by Docker containers running as root

set -e

PROJECT_DIR="/home/jaewilson07/GitHub/local-ai-packaged"
USER="jaewilson07"

echo "Fixing ownership of all files in $PROJECT_DIR..."
echo "This may take a few minutes if there are many files..."

# Change ownership recursively
sudo chown -R ${USER}:${USER} "${PROJECT_DIR}"

# Also fix permissions to ensure user has full access
chmod -R u+rwX "${PROJECT_DIR}"

echo "Ownership fix complete!"
echo ""
echo "Verifying ownership..."
NOT_OWNED=$(find "${PROJECT_DIR}" -not -user ${USER} 2>/dev/null | wc -l)
if [ "$NOT_OWNED" -eq 0 ]; then
    echo "✓ All files are now owned by ${USER}"
else
    echo "⚠ Warning: $NOT_OWNED files are still not owned by ${USER}"
    echo "You may need to check Docker volume mounts or system directories"
fi
