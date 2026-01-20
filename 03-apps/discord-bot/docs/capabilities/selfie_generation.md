# Selfie Generation Capability

The selfie generation capability enables Discord bot users to request AI-generated images (selfies) from characters using natural language.

## Overview

When a user mentions a character and requests a selfie/picture/photo, the bot:

1. **Detects the Request**: Identifies patterns like "send me a selfie", "take a picture", etc.
2. **Identifies Character**: Determines which character was mentioned
3. **Extracts Context**: Pulls descriptive details from the message (e.g., "at the beach")
4. **Generates Prompt**: Builds an optimized image generation prompt
5. **Calls ComfyUI**: Uses the `generate-with-lora` API endpoint
6. **Sends Image**: Downloads and sends the generated image back to Discord

## Architecture

```
Discord User Message
       ↓
SelfieGenerationCapability (priority 55)
       ↓
Character Detection (via APIClient)
       ↓
Prompt Building
       ↓
Lambda API: /api/v1/comfyui/generate-with-lora
       ↓
ComfyUI Workflow Execution
       ↓
Image Generated & Uploaded to Immich/MinIO
       ↓
Bot Downloads Image
       ↓
Discord Embed with Image Sent
```

## Configuration

### Environment Variables

```bash
# Required
DISCORD_BOT_TOKEN=your_discord_bot_token
LAMBDA_API_URL=http://lambda-server:8000

# Enable capabilities (comma-separated)
ENABLED_CAPABILITIES=character,selfie_generation

# Optional: Cloudflare Access (for external API)
CLOUDFLARE_ACCESS_CLIENT_ID=your_client_id
CLOUDFLARE_ACCESS_CLIENT_SECRET=your_client_secret
```

### Capability Settings

The capability can be configured via Lambda API's capability settings:

```json
{
  "enabled_capabilities": ["character", "selfie_generation"],
  "capability_settings": {
    "selfie_generation": {
      "workflow_id": "uuid-of-workflow",
      "default_lora": "alix_character_lora_zit.safetensors",
      "batch_size": 1,
      "optimize_prompt": true,
      "upload_to_immich": true
    }
  }
}
```

**Settings:**
- `workflow_id` (optional): UUID of ComfyUI workflow to use. Auto-discovered if not set.
- `default_lora` (default: `alix_character_lora_zit.safetensors`): Fallback LoRA file
- `batch_size` (default: `1`): Number of images to generate
- `optimize_prompt` (default: `true`): Use AI to enhance the prompt
- `upload_to_immich` (default: `true`): Upload generated images to Immich

## Usage Examples

### Basic Selfie Request

```
User: Hey Alix, can you send me a selfie?
Bot:  📸 Alix is taking a selfie... (this may take 30-60 seconds)
      [... generating ...]
Bot:  [Sends image embed with generated selfie]
```

### Contextual Request

```
User: @Alix show me a picture of you at the beach wearing a sundress
Bot:  📸 Alix is taking a selfie...
      [... generates image with beach/sundress context ...]
Bot:  [Sends contextual selfie]
```

### Trigger Patterns

The capability detects these patterns (case-insensitive):

- `selfie`
- `pic`, `picture`
- `photo`
- `image`
- `show me/us`
- `send me/us`
- `can you send/show/take`
- `take a picture`

## Priority and Dependencies

- **Priority**: 55 (runs before `character_mention` at 60)
- **Requires**: `character_commands` (for character management)
- **Order**: Intercepts image requests before general character chat

## API Integration

### Generate with LoRA Endpoint

```python
POST /api/v1/comfyui/generate-with-lora
{
    "workflow_id": "uuid",
    "prompt": "selfie of Alix, casual, friendly",
    "character_lora": "alix_character_lora_zit.safetensors",
    "batch_size": 1,
    "optimize_prompt": true,
    "upload_to_immich": true
}

Response (202 Accepted):
{
    "id": "run-uuid",
    "status": "pending",
    "workflow_id": "workflow-uuid",
    ...
}
```

### Status Polling

```python
GET /api/v1/comfyui/runs/{run_id}

Response:
{
    "id": "run-uuid",
    "status": "completed",
    "output_images": [
        "http://minio:9000/bucket/path/image.png"
    ],
    "immich_asset_ids": ["asset-uuid"],
    ...
}
```

## Error Handling

The capability handles errors gracefully:

