"""FastAPI application for Lambda multi-project server."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from server.config import settings
from server.core.logging import setup_logging

# Setup structured logging
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Setup FastMCP server first (needed for lifespan)
from contextlib import asynccontextmanager

from server.mcp.fastmcp_server import mcp

# Create ASGI app from MCP server
# Mount at "/mcp" with path='/' gives endpoint at /mcp/
mcp_app = mcp.http_app(path="/")


# Combine MCP lifespan with our startup/shutdown logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("lambda_server_started", extra={"version": "1.0.0"})

    # Generate MCP server modules for code execution
    from pathlib import Path

    from server.mcp.codegen import generate_all_servers

    servers_dir = Path(__file__).parent / "mcp" / "servers"
    generate_all_servers(servers_dir)
    logger.info("mcp_code_generation_complete", extra={"servers_dir": str(servers_dir)})

    # Validate database schema and apply migrations if needed
    try:
        from src.services.database.supabase import DatabaseValidator, SupabaseConfig

        supabase_config = SupabaseConfig()
        validation_service = DatabaseValidator(supabase_config)
        # Path from: 04-lambda/server/main.py to: 01-data/supabase/migrations
        project_root = Path(__file__).parent.parent.parent
        migrations_dir = project_root / "01-data" / "supabase" / "migrations"

        # First validate core tables
        validation_result = await validation_service.validate_core_tables()

        if not validation_result.all_exist:
            logger.warning(
                f"Core tables missing: {validation_result.missing_tables}. Applying migrations..."
            )
            # Apply migrations
            migration_result = await validation_service.apply_all_migrations(migrations_dir)
            if not migration_result.success:
                logger.error(
                    f"Failed to apply migrations. Failed: {migration_result.failed_migrations}"
                )
            else:
                logger.info(
                    f"Applied {len(migration_result.applied_migrations)} migrations successfully"
                )
        else:
            logger.info("Database schema validation passed - all core tables exist")

        # Store service for cleanup
        app.state.db_validation_service = validation_service
    except Exception:
        logger.exception("Database validation error during startup")
        # Don't fail startup - let requests handle the error

    # Run MCP lifespan startup
    async with mcp_app.lifespan(app):
        yield

    # Shutdown
    # Cleanup database validation service
    if hasattr(app.state, "db_validation_service"):
        await app.state.db_validation_service.close()

    logger.info("lambda_server_shutdown")


# Create FastAPI app with combined lifespan
# Disable default docs to use custom dark mode version
app = FastAPI(
    title="Lambda Server",
    description="Multi-project FastAPI server with MCP and REST APIs",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable default docs
    redoc_url="/redoc",  # Keep ReDoc at default location
)


# Custom Swagger UI with dark mode
# Note: FastAPI's get_swagger_ui_html() doesn't support custom_head_html parameter,
# so we return a fully custom HTML response with dark mode CSS/JS embedded
SWAGGER_DARK_MODE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{title} - API Docs</title>
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <link rel="icon" type="image/png" href="https://fastapi.tiangolo.com/img/favicon.png">
    <style>
        /* Dark mode styles - applied by default */
        :root {{
            --dark-bg: #1a1a2e;
            --dark-bg-secondary: #16213e;
            --dark-bg-tertiary: #0f3460;
            --dark-text: #e8e8e8;
            --dark-text-secondary: #b8b8b8;
            --dark-border: #3a3a5c;
            --dark-accent: #4fc3f7;
            --dark-success: #4caf50;
            --dark-warning: #ff9800;
            --dark-error: #f44336;
            --dark-info: #2196f3;
        }}

        body.dark-mode {{
            background-color: var(--dark-bg) !important;
        }}

        body.dark-mode .swagger-ui {{
            background-color: var(--dark-bg) !important;
        }}

        body.dark-mode .swagger-ui .topbar {{
            background-color: var(--dark-bg-secondary) !important;
        }}

        body.dark-mode .swagger-ui .info .title,
        body.dark-mode .swagger-ui .info .description,
        body.dark-mode .swagger-ui .info h1,
        body.dark-mode .swagger-ui .info h2,
        body.dark-mode .swagger-ui .info h3,
        body.dark-mode .swagger-ui .info p,
        body.dark-mode .swagger-ui .info li {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .opblock-tag {{
            color: var(--dark-text) !important;
            border-color: var(--dark-border) !important;
        }}

        body.dark-mode .swagger-ui .opblock-tag:hover {{
            background-color: var(--dark-bg-tertiary) !important;
        }}

        body.dark-mode .swagger-ui .opblock {{
            background-color: var(--dark-bg-secondary) !important;
            border-color: var(--dark-border) !important;
        }}

        body.dark-mode .swagger-ui .opblock .opblock-summary {{
            border-color: var(--dark-border) !important;
        }}

        body.dark-mode .swagger-ui .opblock .opblock-summary-description {{
            color: var(--dark-text-secondary) !important;
        }}

        body.dark-mode .swagger-ui .opblock .opblock-summary-path,
        body.dark-mode .swagger-ui .opblock .opblock-summary-path__deprecated {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .opblock-body pre.microlight {{
            background-color: var(--dark-bg) !important;
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .opblock-section-header {{
            background-color: var(--dark-bg-tertiary) !important;
        }}

        body.dark-mode .swagger-ui .opblock-section-header h4 {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui table thead tr th,
        body.dark-mode .swagger-ui table thead tr td,
        body.dark-mode .swagger-ui .parameter__name,
        body.dark-mode .swagger-ui .parameter__type,
        body.dark-mode .swagger-ui .parameter__in {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .parameter__name.required:after {{
            color: var(--dark-error) !important;
        }}

        body.dark-mode .swagger-ui table tbody tr td {{
            color: var(--dark-text-secondary) !important;
        }}

        body.dark-mode .swagger-ui .model-title,
        body.dark-mode .swagger-ui .model {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .model-box {{
            background-color: var(--dark-bg-secondary) !important;
        }}

        body.dark-mode .swagger-ui section.models {{
            border-color: var(--dark-border) !important;
        }}

        body.dark-mode .swagger-ui section.models h4 {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .model-container {{
            background-color: var(--dark-bg-secondary) !important;
        }}

        body.dark-mode .swagger-ui .prop-type {{
            color: var(--dark-accent) !important;
        }}

        body.dark-mode .swagger-ui .response-col_status {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .response-col_description {{
            color: var(--dark-text-secondary) !important;
        }}

        body.dark-mode .swagger-ui .responses-inner h4,
        body.dark-mode .swagger-ui .responses-inner h5 {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui input[type=text],
        body.dark-mode .swagger-ui textarea,
        body.dark-mode .swagger-ui select {{
            background-color: var(--dark-bg) !important;
            color: var(--dark-text) !important;
            border-color: var(--dark-border) !important;
        }}

        body.dark-mode .swagger-ui .btn {{
            color: var(--dark-text) !important;
            border-color: var(--dark-border) !important;
        }}

        body.dark-mode .swagger-ui .btn:hover {{
            background-color: var(--dark-bg-tertiary) !important;
        }}

        body.dark-mode .swagger-ui .loading-container .loading:after {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .scheme-container {{
            background-color: var(--dark-bg-secondary) !important;
        }}

        body.dark-mode .swagger-ui .servers > label {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .filter-container .filter input[type=text] {{
            background-color: var(--dark-bg) !important;
            color: var(--dark-text) !important;
            border-color: var(--dark-border) !important;
        }}

        body.dark-mode .swagger-ui .markdown p,
        body.dark-mode .swagger-ui .markdown li,
        body.dark-mode .swagger-ui .renderedMarkdown p,
        body.dark-mode .swagger-ui .renderedMarkdown li {{
            color: var(--dark-text-secondary) !important;
        }}

        body.dark-mode .swagger-ui .markdown code,
        body.dark-mode .swagger-ui .renderedMarkdown code {{
            background-color: var(--dark-bg) !important;
            color: var(--dark-accent) !important;
        }}

        body.dark-mode .swagger-ui .download-contents {{
            background-color: var(--dark-bg-tertiary) !important;
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .opblock-description-wrapper p,
        body.dark-mode .swagger-ui .opblock-external-docs-wrapper p {{
            color: var(--dark-text-secondary) !important;
        }}

        body.dark-mode .swagger-ui .tab li {{
            color: var(--dark-text-secondary) !important;
        }}

        body.dark-mode .swagger-ui .tab li.active {{
            color: var(--dark-text) !important;
        }}

        body.dark-mode .swagger-ui .response-control-media-type__title {{
            color: var(--dark-text-secondary) !important;
        }}

        body.dark-mode .swagger-ui .copy-to-clipboard {{
            background-color: var(--dark-bg-tertiary) !important;
        }}

        /* Dark mode toggle button */
        .theme-toggle {{
            position: fixed;
            top: 15px;
            right: 20px;
            z-index: 10000;
            padding: 8px 16px;
            border-radius: 20px;
            border: 2px solid var(--dark-border);
            background-color: var(--dark-bg-secondary);
            color: var(--dark-text);
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .theme-toggle:hover {{
            background-color: var(--dark-bg-tertiary);
            transform: scale(1.05);
        }}

        body:not(.dark-mode) .theme-toggle {{
            background-color: #f5f5f5;
            color: #333;
            border-color: #ddd;
        }}

        .theme-toggle .icon {{
            font-size: 16px;
        }}
    </style>
</head>
<body class="dark-mode">
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {{
            SwaggerUIBundle({{
                url: "{openapi_url}",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                syntaxHighlight: {{
                    theme: "monokai"
                }},
                docExpansion: "list",
                filter: true,
                tryItOutEnabled: true
            }});

            // Create toggle button
            const toggle = document.createElement('button');
            toggle.className = 'theme-toggle';
            toggle.innerHTML = '<span class="icon">🌙</span><span class="text">Dark</span>';
            toggle.onclick = function() {{
                document.body.classList.toggle('dark-mode');
                const isDark = document.body.classList.contains('dark-mode');
                localStorage.setItem('swagger-theme', isDark ? 'dark' : 'light');
                toggle.innerHTML = isDark
                    ? '<span class="icon">🌙</span><span class="text">Dark</span>'
                    : '<span class="icon">☀️</span><span class="text">Light</span>';
            }};

            // Check for saved preference
            const savedTheme = localStorage.getItem('swagger-theme');
            if (savedTheme === 'light') {{
                document.body.classList.remove('dark-mode');
                toggle.innerHTML = '<span class="icon">☀️</span><span class="text">Light</span>';
            }}

            document.body.appendChild(toggle);
        }};
    </script>
</body>
</html>
"""


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    """Custom Swagger UI with dark mode support and toggle."""
    html_content = SWAGGER_DARK_MODE_HTML.format(
        title=app.title,
        openapi_url=app.openapi_url or "/openapi.json",
    )
    return HTMLResponse(content=html_content)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from capabilities.persona.discord_characters.api import router as discord_characters_router
