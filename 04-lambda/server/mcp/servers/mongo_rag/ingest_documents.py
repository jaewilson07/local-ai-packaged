"""Ingest documents into the MongoDB RAG knowledge base. Note: MCP doesn't support file uploads directly - files must already be on the server filesystem. For file uploads, use the REST API POST /api/v1/rag/ingest endpoint. Supported formats: PDF, Word, PowerPoint, Excel, HTML, Markdown, and audio files (with transcription)."""
from typing import Optional, List, Any, Literal
from server.mcp.servers.client import call_mcp_tool

async def ingest_documents(
    file_paths: List[str], clean_before: Optional[bool] = False
) -> dict:
    """
    Ingest documents into the MongoDB RAG knowledge base. Note: MCP doesn't support file uploads directly - files must already be on the server filesystem. For file uploads, use the REST API POST /api/v1/rag/ingest endpoint. Supported formats: PDF, Word, PowerPoint, Excel, HTML, Markdown, and audio files (with transcription).
    
    Args:
        file_paths (List[str]): List of absolute file paths on the server to ingest. Files must already exist on the server filesystem. Supported formats: .pdf, .docx, .doc, .pptx, .ppt, .xlsx, .xls, .md, .markdown, .txt, .html, .htm, .mp3, .wav, .m4a, .flac Required.
        clean_before (bool): If true, deletes all existing documents and chunks before ingestion. Use with caution! Default: False.
    
    Returns:
        Tool response as dictionary.
    """
    return await call_mcp_tool(
        "ingest_documents",
        {
            "file_paths": file_paths,
            "clean_before": clean_before,
        }
    )
