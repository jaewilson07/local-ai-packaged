#!/bin/bash
# Script to re-initialize Infisical project after creating it in the UI

echo "=========================================="
echo "Infisical Project Re-initialization"
echo "=========================================="
echo ""
echo "This script will help you re-initialize your Infisical project."
echo ""
echo "Prerequisites:"
echo "  1. You must have created a project in the Infisical UI"
echo "  2. The project should be named 'local-ai-packaged'"
echo "  3. You should have a 'development' environment"
echo ""
read -p "Have you created the project in the Infisical UI? (y/N): " created

if [[ ! "$created" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Please create the project first:"
    echo "  1. Go to http://localhost:8020 (or your Infisical URL)"
    echo "  2. Create an Organization (if needed)"
    echo "  3. Create a Project named 'local-ai-packaged'"
    echo "  4. Create a 'development' environment"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo ""
echo "Re-initializing Infisical project..."
echo ""

# Run infisical init
cd /home/jaewilson07/GitHub/local-ai-packaged
infisical init

echo ""
echo "=========================================="
echo "Re-syncing secrets from .env to Infisical"
echo "=========================================="
echo ""

# Re-sync secrets using Infisical CLI
echo "Syncing secrets from .env to Infisical..."
echo "Note: Use 'infisical secrets set KEY=value' for each secret, or use the Infisical UI"
echo ""
echo "To sync all secrets, you can use:"
echo "  while IFS='=' read -r key value; do"
echo "    [ -n \"\$key\" ] && [ -n \"\$value\" ] && infisical secrets set \"\$key=\$value\""
echo "  done < .env"
echo ""
echo "Or manually add secrets via the Infisical UI at http://localhost:8020"

echo ""
echo "=========================================="
echo "Verification"
echo "=========================================="
echo ""

# Verify secrets
echo "Listing secrets in Infisical:"
infisical secrets | head -20

echo ""
echo "Done! Your Infisical project should now be properly configured."