from services.external.discord_bot_config.router import router as discord_bot_config_router
from src.services.database.mongodb.router import router as mongodb_router
from src.services.database.neo4j.router import router as neo4j_router

from server.api import (
    admin,
    auth,
    calendar,
    calendar_sync,
    conversation,
    crawl4ai_rag,
    data_view,
    graphiti_rag,
    health,
    knowledge,
    knowledge_base,
    mcp_rest,
    mongo_rag,
    n8n_workflow,
    openwebui_export,
    openwebui_topics,
    persona,
    searxng,
    youtube_rag,
)
from server.projects.blob_storage.router import router as blob_storage_router
from server.projects.comfyui_workflow.router import router as comfyui_workflow_router

app.include_router(health.router, tags=["health"])
app.include_router(admin.router, tags=["admin"])
app.include_router(mongodb_router, prefix="/api/v1/infrastructure", tags=["infrastructure"])
app.include_router(neo4j_router, prefix="/api/v1/infrastructure", tags=["infrastructure"])
app.include_router(blob_storage_router, prefix="/api/v1/storage", tags=["storage"])
app.include_router(comfyui_workflow_router, prefix="/api/v1/comfyui", tags=["comfyui"])
app.include_router(auth.router, tags=["auth"])
app.include_router(mongo_rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(crawl4ai_rag.router, prefix="/api/v1/crawl", tags=["crawl"])
app.include_router(youtube_rag.router, tags=["youtube-rag"])
app.include_router(graphiti_rag.router, tags=["graphiti"])
app.include_router(n8n_workflow.router, prefix="/api/v1/n8n", tags=["n8n"])
app.include_router(openwebui_export.router, prefix="/api/v1/openwebui", tags=["openwebui"])
app.include_router(openwebui_topics.router, prefix="/api/v1/openwebui", tags=["openwebui"])
app.include_router(searxng.router, tags=["searxng"])
app.include_router(calendar_sync.router, prefix="/api/v1/calendar", tags=["calendar"])
app.include_router(calendar.router, prefix="/api/v1/calendar/events", tags=["calendar"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(persona.router, prefix="/api/v1/persona", tags=["persona"])
app.include_router(conversation.router, prefix="/api/v1/conversation", tags=["conversation"])
app.include_router(
    discord_characters_router, prefix="/api/v1/discord/characters", tags=["discord-characters"]
)
app.include_router(discord_bot_config_router, tags=["discord-bot-config"])
app.include_router(data_view.router, prefix="/api/v1/data", tags=["data-view"])
app.include_router(knowledge_base.router)  # Knowledge Base with article proposals
app.include_router(mcp_rest.router)  # REST API wrapper for MCP tools


# Add a simple GET endpoint for MCP server info (for testing/debugging)
# Note: This must be defined BEFORE mounting /mcp to avoid route conflicts
@app.get("/mcp-info")
async def mcp_info():
    """Get information about the MCP server and available tools."""
    # Get registered tools from FastMCP via tool_manager._tools
    registered_tools = []
    if hasattr(mcp, "_tool_manager"):
        tool_manager = mcp._tool_manager
        # Access _tools directly (it's a dict of tool_name -> FunctionTool)
        if hasattr(tool_manager, "_tools") and tool_manager._tools:
            for tool_name, tool in tool_manager._tools.items():
                desc = "No description"
                if hasattr(tool, "description") and tool.description:
                    desc = str(tool.description).split("\n")[0].strip()
                registered_tools.append({"name": tool_name, "description": desc})

    return {
        "server": getattr(mcp, "name", "Lambda Server"),
        "endpoint": "/mcp",
        "protocol": "SSE (Server-Sent Events) - Use MCP client, not browser",
        "note": "The /mcp endpoint uses Server-Sent Events (SSE) for MCP protocol communication. Use an MCP client (like Cursor) to connect, not a web browser. Visit http://localhost:8000/docs for API documentation.",
        "available_tools_count": len(registered_tools),
        "tools": registered_tools[:50],  # Show first 50 tools
    }


# Add OpenAPI endpoint for MCP tools (for Open WebUI compatibility)
# Note: This must be defined BEFORE mounting /mcp to avoid route conflicts
@app.get("/mcp/openapi.json")
async def mcp_openapi():
    """
    Generate OpenAPI 3.0 specification from FastMCP tools.

    This endpoint allows Open WebUI and other OpenAPI-compatible clients
    to discover and use MCP tools via standard OpenAPI specification.
    """

    from fastapi.responses import JSONResponse

    # Get tools from FastMCP
    tools = []
    if hasattr(mcp, "_tool_manager"):
        tool_manager = mcp._tool_manager
        if hasattr(tool_manager, "_tools") and tool_manager._tools:
            for tool_name, tool in tool_manager._tools.items():
                # Get tool description
                description = ""
                if hasattr(tool, "description") and tool.description:
                    description = str(tool.description).split("\n")[0].strip()

                # Get input schema
                input_schema = {"type": "object", "properties": {}, "required": []}

                # Try to extract schema from tool
                if hasattr(tool, "inputSchema"):
                    input_schema = tool.inputSchema
                elif hasattr(tool, "parameters"):
                    input_schema = tool.parameters
                elif hasattr(tool, "func"):
                    # Try to get schema from function signature
                    import inspect

                    sig = inspect.signature(tool.func)
                    properties = {}
                    required = []
                    for param_name, param in sig.parameters.items():
                        if param_name == "self":
                            continue
                        param_type = "string"  # Default
                        if param.annotation != inspect.Parameter.empty:
                            if param.annotation == str:
                                param_type = "string"
                            elif param.annotation == int:
                                param_type = "integer"
                            elif param.annotation == bool:
                                param_type = "boolean"
                            elif param.annotation == float:
                                param_type = "number"
                            elif param.annotation in (list, list):
                                param_type = "array"
                            elif param.annotation in (dict, dict):
                                param_type = "object"

                        properties[param_name] = {"type": param_type, "description": ""}

                        if param.default == inspect.Parameter.empty:
                            required.append(param_name)

                    input_schema = {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    }

                tools.append(
                    {"name": tool_name, "description": description, "inputSchema": input_schema}
                )

    # Generate OpenAPI 3.0 spec
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Lambda MCP Server",
            "description": "Model Context Protocol server with REST API wrapper",
            "version": "1.0.0",
        },
        "servers": [{"url": "/api/v1/mcp", "description": "MCP REST API"}],
        "paths": {
            "/tools/call": {
                "post": {
                    "summary": "Call an MCP tool",
                    "description": "Execute an MCP tool by name with arguments",
                    "operationId": "callTool",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Name of the MCP tool to call",
                                        },
                                        "arguments": {
                                            "type": "object",
                                            "description": "Tool arguments",
                                            "additionalProperties": True,
                                        },
                                    },
                                    "required": ["name"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Tool execution result",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean"},
                                            "result": {"type": "object"},
                                            "error": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/tools/list": {
                "get": {
                    "summary": "List all available MCP tools",
                    "description": "Get a list of all registered MCP tools",
                    "operationId": "listTools",
                    "responses": {
                        "200": {
                            "description": "List of tools",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "tools": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "description": {"type": "string"},
                                                        "inputSchema": {"type": "object"},
                                                    },
                                                },
                                            },
                                            "count": {"type": "integer"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "Tool": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "inputSchema": {"type": "object"},
                    },
                }
            }
        },
    }

    # Add individual tool endpoints to OpenAPI spec
    for tool in tools:
        tool_path = f"/tools/{tool['name']}"
        openapi_spec["paths"][tool_path] = {
            "post": {
                "summary": tool["description"] or f"Call {tool['name']} tool",
                "description": tool["description"] or f"Execute the {tool['name']} MCP tool",
                "operationId": f"call_{tool['name']}",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": tool["inputSchema"]}},
                },
                "responses": {
                    "200": {
                        "description": "Tool execution result",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object", "additionalProperties": True}
                            }
                        },
                    }
                },
            }
        }

    return JSONResponse(content=openapi_spec)


# Mount FastMCP server AFTER defining other routes
# Mount at "/mcp" with path='/' gives endpoint at /mcp/
app.mount("/mcp", mcp_app)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "Lambda Server", "version": "1.0.0", "status": "running"}
