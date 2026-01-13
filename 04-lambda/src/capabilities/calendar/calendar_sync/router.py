"""Calendar sync REST API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from src.capabilities.retrieval.mongo_rag.dependencies import AgentDependencies
from src.server.core.api_utils import DependencyContext
from src.shared.dependency_factory import create_dependency_factory
from src.workflows.automation.n8n_workflow.ai.dependencies import N8nWorkflowDeps

router = APIRouter()
logger = logging.getLogger(__name__)

# Use dependency factory to create deps getter (eliminates boilerplate)
get_agent_deps_for_sync = create_dependency_factory(AgentDependencies)


class CalendarSyncRequest(BaseModel):
    """Request to sync an event from a website to Google Calendar."""

    url: str = Field(..., description="Website URL to scrape for event information")
    event_name_pattern: str | None = Field(
        None, description="Optional pattern or name to use for the event"
    )
    calendar_id: str = Field("primary", description="Google Calendar ID (default: 'primary')")
    timezone: str = Field("America/New_York", description="Timezone for the event")
    location_pattern: str | None = Field(
        None, description="Optional location pattern or specific location string"
    )
    description_template: str | None = Field(
        None, description="Optional description template or specific description"
    )
    workflow_name: str = Field(
        "Scrape Event To Calendar", description="Name of the n8n workflow to use"
    )


class CalendarSyncResponse(BaseModel):
    """Response from calendar sync operation."""

    success: bool = Field(..., description="Whether the sync was successful")
    url: str = Field(..., description="URL that was scraped")
    calendar_id: str = Field(..., description="Calendar ID where event was created/updated")
    action: str | None = Field(None, description="Action taken: 'created' or 'updated'")
    event_id: str | None = Field(None, description="Google Calendar event ID")
    summary: str | None = Field(None, description="Event summary/title")
    start: str | None = Field(None, description="Event start date/time")
    end: str | None = Field(None, description="Event end date/time")
    message: str | None = Field(None, description="Additional message or error details")
    errors: list = Field(default_factory=list, description="List of any errors encountered")


@router.post("/sync", response_model=CalendarSyncResponse)
async def sync_event_to_calendar(
    request: CalendarSyncRequest,
    deps_rag: Annotated[AgentDependencies, Depends(get_agent_deps_for_sync)],
):
    """
    Scrape event information from a website and create/update a Google Calendar event.

    This endpoint first checks if the website content already exists in the RAG knowledge base.
    If found, it extracts event data from the cached HTML content. If not found, it crawls the
    website (which automatically ingests it into RAG), then extracts event data.
    Finally, it creates or updates a Google Calendar event via the n8n workflow.

    **Use Cases:**
    - Sync event information from websites to Google Calendar
    - Automatically keep calendar updated with event details
    - Use cached content from RAG to avoid re-scraping

    **Request Body:**
    ```json
    {
        "url": "https://www.bluesmuse.dance/",
        "calendar_id": "primary",
        "timezone": "America/New_York",
        "event_name_pattern": "Blues Muse 2026",
        "location_pattern": "Philadelphia, PA"
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "url": "https://www.bluesmuse.dance/",
        "calendar_id": "primary",
        "action": "created",
        "event_id": "abc123...",
        "summary": "Blues Muse 2026",
        "start": "20261016T000000Z",
        "end": "20261018T235959Z",
        "message": "Event synced successfully",
        "errors": []
    }
    ```

    **Parameters:**
    - `url` (required): Website URL to scrape for event information
    - `event_name_pattern` (optional): Pattern or name to use for the event
    - `calendar_id` (optional, default: "primary"): Google Calendar ID
    - `timezone` (optional, default: "America/New_York"): Timezone for the event
    - `location_pattern` (optional): Location pattern or specific location string
    - `description_template` (optional): Description template or specific description
    - `workflow_name` (optional, default: "Scrape Event To Calendar"): Name of the n8n workflow

    **Returns:**
    - `CalendarSyncResponse` with success status, event details, and any errors

    **Errors:**
    - `500`: If RAG check fails, crawling fails, or workflow execution fails
    - `404`: If the specified n8n workflow is not found

    **Integration:**
    - Also available as MCP tool: `scrape_event_to_calendar`
    - Uses RAG knowledge base to cache HTML content
    - Automatically crawls and ingests content if not in RAG
    """
    import httpx

    from server.api.n8n_workflow import list_workflows_endpoint
    from server.config import settings

    try:
        # Step 1: Check if content already exists in RAG and get HTML
        logger.info(f"Checking RAG for existing content: {request.url}")
        cached_html = None
        content_found = False

        try:
            # Query MongoDB directly for document by source URL
            # deps_rag is already initialized via FastAPI dependency injection
            from src.capabilities.retrieval.mongo_rag.config import config

            documents_collection = deps_rag.db[config.mongodb_collection_documents]
            # Find document by exact source URL match
            document = await documents_collection.find_one({"source": request.url})

            if document:
                content_found = True
                # Get HTML from metadata if available
                metadata = document.get("metadata", {})
                cached_html = metadata.get("original_html")
                if cached_html:
                    logger.info(
                        f"Found cached HTML in RAG for {request.url} ({len(cached_html)} chars)"
                    )
                else:
                    logger.info(f"Found document in RAG for {request.url} but no HTML stored")
            else:
                logger.info(f"No document found in RAG for {request.url}")

        except Exception as e:
            logger.warning(f"Error checking RAG: {e}. Will proceed with fresh scrape.")
            content_found = False

        # Step 2: If content not found, crawl and ingest into RAG
        if not content_found:
            logger.info(f"Content not found in RAG. Crawling and ingesting: {request.url}")
            try:
                from src.server.api.crawl4ai_rag import crawl_single
                from src.workflows.ingestion.crawl4ai_rag.schemas import CrawlSinglePageRequest

                crawl_request = CrawlSinglePageRequest(
                    url=request.url, chunk_size=1000, chunk_overlap=200
                )
                crawl_result = await crawl_single(crawl_request)
                logger.info(
                    f"Crawled and ingested {request.url} into RAG. Chunks: {crawl_result.chunks_created}"
                )
            except Exception as e:
                logger.warning(f"Error crawling page: {e}. Will proceed with workflow scrape.")
                # Continue to workflow as fallback

        # Step 3: Find the workflow by name and call it
        async with DependencyContext(N8nWorkflowDeps):
            # List workflows to find by name
            workflows_result = await list_workflows_endpoint(active_only=False)
            workflows = workflows_result.get("workflows", [])

            workflow_id = None
            webhook_path = None

            # Find workflow by name
            for workflow in workflows:
                if workflow.get("name") == request.workflow_name:
                    workflow_id = workflow.get("id")
                    # Try to get webhook path from workflow nodes
                    nodes = workflow.get("nodes", [])
                    for node in nodes:
                        if node.get("type") == "n8n-nodes-base.webhook":
                            webhook_path = node.get("parameters", {}).get("path")
                            break
                    break

            if not workflow_id:
                raise HTTPException(
                    status_code=404,
                    detail=f"Workflow '{request.workflow_name}' not found. Please create it first.",
                )

            # Construct webhook URL
            base_url = settings.n8n_api_url.replace("/api/v1", "")
            webhook_url = f"{base_url}/webhook/{webhook_path}" if webhook_path else None

            # Prepare request payload
            payload = {
                "url": request.url,
                "calendar_id": request.calendar_id,
                "timezone": request.timezone,
            }

            # If we have cached HTML, pass it to skip scraping
            if cached_html:
                payload["html_content"] = cached_html
                logger.info(f"Passing cached HTML to workflow ({len(cached_html)} chars)")

            if request.event_name_pattern:
                payload["event_name_pattern"] = request.event_name_pattern
            if request.location_pattern:
                payload["location_pattern"] = request.location_pattern
            if request.description_template:
                payload["description_template"] = request.description_template

            # Call webhook or execute workflow
            if webhook_url:
                # Call webhook directly
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(webhook_url, json=payload)
                    response.raise_for_status()
                    result = response.json()
            else:
                # Fallback: use execute_workflow API
                from src.server.api.n8n_workflow import execute_workflow_endpoint
                from src.workflows.automation.n8n_workflow.ai.models import ExecuteWorkflowRequest

                execute_request = ExecuteWorkflowRequest(
                    workflow_id=workflow_id, input_data={"body": payload}
                )
                execute_result = await execute_workflow_endpoint(execute_request)
                result = execute_result.dict()
                if "data" in result:
                    result = result["data"]

            # Convert workflow result to API response format
            return CalendarSyncResponse(
                success=result.get("action") in ["created", "updated"],
                url=request.url,
                calendar_id=request.calendar_id,
                action=result.get("action"),
                event_id=result.get("eventId"),
                summary=result.get("summary"),
                start=result.get("start"),
                end=result.get("end"),
                message=f"Event {result.get('action', 'processed')} successfully",
                errors=[],
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("calendar_sync_error")
        raise HTTPException(status_code=500, detail=f"Failed to sync event: {e!s}") from e
