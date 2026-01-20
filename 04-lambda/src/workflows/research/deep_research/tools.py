"""Deep research tools for Pydantic AI agents.

This module provides tools for web research, content parsing,
and knowledge base operations. Includes a composite `research_and_store`
tool for Cursor agent integration that searches, filters, and ingests
content in a single operation.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from workflows.research.deep_research.models import (
    IngestedItem,
    ResearchAndStoreRequest,
    ResearchAndStoreResponse,
)

logger = logging.getLogger(__name__)


def _get_deps(ctx: Any):
    """Extract dependencies from context."""
    deps = getattr(ctx, "deps", ctx)
    if hasattr(deps, "_deps"):
        deps = deps._deps
    return deps


async def search_web(ctx: Any, query: str, max_results: int = 10) -> str:
    """
    Search the web using SearXNG.

    Args:
        ctx: Context with dependencies
        query: Search query
        max_results: Maximum number of results

    Returns:
        String with search results
    """
    deps = _get_deps(ctx)
    http_client = getattr(deps, "http_client", None)
    settings = getattr(deps, "settings", None)

    if not http_client or not settings:
        return "[Not Configured] Deep research dependencies not initialized"

    try:
        searxng_url = getattr(settings, "searxng_url", None)
        if not searxng_url:
            return "[Not Configured] SearXNG URL not configured"

        params = {
            "q": query,
            "format": "json",
            "categories": "general",
            "engines": "google,duckduckgo,bing",
        }

        response = await http_client.get(f"{searxng_url}/search", params=params)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])[:max_results]
        if not results:
            return f"No results found for: {query}"

        lines = [f"Found {len(results)} result(s) for '{query}':"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            snippet = r.get("content", "")[:200]
            lines.append(f"\n[{i}] {title}")
            lines.append(f"    URL: {url}")
            lines.append(f"    {snippet}...")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("Error searching web")
        return f"[Error] Web search failed: {e}"


async def fetch_page(ctx: Any, url: str, extract_markdown: bool = True) -> str:
    """
    Fetch and extract content from a web page.

    Args:
        ctx: Context with dependencies
        url: URL to fetch
        extract_markdown: Whether to extract as markdown

    Returns:
        String with page content
    """
    deps = _get_deps(ctx)
    crawler = getattr(deps, "crawler", None)

    if not crawler:
        # Fall back to HTTP client
        http_client = getattr(deps, "http_client", None)
        if not http_client:
            return "[Not Configured] No crawler or HTTP client available"

        try:
            response = await http_client.get(url, follow_redirects=True)
            response.raise_for_status()
            content = response.text[:10000]  # Limit content
            return f"Page content from {url}:\n\n{content}"
        except Exception as e:
            return f"[Error] Failed to fetch page: {e}"

    try:
        result = await crawler.arun(url=url)

        if not result.success:
            return f"[Error] Failed to crawl {url}: {result.error}"

        if extract_markdown and result.markdown:
            content = result.markdown[:10000]  # Limit content
        else:
            content = result.html[:10000] if result.html else "No content"

        return f"Content from {url}:\n\n{content}"

    except Exception as e:
        logger.exception("Error fetching page")
        return f"[Error] Failed to fetch page: {e}"


async def parse_document(ctx: Any, content: str, content_type: str = "text") -> str:
    """
    Parse and structure document content.

    Args:
        ctx: Context with dependencies
        content: Document content to parse
        content_type: Type of content (text, html, pdf)

    Returns:
        String with parsed content
    """
    deps = _get_deps(ctx)
    document_converter = getattr(deps, "document_converter", None)

    if not document_converter:
        # Simple text extraction
        return f"Parsed content ({len(content)} characters):\n\n{content[:5000]}"

    try:
        # Use Docling for structured parsing
        result = document_converter.convert_from_string(content)
        if result.document:
            text = result.document.export_to_markdown()
            return f"Parsed document:\n\n{text[:5000]}"
        return f"Parsed content:\n\n{content[:5000]}"

    except Exception as e:
        logger.exception("Error parsing document")
        return f"[Error] Document parsing failed: {e}"


async def ingest_knowledge(
    ctx: Any,
    content: str,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """
    Ingest content into the knowledge base.

    Args:
        ctx: Context with dependencies
        content: Content to ingest
        source: Source URL or identifier
        metadata: Additional metadata

    Returns:
        String confirming ingestion
    """
    deps = _get_deps(ctx)
    db = getattr(deps, "db", None)
    graphiti_deps = getattr(deps, "graphiti_deps", None)

    if not db and not graphiti_deps:
        return "[Not Configured] No knowledge base connection available"

    try:
        # Try Graphiti first if available
        if graphiti_deps and hasattr(graphiti_deps, "graphiti") and graphiti_deps.graphiti:
            from graphiti_core import EpisodeType

            await graphiti_deps.graphiti.add_episode(
                name=source,
                episode_body=content,
                source=EpisodeType.text,
                reference_time=None,
            )
            return f"Ingested into knowledge graph: {source}"

        # Fall back to MongoDB
        if db:
            collection = db["research_knowledge"]
            doc = {
                "source": source,
                "content": content[:50000],  # Limit size
                "metadata": metadata or {},
            }
            await collection.insert_one(doc)
            return f"Ingested into MongoDB: {source}"

        return "[Error] No storage backend available"

    except Exception as e:
        logger.exception("Error ingesting knowledge")
        return f"[Error] Knowledge ingestion failed: {e}"


async def query_knowledge(
    ctx: Any,
    query: str,
    max_results: int = 5,
) -> str:
    """
    Query the knowledge base.

    Args:
        ctx: Context with dependencies
        query: Search query
        max_results: Maximum results to return

    Returns:
        String with query results
    """
    deps = _get_deps(ctx)
    db = getattr(deps, "db", None)
    graphiti_deps = getattr(deps, "graphiti_deps", None)

    if not db and not graphiti_deps:
        return "[Not Configured] No knowledge base connection available"

    try:
        results = []

        # Try Graphiti first if available
        if graphiti_deps and hasattr(graphiti_deps, "graphiti") and graphiti_deps.graphiti:
            search_results = await graphiti_deps.graphiti.search(query, num_results=max_results)
            for r in search_results:
                results.append(f"- {r.fact}" if hasattr(r, "fact") else f"- {r}")

        # Also search MongoDB
        if db:
            collection = db["research_knowledge"]
            cursor = (
                collection.find(
                    {"$text": {"$search": query}},
                    {"score": {"$meta": "textScore"}},
                )
                .sort([("score", {"$meta": "textScore"})])
                .limit(max_results)
            )

            async for doc in cursor:
                source = doc.get("source", "Unknown")
                content = doc.get("content", "")[:200]
                results.append(f"- [{source}]: {content}...")

        if not results:
            return f"No results found for: {query}"

        return f"Knowledge base results for '{query}':\n" + "\n".join(results)

    except Exception as e:
        logger.exception("Error querying knowledge")
        return f"[Error] Knowledge query failed: {e}"


async def research_and_store(request: ResearchAndStoreRequest) -> ResearchAndStoreResponse:
    """
    Research a topic and automatically store findings in the knowledge base.

    This composite tool performs a complete research workflow:
    1. Searches multiple sources (YouTube, web, Reddit, Hacker News, Dev.to)
    2. Filters results by recency and relevance
    3. Ingests matching content into the MongoDB RAG knowledge base
    4. Returns a summary of what was stored

    Supported sources:
    - youtube: YouTube videos (via transcript extraction)
    - web: General web articles (via SearXNG)
    - reddit: Reddit discussions (via site: search)
    - hackernews: Hacker News posts (via Algolia API)
    - devto: Dev.to articles (via public API)

    Args:
        request: ResearchAndStoreRequest with query, sources, recency filters, etc.

    Returns:
        ResearchAndStoreResponse with details of ingested content
    """
    import httpx
    from services.external.devto.client import search_devto
    from services.external.hackernews.client import search_hackernews

    start_time = datetime.now()
    errors: list[str] = []
    ingested_items: list[IngestedItem] = []
    skipped_items: list[IngestedItem] = []

    # Get the sources to search
    sources = request.get_sources()

    logger.info(
        f"research_and_store_started: query='{request.query}', "
        f"focus={request.focus}, sources={sources}"
    )

    # Counters
    videos_ingested = 0
    articles_ingested = 0
    reddit_ingested = 0
    hackernews_ingested = 0
    devto_ingested = 0
    total_chunks = 0
    items_found = 0

    try:
        # Calculate date cutoff for video recency filter
        cutoff_date = datetime.now() - timedelta(days=request.video_recency_days)

        async with httpx.AsyncClient(timeout=60.0) as client:
            # ================================================================
            # Phase 1: Search each source
            # ================================================================

            # YouTube search (via SearXNG site: search)
            if "youtube" in sources:
                youtube_query = f"{request.query} site:youtube.com"
                try:
                    response = await client.post(
                        "http://localhost:8000/api/v1/searxng/search",
                        json={
                            "query": youtube_query,
                            "result_count": request.max_videos * 2,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    youtube_results = []
                    for result in data.get("results", []):
                        url = result.get("url", "")
                        if "youtube.com/watch" in url or "youtu.be/" in url:
                            youtube_results.append(
                                {
                                    "type": "video",
                                    "source": "youtube",
                                    "url": url,
                                    "title": result.get("title", ""),
                                    "content": result.get("content", ""),
                                }
                            )
                    items_found += len(youtube_results)
                    logger.info(f"YouTube search found {len(youtube_results)} results")

                    # Ingest YouTube videos
                    for item in youtube_results[: request.max_videos]:
                        if videos_ingested >= request.max_videos:
                            break
                        result = await _ingest_youtube_video(
                            client, item, request, cutoff_date, ingested_items, skipped_items
                        )
                        if result["success"]:
                            videos_ingested += 1
                            total_chunks += result.get("chunks", 0)

                except Exception as e:
                    logger.warning(f"YouTube search failed: {e}")
                    errors.append(f"YouTube search error: {e}")

            # Web articles (via SearXNG, excluding YouTube)
            if "web" in sources:
                article_query = f"{request.query} -site:youtube.com -site:reddit.com"
                try:
                    response = await client.post(
                        "http://localhost:8000/api/v1/searxng/search",
                        json={
                            "query": article_query,
                            "result_count": request.max_articles * 2,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    web_results = []
                    for result in data.get("results", []):
                        url = result.get("url", "")
                        if "youtube.com" not in url and "reddit.com" not in url:
                            web_results.append(
                                {
                                    "type": "article",
                                    "source": "web",
                                    "url": url,
                                    "title": result.get("title", ""),
                                    "content": result.get("content", ""),
                                }
                            )
                    items_found += len(web_results)
                    logger.info(f"Web search found {len(web_results)} results")

                    # Ingest web articles
                    for item in web_results[: request.max_articles]:
                        if articles_ingested >= request.max_articles:
                            break
                        result = await _ingest_web_article(client, item, ingested_items)
                        if result["success"]:
                            articles_ingested += 1
                            total_chunks += result.get("chunks", 0)

                except Exception as e:
                    logger.warning(f"Web search failed: {e}")
                    errors.append(f"Web search error: {e}")

            # Reddit (via SearXNG site: search)
            if "reddit" in sources:
                # Build Reddit query - optionally filter by subreddits
                if request.subreddits:
                    # Search specific subreddits
                    for subreddit in request.subreddits[:3]:  # Limit to 3 subreddits
                        reddit_query = f"{request.query} site:reddit.com/r/{subreddit}"
                        await _search_and_ingest_reddit(
                            client,
                            reddit_query,
                            request,
                            items_found,
                            reddit_ingested,
                            total_chunks,
                            ingested_items,
                            errors,
                        )
                else:
                    reddit_query = f"{request.query} site:reddit.com"
                    result = await _search_and_ingest_reddit(
                        client,
                        reddit_query,
                        request,
                        items_found,
                        reddit_ingested,
                        total_chunks,
                        ingested_items,
                        errors,
                    )
                    items_found += result.get("found", 0)
                    reddit_ingested += result.get("ingested", 0)
                    total_chunks += result.get("chunks", 0)

            # Hacker News (via Algolia API - free, no auth)
            if "hackernews" in sources:
                try:
                    hn_results = await search_hackernews(
                        query=request.query,
                        num_results=request.max_community_posts,
                        sort_by="relevance",
                    )
                    items_found += len(hn_results)
                    logger.info(f"Hacker News search found {len(hn_results)} results")

                    # Ingest HN stories
                    for item in hn_results[: request.max_community_posts]:
                        if hackernews_ingested >= request.max_community_posts:
                            break
                        result = await _ingest_hackernews_story(client, item, ingested_items)
                        if result["success"]:
                            hackernews_ingested += 1
                            total_chunks += result.get("chunks", 0)

                except Exception as e:
                    logger.warning(f"Hacker News search failed: {e}")
                    errors.append(f"Hacker News search error: {e}")

            # Dev.to (via public API - free, no auth)
            if "devto" in sources:
                try:
                    # Search Dev.to with relevant AI/coding tags
                    devto_results = await search_devto(
                        query=request.query,
                        num_results=request.max_community_posts,
                    )
                    items_found += len(devto_results)
                    logger.info(f"Dev.to search found {len(devto_results)} results")

                    # Ingest Dev.to articles
                    for item in devto_results[: request.max_community_posts]:
                        if devto_ingested >= request.max_community_posts:
                            break
                        result = await _ingest_devto_article(client, item, ingested_items)
                        if result["success"]:
                            devto_ingested += 1
                            total_chunks += result.get("chunks", 0)

                except Exception as e:
                    logger.warning(f"Dev.to search failed: {e}")
                    errors.append(f"Dev.to search error: {e}")

        # ================================================================
        # Phase 2: Build response
        # ================================================================
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        successful_items = [i for i in ingested_items if i.success]
        community_posts_ingested = reddit_ingested + hackernews_ingested + devto_ingested

        logger.info(
            f"research_and_store_completed: query='{request.query}', "
            f"videos={videos_ingested}, articles={articles_ingested}, "
            f"reddit={reddit_ingested}, hn={hackernews_ingested}, devto={devto_ingested}, "
            f"chunks={total_chunks}, time={processing_time:.2f}ms"
        )

        return ResearchAndStoreResponse(
            success=len(errors) == 0 and len(successful_items) > 0,
            query=request.query,
            focus=request.focus,
            sources_searched=sources,
            items_found=items_found,
            items_ingested=len(successful_items),
            videos_ingested=videos_ingested,
            articles_ingested=articles_ingested,
            community_posts_ingested=community_posts_ingested,
            reddit_ingested=reddit_ingested,
            hackernews_ingested=hackernews_ingested,
            devto_ingested=devto_ingested,
            total_chunks_created=total_chunks,
            ingested_items=ingested_items,
            skipped_items=skipped_items,
            errors=errors,
            processing_time_ms=processing_time,
            project_scope=request.project_scope,
            tags=request.tags,
        )

    except Exception as e:
        logger.exception(f"research_and_store_failed: {e}")
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        return ResearchAndStoreResponse(
            success=False,
            query=request.query,
            focus=request.focus,
            sources_searched=sources,
            errors=[str(e)],
            processing_time_ms=processing_time,
            project_scope=request.project_scope,
            tags=request.tags,
        )


async def _ingest_youtube_video(
    client: Any,
    item: dict,
    request: ResearchAndStoreRequest,
    cutoff_date: datetime,
    ingested_items: list[IngestedItem],
    skipped_items: list[IngestedItem],
) -> dict:
    """Ingest a YouTube video and return result."""
    try:
        logger.info(f"Ingesting YouTube video: {item['url']}")

        response = await client.post(
            "http://localhost:8000/api/v1/youtube/ingest",
            json={
                "url": item["url"],
                "extract_chapters": True,
                "extract_entities": request.extract_entities,
                "extract_topics": request.extract_topics,
                "chunk_by_chapters": True,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            # Check recency filter
            should_skip = False
            published_date = None

            if result.get("upload_date"):
                try:
                    upload_dt = datetime.strptime(result["upload_date"], "%Y%m%d")
                    published_date = upload_dt.strftime("%Y-%m-%d")
                    if upload_dt < cutoff_date:
                        should_skip = True
                except ValueError:
                    pass

            if result.get("skipped"):
                skipped_items.append(
                    IngestedItem(
                        type="video",
                        url=item["url"],
                        title=result.get("title", item["title"]),
                        success=True,
                        error=result.get("skipped_reason", "Already exists"),
                        published_date=published_date,
                        source="youtube",
                    )
                )
                return {"success": False}
            elif should_skip:
                skipped_items.append(
                    IngestedItem(
                        type="video",
                        url=item["url"],
                        title=result.get("title", item["title"]),
                        success=True,
                        error=f"Video too old (published {published_date})",
                        published_date=published_date,
                        source="youtube",
                    )
                )
                return {"success": False}
            else:
                ingested_items.append(
                    IngestedItem(
                        type="video",
                        url=item["url"],
                        title=result.get("title", item["title"]),
                        document_id=result.get("document_id"),
                        chunks_created=result.get("chunks_created", 0),
                        success=True,
                        published_date=published_date,
                        source="youtube",
                    )
                )
                return {"success": True, "chunks": result.get("chunks_created", 0)}
        else:
            ingested_items.append(
                IngestedItem(
                    type="video",
                    url=item["url"],
                    title=item["title"],
                    success=False,
                    error="; ".join(result.get("errors", ["Unknown error"])),
                    source="youtube",
                )
            )
            return {"success": False}

    except Exception as e:
        logger.warning(f"Failed to ingest YouTube video {item['url']}: {e}")
        ingested_items.append(
            IngestedItem(
                type="video",
                url=item["url"],
                title=item.get("title", ""),
                success=False,
                error=str(e),
                source="youtube",
            )
        )
        return {"success": False}


async def _ingest_web_article(
    client: Any,
    item: dict,
    ingested_items: list[IngestedItem],
) -> dict:
    """Ingest a web article via crawl and return result."""
    try:
        logger.info(f"Crawling and ingesting article: {item['url']}")

        response = await client.post(
            "http://localhost:8000/api/v1/crawl/single",
            json={
                "url": item["url"],
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            ingested_items.append(
                IngestedItem(
                    type="article",
                    url=item["url"],
                    title=result.get("title", item.get("title", "")),
                    document_id=(
                        result.get("document_ids", [None])[0]
                        if result.get("document_ids")
                        else None
                    ),
                    chunks_created=result.get("chunks_created", 0),
                    success=True,
                    source="web",
                )
            )
            return {"success": True, "chunks": result.get("chunks_created", 0)}
        else:
            ingested_items.append(
                IngestedItem(
                    type="article",
                    url=item["url"],
                    title=item.get("title", ""),
                    success=False,
                    error=result.get("error", "Unknown error"),
                    source="web",
                )
            )
            return {"success": False}

    except Exception as e:
        logger.warning(f"Failed to ingest article {item['url']}: {e}")
        ingested_items.append(
            IngestedItem(
                type="article",
                url=item["url"],
                title=item.get("title", ""),
                success=False,
                error=str(e),
                source="web",
            )
        )
        return {"success": False}


async def _search_and_ingest_reddit(
    client: Any,
    query: str,
    request: ResearchAndStoreRequest,
    items_found: int,
    reddit_ingested: int,
    total_chunks: int,
    ingested_items: list[IngestedItem],
    errors: list[str],
) -> dict:
    """Search Reddit via SearXNG and ingest results."""
    found = 0
    ingested = 0
    chunks = 0

    try:
        response = await client.post(
            "http://localhost:8000/api/v1/searxng/search",
            json={
                "query": query,
                "result_count": request.max_community_posts * 2,
            },
        )
        response.raise_for_status()
        data = response.json()

        reddit_results = []
        for result in data.get("results", []):
            url = result.get("url", "")
            if "reddit.com" in url:
                reddit_results.append(
                    {
                        "type": "reddit",
                        "source": "reddit",
                        "url": url,
                        "title": result.get("title", ""),
                        "content": result.get("content", ""),
                    }
                )
        found = len(reddit_results)
        logger.info(f"Reddit search found {found} results")

        # Ingest Reddit posts (crawl them)
        for item in reddit_results[: request.max_community_posts]:
            result = await _ingest_reddit_post(client, item, ingested_items)
            if result["success"]:
                ingested += 1
                chunks += result.get("chunks", 0)

    except Exception as e:
        logger.warning(f"Reddit search failed: {e}")
        errors.append(f"Reddit search error: {e}")

    return {"found": found, "ingested": ingested, "chunks": chunks}


async def _ingest_reddit_post(
    client: Any,
    item: dict,
    ingested_items: list[IngestedItem],
) -> dict:
    """Ingest a Reddit post via crawl and return result."""
    try:
        logger.info(f"Crawling Reddit post: {item['url']}")

        response = await client.post(
            "http://localhost:8000/api/v1/crawl/single",
            json={
                "url": item["url"],
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            ingested_items.append(
                IngestedItem(
                    type="reddit",
                    url=item["url"],
                    title=result.get("title", item.get("title", "")),
                    document_id=(
                        result.get("document_ids", [None])[0]
                        if result.get("document_ids")
                        else None
                    ),
                    chunks_created=result.get("chunks_created", 0),
                    success=True,
                    source="reddit",
                )
            )
            return {"success": True, "chunks": result.get("chunks_created", 0)}
        else:
            ingested_items.append(
                IngestedItem(
                    type="reddit",
                    url=item["url"],
                    title=item.get("title", ""),
                    success=False,
                    error=result.get("error", "Unknown error"),
                    source="reddit",
                )
            )
            return {"success": False}

    except Exception as e:
        logger.warning(f"Failed to ingest Reddit post {item['url']}: {e}")
        ingested_items.append(
            IngestedItem(
                type="reddit",
                url=item["url"],
                title=item.get("title", ""),
                success=False,
                error=str(e),
                source="reddit",
            )
        )
        return {"success": False}


async def _ingest_hackernews_story(
    client: Any,
    item: dict,
    ingested_items: list[IngestedItem],
) -> dict:
    """Ingest a Hacker News story and return result."""
    try:
        # HN stories can be either external links or self-posts
        url = item.get("url") or item.get(
            "hn_url", f"https://news.ycombinator.com/item?id={item.get('id')}"
        )
        logger.info(f"Crawling Hacker News story: {url}")

        response = await client.post(
            "http://localhost:8000/api/v1/crawl/single",
            json={
                "url": url,
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            ingested_items.append(
                IngestedItem(
                    type="hackernews",
                    url=url,
                    title=result.get("title", item.get("title", "")),
                    document_id=(
                        result.get("document_ids", [None])[0]
                        if result.get("document_ids")
                        else None
                    ),
                    chunks_created=result.get("chunks_created", 0),
                    success=True,
                    source="hackernews",
                    author=item.get("author"),
                    score=item.get("score"),
                )
            )
            return {"success": True, "chunks": result.get("chunks_created", 0)}
        else:
            ingested_items.append(
                IngestedItem(
                    type="hackernews",
                    url=url,
                    title=item.get("title", ""),
                    success=False,
                    error=result.get("error", "Unknown error"),
                    source="hackernews",
                )
            )
            return {"success": False}

    except Exception as e:
        url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}"
        logger.warning(f"Failed to ingest HN story {url}: {e}")
        ingested_items.append(
            IngestedItem(
                type="hackernews",
                url=url,
                title=item.get("title", ""),
                success=False,
                error=str(e),
                source="hackernews",
            )
        )
        return {"success": False}


async def _ingest_devto_article(
    client: Any,
    item: dict,
    ingested_items: list[IngestedItem],
) -> dict:
    """Ingest a Dev.to article and return result."""
    try:
        url = item.get("url", "")
        logger.info(f"Crawling Dev.to article: {url}")

        response = await client.post(
            "http://localhost:8000/api/v1/crawl/single",
            json={
                "url": url,
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            ingested_items.append(
                IngestedItem(
                    type="devto",
                    url=url,
                    title=result.get("title", item.get("title", "")),
                    document_id=(
                        result.get("document_ids", [None])[0]
                        if result.get("document_ids")
                        else None
                    ),
                    chunks_created=result.get("chunks_created", 0),
                    success=True,
                    source="devto",
                    author=item.get("author_username"),
                    score=item.get("reactions_count"),
                )
            )
            return {"success": True, "chunks": result.get("chunks_created", 0)}
        else:
            ingested_items.append(
                IngestedItem(
                    type="devto",
                    url=url,
                    title=item.get("title", ""),
                    success=False,
                    error=result.get("error", "Unknown error"),
                    source="devto",
                )
            )
            return {"success": False}

    except Exception as e:
        url = item.get("url", "")
        logger.warning(f"Failed to ingest Dev.to article {url}: {e}")
        ingested_items.append(
            IngestedItem(
                type="devto",
                url=url,
                title=item.get("title", ""),
                success=False,
                error=str(e),
                source="devto",
            )
        )
        return {"success": False}


__all__ = [
    "fetch_page",
    "ingest_knowledge",
    "parse_document",
    "query_knowledge",
    "research_and_store",
    "search_web",
]
