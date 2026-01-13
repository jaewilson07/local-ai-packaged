# Service Samples

This directory contains example scripts demonstrating the core functionality of all major services in the local-ai-packaged project. These samples are designed to be educational, self-contained, and demonstrate real-world use cases.

## Overview

The samples are organized by service type:

- **RAG Services**: MongoDB RAG, Graphiti RAG, Crawl4AI RAG
- **Major Services**: Calendar, Conversation, Persona, N8N Workflow, Open WebUI, Neo4j

Each sample includes:
- Clear documentation explaining what it does
- Prerequisites and setup instructions
- Error handling and cleanup
- Real-world use cases relevant to the project goals

## Prerequisites

Before running any samples, ensure:

1. **Dependencies installed**: Install all required dependencies:
   ```bash
   # Using the setup script (recommended - installs CLIs and Python dependencies)
   python setup/install_clis.py

   # Or manually install just Python dependencies
   cd 04-lambda && uv pip install -e ".[test,samples]"

   # For Graphiti samples, also install graphiti dependencies:
   cd 04-lambda && uv pip install -e ".[test,samples,graphiti]"
   ```

   Required dependencies include:
   - `pydantic-ai` - For agent tools and RunContext
   - `neo4j` - For Neo4j graph database operations
   - `requests` - For API verification helpers
   - `pymongo` - For MongoDB operations
   - And many others (see `04-lambda/pyproject.toml`)

