# Imported n8n Workflows

This directory contains n8n workflows imported from various sources, organized by category.

## Directory Structure

- `gmail/` - Gmail and email-related workflows
- `youtube/` - YouTube video research and analysis workflows
- `research/` - Deep research and AI agent workflows
- `mixed/` - Workflows combining multiple categories

## Imported Workflows

### Gmail Workflows

#### nostr-damus-gmail-telegram.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Nostr #damus AI Powered Reporting with Gmail and Telegram integration
- **Required Credentials**:
  - Gmail (OAuth2)
  - Telegram Bot Token
  - OpenAI API Key (if using AI features)
- **Import Date**: 2025-01-05

#### wordpress-pdf-gmail-human-loop.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Easy WordPress Content Creation from PDF Docs with Human in the Loop Gmail
- **Required Credentials**:
  - Gmail (OAuth2)
  - WordPress API credentials
  - OpenAI API Key (for content generation)
- **Import Date**: 2025-01-05

### YouTube Workflows

#### youtube-comment-analysis-agent.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: YouTube Video Comment Analysis Agent
- **Required Credentials**:
  - YouTube Data API v3 Key
  - OpenAI API Key (for analysis)
- **Import Date**: 2025-01-05

#### monitor-youtube-channels-rss.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Monitor Favorite YouTube Channels Through RSS feeds and Receive Notifications
- **Required Credentials**:
  - RSS feeds (no credentials needed)
  - Notification service (e.g., Telegram, Email)
- **Import Date**: 2025-01-05

#### youtube-summarization-chatbot.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Ultimate AI-Powered Chatbot for YouTube Summarization & Analysis
- **Required Credentials**:
  - YouTube Data API v3 Key
  - OpenAI API Key
  - Vector database (e.g., Qdrant) for chat memory
- **Import Date**: 2025-01-05

#### youtube-video-summarization.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: AI-Powered YouTube Video Summarization & Analysis
- **Required Credentials**:
  - YouTube Data API v3 Key
  - OpenAI API Key
- **Import Date**: 2025-01-05

#### youtube-analyze-gemini.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Analyze YouTube Video for Summaries, Transcripts & Content with Google Gemini AI
- **Required Credentials**:
  - YouTube Data API v3 Key
  - Google Gemini API Key
- **Import Date**: 2025-01-05

### Research Workflows

#### tavily-researcher.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: The Ultimate Free AI-Powered Researcher with Tavily Web Search & Extract
- **Required Credentials**:
  - Tavily API Key
  - OpenAI API Key (optional, for summarization)
- **Import Date**: 2025-01-05

#### perplexity-research-html.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Perplexity Research to HTML AI-Powered Content Creation
- **Required Credentials**:
  - Perplexity API Key
  - OpenAI API Key (for content generation)
- **Import Date**: 2025-01-05

#### rag-chatbot-google-drive-qdrant.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: AI Powered RAG Chatbot for Your Docs with Google Drive, Gemini, and Qdrant
- **Required Credentials**:
  - Google Drive (OAuth2)
  - Google Gemini API Key
  - Qdrant connection (vector database)
- **Import Date**: 2025-01-05

#### web-search-chatbot-brave.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Build a Web Search Chatbot with GPT-4o and MCP Brave Search
- **Required Credentials**:
  - Brave Search API Key
  - OpenAI API Key (GPT-4o)
- **Import Date**: 2025-01-05

#### ai-chatbot-long-term-memory.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Empower Your AI Chatbot with Long-Term Memory and Dynamic Tool Routing
- **Required Credentials**:
  - OpenAI API Key
  - Database for memory storage (PostgreSQL recommended)
- **Import Date**: 2025-01-05

#### deepseek-agent-telegram-memory.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: DeepSeek AI Agent with Telegram and Long-Term Memory
- **Required Credentials**:
  - DeepSeek API Key
  - Telegram Bot Token
  - Database for memory storage
- **Import Date**: 2025-01-05

#### ai-agent-chatbot-memory-notes.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: AI Agent Chatbot with Long-Term Memory, Note Storage, and Telegram
- **Required Credentials**:
  - OpenAI API Key
  - Telegram Bot Token
  - Database for memory and notes storage
- **Import Date**: 2025-01-05

#### multi-ai-agent-supabase.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Multi-AI Agent Chatbot for Postgres Supabase DB and QuickCharts with Tool Router
- **Required Credentials**:
  - Supabase/PostgreSQL connection
  - OpenAI API Key
  - QuickCharts API (if used)
- **Import Date**: 2025-01-05

#### V1_Local_RAG_AI_Agent.json
- **Source**: Local repository (pre-existing)
- **Description**: Local RAG AI Agent using Ollama and Postgres
- **Required Credentials**:
  - Ollama API (local)
  - PostgreSQL connection
- **Import Date**: Pre-existing

