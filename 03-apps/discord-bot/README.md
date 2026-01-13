# Discord Bot for Immich Integration

Discord bot that bridges Discord uploads to Immich, manages user face mapping, and sends automated notifications when users are detected in new photos.

## Features

- **Drag-and-Drop Ingest**: Automatically uploads files from `#event-uploads` channel to Immich
- **User Face Mapping**: `/claim_face` command to link Discord users to Immich person profiles
- **Spotted Notifications**: Sends DMs when users are detected in new photos/videos
- **MCP Server Integration**: Exposes Discord management tools via MCP protocol for AI assistants and programmatic access

## Architecture

- **Stack**: `03-apps` (application layer)
- **Container**: `discord-bot`
- **Network**: `ai-network` (shared Docker network)
- **Database**: SQLite (`bot.sqlite` in `data/` directory)

## Setup

### 1. Generate Immich API Key

1. Access Immich web UI (typically `http://localhost:2283` or your configured hostname)
2. Navigate to **Settings** → **API Keys**
3. Click **Create API Key**
4. Copy the generated API key
5. Add to `.env` file as `IMMICH_API_KEY`

### 2. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**
3. Give it a name (e.g., "Immich Bridge Bot")
4. Go to **Bot** section
5. Click **Create Bot**
6. Copy the **Token** (this is your `DISCORD_BOT_TOKEN`)
7. Under **Privileged Gateway Intents**, enable:
   - ✅ **MESSAGE CONTENT INTENT** (required to read message content)
8. Save changes

### 3. Invite Bot to Server

1. In Discord Developer Portal, go to **OAuth2** → **URL Generator**
2. Select scopes:
   - `bot`
   - `applications.commands` (for slash commands)
3. Select bot permissions:
   - Send Messages
   - Read Messages/View Channels
   - Attach Files
   - Use Slash Commands
4. Copy the generated URL and open it in a browser
5. Select your server and authorize

### 4. Get Channel ID (Optional)

If you want to restrict uploads to a specific channel:

1. In Discord, enable **Developer Mode**:
   - User Settings → Advanced → Developer Mode
2. Right-click on the channel (e.g., `#event-uploads`)
3. Click **Copy ID**
4. Add to `.env` file as `DISCORD_UPLOAD_CHANNEL_ID`

**Note**: If `DISCORD_UPLOAD_CHANNEL_ID` is empty, the bot will allow uploads from any channel.

### 5. Configure Environment Variables

Add these to your root `.env` file:

```bash
# Required
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Optional - Channel restriction (leave empty to allow uploads from any channel)
DISCORD_UPLOAD_CHANNEL_ID=

# Immich Configuration
IMMICH_SERVER_URL=http://immich-server:2283

# Optional - For user-specific Immich API keys (requires Discord account linking)
# LAMBDA_API_URL=http://lambda-server:8000  # Defaults to internal network
# CLOUDFLARE_EMAIL=your-email@example.com   # Your Cloudflare Access email

# Optional: MCP Server Configuration
MCP_ENABLED=true
MCP_PORT=8001
MCP_HOST=0.0.0.0
```

**Note**: `IMMICH_API_KEY` is no longer required. The bot will use user-specific API keys when available, or fall back to a global key if configured.

## Starting the Bot

The bot is part of the `apps` stack and will start automatically:

```bash
# Start apps stack (includes Discord bot)
python start_services.py --stack apps

# Or start all stacks
python start_services.py --profile cpu
```

## Usage

### Upload Files to Immich

1. Upload a file (jpg, png, mp4, mov) to any channel (or specific channel if `DISCORD_UPLOAD_CHANNEL_ID` is set)
2. Bot will automatically:
   - Download the file
   - Upload it to your Immich account (if Discord account is linked) or global account
   - Set description: "Uploaded by [YourName]"
   - Reply with confirmation

**Note**: Files larger than 25MB (Discord limit) will be rejected with an error message.

### Link Discord Account to Cloudflare Auth

To enable user-specific Immich uploads:

1. Authenticate via Cloudflare Access (visit `https://api.datacrew.space/api/me`)
2. Link your Discord account:
   ```bash
   curl -X POST https://api.datacrew.space/api/me/discord/link \
     -H "Cf-Access-Jwt-Assertion: <your-jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{"discord_user_id": "your-discord-user-id"}'
   ```
3. Uploads from your Discord account will now go to your personal Immich account

**Note**: If your Discord account is not linked, uploads will use the global Immich API key (if configured) or fail.

### Link Your Face

1. Run `/claim_face [SearchName]` in any channel
2. Bot will search Immich for people matching the name
3. Select the person that matches you from the dropdown
4. Your Discord account is now linked to that Immich person
5. You'll receive DMs when you're detected in new photos

### Receive Notifications

Once you've linked your face:
- Bot checks Immich every 2 minutes for new assets
- If a new photo/video contains your face, you'll receive a DM
- DM includes thumbnail and link to view in Immich gallery

## Troubleshooting

### Bot Not Responding

