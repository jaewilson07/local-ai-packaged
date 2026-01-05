# Archived Files

This directory contains old configuration files that have been replaced by the modular Docker Compose architecture.

## docker-compose.yml.old

This was the original `docker-compose.yml` file that used the `include:` directive to include Supabase compose files. It has been replaced by the modular architecture in the `compose/` directory.

## docker-compose.yml

This is the root `docker-compose.yml` file that was archived after migration to modular architecture. It is identical to `docker-compose.yml.old` and uses the old `include:` directive pattern. The file was moved from the project root to the archive directory as it is no longer used by `start_services.py`, which now exclusively uses modular compose files.

## INFISICAL_SUPABASE_CONFLICTS.md

This document described conflicts between Infisical and Supabase services that occurred with the old architecture using `include:` directives. These conflicts have been resolved by the modular Docker Compose architecture, making this documentation outdated. The file has been archived for historical reference.

### Migration Notes

- **Old approach**: Single `docker-compose.yml` with `include:` directive
- **New approach**: Modular compose files in `compose/` subdirectories
- **Benefits**: No conflicts, easier updates, better organization

### If You Need to Reference the Old File

The old file is preserved here for reference. However, you should use the new modular compose files:

- `compose/core/docker-compose.yml` - Core infrastructure
- `compose/supabase/docker-compose.yml` - Supabase services
- `compose/infisical/docker-compose.yml` - Infisical service
- `compose/ai/docker-compose.yml` - AI services
- `compose/workflow/docker-compose.yml` - Workflow services
- `compose/data/docker-compose.yml` - Data stores
- `compose/observability/docker-compose.yml` - Observability services
- `compose/web/docker-compose.yml` - Web interfaces

See `docs/modular-compose-architecture.md` for full documentation.

