"""REST API wrapper for FastMCP tools.

This module provides REST API endpoints that wrap FastMCP tools, making them
accessible via standard HTTP POST requests. This allows clients like Open WebUI
that don't fully support FastMCP's Streamable HTTP transport to still use the tools.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.mcp.fastmcp_server import mcp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp-rest"])


class ToolCallRequest(BaseModel):
    """Request model for calling an MCP tool."""

    name: str = Field(..., description="Name of the MCP tool to call")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolCallResponse(BaseModel):
    """Response model for tool call."""

    success: bool
    result: Any = None
    error: str | None = None


@router.get("/tools/list")
async def list_tools() -> dict[str, Any]:
    """
    List all available MCP tools.

    Returns a list of all tools registered with FastMCP, including their
    names, descriptions, and input schemas.
    """
    try:
        tools = []

        # Get tools from FastMCP
        if hasattr(mcp, "_tool_manager"):
            tool_manager = mcp._tool_manager
            if hasattr(tool_manager, "_tools") and tool_manager._tools:
                for tool_name, tool in tool_manager._tools.items():
                    tool_info = {"name": tool_name, "description": "", "inputSchema": {}}

                    # Extract description
                    if hasattr(tool, "description") and tool.description:
                        tool_info["description"] = str(tool.description).split("\n")[0].strip()

                    # Extract input schema if available
                    if hasattr(tool, "inputSchema"):
                        tool_info["inputSchema"] = tool.inputSchema
                    elif hasattr(tool, "parameters"):
                        # Try to get parameters from tool
                        tool_info["inputSchema"] = tool.parameters

                    tools.append(tool_info)

        return {"tools": tools, "count": len(tools)}
    except Exception as e:
        logger.exception(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {e!s}")


@router.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest) -> ToolCallResponse:
    """
    Call an MCP tool via REST API.

    This endpoint wraps FastMCP's tool calling mechanism, allowing clients
    that don't support Streamable HTTP to still use MCP tools via standard
    REST API calls.

    Args:
        request: Tool call request with tool name and arguments

    Returns:
        Tool call response with result or error
    """
    if not request.name:
        raise HTTPException(status_code=400, detail="Tool name is required")

    try:
        logger.info(f"Calling MCP tool: {request.name} with arguments: {request.arguments}")

        # Call the tool via FastMCP
        # FastMCP's tool manager handles tool execution
        if hasattr(mcp, "_tool_manager"):
            tool_manager = mcp._tool_manager
            if hasattr(tool_manager, "_tools") and request.name in tool_manager._tools:
                tool = tool_manager._tools[request.name]

                # FastMCP tools are FunctionTool objects with a 'run' method
                if hasattr(tool, "run"):
                    # Use the run method to execute the tool
                    # run() expects arguments as a dict, not keyword arguments
                    if callable(tool.run):
                        import inspect

                        if inspect.iscoroutinefunction(tool.run):
                            tool_result = await tool.run(arguments=request.arguments)
                        else:
                            tool_result = tool.run(arguments=request.arguments)
                        # Extract result from ToolResult object
                        if hasattr(tool_result, "content"):
                            # ToolResult has content array
                            if tool_result.content and len(tool_result.content) > 0:
                                first_item = tool_result.content[0]
                                if hasattr(first_item, "text"):
                                    import json

                                    try:
                                        result = json.loads(first_item.text)
                                    except json.JSONDecodeError:
                                        result = first_item.text
                                else:
                                    result = first_item
                            else:
                                result = {}
                        elif hasattr(tool_result, "result"):
                            result = tool_result.result
                        else:
                            result = tool_result
                    else:
                        raise ValueError(f"Tool {request.name} run method is not callable")
                # Fallback: try to access underlying function
                elif hasattr(tool, "fn"):
                    func = tool.fn
                    if callable(func):
                        import inspect

                        if inspect.iscoroutinefunction(func):
                            result = await func(**request.arguments)
                        else:
                            result = func(**request.arguments)
                    else:
                        raise ValueError(f"Tool {request.name} function is not callable")
                else:
                    raise ValueError(
                        f"Tool {request.name} does not have a run method or fn attribute"
                    )
            else:
                raise ValueError(f"Tool {request.name} not found in tool manager")
        elif hasattr(mcp, "_call_tool"):
            # Fallback: try FastMCP's internal method (may have different signature)
            try:
                result = await mcp._call_tool(request.name, request.arguments)
            except TypeError:
                # If signature doesn't match, try alternative approach
                raise ValueError(f"Tool {request.name} not found or call method incompatible")
        elif hasattr(mcp, "_tool_manager"):
            # Alternative: call via tool manager
            tool_manager = mcp._tool_manager
            if hasattr(tool_manager, "_tools") and request.name in tool_manager._tools:
                tool = tool_manager._tools[request.name]
                # Call the tool function directly
                if hasattr(tool, "func"):
                    # Tool is a FunctionTool wrapper
                    func = tool.func
                    if callable(func):
                        # Check if it's async
                        import inspect

                        if inspect.iscoroutinefunction(func):
                            result = await func(**request.arguments)
                        else:
                            result = func(**request.arguments)
                    else:
                        raise ValueError(f"Tool {request.name} function is not callable")
                elif callable(tool):
                    # Tool is directly callable
                    import inspect

                    if inspect.iscoroutinefunction(tool):
                        result = await tool(**request.arguments)
                    else:
                        result = tool(**request.arguments)
                else:
                    raise ValueError(f"Tool {request.name} is not callable")
            else:
                raise ValueError(f"Tool {request.name} not found")
        else:
            raise RuntimeError("FastMCP tool manager not available")

        logger.info(f"Tool {request.name} completed successfully")
        return ToolCallResponse(success=True, result=result)

    except ValueError as e:
        logger.warning(f"Tool call failed (validation): {e}")
        return ToolCallResponse(success=False, error=str(e))
    except Exception as e:
        logger.exception(f"Tool call failed: {e}")
        return ToolCallResponse(success=False, error=str(e))


@router.get("/info")
async def mcp_info() -> dict[str, Any]:
    """
    Get information about the MCP server.

    Returns server metadata including name, available tools count, and
    supported transport methods.
    """
    try:
        tools = []
        if hasattr(mcp, "_tool_manager"):
            tool_manager = mcp._tool_manager
            if hasattr(tool_manager, "_tools") and tool_manager._tools:
                for tool_name, tool in tool_manager._tools.items():
                    desc = "No description"
                    if hasattr(tool, "description") and tool.description:
                        desc = str(tool.description).split("\n")[0].strip()
                    tools.append({"name": tool_name, "description": desc})

        return {
            "server": getattr(mcp, "name", "Lambda Server"),
            "transports": {"streamable_http": "/mcp/", "rest_api": "/api/v1/mcp/tools/call"},
            "available_tools_count": len(tools),
            "tools": tools[:20],  # Show first 20 tools
        }
    except Exception as e:
        logger.exception(f"Error getting MCP info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get MCP info: {e!s}")
