#!/bin/bash
# Setup Infisical Project: local-aipackaged
# This script helps set up a new Infisical project for the local-ai-packaged repository

set -e

PROJECT_NAME="local-aipackaged"
INFISICAL_URL="${INFISICAL_SITE_URL:-http://localhost:8010}"

echo "=" * 60
echo "Infisical Project Setup: $PROJECT_NAME"
echo "=" * 60
echo ""

# Check if Infisical CLI is installed
if ! command -v infisical &> /dev/null; then
    echo "❌ Infisical CLI not found"
    echo "   Install it: python3 utils/setup/install_clis.py"
    exit 1
fi

echo "✅ Infisical CLI found: $(infisical --version | head -1)"
echo ""

# Check if Infisical is accessible
echo "🔍 Checking Infisical accessibility..."
if curl -s "$INFISICAL_URL/api/health" > /dev/null 2>&1; then
    echo "✅ Infisical is accessible at $INFISICAL_URL"
else
    echo "⚠️  Infisical not accessible at $INFISICAL_URL"
    echo "   Make sure Infisical is running:"
    echo "     docker ps | grep infisical"
    echo "   Or check if it's on a different port/URL"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "📋 Setup Steps:"
echo ""
echo "1. Access Infisical UI:"
echo "   Open: $INFISICAL_URL/admin/signup"
echo "   (Or $INFISICAL_URL if already signed up)"
echo ""
echo "2. Create Organization (if needed):"
echo "   - Click 'Create Organization'"
echo "   - Name it (e.g., 'DataCrew' or 'Personal')"
echo ""
echo "3. Create Project:"
echo "   - Click 'Create Project'"
echo "   - Name: $PROJECT_NAME"
echo "   - Select or create environments:"
echo "     * development (for local dev)"
echo "     * production (for production)"
echo ""
read -p "Press Enter when you've created the project in the UI..."

echo ""
echo "4. Authenticate CLI:"
echo "   This will open a browser for authentication..."
infisical login --host="$INFISICAL_URL"

echo ""
echo "5. Initialize project in this directory:"
echo "   This will create .infisical.json config file..."
cd /home/jaewilson07/GitHub/local-ai-packaged
infisical init

echo ""
echo "✅ Project setup complete!"
echo ""
echo "Next steps:"
echo "1. Add secrets to Infisical (via UI or CLI)"
echo "2. Test secret export: infisical export --format=dotenv"
echo "3. Use with start_services.py: python start_services.py --use-infisical"
echo ""
echo "For more info, see: 00-infrastructure/docs/infisical/setup.md"

