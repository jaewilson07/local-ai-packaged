"""MCP client for calling MCP tools from generated Python modules."""

import json
import logging
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    try:
        import aiohttp
        httpx = None
    except ImportError:
        httpx = None
        aiohttp = None

logger = logging.getLogger(__name__)

# Default MCP server URL (can be overridden)
MCP_SERVER_URL = "http://localhost:8000"


async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Call an MCP tool by name with arguments.
    
    This function makes an HTTP request to the MCP server's /mcp/tools/call endpoint.
    It handles error responses and raises appropriate exceptions.
    
    Args:
        tool_name: Name of the MCP tool to call
        arguments: Dictionary of arguments to pass to the tool
    
    Returns:
        Tool response as dictionary. The actual structure depends on the tool.
    
    Raises:
        ValueError: If tool_name is empty or arguments is not a dict
        ConnectionError: If unable to connect to MCP server
        RuntimeError: If the tool call returns an error response
    """
    if not tool_name:
        raise ValueError("tool_name cannot be empty")
    
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be a dictionary")
    
    url = f"{MCP_SERVER_URL}/mcp/tools/call"
    payload = {
        "name": tool_name,
        "arguments": arguments
    }
    
    try:
        if httpx:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
        elif aiohttp:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=300)) as response:
                    response.raise_for_status()
                    result = await response.json()
        else:
            raise ImportError("Neither httpx nor aiohttp is available. Please install one of them.")
        
        # Check for error response
        if "error" in result:
            error = result["error"]
            error_code = error.get("code", "UNKNOWN_ERROR")
            error_message = error.get("message", "An error occurred")
            error_details = error.get("details", "")
            
            error_msg = f"MCP tool '{tool_name}' failed with {error_code}: {error_message}"
            if error_details:
                error_msg += f" ({error_details})"
            
            raise RuntimeError(error_msg)
        
        # Extract content from MCP response format
        if "content" in result:
            content = result["content"]
            if content and len(content) > 0:
                first_item = content[0]
                if first_item.get("type") == "json":
                    # Parse JSON content
                    return json.loads(first_item.get("text", "{}"))
                else:
                    # Return text content
                    return first_item.get("text", "")
        
        # Fallback: return entire result
        return result
            
    except Exception as http_error:
        # Handle HTTP errors from either httpx or aiohttp
        if httpx and isinstance(http_error, httpx.HTTPStatusError):
            e = http_error
            logger.error(f"MCP tool call HTTP error: {e.response.status_code} - {e.response.text}")
            raise ConnectionError(f"MCP server returned error {e.response.status_code}: {e.response.text}")
        elif aiohttp and isinstance(http_error, aiohttp.ClientResponseError):
            e = http_error
            logger.error(f"MCP tool call HTTP error: {e.status} - {e.message}")
            raise ConnectionError(f"MCP server returned error {e.status}: {e.message}")
        elif (httpx and isinstance(http_error, httpx.RequestError)) or (aiohttp and isinstance(http_error, aiohttp.ClientError)):
            e = http_error
            logger.error(f"MCP tool call connection error: {e}")
            raise ConnectionError(f"Unable to connect to MCP server at {url}: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"MCP tool call JSON decode error: {e}")
        raise RuntimeError(f"Invalid JSON response from MCP server: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error calling MCP tool '{tool_name}': {e}")
        raise


def set_mcp_server_url(url: str) -> None:
    """
    Set the MCP server URL.
    
    Args:
        url: Base URL of the MCP server (e.g., "http://localhost:8000")
    """
    global MCP_SERVER_URL
    MCP_SERVER_URL = url.rstrip("/")
    logger.info(f"MCP server URL set to: {MCP_SERVER_URL}")

