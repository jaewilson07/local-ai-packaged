# Supabase Migrations

This directory contains SQL migration files for the Supabase database.

## Migration Files

- **`000_profiles_table.sql`** - Creates the `profiles` table for user authentication and management
- **`001_comfyui_workflows.sql`** - Creates ComfyUI workflow management tables

## Applying Migrations

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

This error occurs when the `profiles` table hasn't been created yet. Apply the migration:

```bash
# Local development
./scripts/apply_profiles_migration.sh

# Or manually
docker exec -i supabase-db psql -U postgres -d postgres < migrations/000_profiles_table.sql
```

### Error: "permission denied for schema public"

The database user may not have CREATE TABLE permissions. Ensure you're using a user with appropriate privileges (e.g., `postgres` superuser or a user with CREATE permissions).

### Migration Already Applied

If you see "relation already exists" errors, the migration has already been applied. This is safe to ignore if using `CREATE TABLE IF NOT EXISTS`.

## Migration Order

Migrations are numbered to ensure proper execution order:
- `000_*` - Base schema (profiles, etc.)
- `001_*` - Application-specific tables (ComfyUI, etc.)

Always apply migrations in numerical order.

## Production Deployment

For production environments:

1. **Backup the database first**:
   ```bash
   pg_dump -h <host> -U postgres -d postgres > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Apply migrations** using one of the methods above

3. **Verify** the migration was successful:
   ```sql
   SELECT * FROM information_schema.tables WHERE table_name = 'profiles';
   ```

## Notes

- Migrations use `CREATE TABLE IF NOT EXISTS` to be idempotent
- All migrations include proper indexes for performance
- The `profiles` table is required for the Lambda API authentication system
