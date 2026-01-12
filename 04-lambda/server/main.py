"""FastAPI application for Lambda multi-project server."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    # Run MCP lifespan startup
    async with mcp_app.lifespan(app):
        yield

    # Shutdown
    logger.info("lambda_server_shutdown")


# Create FastAPI app with combined lifespan
app = FastAPI(
    title="Lambda Server",
    description="Multi-project FastAPI server with MCP and REST APIs",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from server.api import (
    auth,
    calendar,
    calendar_sync,
    conversation,
    crawl4ai_rag,
    data_view,
    graphiti_rag,
    health,
    knowledge,
    mcp_rest,
    mongo_rag,
    n8n_workflow,
    openwebui_export,
    openwebui_topics,
    persona,
    searxng,
)
from server.projects.blob_storage.router import router as blob_storage_router
from server.projects.comfyui_workflow.router import router as comfyui_workflow_router
from server.projects.discord_characters.api import router as discord_characters_router

app.include_router(health.router, tags=["health"])
app.include_router(blob_storage_router, prefix="/api/v1/storage", tags=["storage"])
app.include_router(comfyui_workflow_router, prefix="/api/v1/comfyui", tags=["comfyui"])
app.include_router(auth.router, tags=["auth"])
app.include_router(mongo_rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(crawl4ai_rag.router, prefix="/api/v1/crawl", tags=["crawl"])
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
app.include_router(discord_characters_router, prefix="/api/v1", tags=["discord-characters"])
app.include_router(data_view.router, prefix="/api/v1/data", tags=["data-view"])
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
