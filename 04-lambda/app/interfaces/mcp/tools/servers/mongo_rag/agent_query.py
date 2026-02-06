"""Query the conversational RAG agent with natural language. The agent can search the knowledge base, synthesize information, and provide natural language responses. It automatically decides when to search and how to combine search results into coherent answers."""

from server.mcp.servers.client import call_mcp_tool


async def agent_query(query: str) -> dict:
    """
    Query the conversational RAG agent with natural language. The agent can search the knowledge base, synthesize information, and provide natural language responses. It automatically decides when to search and how to combine search results into coherent answers.

    Args:
        query (str): Natural language question or query. The agent will determine if a search is needed, search the knowledge base if relevant, and synthesize results into a coherent answer. Required.

    Returns:
        Tool response as dictionary.
    """
    return await call_mcp_tool(
        "agent_query",
        {
            "query": query,
        },
    )
