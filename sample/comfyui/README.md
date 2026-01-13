# ComfyUI Sample Scripts

Sample scripts for working with ComfyUI workflows and LoRA models.

## Execute Workflow (End-to-End)

### `execute_workflow_sample.py`

Complete end-to-end workflow execution example that demonstrates:
1. Creating a workflow in Supabase
2. Checking if LoRA models exist
3. Executing the workflow via API
4. Polling for completion
5. Displaying results (output images, errors)

**Prerequisites:**
- Lambda server running and accessible
- ComfyUI service running
- `CLOUDFLARE_EMAIL` in `.env` file (for user identification)

**Usage:**
```bash
# For local development (uses internal network, no auth required)
python sample/comfyui/execute_workflow_sample.py

# For external API access (requires JWT token)
export API_BASE_URL=https://api.datacrew.space
export CF_ACCESS_JWT=your-cloudflare-access-jwt-token
python sample/comfyui/execute_workflow_sample.py
```

**Note**: The script automatically defaults to internal network URLs (`http://lambda-server:8000`) when running locally, which bypasses Cloudflare Access authentication. For external URLs, you'll need a Cloudflare Access JWT token.

**What it does:**
- Creates a workflow from the embedded JSON (Alix character image generation)
- Checks if the required LoRA (`alix_character_lora_zit_merged_2000_3000.safetensors`) exists
- Executes the workflow
- Polls for completion (up to 10 minutes)
- Displays output images and execution metadata

**Workflow Details:**
- Uses LoRA: `alix_character_lora_zit_merged_2000_3000.safetensors`
- Generates images with prompt about "i wish you were here"
- Creates 3 images (batch_size: 3)
- Saves both processed and raw images

**Database Tracking:**
The workflow execution is automatically tracked in Supabase:
- `comfyui_workflows` - Stores the workflow configuration
- `comfyui_workflow_runs` - Tracks execution with:
  - Status (pending → running → completed/failed)
  - ComfyUI request ID
  - Output image URLs
  - Error messages (if failed)
  - Execution timestamps

## Import LoRA from Google Drive

### `import_lora_from_google_drive.py`

Imports the sample Alix character LoRA from Google Drive.

### LoRA Versioning System

The API uses **character_name** as the unique identifier (trigger word) for LoRAs:

- **character_name is required** - This is the trigger word you use in prompts (e.g., "alix")
- **One active LoRA per character** - Only one version can be active at a time
- **Versioning for rollback** - When you upload a new LoRA for an existing character with `replace=True`, the old version is archived (not deleted)
- **Rollback support** - You can switch between versions without re-uploading

**Behavior on duplicate:**
- `replace=False` (default): Raises 409 Conflict error if character exists
- `replace=True`: Creates a new version, archives the current one

### Prerequisites

1. **Google Drive OAuth Token**: You need to obtain an OAuth token for Google Drive API access.

   To get a token, you can:
   - Use the Google OAuth Playground: https://developers.google.com/oauthplayground/
   - Select "Drive API v3" and the scope: `https://www.googleapis.com/auth/drive.readonly`
   - Authorize and exchange for tokens
   - Copy the refresh token and create a JSON like:
     ```json
     {
       "access_token": "...",
       "refresh_token": "...",
       "token_uri": "https://oauth2.googleapis.com/token",
       "client_id": "your-client-id",
       "client_secret": "your-client-secret",
       "scopes": ["https://www.googleapis.com/auth/drive.readonly"]
     }
     ```
   - Set it as `GDOC_TOKEN` in your `.env` file

2. **CLOUDFLARE_EMAIL**: Set in `.env` for user identification.

### Using the Script

```bash
# For local development (uses internal network, no auth required)
python sample/comfyui/import_lora_from_google_drive.py

# For external API access (requires JWT token)
export API_BASE_URL=https://api.datacrew.space
export CF_ACCESS_JWT=your-cloudflare-access-jwt-token
python sample/comfyui/import_lora_from_google_drive.py
```

The script will:
1. Download the LoRA file from Google Drive (ID: `1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7`)
2. Check if a LoRA for character "alix" already exists
3. If exists and `replace=False`: Error (409 Conflict)
4. If exists and `replace=True`: Create new version, archive old
5. If doesn't exist: Create first version
6. Verify the LoRA appears in `/api/me/data/loras`
7. List all user's LoRAs

### Using the API Endpoint

#### Import a new LoRA (first time)
```bash
curl -X POST "http://lambda-server:8000/api/v1/comfyui/loras/import-from-google-drive" \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_file_id": "1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7",
    "character_name": "alix",
    "name": "Alix Character LoRA",
    "description": "Alix character LoRA for image generation",
    "tags": ["character", "alix", "sample"]
  }'
```

#### Replace with new version
```bash
curl -X POST "http://lambda-server:8000/api/v1/comfyui/loras/import-from-google-drive" \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_file_id": "NEW_FILE_ID_HERE",
    "character_name": "alix",
    "name": "Alix Character LoRA v2",
    "description": "Updated Alix LoRA with better training",
    "replace": true
  }'
```

#### Rollback to previous version
```bash
curl -X PUT "http://lambda-server:8000/api/v1/comfyui/loras/by-character/alix/rollback/1"
```

#### Get version history
```bash
curl -X GET "http://lambda-server:8000/api/v1/comfyui/loras/by-character/alix"
```

## List All LoRAs

The ComfyUI LoRA endpoints support both internal network (no auth) and external network (JWT required) access.

### Using the Test Script

```bash
# For local development (uses internal network, no auth required)
python sample/comfyui/test_list_loras.py

# For external API access (requires JWT token)
export API_BASE_URL=https://api.datacrew.space
export CF_ACCESS_JWT=your-cloudflare-access-jwt-token
python sample/comfyui/test_list_loras.py
```

**Note**: The script automatically defaults to internal network URLs (`http://lambda-server:8000`) when running locally, which bypasses Cloudflare Access authentication. For external URLs, you'll need a Cloudflare Access JWT token.

### Using curl

```bash
# List active LoRAs only (default)
curl -X GET "http://lambda-server:8000/api/v1/comfyui/loras"

# Include archived/inactive versions
curl -X GET "http://lambda-server:8000/api/v1/comfyui/loras?include_inactive=true"

# External network (requires JWT token)
curl -X GET "https://api.datacrew.space/api/v1/comfyui/loras" \
  -H "Cf-Access-Jwt-Assertion: $CF_ACCESS_JWT"
```

### Important Notes

- **Local Development**: Scripts default to internal network URLs, which bypass authentication (network isolation provides security)
- **External Access**: For external URLs, you need a Cloudflare Access JWT token (obtain from browser DevTools when accessing through Cloudflare Access)
- **User Identification**: Scripts automatically load `CLOUDFLARE_EMAIL` from `.env` for user identification
- **Authentication Helpers**: All sample scripts should use helper functions from `sample/shared/auth_helpers.py` for consistent authentication handling. See [sample/README.md](../README.md#authentication) for details.

The endpoint supports query parameters:
- `limit`: Maximum number of results (default: 100)
- `offset`: Pagination offset (default: 0)
- `include_inactive`: Include archived versions (default: false)

Example response:
```json
{
  "models": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "name": "Alix Character LoRA",
      "filename": "alix.safetensors",
      "minio_path": "user-{uuid}/loras/alix.safetensors",
      "file_size": 12345678,
      "description": "Alix character LoRA for image generation",
      "tags": ["character", "alix", "sample"],
      "character_name": "alix",
      "version": 2,
      "is_active": true,
      "parent_id": "previous-version-uuid",
      "replaced_at": null,
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "count": 1
}
```