#### V2_Local_Supabase_RAG_AI_Agent.json
- **Source**: Local repository (pre-existing)
- **Description**: Local Supabase RAG AI Agent
- **Required Credentials**:
  - Ollama API (local)
  - Supabase/PostgreSQL connection
- **Import Date**: Pre-existing

#### V3_Local_Agentic_RAG_AI_Agent.json
- **Source**: Local repository (pre-existing)
- **Description**: Local Agentic RAG AI Agent
- **Required Credentials**:
  - Ollama API (local)
  - Supabase/PostgreSQL connection
- **Import Date**: Pre-existing

### Mixed Category Workflows

#### social-media-content-creation.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Automate Multi-Platform Social Media Content Creation with AI
- **Required Credentials**:
  - Social media platform APIs (Twitter, LinkedIn, Facebook, etc.)
  - OpenAI API Key
- **Import Date**: 2025-01-05

#### audio-transcribe-summarize-drive.json
- **Source**: workflowsdiy/n8n-workflows
- **Description**: Use OpenAI to Transcribe Audio, Summarize with AI, and Save to Google Drive
- **Required Credentials**:
  - OpenAI API Key
  - Google Drive (OAuth2)
- **Import Date**: 2025-01-05

#### tech-daily-digest.json
- **Source**: duthaho/n8n-workflows
- **Description**: Tech daily digest with AI-powered summaries
- **Required Credentials**:
  - RSS feeds or news APIs
  - OpenAI API Key (for summarization)
  - Email service (for delivery)
- **Import Date**: 2025-01-05

#### daily-newsletter-aggregator.json
- **Source**: duthaho/n8n-workflows
- **Description**: Daily newsletter aggregator
- **Required Credentials**:
  - RSS feeds or content sources
  - Email service (SMTP or service API)
- **Import Date**: 2025-01-05

## n8n.io Official Templates (Manual Download Required)

The following templates from n8n.io need to be manually downloaded and imported:

1. **Classify YouTube Videos & Generate Email Summaries with GPT-4 and Gmail** (Template ID: 9616)
   - URL: https://n8n.io/workflows/9616-classify-youtube-videos-and-generate-email-summaries-with-gpt-4-and-gmail/
   - Category: YouTube + Gmail
   - Description: Monitors YouTube channels, classifies videos as viral (≥1000 likes) or normal, generates summaries with GPT-4, and sends via Gmail
   - **To Import**: Visit the URL, click "Use for free", then "Copy template to clipboard (JSON)", and save to `youtube/classify-youtube-videos-gmail-summaries.json`

2. **Analyze YouTube Channels & Send Performance Reports with GPT-4o-mini and Gmail** (Template ID: 8167)
   - URL: https://n8n.io/workflows/8167-analyze-youtube-channels-and-send-performance-reports-with-gpt-4o-mini-and-gmail/
   - Category: YouTube + Gmail
   - Description: Automates YouTube channel analysis, generates key metrics, and sends reports via email
   - **To Import**: Visit the URL, click "Use for free", then "Copy template to clipboard (JSON)", and save to `youtube/analyze-youtube-channels-reports.json`

3. **Track Social Media Growth and Weekly Reports with X API, YouTube API, and Gmail** (Template ID: 9718)
   - URL: https://n8n.io/workflows/9718-track-social-media-growth-and-weekly-reports-with-x-api-youtube-api-and-gmail/
   - Category: Mixed (Social Media + YouTube + Gmail)
   - Description: Monitors social media growth and sends automated weekly summary emails via Gmail
   - **To Import**: Visit the URL, click "Use for free", then "Copy template to clipboard (JSON)", and save to `mixed/social-media-growth-reports.json`

## Import Instructions

### Automatic Import (via Docker)

The workflows in this directory are automatically imported when the `n8n-import` container runs:

```bash
# The import happens automatically when starting the apps stack
python start_services.py --stack apps
```

The import command used is:
```bash
n8n import:workflow --separate --input=/backup/workflows
```

This will recursively import all JSON files from subdirectories.

### Manual Import

1. Access your n8n instance
2. Go to Workflows → Import from File
3. Select the desired workflow JSON file
4. Configure credentials as needed
5. Save and activate the workflow

## Configuration Notes

- **Credentials**: Most workflows require API keys or OAuth credentials. Configure these in n8n's Credentials section before activating workflows.
- **Environment Variables**: Some workflows may reference environment variables. Ensure these are set in your `.env` file or n8n environment.
- **Database Connections**: Workflows using databases (PostgreSQL, Supabase) will use the connection configured in your n8n instance.
- **Local Services**: Workflows using local services (Ollama, Qdrant) should reference container names (e.g., `ollama:11434`, `qdrant:6333`).

## Sources

- **workflowsdiy/n8n-workflows**: https://github.com/workflowsdiy/n8n-workflows
- **duthaho/n8n-workflows**: https://github.com/duthaho/n8n-workflows
- **n8n.io Templates**: https://n8n.io/workflows/

## Last Updated

2025-01-05
