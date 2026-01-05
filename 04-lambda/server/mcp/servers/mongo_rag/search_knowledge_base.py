"""Search the MongoDB RAG knowledge base using semantic, text, or hybrid search. Searches across all ingested documents including crawled web pages. Results are ranked by relevance and include metadata for filtering and context."""
from typing import Optional, List, Any, Literal
from server.mcp.servers.client import call_mcp_tool

async def search_knowledge_base(
    query: str, match_count: Optional[int] = 5, search_type: Optional[str] = "hybrid"
) -> dict:
    """
    Search the MongoDB RAG knowledge base using semantic, text, or hybrid search. Searches across all ingested documents including crawled web pages. Results are ranked by relevance and include metadata for filtering and context.
    
    Args:
        query (str): Search query text. Can be a question, phrase, or keywords. Required.
        match_count (int): Number of results to return. Range: 1-50. Default: 5.
        search_type (str): Type of search to perform. 'semantic' uses vector embeddings (best for conceptual queries), 'text' uses keyword matching (best for exact terms), 'hybrid' combines both using Reciprocal Rank Fusion (recommended). Default: "hybrid".
    
    Returns:
        Tool response as dictionary.
    """
    return await call_mcp_tool(
        "search_knowledge_base",
        {
            "query": query,
            "match_count": match_count,
            "search_type": search_type,
        }
    )
