"""API module - re-exports routers from workflows and capabilities.

This module acts as a facade, aggregating all workflow and capability routers
into a single import location for the main FastAPI application.
"""

# Workflow: Chat
# Capability: Calendar
from capabilities.calendar.calendar_sync.router import router as calendar_sync
from capabilities.calendar.router import router as calendar

# Capability: Knowledge Graph
from capabilities.knowledge_graph.knowledge.router import router as knowledge
from capabilities.knowledge_graph.knowledge_base.router import router as knowledge_base

# Capability: Persona
from capabilities.persona.persona_state.router import router as persona

# Capability: Processing
from capabilities.processing.openwebui_topics.router import router as openwebui_topics
from capabilities.retrieval.graphiti_rag.router import router as graphiti_rag

# Capability: Retrieval
from capabilities.retrieval.mongo_rag.router import router as mongo_rag
from mcp_server.router import router as mcp_rest
from services.auth.router import router as auth

# Workflow: Automation
from workflows.automation.n8n_workflow.router import router as n8n_workflow
from workflows.chat.conversation.router import router as conversation

# Workflow: Ingestion
from workflows.ingestion.crawl4ai_rag.router import router as crawl4ai_rag
from workflows.ingestion.openwebui_export.router import router as openwebui_export
from workflows.ingestion.youtube_rag.router import router as youtube_rag

# Server-level routers
from server.admin import router as admin
from server.data_view import router as data_view
from server.health import router as health

__all__ = [
    "admin",
    "auth",
    "calendar",
    "calendar_sync",
    "conversation",
    "crawl4ai_rag",
    "data_view",
    "graphiti_rag",
    "health",
    "knowledge",
    "knowledge_base",
    "mcp_rest",
    "mongo_rag",
    "n8n_workflow",
    "openwebui_export",
    "openwebui_topics",
    "persona",
    "youtube_rag",
]
