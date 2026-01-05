"""Search the web using SearXNG metasearch engine. Use this when you need current information, real-time data, or information not in the knowledge base. Automatically searches multiple search engines and returns ranked results."""
from typing import Optional, List
from server.mcp.servers.client import call_mcp_tool

async def web_search(
    query: str,
    result_count: Optional[int] = 10,
    categories: Optional[str] = None,
    engines: Optional[List[str]] = None
) -> dict:
    """
    Search the web using SearXNG metasearch engine. Use this when you need current information, real-time data, or information not in the knowledge base. Automatically searches multiple search engines and returns ranked results.
    
    Args:
        query (str): Search query string. Required.
        result_count (int): Number of results to return. Range: 1-20. Default: 10.
        categories (str): Filter by category (general, news, images, etc.). Optional.
        engines (List[str]): Filter by specific search engines. Optional.
    
    Returns:
        Tool response as dictionary.
    """
    args = {
        "query": query,
        "result_count": result_count,
    }
    
    if categories:
        args["categories"] = categories
    
    if engines:
        args["engines"] = engines
    
    return await call_mcp_tool(
        "web_search",
        args
    )

