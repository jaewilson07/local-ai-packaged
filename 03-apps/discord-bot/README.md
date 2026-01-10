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

### 4. Get Channel ID

1. In Discord, enable **Developer Mode**:
   - User Settings → Advanced → Developer Mode
2. Right-click on the `#event-uploads` channel
3. Click **Copy ID**
4. Add to `.env` file as `DISCORD_UPLOAD_CHANNEL_ID`

### 5. Configure Environment Variables

Copy `config/.env.example` to your root `.env` file and fill in:

```bash
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_UPLOAD_CHANNEL_ID=your_channel_id_here
IMMICH_API_KEY=your_immich_api_key_here
IMMICH_SERVER_URL=http://immich-server:2283

# Optional: MCP Server Configuration
MCP_ENABLED=true
MCP_PORT=8001
MCP_HOST=0.0.0.0
```

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

1. Upload a file (jpg, png, mp4, mov) to the `#event-uploads` channel
2. Bot will automatically:
   - Download the file
   - Upload it to Immich
   - Set description: "Uploaded by [YourName]"
   - Reply with confirmation

**Note**: Files larger than 25MB (Discord limit) will be rejected with an error message.

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
│   ├── utils.py             # Utility functions
│   ├── handlers/
│   │   ├── upload_handler.py      # File upload handling
│   │   ├── command_handler.py     # Slash commands
│   │   └── notification_task.py   # Background polling
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

## License

Part of the local-ai-packaged infrastructure.
