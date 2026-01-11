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

2. **User ID**: You need your user UUID from Supabase/auth system.

### Using the Script

```bash
# Set your user ID
export USER_ID=your-user-uuid-here

# Run the import script
python sample/comfyui/import_lora_from_google_drive.py
```

The script will:
1. Download the LoRA file from Google Drive (ID: `1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7`)
2. Rename it to `jw_sample_lora.safetensors`
3. Upload it to MinIO
4. Create metadata in Supabase

### Using the API Endpoint

Alternatively, you can use the API endpoint directly:

```bash
# Internal network (no auth required)
curl -X POST "http://lambda-server:8000/api/v1/comfyui/loras/import-from-google-drive" \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_file_id": "1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7",
    "name": "jw_sample_lora",
    "description": "Sample LoRA imported from Google Drive",
    "tags": ["sample", "imported"]
  }'

# External network (requires JWT token)
curl -X POST "https://api.datacrew.space/api/v1/comfyui/loras/import-from-google-drive" \
  -H "Cf-Access-Jwt-Assertion: $CF_ACCESS_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_file_id": "1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7",
    "name": "jw_sample_lora",
    "description": "Sample LoRA imported from Google Drive",
    "tags": ["sample", "imported"]
  }'
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
# Internal network (no auth required)
curl -X GET "http://lambda-server:8000/api/v1/comfyui/loras"

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

Example response:
```json
{
  "models": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "name": "jw_sample_lora",
      "filename": "jw_sample_lora.safetensors",
      "minio_path": "user-{uuid}/loras/jw_sample_lora.safetensors",
      "file_size": 12345678,
      "description": "Sample LoRA",
      "tags": ["sample"],
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "count": 1
}
```
