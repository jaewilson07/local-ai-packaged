"""Knowledge Base REST API endpoints."""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated, Any

import openai
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo import AsyncMongoClient
from src.capabilities.knowledge_graph.knowledge_base.config import config
from src.capabilities.knowledge_graph.knowledge_base.models import (
    Article,
    ArticleCreateRequest,
    ArticleEditProposal,
    ArticleListResponse,
    ArticleSearchRequest,
    ArticleUpdateRequest,
    ChatQueryRequest,
    ChatQueryResponse,
    FetchUrlRequest,
    ProposalCreateRequest,
    ProposalReviewRequest,
    ProposalStatus,
)
from src.capabilities.knowledge_graph.knowledge_base.services.article_service import ArticleService
from src.capabilities.knowledge_graph.knowledge_base.services.chat_service import ChatService
from src.capabilities.knowledge_graph.knowledge_base.services.notification_service import (
    NotificationService,
)
from src.capabilities.knowledge_graph.knowledge_base.services.proposal_service import (
    ProposalService,
)
from src.services.auth.dependencies import get_current_user
from src.services.auth.models import User
from src.shared.constants import DatabaseDefaults

router = APIRouter(prefix="/api/v1/kb", tags=["knowledge_base"])
logger = logging.getLogger(__name__)