1. Check bot is running: `docker compose -p localai-apps ps discord-bot`
2. Check logs: `docker compose -p localai-apps logs -f discord-bot`
3. Verify environment variables are set correctly

### Upload Failures

1. Check Immich is running: `docker compose -p localai-apps ps immich-server`
2. Verify `IMMICH_API_KEY` is correct
3. Check bot logs for error messages

### Notifications Not Working

1. Verify you've run `/claim_face` and selected your person
2. Check database: `docker exec discord-bot sqlite3 /app/data/bot.sqlite "SELECT * FROM users;"`
3. Ensure Immich has detected faces in the photos
4. Check bot logs for notification errors

### Database Issues

Database is stored in `03-apps/discord-bot/data/bot.sqlite`. To reset:

```bash
# Stop bot
docker compose -p localai-apps stop discord-bot

# Remove database
rm 03-apps/discord-bot/data/bot.sqlite

# Restart bot (will recreate database)
docker compose -p localai-apps start discord-bot
```

## Development

### Project Structure

```
discord-bot/
├── bot/
│   ├── main.py              # Entry point (Discord bot + MCP server)
│   ├── config.py            # Configuration
│   ├── database.py          # SQLite operations
│   ├── immich_client.py     # Immich API client
│   ├── api_client.py        # Lambda API client
│   ├── utils.py             # Utility functions
│   ├── capabilities/        # Capability-based extensibility system
│   │   ├── __init__.py           # Public exports
│   │   ├── base.py               # BaseCapability class
│   │   ├── registry.py           # CapabilityRegistry + event bus
│   │   ├── echo.py               # Echo capability
│   │   ├── upload.py             # Upload + face claiming capability
│   │   ├── character_commands.py # Character management commands
│   │   ├── character_mention.py  # Character mention responses
│   │   └── character.py          # DEPRECATED (split into above)
│   ├── agents/              # Agent-based background workers
│   │   ├── __init__.py           # Public exports
│   │   ├── base.py               # BaseAgent class
│   │   ├── manager.py            # AgentManager
│   │   ├── discord_comm.py       # Discord communication layer
│   │   ├── bluesky_agent.py      # Bluesky integration
│   │   ├── tumblr_agent.py       # Tumblr integration
│   │   ├── supabase_event_agent.py  # Supabase events
│   │   └── character_engagement_agent.py  # Character engagement
│   ├── handlers/            # Legacy handlers (migration planned)
│   │   ├── upload_handler.py      # DEPRECATED - use UploadCapability
│   │   ├── command_handler.py     # DEPRECATED - use UploadCapability
│   │   └── notification_task.py   # Legacy (migration to Agent planned)
│   └── mcp/                  # MCP server implementation
│       ├── server.py         # FastMCP server setup
│       ├── models.py         # Pydantic models
│       └── tools/            # MCP tool implementations
│           ├── server_tools.py    # Server information tools
│           ├── message_tools.py   # Message management tools
│           ├── channel_tools.py   # Channel management tools
│           ├── event_tools.py     # Event management tools
│           └── role_tools.py      # Role management tools
├── data/                    # Persistent storage (SQLite DB)
├── config/                  # Configuration templates
├── Dockerfile               # Container definition
└── pyproject.toml          # Python dependencies
```

### Local Development

```bash
# Install dependencies
cd 03-apps/discord-bot
pip install -e .

# Run bot
python -m bot.main
```

## MCP Server Integration

The Discord bot includes an MCP (Model Context Protocol) server that exposes Discord management tools for AI assistants and programmatic access.

### Available MCP Tools

#### Server Information
- `list_servers` - List all Discord servers the bot is in
- `get_server_info` - Get detailed server information
- `get_channels` - List all channels in a server
- `list_members` - List server members with roles
- `get_user_info` - Get detailed user information

#### Message Management
- `send_message` - Send a message to a channel
- `read_messages` - Read recent message history
- `add_reaction` - Add a reaction emoji to a message
- `add_multiple_reactions` - Add multiple reactions
- `remove_reaction` - Remove a reaction
- `moderate_message` - Delete messages and timeout users

#### Channel Management
- `create_text_channel` - Create a new text channel
- `delete_channel` - Delete a channel
- `create_category` - Create a category channel
- `move_channel` - Move channel to different category

#### Event Management
- `create_scheduled_event` - Create a scheduled event (external, voice, or stage)
- `edit_scheduled_event` - Edit an existing scheduled event

#### Role Management
- `add_role` - Add a role to a user
- `remove_role` - Remove a role from a user

### MCP Server Endpoints

- `POST /mcp/tools/list` - List available MCP tools
- `POST /mcp/tools/call` - Execute an MCP tool

### Connecting to MCP Server

The MCP server runs on port 8001 (configurable via `MCP_PORT`). To connect:

1. **Open WebUI**: Configure MCP server URL as `http://localhost:8001/mcp`
2. **Claude Desktop**: Add to MCP settings:
   ```json
   {
     "mcpServers": {
       "discord-bot": {
         "url": "http://localhost:8001/mcp"
       }
     }
   }
   ```

### Disabling MCP Server

Set `MCP_ENABLED=false` in your `.env` file to disable the MCP server and run only the Discord bot.

