# Discord Character Bot

Discord bot that enables AI characters with distinct personalities to interact in Discord channels. Characters can be added to channels, respond to mentions, and occasionally engage in conversations spontaneously.

## Features

- **Character Management**: Add, remove, and list AI characters in channels
- **Direct Mentions**: Characters respond when mentioned by name
- **Random Engagement**: Characters may spontaneously join conversations (15% probability)
- **Personality Integration**: Uses persona service for character definitions
- **Conversation History**: Maintains separate history per channel+character
- **Rich Embeds**: Responses displayed as Discord embeds with character avatars

## Architecture

- **Stack**: `03-apps` (application layer)
- **Container**: `discord-character-bot`
- **Network**: `ai-network` (shared Docker network)
- **Storage**: MongoDB (via Lambda API)

## Setup

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**
3. Give it a name (e.g., "Character Bot")
4. Go to **Bot** section
5. Click **Create Bot**
6. Copy the **Token** (this is your `DISCORD_BOT_TOKEN`)
7. Under **Privileged Gateway Intents**, enable:
   - ✅ **MESSAGE CONTENT INTENT** (required to read message content)
8. Save changes

### 2. Invite Bot to Server

1. In Discord Developer Portal, go to **OAuth2** → **URL Generator**
2. Select scopes:
   - `bot`
   - `applications.commands` (for slash commands)
3. Select bot permissions:
   - Send Messages
   - Read Messages/View Channels
   - Use Slash Commands
   - Embed Links
4. Copy the generated URL and open it in a browser
5. Select your server and authorize

### 3. Configure Environment Variables

Add to `.env` file:

```bash
DISCORD_BOT_TOKEN=your_discord_bot_token_here
LAMBDA_API_URL=http://lambda:8000
LAMBDA_API_KEY=optional_api_key
MAX_CHARACTERS_PER_CHANNEL=5
ENGAGEMENT_PROBABILITY=0.15
ENGAGEMENT_CHECK_INTERVAL=60
```

## Starting the Bot

The bot is part of the `apps` stack and will start automatically:

```bash
# Start apps stack (includes Discord character bot)
python start_services.py --stack apps

# Or start all stacks
python start_services.py --profile cpu
```

## Usage

### Commands

#### `/add_character name:<character_name>`
Adds an AI character to the current channel. The character must exist in the persona service.

**Example:**
```
/add_character name:athena
```

#### `/remove_character name:<character_name>`
Removes a character from the current channel and clears its conversation history.

**Example:**
```
/remove_character name:athena
```

#### `/list_characters`
Lists all active characters in the current channel with their names and descriptions.

#### `/clear_history [character:<name>]`
Clears conversation history for the channel. Optionally specify a character to clear only that character's history.

**Examples:**
```
/clear_history
/clear_history character:athena
```

### Chat Interactions

#### Direct Mentions
Mention a character by name to get a response:

```
@Athena, what's your opinion on courage?
```

The bot will detect the mention and generate a response in character.

#### Random Engagement
Characters may spontaneously join conversations with a 15% probability (configurable). The bot monitors channels and triggers engagement when appropriate.

## Project Structure

```
discord-character-bot/
├── bot/
│   ├── main.py                    # Bot entry point
│   ├── config.py                  # Configuration
│   ├── api_client.py              # HTTP client for Lambda API
│   └── handlers/
│       ├── command_handler.py     # Slash command handlers
│       ├── message_handler.py     # Message mention detection
│       └── engagement_task.py    # Background engagement task
├── data/                          # Local state (if needed)
├── config/                        # Configuration templates
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Development

### Local Development

```bash
# Install dependencies
cd 03-apps/discord-character-bot
pip install -e .

# Run bot
python -m bot.main
```

## Troubleshooting

### Bot Not Responding

1. Check bot is running: `docker compose -p localai-apps ps discord-character-bot`
2. Check logs: `docker compose -p localai-apps logs -f discord-character-bot`
3. Verify environment variables are set correctly
4. Check Lambda API is accessible: `curl http://lambda:8000/api/v1/health`

### Characters Not Responding

1. Verify character exists in persona service
2. Check character is added to channel: `/list_characters`
3. Check bot logs for API errors
4. Verify Lambda API is running and accessible

### Commands Not Appearing

- Commands may take up to an hour to propagate globally
- For faster testing, restart the bot or use guild-specific commands

## API Integration

The bot communicates with Lambda services via HTTP:

- `POST /api/v1/discord/characters/add` - Add character
- `POST /api/v1/discord/characters/remove` - Remove character
- `GET /api/v1/discord/characters/list` - List characters
- `POST /api/v1/discord/characters/chat` - Generate response
- `POST /api/v1/discord/characters/engage` - Check engagement

## License

Part of the local-ai-packaged infrastructure.
