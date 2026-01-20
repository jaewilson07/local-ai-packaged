# User Preferences System - Sample Scripts

This directory contains sample scripts demonstrating the hierarchical user preferences system.

## Overview

The preferences system provides a centralized way to manage user, organization, and system-level settings with hierarchical resolution:

```
System Defaults → Organization Settings → User Preferences
   (Lowest)            (Medium)              (Highest Priority)
```

## Available Scripts

### 1. `manage_preferences.py`

Complete demonstration of preferences API including:
- Listing available categories
- Getting all preferences (with optional category filter)
- Viewing preference definitions (metadata)
- Updating user preferences
- Deleting preferences (revert to defaults)
- Source tracking (user vs system)

**Usage:**
```bash
python sample/preferences/manage_preferences.py
```

### 2. `google_drive_with_preferences.py`

Shows how preferences integrate with real application features (Google Drive):
- Setting user's default Google Drive folder
- Fetching preference values
- Example FastAPI route implementation
- Preference resolution logic

**Usage:**
```bash
python sample/preferences/google_drive_with_preferences.py
```

## Preference Categories

| Category | Keys | Example Use Case |
|----------|------|------------------|
| **google_drive** | default_folder_id, search_scope, page_size | Google Drive file operations |
| **llm** | default_model, temperature, max_tokens, provider | LLM inference |
| **embeddings** | model, provider | Vector embeddings |
| **ui** | theme, items_per_page, default_view | UI preferences |
| **crawl** | max_depth, max_pages, timeout | Web crawling |
| **rag** | search_mode, top_k, use_rerank | RAG searches |
| **workflows** | auto_save | Workflow execution |
| **notifications** | email_enabled, discord_enabled | Notification channels |
| **immich** | auto_backup, backup_folder | Immich integration |

## API Endpoints

### Get All Preferences
```bash
GET /api/v1/preferences
GET /api/v1/preferences?category=google_drive
```

### Get Specific Preference
```bash
GET /api/v1/preferences/{key}
```

### Update Preference
```bash
PUT /api/v1/preferences/{key}
Content-Type: application/json

{
  "value": "new_value"
}
```

### Delete Preference (Revert to Default)
```bash
DELETE /api/v1/preferences/{key}
```

### List Categories
```bash
GET /api/v1/preferences/categories
```

### List Preference Definitions
```bash
GET /api/v1/preferences/definitions
GET /api/v1/preferences/definitions?category=llm
```

## Integration Patterns

### Pattern 1: Route-Level Resolution

```python
@router.post("/endpoint")
async def endpoint(
    param: str | None = None,
    user: User = Depends(get_current_user),
    prefs: PreferencesService = Depends(get_preferences_service)
):
    # Resolve: explicit param → user pref → system default
    resolved = param or await prefs.get(user.id, "key", default="fallback")
    # Use resolved value...
```

### Pattern 2: Dependency Injection

```python
class MyDependencies(BaseModel):
    user: User
    preferences: PreferencesService

    async def get_config(self) -> dict:
        return {
            "setting1": await self.preferences.get(self.user.id, "key1"),
            "setting2": await self.preferences.get(self.user.id, "key2"),
        }
```

## Database Schema

The preferences system uses the following tables in Supabase:

- **preference_definitions**: System-wide preference catalog (managed by admins)
- **user_preferences**: User-specific overrides
- **organizations**: Organizations/teams (Phase 2)
- **organization_preferences**: Org-level defaults (Phase 2)
- **organization_members**: User membership in orgs (Phase 2)

See: `01-data/supabase/migrations/007_user_preferences.sql`

## Documentation

For complete documentation, see:
- **PRD**: `.cursor/PRDS/user-preferences-system.md`
- **Service Code**: `04-lambda/src/services/preferences/`
- **Architecture**: `AGENTS.md` (root)
