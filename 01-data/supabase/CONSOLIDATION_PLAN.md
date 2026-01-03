# Supabase Directory Consolidation Plan

## Current Situation

### Parallel Directories (to be removed)
- `/home/jaewilson07/GitHub/supabase` - Full Supabase repository (1.3GB)
- `/home/jaewilson07/GitHub/sb-project` - Supabase project (172KB)

### Project Structure
- `01-data/supabase/upstream/` - Already contains Supabase repository files
- `01-data/supabase/docker-compose.yml` - References updated to use `./upstream/docker/volumes/`

## Changes Made

### 1. Updated docker-compose.yml References ✅
All volume paths updated from:
- `../../../supabase/docker/volumes/` → `./upstream/docker/volumes/`

This makes the project self-contained and removes dependency on parallel directories.

### 2. Files Already in Project ✅
- `01-data/supabase/upstream/docker/volumes/` - Contains all required volumes
- `01-data/supabase/upstream/docker/docker-compose.yml` - Used by update script
- `01-data/supabase/upstream/docker/docker-compose.s3.yml` - Used by update script

## Next Steps

### Before Removing Parallel Directories

1. **Verify volumes are in project**:
   ```bash
   ls -la 01-data/supabase/upstream/docker/volumes/
   # Should show: api, db, functions, logs, pooler, storage
   ```

2. **Check for database data**:
   - If parallel directory has database data, it may need to be moved
   - Check: `supabase/docker/volumes/db/data/`

3. **Verify sb-project contents**:
   - Check if sb-project has any unique files needed
   - Compare with project structure

### Safe to Remove

After verification, these can be removed:
- `/home/jaewilson07/GitHub/supabase` - Full repository (already in upstream/)
- `/home/jaewilson07/GitHub/sb-project` - Appears to be duplicate project files

## Benefits

1. **Self-contained**: Project no longer depends on external directories
2. **Portable**: Can be moved/cloned without parallel directory requirements
3. **Cleaner**: Removes duplicate Supabase installations
4. **Maintainable**: All Supabase files in one place (`01-data/supabase/`)

