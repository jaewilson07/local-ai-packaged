"""REST API endpoints for YouTube RAG operations."""

import logging

from fastapi import APIRouter, Depends
from src.server.core.error_handling import handle_project_errors
from src.services.auth.dependencies import get_current_user
from src.services.auth.models import User
from src.workflows.ingestion.youtube_rag.dependencies import YouTubeRAGDeps
from src.workflows.ingestion.youtube_rag.models import (
    GetYouTubeMetadataRequest,
    GetYouTubeMetadataResponse,
    IngestYouTubeRequest,
    IngestYouTubeResponse,
)
from src.workflows.ingestion.youtube_rag.tools import (
    get_youtube_metadata as get_metadata_tool,
)
from src.workflows.ingestion.youtube_rag.tools import (
    ingest_youtube_video as ingest_tool,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/youtube", tags=["youtube-rag"])


@router.post("/ingest", response_model=IngestYouTubeResponse)
@handle_project_errors()
async def ingest_youtube_video(
    request: IngestYouTubeRequest,
    user: User = Depends(get_current_user),
) -> IngestYouTubeResponse:
    """
    Ingest a YouTube video into the MongoDB RAG knowledge base.

    Extracts transcript, metadata, chapters, and optionally entities/topics.
    The video becomes immediately searchable via search endpoints.
    """
    # Create deps without MongoDB since we're using ContentIngestionService
    deps = YouTubeRAGDeps.from_settings(
        preferred_language=request.preferred_language,
        skip_mongodb=True,
    )
    await deps.initialize()

    try:
        result = await ingest_tool(
            deps,
            request,
            user_id=str(user.id),
            user_email=user.email,
        )

        if not result.success and result.errors:
            # Return the result but with appropriate status
            # Don't raise HTTPException for partial success
            pass

        return result

    finally:
        await deps.cleanup()


@router.post("/metadata", response_model=GetYouTubeMetadataResponse)
@handle_project_errors()
async def get_youtube_metadata(request: GetYouTubeMetadataRequest) -> GetYouTubeMetadataResponse:
    """
    Get YouTube video metadata without ingesting.

    Useful for previewing video content before deciding to ingest.
    """
    deps = YouTubeRAGDeps.from_settings()
    await deps.initialize()

    try:
        result = await get_metadata_tool(deps, request)
        return result

    finally:
        await deps.cleanup()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint for YouTube RAG service."""
    try:
        # Try to import dependencies to verify they're available
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: F401

        transcript_api_available = True
    except ImportError:
        transcript_api_available = False

    try:
        import yt_dlp  # noqa: F401

        ytdlp_available = True
    except ImportError:
        ytdlp_available = False

    return {
        "status": "healthy" if transcript_api_available else "degraded",
        "youtube_transcript_api": transcript_api_available,
        "yt_dlp": ytdlp_available,
    }
