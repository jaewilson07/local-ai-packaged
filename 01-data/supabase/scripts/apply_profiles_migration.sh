#!/bin/bash
# Script to apply the profiles table migration to Supabase
# Usage: ./apply_profiles_migration.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATION_FILE="${SCRIPT_DIR}/../migrations/000_profiles_table.sql"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo "Error: Migration file not found: $MIGRATION_FILE"
    exit 1
fi

# Check if Supabase DB container is running
if ! docker ps | grep -q supabase-db; then
    echo "Error: Supabase database container (supabase-db) is not running"
    echo "Please start Supabase first: python start_services.py --stack data"
    exit 1
fi

echo "Applying profiles table migration..."
echo "Migration file: $MIGRATION_FILE"
echo ""

# Apply migration using psql in the container
docker exec -i supabase-db psql -U postgres -d postgres < "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration applied successfully!"
    echo "The profiles table should now exist in the database."
else
    echo ""
    echo "❌ Migration failed. Please check the error messages above."
    exit 1
fi