2. **Services are running**: MongoDB, Neo4j, Ollama, N8N (as needed)
3. **Environment variables configured**: See `.env` or Infisical for required variables
4. **Python path**: Samples automatically add the project to `sys.path`
5. **Authentication**: For scripts making HTTP API calls, see [Authentication](#authentication) section below

## RAG Services

### MongoDB RAG

MongoDB RAG provides enhanced Retrieval-Augmented Generation with vector search, memory tools, and advanced query processing.

#### `mongo_rag/semantic_search_example.py`
Demonstrates pure semantic (vector) search over documents stored in MongoDB.

**Features:**
- Vector similarity search using MongoDB Atlas
- Document retrieval with similarity scores
- Source tracking and metadata

**Prerequisites:**
- MongoDB running with vector search index
- Documents ingested (use `document_ingestion_example.py`)

#### `mongo_rag/hybrid_search_example.py`
Demonstrates hybrid search combining semantic and text search using Reciprocal Rank Fusion (RRF).

**Features:**
- Semantic search (vector similarity)
- Text search (keyword matching)
- Hybrid search (combines both with RRF)
- Comparison of search strategies

**Prerequisites:**
- MongoDB running with vector search index
- Documents ingested

#### `mongo_rag/document_ingestion_example.py`
Demonstrates ingesting documents (PDF, Markdown, etc.) into MongoDB for vector search.

**Features:**
- Automatic document conversion (PDF, Word, etc. to Markdown)
- Intelligent chunking with configurable size and overlap
- Embedding generation and storage
- Support for multiple formats (PDF, Word, PowerPoint, Excel, HTML, Markdown, Text)

**Prerequisites:**
- MongoDB running
- Documents folder with files to ingest

#### `mongo_rag/memory_tools_example.py`
Demonstrates MongoDB RAG's memory tools for persistent conversation context and knowledge storage.

**Features:**
- Store and retrieve conversation messages
- Store and search facts
- Store web content for later retrieval
- Get context windows for conversations

**Prerequisites:**
- MongoDB running

#### `mongo_rag/enhanced_rag_example.py`
Demonstrates advanced RAG capabilities including query decomposition, document grading, and citation extraction.

**Features:**
- Query decomposition (breaking complex queries into sub-queries)
- Document grading (filtering irrelevant documents using LLM)
- Citation extraction (identifying sources for answers)
- Result synthesis (combining results from multiple queries)
- Query rewriting (improving query quality)

**Prerequisites:**
- MongoDB running with documents ingested
- LLM available (Ollama or OpenAI)

### Graphiti RAG

Graphiti RAG provides knowledge graph search, repository parsing, and AI script validation using Neo4j.

#### `graphiti_rag/knowledge_graph_search_example.py`
Demonstrates searching the Graphiti knowledge graph for entities and relationships.

**Features:**
- Hybrid search (semantic + keyword + graph traversal)
- Entity and relationship discovery
- Similarity scoring

**Prerequisites:**
- Graphiti configured (USE_GRAPHITI=true)
- Neo4j running
- Knowledge graph populated (use `repository_parsing_example.py`)

#### `graphiti_rag/repository_parsing_example.py`
Demonstrates parsing a GitHub repository into the Neo4j knowledge graph.

**Features:**
- Extracts code structure (classes, methods, functions)
- Creates nodes and relationships in Neo4j
- Enables hallucination detection

**Prerequisites:**
- Neo4j running (USE_KNOWLEDGE_GRAPH=true)
- GitHub repository URL (must end with .git)

#### `graphiti_rag/script_validation_example.py`
Demonstrates validating AI-generated Python scripts against the knowledge graph to detect hallucinations.

**Features:**
- Validates import statements
- Checks method calls and class instantiations
- Detects non-existent functions and incorrect signatures
- Generates hallucination reports

**Prerequisites:**
- Neo4j running with knowledge graph populated
- Python script to validate

#### `graphiti_rag/cypher_query_example.py`
Demonstrates querying the Neo4j knowledge graph using Cypher queries.

**Features:**
- List repositories
- Explore repository statistics
- Execute custom Cypher queries
- Query code structure patterns

**Prerequisites:**
- Neo4j running with knowledge graph populated

### Crawl4AI RAG

Crawl4AI RAG provides automated web crawling with immediate ingestion into MongoDB RAG.

#### `crawl4ai_rag/single_page_crawl_example.py`
Demonstrates crawling a single web page and automatically ingesting it into MongoDB RAG.

**Features:**
- Crawls single URL
- Extracts content as markdown
- Automatic chunking and embedding
- Immediate searchability

**Prerequisites:**
- MongoDB running

#### `crawl4ai_rag/deep_crawl_example.py`
Demonstrates deep crawling of a website, following internal links recursively.

**Features:**
- Recursive crawling up to specified depth
- Domain and subdomain filtering
- Automatic ingestion of all discovered pages
- Concurrent crawling for performance

**Prerequisites:**
- MongoDB running

#### `crawl4ai_rag/adaptive_crawl_example.py`
Demonstrates adaptive crawling strategies that adjust parameters based on site characteristics.

**Features:**
- Shallow crawl to assess site structure
- Dynamic depth adjustment
- Domain filtering strategies
- Optimized chunk sizes

**Prerequisites:**
- MongoDB running

## Major Services

### Calendar

Calendar project provides Google Calendar integration with sync state tracking.

#### `calendar/create_event_example.py`
Demonstrates creating Google Calendar events with automatic sync state tracking.

**Features:**
- Create calendar events via Google Calendar API
- Automatic sync state tracking in MongoDB
- Duplicate prevention
- OAuth2 authentication

**Prerequisites:**
- MongoDB running
- Google Calendar OAuth2 credentials configured

#### `calendar/list_events_example.py`
Demonstrates listing and filtering Google Calendar events.

**Features:**
- List events by time range
- Filter by calendar ID
- Format event data for display

**Prerequisites:**
- MongoDB running
- Google Calendar OAuth2 credentials configured

#### `calendar/sync_state_example.py`
Demonstrates how sync state tracking prevents duplicate events.

**Features:**
- Check sync state for existing events
- Create and update sync state
- Demonstrate duplicate prevention logic

**Prerequisites:**
- MongoDB running

### Conversation

Conversation project provides multi-agent orchestration for context-aware responses.

#### `conversation/orchestration_example.py`
Demonstrates conversation orchestration coordinating multiple agents and tools.

**Features:**
- Gets persona voice instructions
- Plans response using available tools
- Executes tools (search, memory, calendar)
- Generates context-aware response
- Records interaction for persona state

**Prerequisites:**
- MongoDB running
- Ollama or OpenAI configured

#### `conversation/multi_agent_example.py`
Demonstrates multi-agent coordination for complex queries requiring multiple services.

**Features:**
- Coordinates persona, memory, knowledge, and calendar agents
- Handles complex multi-part queries
- Synthesizes responses from multiple sources

**Prerequisites:**
- MongoDB running
- Ollama or OpenAI configured

### Persona

Persona project manages character/persona state and generates dynamic voice instructions.

#### `persona/mood_tracking_example.py`
Demonstrates tracking and analyzing mood state from conversations.

**Features:**
- LLM-based mood analysis
- Tracks primary emotion and intensity
- Updates persona mood state in MongoDB

**Prerequisites:**
- MongoDB running
- Ollama or OpenAI configured

#### `persona/voice_instructions_example.py`
Demonstrates generating dynamic voice instructions based on persona state.

**Features:**
- Generates style instructions from current state
- Incorporates mood, relationship, and context
- Guides persona response style

**Prerequisites:**
- MongoDB running
- Ollama or OpenAI configured

#### `persona/relationship_management_example.py`
Demonstrates tracking and managing relationship state between users and personas.

**Features:**
- Tracks affection and trust levels
- Analyzes relationship dynamics
- Updates relationship state in MongoDB

**Prerequisites:**
- MongoDB running
- Ollama or OpenAI configured

### N8N Workflow

N8N Workflow project provides agentic workflow management with RAG-enhanced creation.

#### `n8n_workflow/create_workflow_example.py`
Demonstrates creating an N8N workflow with RAG-enhanced design.

**Features:**
- Creates workflows with nodes and connections
- Searches knowledge base for best practices
- Discovers available nodes via N8N API

**Prerequisites:**
- N8N running and accessible
- MongoDB running (for RAG knowledge base)

#### `n8n_workflow/execute_workflow_example.py`
Demonstrates executing an N8N workflow with input data.

**Features:**
- Executes workflows programmatically
- Passes input data to workflows
- Returns execution results

**Prerequisites:**
- N8N running and accessible
- Existing workflow ID

#### `n8n_workflow/rag_enhanced_workflow_example.py`
Demonstrates RAG-enhanced workflow creation using knowledge base search.

**Features:**
- Searches knowledge base for workflow patterns
- Discovers available nodes
- Finds node configuration examples
- Creates informed workflows

**Prerequisites:**
- N8N running and accessible
- MongoDB running (for RAG knowledge base)

### Open WebUI

Open WebUI projects enable exporting conversations and classifying topics.

#### `openwebui/export_conversation_example.py`
Demonstrates exporting Open WebUI conversations to MongoDB RAG.

**Features:**
- Exports conversations to MongoDB
- Chunks conversations for semantic search
- Generates embeddings
- Preserves metadata (ID, title, topics)

**Prerequisites:**
- MongoDB running
- Ollama or OpenAI configured (for embeddings)

#### `openwebui/topic_classification_example.py`
Demonstrates classifying topics for conversations using LLM-based analysis.

**Features:**
- Analyzes conversation content
- Identifies 3-5 main topics
- Provides reasoning for classification

**Prerequisites:**
- Ollama or OpenAI configured

### Neo4j

Neo4j samples demonstrate basic graph database operations.

#### `neo4j/basic_cypher_example.py`
Demonstrates basic Cypher query operations using Neo4j directly.

**Features:**
- Creating nodes and relationships
- Querying nodes and relationships
- Updating and deleting data

**Prerequisites:**
- Neo4j running and configured

#### `neo4j/knowledge_graph_example.py`
Demonstrates building a knowledge graph in Neo4j with entities and relationships.

**Features:**
- Creating entities with properties
- Creating relationships between entities
- Querying graph patterns
- Traversing relationships

**Prerequisites:**
- Neo4j running and configured

## Authentication

Sample scripts that make HTTP API calls use Cloudflare Zero Trust authentication. The authentication system supports two access patterns:

### Internal Network Access (Local Development)

When running scripts locally, they default to using internal network URLs (`http://lambda-server:8000`) which **bypass Cloudflare Access authentication** (network isolation provides security):

```python
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers

# Defaults to http://lambda-server:8000 when running locally
api_base_url = get_api_base_url()

# Returns empty headers for internal network (no auth required)
headers = get_auth_headers()
```

**Benefits**:
- No JWT token required
- Works seamlessly in local development
- Faster (no external network calls)

### External Network Access (Production)

For external URLs (`https://api.datacrew.space`), scripts require a Cloudflare Access JWT token:

```bash
# Set external API URL
export API_BASE_URL=https://api.datacrew.space

# Get JWT token from browser DevTools (Cf-Access-Jwt-Assertion header)
export CF_ACCESS_JWT=your-jwt-token-here
```

**Getting a JWT Token**:
1. Access your application through Cloudflare Access
2. Open browser DevTools (F12)
3. Go to Network tab
4. Make a request to any endpoint
5. Look for the `Cf-Access-Jwt-Assertion` header in the request
6. Copy that value and set it as `CF_ACCESS_JWT`

### User Identification

All scripts automatically load `CLOUDFLARE_EMAIL` from your `.env` file for user identification:

```bash
# In your .env file
CLOUDFLARE_EMAIL=your-email@example.com
```

The shared authentication helpers (`sample/shared/auth_helpers.py`) automatically:
- Load `.env` from project root
- Provide `get_cloudflare_email()` for user identification
- Handle internal vs external URL detection
- Generate appropriate authentication headers

**Reference**: See [sample/shared/auth_helpers.py](sample/shared/auth_helpers.py) for complete implementation details.

## Running Samples

### Basic Usage

```bash
# Navigate to sample directory
cd sample/<service>/<sample>

# Run the sample
python <sample_name>.py
```

### Example

```bash
# Run MongoDB RAG semantic search example
cd sample/mongo_rag
python semantic_search_example.py
```

### Authentication

All sample scripts that make HTTP API calls should use the shared authentication helpers from `sample/shared/auth_helpers.py`:

```python
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers, get_cloudflare_email

# Get API base URL (defaults to internal network for local development)
api_base_url = get_api_base_url()

# Get authentication headers (empty for internal, JWT for external)
headers = get_auth_headers()

# Get user email for identification
cloudflare_email = get_cloudflare_email()
```

**Key Points**:
- **Internal Network** (`http://lambda-server:8000`): No authentication required (network isolation provides security)
- **External Network** (`https://api.datacrew.space`): Requires Cloudflare Access JWT token in `Cf-Access-Jwt-Assertion` header
- **CLOUDFLARE_EMAIL**: Automatically loaded from `.env` file in project root for user identification
- **Default Behavior**: Scripts default to internal network URLs when running locally, allowing seamless local development without JWT tokens

**Available Helper Functions**:
- `get_cloudflare_email()` - Get `CLOUDFLARE_EMAIL` from environment variables
- `get_api_base_url()` - Get API base URL (defaults to internal network)
- `get_auth_headers()` - Get authentication headers (handles internal vs external URLs automatically)
- `require_cloudflare_email()` - Require and validate `CLOUDFLARE_EMAIL` is set
- `is_internal_url()` - Check if URL is internal (bypasses authentication)

**Example Usage**:
```python
import requests
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers

api_base_url = get_api_base_url()
headers = get_auth_headers()

response = requests.get(
    f"{api_base_url}/api/v1/comfyui/loras",
    headers=headers
)
```

**Reference**: See [sample/shared/auth_helpers.py](sample/shared/auth_helpers.py) for complete implementation and [AGENTS.md](../AGENTS.md) for detailed authentication patterns.

### Environment Setup

Most samples require environment variables. Ensure your `.env` file or Infisical is configured with:

- `MONGODB_URI`: MongoDB connection string
- `NEO4J_URI`: Neo4j connection string
- `NEO4J_USER`: Neo4j username
- `NEO4J_PASSWORD`: Neo4j password
- `LLM_BASE_URL`: LLM API base URL (e.g., Ollama)
- `EMBEDDING_BASE_URL`: Embedding API base URL
- `LLM_MODEL`: LLM model name
- `EMBEDDING_MODEL`: Embedding model name
- `N8N_API_URL`: N8N API URL
- `N8N_API_KEY`: N8N API key (if required)
- `GOOGLE_CALENDAR_CREDENTIALS_PATH`: Path to Google Calendar OAuth2 credentials
- `CLOUDFLARE_EMAIL`: Your Cloudflare Access email (for authenticated API calls)
- `CF_ACCESS_JWT`: Cloudflare Access JWT token (only needed for external API calls)
- `CLOUDFLARE_EMAIL`: Your Cloudflare email for user identification (automatically loaded by sample scripts)
- `API_BASE_URL`: API base URL (defaults to `http://lambda-server:8000` for internal network)
- `CF_ACCESS_JWT`: Cloudflare Access JWT token (required only for external URLs)

## Sample Structure

All samples follow a consistent structure:

1. **Imports**: Project imports with path setup
2. **Configuration**: Logging and environment setup
3. **Main Function**: Async main function with example logic
4. **Error Handling**: Try/except with cleanup
5. **Documentation**: Clear docstrings and comments

## Integration Examples

Samples can be combined to demonstrate end-to-end workflows:

1. **Document Q&A Pipeline**:
   - `crawl4ai_rag/single_page_crawl_example.py` → Crawl documentation
   - `mongo_rag/document_ingestion_example.py` → Ingest documents
   - `mongo_rag/hybrid_search_example.py` → Search documents
   - `mongo_rag/enhanced_rag_example.py` → Get enhanced answers

2. **Conversation Memory Pipeline**:
   - `openwebui/export_conversation_example.py` → Export conversation
   - `mongo_rag/memory_tools_example.py` → Store in memory
   - `conversation/orchestration_example.py` → Use in orchestration

3. **Code Analysis Pipeline**:
   - `graphiti_rag/repository_parsing_example.py` → Parse repository
   - `graphiti_rag/cypher_query_example.py` → Query structure
   - `graphiti_rag/script_validation_example.py` → Validate scripts

## Validation

All samples include validation to ensure they work correctly. Validation is performed through multiple mechanisms:

### 1. Exit Code Validation

Each sample should exit with code 0 on success, non-zero on failure:
- **Success**: Exit code 0 indicates the sample completed successfully
- **Failure**: Exit code 1 (or exception) indicates the sample failed

### 2. Verification Helpers

Many samples use verification helpers from `sample/shared/verification_helpers.py`:

- **`verify_search_results()`**: Validates search results are returned (for samples that don't create persistent data)
- **`verify_rag_data()`**: Validates RAG data via `/api/me/data/rag` endpoint (documents, chunks, sources, workflows)
- **`verify_calendar_data()`**: Validates calendar events via `/api/me/data/calendar` endpoint
- **`verify_neo4j_data()`**: Validates Neo4j nodes/relationships via `/api/v1/data/neo4j` endpoint
- **`verify_mongodb_data()`**: Validates MongoDB documents via `/api/v1/data/mongodb` endpoint
- **`verify_supabase_data()`**: Validates Supabase tables via `/api/v1/data/supabase` endpoint
- **`verify_storage_data()`**: Validates MinIO storage files via `/api/v1/data/storage` endpoint
- **`verify_loras_data()`**: Validates ComfyUI LoRA models via `/api/me/data/loras` endpoint

All verification helpers:
- Support retry logic (3 retries with 2s delay) for eventual consistency
- Return `(success: bool, message: str)` tuples
- Handle authentication automatically (internal vs external URLs)
- Provide clear success/failure messages

### 3. API Verification

Samples that create persistent data verify via REST API:

- **Internal Network**: `http://lambda-server:8000` (no authentication required)
- **External Network**: `https://api.datacrew.space` (requires Cloudflare Access JWT)

Verification functions automatically:
- Detect internal vs external URLs
- Handle authentication headers
- Retry on transient failures
- Validate data structure and counts

### 4. Result Validation

Samples validate their own results:

- **Structure Validation**: Check that results have expected fields and structure
- **Count Validation**: Verify minimum expected counts are met
- **Content Validation**: Ensure data content matches expectations
- **State Validation**: Confirm operations completed successfully (create, update, delete)

### 5. Error Handling

All samples include comprehensive error handling:

- **Try/Except Blocks**: Catch and handle exceptions gracefully
- **Cleanup**: Ensure proper cleanup in finally blocks (close connections, cleanup resources)
- **Logging**: Log errors with context for debugging
- **User-Friendly Messages**: Provide clear error messages explaining what went wrong

### Running All Samples

Use `scripts/run_all_samples.py` to run and validate all samples:

```bash
# Run all samples
python scripts/run_all_samples.py

# Run with verbose output
python scripts/run_all_samples.py --verbose

# Run only specific samples (filter by pattern)
python scripts/run_all_samples.py --filter calendar

# Run with longer timeout and continue on errors
python scripts/run_all_samples.py --timeout 600 --continue-on-error
```

The script will:
- Discover all Python sample files
- Execute each sample with timeout protection
- Report success/failure for each sample
- Provide a summary with pass/fail counts
- Show validation results and error messages

### Validation Documentation

Each sample includes validation documentation in its docstring explaining:
- What validation is performed
- How results are verified
- What causes validation to fail
- How to interpret validation results

See individual sample files for detailed validation documentation.

## Notes

- Samples are designed to be educational and demonstrate best practices
- All samples include error handling and cleanup
- Samples use async/await patterns consistent with the project
- Each sample is self-contained but can be combined for complex workflows
- Samples demonstrate real use cases from the project's AGENTS.md files
- All samples include validation to ensure they work correctly

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the correct directory and Python path is set
2. **Connection Errors**: Verify services are running (MongoDB, Neo4j, Ollama, etc.)
3. **Environment Variables**: Check `.env` file or Infisical configuration
4. **Missing Dependencies**: Run `uv pip install -e ".[test]"` in `04-lambda/` directory

### Getting Help

- Check service-specific AGENTS.md files for detailed documentation
- Review sample code comments for implementation details
- Check service logs for detailed error messages

## Contributing

When adding new samples:

1. Follow the existing sample structure
2. Include comprehensive docstrings
3. Add error handling and cleanup
4. Document prerequisites clearly
5. Update this README with sample description