1. **No Workflow**: Auto-discovers compatible workflow or shows error
2. **API Errors**: Logs and shows user-friendly message
3. **Timeout**: Shows timeout message with run ID for manual checking
4. **Failed Generation**: Shows character-specific error message
5. **Download Errors**: Attempts URL conversion (internal → external MinIO)

## Events

The capability emits events for other capabilities:

```python
Event: "selfie_generated"
Data: {
    "character_name": "Alix",
    "user_id": "discord_user_id",
    "channel_id": "discord_channel_id",
    "run_id": "workflow_run_uuid",
    "image_url": "http://..."
}
```

## Testing

### Manual Test

1. Start the Discord bot:
   ```bash
   cd 03-apps/discord-bot
   python -m bot.main
   ```

2. Verify capability loaded:
   ```
   INFO - Selfie generation capability ready - listening for image requests
   ```

3. Add a character to a channel:
   ```
   /add_character character_id:alix
   ```

4. Request a selfie:
   ```
   Hey Alix, send me a selfie!
   ```

### Automated Test Script

```bash
python sample/discord/test_selfie_generation.py
```

This script verifies:
- Required environment variables
- Enabled capabilities
- Configuration settings
- Provides troubleshooting tips

## Troubleshooting

### Bot doesn't respond to selfie requests

**Check:**
1. Capability enabled: `ENABLED_CAPABILITIES=character,selfie_generation`
2. Character added to channel: `/add_character`
3. Bot logs show: `Selfie generation capability ready`
4. Message matches trigger patterns

### "No workflow configured" error

**Solutions:**
1. Let auto-discovery find a workflow (requires API access)
2. Manually set `workflow_id` in capability settings
3. Create a workflow with `parameter_overrides` metadata

**Check workflows:**
```bash
curl http://localhost:8000/api/v1/comfyui/workflows
```

### Image generation times out

**Check:**
1. ComfyUI service is running: `docker ps | grep comfyui`
2. ComfyUI has the LoRA model in `loras/` directory
3. ComfyUI has base model (Z-Image-Turbo)
4. Lambda server logs: `docker logs lambda-server`
5. ComfyUI logs: `docker logs comfyui`

### Bot can't download image

**Issue:** MinIO URL conversion fails (internal → external)

**Solution:**
- Ensure MinIO is accessible on `localhost:9000` (or update URL conversion in code)
- Check MinIO bucket permissions
- Verify image actually generated: Check MinIO bucket in browser

### LoRA not found

**Check:**
1. Character has `lora` field set in Lambda API
2. LoRA file exists: `GET /api/v1/comfyui/loras`
3. ComfyUI can access LoRA: `ls 02-compute/comfyui/data/models/loras/`

### Prompt optimization fails

**Workaround:**
- Disable prompt optimization: Set `optimize_prompt: false` in capability settings
- Or fix Ollama connection in Lambda server

## Implementation Details

### Prompt Building

The capability builds prompts from user context:

```python
# Input: "Hey Alix, send me a selfie at the beach in a sundress"
# Output: "selfie of Alix, at the beach in a sundress"

# Input: "Alix can you send me a pic?"
# Output: "selfie of Alix, casual, friendly, natural lighting, handheld camera"
```

### URL Conversion

MinIO URLs are converted for external access:

```python
# Internal: http://minio:9000/bucket/image.png
# External: http://localhost:9000/bucket/image.png
```

### Background Execution

Image generation runs in an asyncio task to avoid blocking:

```python
asyncio.create_task(
    self._generate_and_send_selfie(...)
)
```

This allows the bot to:
- Immediately acknowledge the request
- Update status message during generation
- Handle multiple concurrent requests

## Future Enhancements

Potential improvements:

1. **Multi-image responses**: Support batch_size > 1, send as gallery
2. **Style selection**: Allow users to specify styles ("cyberpunk selfie")
3. **Image variations**: Generate multiple versions, let user pick
4. **Conversation memory**: Remember previous selfie contexts
5. **Social media integration**: Auto-post to Bluesky/Tumblr
6. **Image editing**: "Make it more dramatic", "Add sunglasses"
7. **Progress updates**: Stream ComfyUI progress to Discord (via SSE)

## Related Documentation

- [Character Mention Capability](character_mention.py)
- [ComfyUI Workflow API](../../../../04-lambda/src/server/projects/comfyui_workflow/README.md)
- [Generate with LoRA Sample](../../../../sample/comfyui/generate_with_lora_streaming.py)
- [Discord Bot README](../../README.md)
