"""YouTube content ingestion into MongoDB RAG.

This module provides YouTube video ingestion capabilities.

For ingestion, use the centralized ContentIngestionService:

    from capabilities.retrieval.mongo_rag.ingestion.content_service import ContentIngestionService

    service = ContentIngestionService()
    await service.initialize()
    result = await service.ingest_scraped_content(scraped_content)
    await service.close()

Or use the /api/v1/youtube/ingest endpoint directly.
"""

# No exports - use ContentIngestionService from mongo_rag instead
__all__: list[str] = []