## API Reference

### Immich API Endpoints Used

- `POST /api/asset/upload` - Upload asset
- `GET /api/person` - List people (filtered by name)
- `GET /api/person/{id}/thumbnail` - Get person thumbnail
- `GET /api/asset/{id}/faces` - Get face detections
- `GET /api/asset` - List assets (with `updatedAfter` filter)
- `GET /api/asset/{id}/thumbnail` - Get asset thumbnail

See [Immich API Documentation](https://immich.app/docs/api) for details.

## Testing

The Discord bot includes a comprehensive test suite that allows testing functionality without requiring a live Discord bot instance.

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (Discord mocks, Immich mocks, DB fixtures)
├── unit/                    # Unit tests with mocks
│   ├── test_database.py
│   ├── test_immich_client.py
│   ├── test_upload_capability.py
│   ├── test_claim_face_capability.py
│   ├── test_notification_task.py
│   └── test_utils.py
├── integration/            # Integration tests with real database
│   ├── test_upload_capability_flow.py
│   ├── test_claim_face_capability_flow.py
│   └── test_notification_flow.py
└── manual/                 # Manual testing utilities
    ├── test_immich_connection.py
    ├── test_discord_connection.py
    └── test_mcp_tools.py
```

### Running Tests

#### Unit Tests

```bash
cd 03-apps/discord-bot

# Run all unit tests
pytest tests/unit -v

# Run specific test file
pytest tests/unit/test_upload_capability.py -v

# Run with coverage
pytest --cov=bot --cov-report=html tests/unit
```

#### Integration Tests

```bash
# Run all integration tests
pytest tests/integration -v

# Run specific integration test
pytest tests/integration/test_upload_capability_flow.py -v
```

#### All Tests

```bash
# Run all tests
pytest tests/ -v

# Run with markers
pytest -m unit -v          # Only unit tests
pytest -m integration -v  # Only integration tests
```

### Manual Testing Utilities

These utilities can be run independently to test connectivity and functionality:

#### Test Immich Connection

```bash
# Test Immich API connectivity
python -m tests.manual.test_immich_connection

# Test with upload
python -m tests.manual.test_immich_connection --upload
```

#### Test Discord Connection

```bash
# Test Discord bot connectivity
python -m tests.manual.test_discord_connection
```

#### Test MCP Server

```bash
# Test MCP server endpoints (requires bot to be running)
python -m tests.manual.test_mcp_tools
```

### Validation Script

The validation script provides quick checks for configuration and connectivity:

```bash
# Validate configuration
python scripts/validate.py config

# Test Immich connection
python scripts/validate.py immich

# Test Discord connection
python scripts/validate.py discord

# Check database schema
python scripts/validate.py database

# Test MCP server
python scripts/validate.py mcp

# Run all validations
python scripts/validate.py all
```

### Testing Best Practices

1. **Run tests before committing**: Always run the test suite before committing changes
   ```bash
   pytest tests/ -v
   ```

2. **Test specific functionality**: When working on a feature, run relevant tests
   ```bash
   pytest tests/unit/test_upload_handler.py -v
   ```

3. **Use manual tests for connectivity**: Use manual testing utilities to verify external service connections

4. **Validate configuration**: Use the validation script to check configuration before starting the bot
   ```bash
   python scripts/validate.py all
   ```

5. **Check coverage**: Aim for >80% code coverage
   ```bash
   pytest --cov=bot --cov-report=term-missing tests/
   ```

### Writing New Tests

When adding new functionality, follow these patterns:

#### Unit Test Example

```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_new_feature(mock_discord_message, mock_immich_client):
    """Test new feature."""
    # Setup
    # ...

    # Execute
    result = await new_feature_function(mock_discord_message, mock_immich_client)

    # Assert
    assert result is not None
```

#### Integration Test Example

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_new_workflow(test_database, mock_discord_client):
    """Test complete workflow."""
    # Setup with real database
    # ...

    # Execute workflow
    # ...

    # Verify results
    # ...
```

### Test Fixtures

Common fixtures available in `conftest.py`:

- `mock_discord_client` - Mock Discord client
- `mock_discord_message` - Mock Discord message
- `mock_discord_attachment` - Mock Discord attachment
- `mock_discord_interaction` - Mock Discord interaction
- `mock_immich_client` - Mock Immich client
- `test_database` - Temporary test database
- `sample_immich_people` - Sample people data
- `sample_immich_asset` - Sample asset data

### Troubleshooting Tests

#### Tests Failing

1. Check that all dependencies are installed:
   ```bash
   pip install -e ".[dev]"
   ```

2. Verify environment variables are set (tests use defaults if not set)

3. Check test logs for specific error messages

#### Import Errors

If you see import errors, ensure you're running tests from the project root:
```bash
cd 03-apps/discord-bot
pytest tests/
```

#### Database Lock Errors

If you see SQLite lock errors, ensure tests are not running concurrently:
```bash
pytest tests/ -n 1  # Run tests sequentially
```

## License

Part of the local-ai-packaged infrastructure.