# Dependency to get MongoDB client and services
async def get_services(
    user: User = Depends(get_current_user),
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Dependency that yields Knowledge Base services.

    Creates MongoDB connection and service instances.
    """
    mongo_client = AsyncMongoClient(
        config.mongodb_uri, serverSelectionTimeoutMS=DatabaseDefaults.MONGO_TIMEOUT_MS
    )
    openai_client = openai.AsyncOpenAI(
        api_key=config.embedding_api_key,
        base_url=config.embedding_base_url,
    )

    article_service = ArticleService(mongo_client, openai_client)
    notification_service = NotificationService(mongo_client)
    proposal_service = ProposalService(mongo_client, article_service, notification_service)
    chat_service = ChatService(openai_client)

    try:
        yield {
            "user": user,
            "article_service": article_service,
            "proposal_service": proposal_service,
            "chat_service": chat_service,
            "notification_service": notification_service,
        }
    finally:
        await mongo_client.close()


# ============================================================================
# Article Endpoints
# ============================================================================


@router.get("/articles", response_model=ArticleListResponse)
async def list_articles(
    services: Annotated[dict, Depends(get_services)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source_type: str | None = None,
    tags: str | None = None,
):
    """
    List articles with pagination and filtering.

    **Parameters:**
    - `page`: Page number (1-indexed)
    - `per_page`: Items per page (1-100)
    - `source_type`: Filter by source (circle_so, dev_to, manual, etc.)
    - `tags`: Comma-separated list of tags to filter by
    """
    article_service = services["article_service"]

    tags_list = tags.split(",") if tags else None
    articles, total = await article_service.list_articles(
        page=page,
        per_page=per_page,
        source_type=source_type,
        tags=tags_list,
    )

    return ArticleListResponse(
        articles=articles,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/articles/{article_id}")
async def get_article(
    article_id: str,
    services: Annotated[dict, Depends(get_services)],
) -> Article:
    """Get a single article by ID."""
    article_service = services["article_service"]
    article = await article_service.get_article(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return article


@router.get("/articles/slug/{slug}")
async def get_article_by_slug(
    slug: str,
    services: Annotated[dict, Depends(get_services)],
) -> Article:
    """Get a single article by slug."""
    article_service = services["article_service"]
    article = await article_service.get_article_by_slug(slug)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return article


@router.post("/articles")
async def create_article(
    request: ArticleCreateRequest,
    services: Annotated[dict, Depends(get_services)],
) -> Article:
    """
    Create a new article.

    The current user becomes the article owner.
    """
    user = services["user"]
    article_service = services["article_service"]

    article = await article_service.create_article(request, user.email)
    return article


@router.put("/articles/{article_id}")
async def update_article(
    article_id: str,
    request: ArticleUpdateRequest,
    services: Annotated[dict, Depends(get_services)],
) -> Article:
    """
    Update an article (owner only).

    Creates a version history entry for the change.
    """
    user = services["user"]
    article_service = services["article_service"]

    # Check ownership
    article = await article_service.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.author_email != user.email and user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only the article owner can directly edit. Use the proposal system instead.",
        )

    updated = await article_service.update_article(article_id, request, user.email)
    return updated


@router.delete("/articles/{article_id}")
async def delete_article(
    article_id: str,
    services: Annotated[dict, Depends(get_services)],
):
    """Delete an article (owner or admin only)."""
    user = services["user"]
    article_service = services["article_service"]

    article = await article_service.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.author_email != user.email and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the article owner can delete")

    await article_service.delete_article(article_id)
    return {"success": True, "message": "Article deleted"}


@router.get("/articles/{article_id}/history")
async def get_article_history(
    article_id: str,
    services: Annotated[dict, Depends(get_services)],
):
    """Get version history for an article."""
    article_service = services["article_service"]
    history = await article_service.get_article_history(article_id)
    return {"history": [h.model_dump() for h in history]}


@router.post("/search")
async def search_articles(
    request: ArticleSearchRequest,
    services: Annotated[dict, Depends(get_services)],
):
    """
    Search articles using semantic similarity.

    Uses vector embeddings for conceptual matching.
    """
    article_service = services["article_service"]

    try:
        results = await article_service.search_articles(
            request.query,
            request.match_count,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Proposal Endpoints
# ============================================================================


@router.post("/proposals")
async def create_proposal(
    request: ProposalCreateRequest,
    services: Annotated[dict, Depends(get_services)],
) -> dict[str, Any]:
    """
    Submit an article edit proposal.

    The proposal will be reviewed by the article owner.
    """
    user = services["user"]
    proposal_service = services["proposal_service"]

    try:
        proposal = await proposal_service.create_proposal(request, user.email)
        return {"success": True, "proposal_id": proposal.id, "proposal": proposal}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/proposals/mine")
async def get_my_proposals(
    services: Annotated[dict, Depends(get_services)],
    status: str | None = None,
):
    """Get proposals submitted by the current user."""
    user = services["user"]
    proposal_service = services["proposal_service"]

    status_enum = ProposalStatus(status) if status else None
    proposals = await proposal_service.list_user_proposals(user.email, status_enum)

    return {"proposals": [p.model_dump() for p in proposals], "count": len(proposals)}


@router.get("/proposals/review")
async def get_proposals_for_review(
    services: Annotated[dict, Depends(get_services)],
):
    """Get proposals pending review for articles owned by current user."""
    user = services["user"]
    proposal_service = services["proposal_service"]

    proposals = await proposal_service.list_proposals_for_review(user.email)

    return {"proposals": [p.model_dump() for p in proposals], "count": len(proposals)}


@router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    services: Annotated[dict, Depends(get_services)],
) -> ArticleEditProposal:
    """Get a single proposal by ID."""
    proposal_service = services["proposal_service"]
    proposal = await proposal_service.get_proposal(proposal_id)

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return proposal


@router.post("/proposals/{proposal_id}/review")
async def review_proposal(
    proposal_id: str,
    request: ProposalReviewRequest,
    services: Annotated[dict, Depends(get_services)],
):
    """
    Review a proposal (approve, reject, or request changes).

    Only the article owner can review proposals.
    """
    user = services["user"]
    proposal_service = services["proposal_service"]

    try:
        proposal = await proposal_service.review_proposal(
            proposal_id,
            request,
            user.email,
        )
        return {
            "success": True,
            "message": f"Proposal {request.action}ed",
            "proposal": proposal,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/proposals/{proposal_id}")
async def cancel_proposal(
    proposal_id: str,
    services: Annotated[dict, Depends(get_services)],
):
    """Cancel a pending proposal (proposer only)."""
    user = services["user"]
    proposal_service = services["proposal_service"]

    success = await proposal_service.cancel_proposal(proposal_id, user.email)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Could not cancel proposal. It may not exist, not be yours, or not be pending.",
        )

    return {"success": True, "message": "Proposal cancelled"}


@router.get("/proposals/stats")
async def get_proposal_stats(
    services: Annotated[dict, Depends(get_services)],
):
    """Get proposal statistics for the current user."""
    user = services["user"]
    proposal_service = services["proposal_service"]

    stats = await proposal_service.get_proposal_stats(user.email)
    return {"stats": stats}


# ============================================================================
# Chat Endpoints
# ============================================================================


@router.post("/chat", response_model=ChatQueryResponse)
async def chat_query(
    request: ChatQueryRequest,
    services: Annotated[dict, Depends(get_services)],
):
    """
    Chat with the knowledge base using RAG context.

    Combines knowledge base results and web search results to generate
    an informed response with citations.
    """
    chat_service = services["chat_service"]

    result = await chat_service.chat(
        request.query,
        request.rag_results,
        request.web_results,
    )

    return ChatQueryResponse(
        answer=result["answer"],
        citations=result["citations"],
    )


@router.post("/fetch-url")
async def fetch_url(
    request: FetchUrlRequest,
    services: Annotated[dict, Depends(get_services)],
):
    """
    Fetch and parse content from a URL.

    Used to display external sources in the article viewer.
    """
    chat_service = services["chat_service"]
    result = await chat_service.fetch_url_content(request.url)
    return result


# ============================================================================
# Import Endpoints
# ============================================================================


@router.post("/import/markdown")
async def import_markdown(
    title: str,
    content: str,
    services: Annotated[dict, Depends(get_services)],
    source_url: str | None = None,
    tags: str | None = None,
):
    """
    Import an article from markdown content.

    Used for bulk importing existing articles.
    """
    user = services["user"]
    article_service = services["article_service"]

    tags_list = tags.split(",") if tags else []
    article = await article_service.import_from_markdown(
        title=title,
        content=content,
        source_url=source_url,
        author_email=user.email,
        tags=tags_list,
    )

    return {"success": True, "article": article}


# ============================================================================
# Notification Endpoints
# ============================================================================


@router.get("/notifications")
async def get_notifications(
    services: Annotated[dict, Depends(get_services)],
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
):
    """Get notifications for the current user."""
    user = services["user"]
    notification_service = services["notification_service"]

    notifications = await notification_service.get_user_notifications(
        user.email,
        unread_only=unread_only,
        limit=limit,
    )

    unread_count = await notification_service.get_unread_count(user.email)

    return {
        "notifications": notifications,
        "count": len(notifications),
        "unread_count": unread_count,
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    services: Annotated[dict, Depends(get_services)],
):
    """Mark a notification as read."""
    user = services["user"]
    notification_service = services["notification_service"]

    success = await notification_service.mark_notification_read(
        notification_id,
        user.email,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"success": True}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    services: Annotated[dict, Depends(get_services)],
):
    """Mark all notifications as read."""
    user = services["user"]
    notification_service = services["notification_service"]

    count = await notification_service.mark_all_read(user.email)
    return {"success": True, "marked_read": count}


@router.get("/notifications/count")
async def get_unread_count(
    services: Annotated[dict, Depends(get_services)],
):
    """Get count of unread notifications."""
    user = services["user"]
    notification_service = services["notification_service"]

    count = await notification_service.get_unread_count(user.email)
    return {"unread_count": count}


# ============================================================================
# Re-indexing Endpoints
# ============================================================================


@router.post("/articles/{article_id}/reindex")
async def reindex_article(
    article_id: str,
    services: Annotated[dict, Depends(get_services)],
):
    """
    Manually trigger re-indexing (re-embedding) of an article.

    Useful when embeddings need to be regenerated or after manual edits.
    Only article owner or admin can trigger this.
    """
    user = services["user"]
    article_service = services["article_service"]

    article = await article_service.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.author_email != user.email and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only article owner can reindex")

    try:
        # Regenerate embedding
        embedding = await article_service.generate_embedding(article.content)

        # Update in database
        from bson import ObjectId

        await article_service.collection.update_one(
            {"_id": ObjectId(article_id)},
            {"$set": {"content_embedding": embedding}},
        )

        return {"success": True, "message": "Article re-indexed successfully"}

    except Exception as e:
        logger.error(f"Reindex error for {article_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Reindex failed: {e!s}") from e


@router.post("/articles/reindex-all")
async def reindex_all_articles(
    services: Annotated[dict, Depends(get_services)],
):
    """
    Trigger re-indexing of all articles owned by the current user.

    Admin can reindex all articles in the system.
    """
    user = services["user"]
    article_service = services["article_service"]

    # Build filter - admin sees all, others see their own
    filter_dict = {}
    if user.role != "admin":
        filter_dict["author_email"] = user.email

    # Count articles to reindex
    count = await article_service.collection.count_documents(filter_dict)

    if count == 0:
        return {"success": True, "message": "No articles to reindex", "reindexed": 0}

    # Reindex in batches
    reindexed = 0
    errors = []

    async for doc in article_service.collection.find(filter_dict):
        try:
            embedding = await article_service.generate_embedding(doc["content"])
            await article_service.collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"content_embedding": embedding}},
            )
            reindexed += 1
        except Exception as e:
            errors.append({"article_id": str(doc["_id"]), "error": str(e)})

    return {
        "success": True,
        "message": f"Reindexed {reindexed} of {count} articles",
        "reindexed": reindexed,
        "errors": errors if errors else None,
    }
