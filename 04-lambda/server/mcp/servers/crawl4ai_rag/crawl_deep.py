"""Deep crawl a website recursively and ingest all discovered pages into MongoDB. Follows internal links up to specified depth with optional domain/subdomain filtering. All pages become immediately searchable. Each page's metadata includes crawl depth and parent URL for traceability."""

from server.mcp.servers.client import call_mcp_tool


async def crawl_deep(
    url: str,
    max_depth: int,
    allowed_domains: list[str] | None = None,
    allowed_subdomains: list[str] | None = None,
    chunk_size: int | None = 1000,
    chunk_overlap: int | None = 200,
) -> dict:
    """
    Deep crawl a website recursively and ingest all discovered pages into MongoDB. Follows internal links up to specified depth with optional domain/subdomain filtering. All pages become immediately searchable. Each page's metadata includes crawl depth and parent URL for traceability.

    Args:
        url (str): Starting URL for the crawl. Must be a valid HTTP/HTTPS URL. Required.
        max_depth (int): Maximum recursion depth. Range: 1-10. Depth 1 = starting page only, Depth 2 = starting page + 1 level of links, Depth 3 = starting page + 2 levels (recommended for most sites). Required.
        allowed_domains (List[str]): List of allowed domains for exact matching. If not provided, allows all domains from the starting URL. Example: ["example.com", "docs.example.com"]
        allowed_subdomains (List[str]): List of allowed subdomain prefixes. If not provided, allows all subdomains. Example: ["docs", "api", "blog"] matches docs.example.com, api.example.com, etc.
        chunk_size (int): Chunk size for document splitting. Range: 100-5000. Larger chunks preserve more context but may exceed embedding model limits. Default: 1000.
        chunk_overlap (int): Chunk overlap size. Range: 0-500. Overlap helps maintain context across chunk boundaries. Default: 200.

    Returns:
        Tool response as dictionary.
    """
    return await call_mcp_tool(
        "crawl_deep",
        {
            "url": url,
            "max_depth": max_depth,
            "allowed_domains": allowed_domains,
            "allowed_subdomains": allowed_subdomains,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
    )
