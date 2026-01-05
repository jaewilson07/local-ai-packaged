"""FastAPI application for Lambda multi-project server."""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from server.config import settings
from server.core.logging import setup_logging

# Setup structured logging
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Setup FastMCP server first (needed for lifespan)
from server.mcp.fastmcp_server import mcp
from contextlib import asynccontextmanager

# Create ASGI app from MCP server
# Mount at "/mcp" with path='/' gives endpoint at /mcp/
mcp_app = mcp.http_app(path='/')

# Combine MCP lifespan with our startup/shutdown logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("lambda_server_started", extra={"version": "1.0.0"})
    
    # Generate MCP server modules for code execution
    try:
        from pathlib import Path
        from server.mcp.codegen import generate_all_servers
        
        servers_dir = Path(__file__).parent / "mcp" / "servers"
        generate_all_servers(servers_dir)
        logger.info("mcp_code_generation_complete", extra={"servers_dir": str(servers_dir)})
    except Exception as e:
        logger.exception(f"mcp_code_generation_failed: {e}")
        # Don't fail startup if code generation fails
    
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
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from server.api import health, mongo_rag, crawl4ai_rag, graphiti_rag, n8n_workflow, openwebui_export, openwebui_topics, searxng, calendar_sync
app.include_router(health.router, tags=["health"])
app.include_router(mongo_rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(crawl4ai_rag.router, prefix="/api/v1/crawl", tags=["crawl"])
app.include_router(graphiti_rag.router, tags=["graphiti"])
app.include_router(n8n_workflow.router, prefix="/api/v1/n8n", tags=["n8n"])
app.include_router(openwebui_export.router, prefix="/api/v1/openwebui", tags=["openwebui"])
app.include_router(openwebui_topics.router, prefix="/api/v1/openwebui", tags=["openwebui"])
app.include_router(searxng.router, tags=["searxng"])
app.include_router(calendar_sync.router, prefix="/api/v1/calendar", tags=["calendar"])

# Add a simple GET endpoint for MCP server info (for testing/debugging)
# Note: This must be defined BEFORE mounting /mcp to avoid route conflicts
@app.get("/mcp-info")
async def mcp_info():
    """Get information about the MCP server and available tools."""
    try:
        # Get registered tools from FastMCP via tool_manager._tools
        registered_tools = []
        if hasattr(mcp, '_tool_manager'):
            tool_manager = mcp._tool_manager
            # Access _tools directly (it's a dict of tool_name -> FunctionTool)
            if hasattr(tool_manager, '_tools') and tool_manager._tools:
                for tool_name, tool in tool_manager._tools.items():
                    desc = 'No description'
                    if hasattr(tool, 'description') and tool.description:
                        desc = str(tool.description).split('\n')[0].strip()
                    registered_tools.append({
                        "name": tool_name,
                        "description": desc
                    })
        
        return {
            "server": getattr(mcp, 'name', 'Lambda Server'),
            "endpoint": "/mcp",
            "protocol": "SSE (Server-Sent Events) - Use MCP client, not browser",
            "note": "The /mcp endpoint uses Server-Sent Events (SSE) for MCP protocol communication. Use an MCP client (like Cursor) to connect, not a web browser. Visit http://localhost:8000/docs for API documentation.",
            "available_tools_count": len(registered_tools),
            "tools": registered_tools[:50]  # Show first 50 tools
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "server": "Lambda Server",
            "endpoint": "/mcp"
        }

# Mount FastMCP server AFTER defining other routes
# Mount at "/mcp" with path='/' gives endpoint at /mcp/
app.mount("/mcp", mcp_app)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Lambda Server",
        "version": "1.0.0",
        "status": "running"
    }

