""""""

from server.mcp.servers.client import call_mcp_tool


async def unknown() -> dict:
    """


    Args:


    Returns:
        Tool response as dictionary.
    """
    return await call_mcp_tool("unknown", {})
