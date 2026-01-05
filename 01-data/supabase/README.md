# Supabase Local Service

This directory contains the local service configuration for Supabase.

## Structure

- **docker-compose.yml**: Service definitions.
- **upstream/**: Cloned repository from `github.com/supabase/supabase` (used for docker configurations).
- **data/**: Persistent data storage (database, storage, etc.).
- **config/**: Local configuration overrides.

## Usage

Managed by `start_services.py`.

```bash
# Start data stack
python start_services.py --stack data
```
