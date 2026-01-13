# Supabase Migrations

This directory contains SQL migration files for the Supabase database.

## Migration Files

- **`000_profiles_table.sql`** - Creates the `profiles` table for user authentication and management (CRITICAL - required for system to function)
- **`001_comfyui_workflows.sql`** - Creates ComfyUI workflow management tables (optional)
- **`002_workflow_publishing.sql`** - Workflow publishing features (optional)
- **`003_workflow_parameters.sql`** - Workflow parameters management (optional)
- **`004_lora_character_mapping.sql`** - LoRA character mapping (optional)
- **`005_immich_user_mapping.sql`** - Immich user mapping (optional)

## Automatic Migration Application

**Migrations are now automatically applied during Lambda server startup.**

The Lambda server (`04-lambda`) validates that core tables exist on startup and automatically applies migrations if they are missing. This ensures:

- Core tables (like `profiles`) are always present
- Migrations are applied in order
- System fails fast with clear error messages if migrations cannot be applied

### Core Tables (Required)

These tables are validated on startup and migrations are auto-applied if missing:

- `profiles` - User authentication and management (CRITICAL)

### Optional Tables

These tables are checked but missing them won't prevent startup:

- `comfyui_workflows` - ComfyUI workflow storage
- `comfyui_workflow_runs` - Workflow execution history
- `comfyui_lora_models` - LoRA model metadata

## Manual Application (Fallback)

If automatic migration fails, you can manually apply migrations:

### Option 1: Using the Script (Recommended for Local Development)

If you're running Supabase locally via Docker:

```bash
cd 01-data/supabase
./scripts/apply_profiles_migration.sh
```

This script will:
1. Check if the Supabase database container is running
2. Apply the migration using `psql` inside the container

### Option 2: Manual Application via Docker

```bash
# Apply a specific migration
docker exec -i supabase-db psql -U postgres -d postgres < migrations/000_profiles_table.sql

# Or apply all migrations in order
for migration in migrations/*.sql; do
    echo "Applying $migration..."
    docker exec -i supabase-db psql -U postgres -d postgres < "$migration"
done
```

### Option 3: Using Supabase Studio

1. Access Supabase Studio at `http://localhost:3000` (or your Supabase URL)
2. Navigate to the SQL Editor
3. Copy and paste the contents of the migration file
4. Execute the SQL

### Option 4: Direct Database Connection

If you have direct database access:

```bash
psql -h <host> -U postgres -d postgres -f migrations/000_profiles_table.sql
```

## Troubleshooting

### Error: "relation 'profiles' does not exist"

This error occurs when the `profiles` table hasn't been created yet. The Lambda server should automatically apply migrations on startup. If this error persists:

1. Check Lambda server logs for migration errors
2. Verify database connection is working
3. Manually apply the migration using one of the methods above

### Error: "permission denied for schema public"

The database user may not have CREATE TABLE permissions. Ensure you're using a user with appropriate privileges (e.g., `postgres` superuser or a user with CREATE permissions).

### Migration Already Applied

If you see "relation already exists" errors, the migration has already been applied. This is safe to ignore if using `CREATE TABLE IF NOT EXISTS`.

## Migration Order

Migrations are numbered to ensure proper execution order:
- `000_*` - Base schema (profiles, etc.) - CRITICAL
- `001_*` - Application-specific tables (ComfyUI, etc.) - Optional

Always apply migrations in numerical order.

## Protection Against Table Deletion

**IMPORTANT**: Core tables like `profiles` are critical for system operation. To prevent accidental deletion:

1. **Never run `DROP TABLE` commands** on core tables in production
2. **Always backup the database** before making schema changes
3. **Use migrations** for all schema changes (never modify tables directly)
4. **Test migrations** in a development environment first

The Lambda server validates core tables on every startup. If a core table is missing, the server will:
- Attempt to auto-apply migrations
- Log errors if migrations fail
- Continue running (to allow manual intervention) but authentication will fail

## Production Deployment

For production environments:

1. **Backup the database first**:
   ```bash
   pg_dump -h <host> -U postgres -d postgres > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Migrations are automatically applied** during Lambda server startup

3. **Verify** the migration was successful:
   ```sql
   SELECT * FROM information_schema.tables WHERE table_name = 'profiles';
   ```

## Notes

- Migrations use `CREATE TABLE IF NOT EXISTS` to be idempotent
- All migrations include proper indexes for performance
- The `profiles` table is required for the Lambda API authentication system
- Automatic migration application ensures the system is always in a valid state
