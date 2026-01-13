"""Citation extraction from documents."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_citations(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Extract citations from documents.

    Formats citations with metadata for source tracking.

    Args:
        documents: List of document dicts with 'content' and 'metadata' keys

    Returns:
        List of citation dicts with source information
    """
    citations = []

    for i, doc in enumerate(documents):
        metadata = doc.get("metadata", {})
        content = doc.get("content", doc.get("text", ""))

        citation = {
            "id": i + 1,
            "content": content[:200] + "..." if len(content) > 200 else content,
            "source": metadata.get("source", "unknown"),
            "title": metadata.get("title", metadata.get("document_title", "")),
            "url": metadata.get("url", ""),
            "chunk_id": doc.get("chunk_id"),
            "document_id": doc.get("document_id"),
        }

        citations.append(citation)

    return citations


def format_citations(citations: list[dict[str, Any]]) -> str:
    """
    Format citations as a readable string.

    Args:
        citations: List of citation dicts

    Returns:
        Formatted citation string
    """
    if not citations:
        return ""

    lines = ["Citations:"]
    for cit in citations:
        source = cit.get("source", "unknown")
        title = cit.get("title", "")
        url = cit.get("url", "")

        if title:
            lines.append(f"[{cit['id']}] {title} ({source})")
        elif url:
            lines.append(f"[{cit['id']}] {url} ({source})")
        else:
            lines.append(f"[{cit['id']}] {source}")

    return "\n".join(lines)
