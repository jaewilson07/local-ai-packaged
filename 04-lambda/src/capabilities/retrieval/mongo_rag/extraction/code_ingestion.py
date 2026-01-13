"""Ingest code examples into MongoDB."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from bson import ObjectId
from pymongo import AsyncMongoClient

from server.projects.mongo_rag.config import config
from server.projects.mongo_rag.extraction.code_extractor import extract_code_blocks
from server.projects.mongo_rag.extraction.code_summarizer import generate_code_example_summary
from server.projects.mongo_rag.ingestion.chunker import DocumentChunk
from server.projects.mongo_rag.ingestion.embedder import create_embedder

logger = logging.getLogger(__name__)


async def ingest_code_examples(
    mongo_client: AsyncMongoClient,
    document_id: str,
    markdown_content: str,
    source: str,
    metadata: dict[str, Any] | None = None,
    min_code_length: int = 300,
) -> dict[str, Any]:
    """
    Extract code examples from markdown and store them in MongoDB.

    Args:
        mongo_client: MongoDB client
        document_id: Parent document ID
        markdown_content: Markdown content to extract code from
        source: Document source path
        metadata: Optional document metadata
        min_code_length: Minimum length of code blocks to extract

    Returns:
        Dictionary with ingestion statistics
    """
    db = mongo_client[config.mongodb_database]
    code_examples_collection = db["code_examples"]

    # Extract code blocks
    code_blocks = extract_code_blocks(markdown_content, min_length=min_code_length)

    if not code_blocks:
        return {"code_examples_extracted": 0, "code_examples_stored": 0, "errors": []}

    logger.info(f"Extracted {len(code_blocks)} code blocks from document {document_id}")

    # Generate summaries in parallel
    embedder = create_embedder()
    summaries = []
    errors = []

    # Process summaries concurrently
    summary_tasks = [
        generate_code_example_summary(
            block["code"], block["context_before"], block["context_after"]
        )
        for block in code_blocks
    ]

    try:
        summaries = await asyncio.gather(*summary_tasks, return_exceptions=True)
    except Exception:
        logger.exception("Error generating summaries")
        summaries = ["Code example for demonstration purposes."] * len(code_blocks)

    # Fix any exceptions in summaries
    for i, summary in enumerate(summaries):
        if isinstance(summary, Exception):
            logger.warning(f"Summary generation failed for block {i}: {summary}")
            summaries[i] = "Code example for demonstration purposes."

    # Generate embeddings for code examples (code + summary)
    # Create DocumentChunk objects for embedder
    code_chunks = [
        DocumentChunk(
            content=f"{block['code']}\n\nSummary: {summary}",
            index=i,
            start_char=0,
            end_char=len(f"{block['code']}\n\nSummary: {summary}"),
            metadata={"type": "code_example", "language": block["language"]},
        )
        for i, (block, summary) in enumerate(zip(code_blocks, summaries, strict=False))
    ]

    embedded_chunks = await embedder.embed_chunks(code_chunks)

    # Prepare documents for insertion
    code_documents = []
    for i, (block, summary, chunk) in enumerate(
        zip(code_blocks, summaries, embedded_chunks, strict=False)
    ):
        code_doc = {
            "document_id": ObjectId(document_id) if isinstance(document_id, str) else document_id,
            "code": block["code"],
            "summary": summary,
            "language": block["language"],
            "context_before": block["context_before"],
            "context_after": block["context_after"],
            "source": source,
            "embedding": chunk.embedding if chunk.embedding else [],
            "metadata": {
                **(metadata or {}),
                "char_count": len(block["code"]),
                "line_count": len(block["code"].split("\n")),
                "chunk_index": i,
            },
            "created_at": datetime.now(),
        }
        code_documents.append(code_doc)

    # Insert into MongoDB
    stored_count = 0
    try:
        if code_documents:
            # Delete existing code examples for this document first
            await code_examples_collection.delete_many(
                {
                    "document_id": (
                        ObjectId(document_id) if isinstance(document_id, str) else document_id
                    )
                }
            )

            # Insert new code examples
            result = await code_examples_collection.insert_many(code_documents, ordered=False)
            stored_count = len(result.inserted_ids)
            logger.info(f"Stored {stored_count} code examples for document {document_id}")
    except Exception as e:
        error_msg = f"Error storing code examples: {e!s}"
        logger.exception(error_msg)
        errors.append(error_msg)

    return {
        "code_examples_extracted": len(code_blocks),
        "code_examples_stored": stored_count,
        "errors": errors,
    }
