# Vestigial Files Analysis

This document identifies files that may no longer be relevant after the migration to the modular Docker Compose architecture. Files are categorized by confidence level that they are vestigial.

**Last Updated**: Based on analysis of `start_services.py` and modular compose architecture migration

## High Confidence - Vestigial (Can be archived)

### 1. `docker-compose.yml` (root directory)

**Status**: ✅ **VESTIGIAL - Safe to archive**

**Evidence**:

- Uses old `include:` directive pattern (lines 1-3)
- Identical to `archive/docker-compose.yml.old`
- `start_services.py` now uses modular compose files exclusively:
  - `compose/core/docker-compose.yml`
  - `compose/supabase/docker-compose.yml`
  - `compose/infisical/docker-compose.yml`
  - `compose/ai/docker-compose.yml`
  - `compose/workflow/docker-compose.yml`
  - `compose/data/docker-compose.yml`
  - `compose/observability/docker-compose.yml`
  - `compose/web/docker-compose.yml`
- Only referenced in unused functions: `start_infisical_old()`, `start_supabase()`, `start_local_ai_old()`

**Action**: Move to `archive/docker-compose.yml` (verify it's identical to `.old` first)

**Risk**: Low - Not used by current architecture

---

### 2. Unused Functions in `start_services.py`

**Status**: ✅ **VESTIGIAL - Can be removed**

**Functions to remove**:

1. **`prepare_supabase_env()`** (line 174)

   - Commented out in `main()` (line 1116: `# prepare_supabase_env() removed - using root .env file only`)
   - Never called
   - **Action**: Remove function

2. **`start_infisical_old()`** (line 426)

   - Old implementation using `docker run` or old compose approach
   - Never called - replaced by modular compose architecture
   - **Action**: Remove function

3. **`start_supabase()`** (line 622)

   - Old implementation for starting Supabase separately
   - Never called - Supabase now started via `start_all_services()`
   - **Action**: Remove function

4. **`start_local_ai_old()`** (line 847)
   - Old implementation using root `docker-compose.yml`
   - Never called - replaced by `start_all_services()`
   - **Action**: Remove function

**Action**: Remove these four functions from `start_services.py`

**Risk**: Low - Functions are never called

---

## Medium Confidence - Potentially Vestigial (Review needed)

### 3. `docker-compose.override.public.supabase.yml`

**Status**: ⚠️ **POTENTIALLY VESTIGIAL - Review needed**

**Evidence**:

- Still referenced in `start_services.py`:
  - `pull_docker_images()` (line 242) - when pulling Supabase images (now uses modular compose)
  - `start_supabase()` (line 669) - old unused function
- Supabase is now managed via `compose/supabase/docker-compose.yml`
- The override file only resets ports for `analytics`, `kong`, and `supavisor` services
- `pull_docker_images()` has been updated to use `compose/supabase/docker-compose.yml` (✅ Updated)

**Action**:

1. ✅ `pull_docker_images()` has been refactored to use modular compose
2. Check if this override file is still needed or if port overrides should be in `compose/supabase/docker-compose.yml`
3. If not needed, this override file can be removed

**Risk**: Low - May still be needed for port overrides in public deployments

---

### 4. `docs/INFISICAL_SUPABASE_CONFLICTS.md`

**Status**: ⚠️ **OUTDATED - Should be archived or updated**

**Evidence**:

- Documents conflicts from old architecture using `include:` directive
- Describes problems that are resolved by modular architecture
- References old startup sequence that no longer exists
- Solutions described are no longer applicable

**Content Summary**:

- Describes conflicts when using `include:` directive
- Recommends "Solution 1: Use Unified Compose" which is now the default
- References old `docker-compose.yml` structure

**Action**:

- Option 1: Archive as historical reference
- Option 2: Update to document that conflicts are resolved in modular architecture
- Option 3: Remove if no longer needed

**Risk**: Low - Documentation only, doesn't affect functionality

---

## Low Confidence - Likely Still Relevant

### 5. `n8n_pipe.py`

**Status**: ✅ **STILL RELEVANT**

**Evidence**: Referenced in README.md (line 597) as function to add to Open WebUI

**Action**: Keep

---

### 6. `n8n-tool-workflows/` directory

**Status**: ✅ **STILL RELEVANT**

**Evidence**: Contains workflow JSON files that are likely imported into n8n

**Action**: Keep

---

### 7. `flowise/` directory

**Status**: ✅ **STILL RELEVANT**

**Evidence**: Contains custom tool definitions and chatflow configurations for Flowise

**Action**: Keep

---

### 8. Override Files (Still in Use)

**Status**: ✅ **STILL RELEVANT**

- `docker-compose.override.private.yml` - Referenced in `start_all_services()` (line 385)
- `docker-compose.override.public.yml` - Referenced in `start_all_services()` (line 388)

**Action**: Keep

---

## Summary

### Files to Archive (High Confidence)

1. ✅ `docker-compose.yml` (root) → `archive/docker-compose.yml`
2. ✅ Remove 4 unused functions from `start_services.py`:
   - `prepare_supabase_env()`
   - `start_infisical_old()`
   - `start_supabase()`
   - `start_local_ai_old()`
3. ✅ Remove `ensure_redis_running()` function - Redis now managed via modular compose
4. ✅ Archive `docs/INFISICAL_SUPABASE_CONFLICTS.md` → `archive/INFISICAL_SUPABASE_CONFLICTS.md`

### Files to Review (Medium Confidence)

3. ⚠️ `docker-compose.override.public.supabase.yml` - Review if still needed (✅ `pull_docker_images()` refactored)
4. ⚠️ `docs/INFISICAL_SUPABASE_CONFLICTS.md` - Archive or update
5. ⚠️ `supabase/docker/docker-compose.yml` - Optional, only needed for update script (see `docs/supabase/docker-directory-requirements.md`)

### Files to Keep (Low Confidence / Still Relevant)

5. ✅ `n8n_pipe.py`
6. ✅ `n8n-tool-workflows/`
7. ✅ `flowise/`
8. ✅ Override files (private/public)

---

## Implementation Notes

1. **Before archiving `docker-compose.yml`**: Verify it's identical to `archive/docker-compose.yml.old` using diff
2. **After removing functions**: Test that `start_services.py` still works correctly
3. ✅ **For override file**: `pull_docker_images()` has been refactored to use modular compose architecture
4. **For conflicts doc**: Decide whether to archive (historical) or update (current state)
5. **For supabase/docker/**: See `docs/supabase/docker-directory-requirements.md` for what's essential vs optional

---

## Verification Checklist

After archiving, verify:

- [ ] `start_services.py` runs without errors
- [ ] No broken imports or references
- [ ] All services start correctly
- [ ] Documentation updated
- [ ] Git history preserved (files moved, not deleted)
