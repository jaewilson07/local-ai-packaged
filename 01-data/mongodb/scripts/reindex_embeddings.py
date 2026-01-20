#!/usr/bin/env python3
"""
Reindex all chunks with a new embedding model.

This script regenerates embeddings for all existing chunks in MongoDB
using the currently configured embedding model.

Usage:
    python reindex_embeddings.py

    # Dry run (show what would be updated)
    python reindex_embeddings.py --dry-run

    # Limit to N chunks (for testing)
    python reindex_embeddings.py --limit 10

Environment Variables:
    MONGODB_URI - MongoDB connection string
    EMBEDDING_MODEL - Embedding model to use (default: qwen3-embedding:4b)
    EMBEDDING_BASE_URL - Embedding API base URL (default: http://localhost:11434/v1)
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment
try:
    from dotenv import load_dotenv

    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from datetime import datetime

from openai import AsyncOpenAI
from pymongo import MongoClient

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv(
    "MONGODB_HOST_URI",
    "mongodb://admin:admin123@localhost:27017/?directConnection=true&authSource=admin",
)
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "rag_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:4b")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
BATCH_SIZE = 10  # Process in batches to avoid memory issues

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def generate_embedding(client: AsyncOpenAI, text: str, model: str) -> list[float]:
    """Generate embedding for a single text."""
    try:
        response = await client.embeddings.create(
            model=model,
            input=text,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise


async def reindex_chunks(
    dry_run: bool = False,
    limit: int | None = None,
    batch_size: int = BATCH_SIZE,
) -> dict:
    """
    Reindex all chunks with new embeddings.

    Args:
        dry_run: If True, don't update database
        limit: Maximum number of chunks to process
        batch_size: Number of chunks to process per batch

    Returns:
        Dict with counts of processed, updated, and failed chunks
    """
    results = {"processed": 0, "updated": 0, "failed": 0, "skipped": 0}

    logger.info("=" * 60)
    logger.info("Embedding Reindexing Script")
    logger.info("=" * 60)
    logger.info(f"MongoDB: {MONGODB_URI[:50]}...")
    logger.info(f"Database: {DATABASE_NAME}")
    logger.info(f"Embedding Model: {EMBEDDING_MODEL}")
    logger.info(f"Embedding URL: {EMBEDDING_BASE_URL}")
    logger.info(f"Batch Size: {batch_size}")
    if dry_run:
        logger.info("DRY RUN MODE - No updates will be made")
    if limit:
        logger.info(f"Limit: {limit} chunks")
    logger.info("=" * 60)

    # Connect to MongoDB
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command("ping")
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return results

    db = mongo_client[DATABASE_NAME]
    chunks_collection = db["chunks"]

    # Create OpenAI client for embeddings
    openai_client = AsyncOpenAI(
        base_url=EMBEDDING_BASE_URL,
        api_key="not-needed",  # Ollama doesn't need API key
    )

    # Get total count
    total_count = chunks_collection.count_documents({})
    process_count = min(total_count, limit) if limit else total_count
    logger.info(f"Total chunks: {total_count}, will process: {process_count}")

    # Process in batches
    cursor = (
        chunks_collection.find({}).limit(process_count) if limit else chunks_collection.find({})
    )

    batch = []
    for chunk in cursor:
        batch.append(chunk)

        if len(batch) >= batch_size:
            batch_results = await process_batch(chunks_collection, openai_client, batch, dry_run)
            results["processed"] += batch_results["processed"]
            results["updated"] += batch_results["updated"]
            results["failed"] += batch_results["failed"]
            results["skipped"] += batch_results["skipped"]
            batch = []

            # Progress update
            logger.info(
                f"Progress: {results['processed']}/{process_count} "
                f"(updated: {results['updated']}, failed: {results['failed']})"
            )

    # Process remaining batch
    if batch:
        batch_results = await process_batch(chunks_collection, openai_client, batch, dry_run)
        results["processed"] += batch_results["processed"]
        results["updated"] += batch_results["updated"]
        results["failed"] += batch_results["failed"]
        results["skipped"] += batch_results["skipped"]

    # Summary
    logger.info("=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    logger.info(f"Processed: {results['processed']}")
    logger.info(f"Updated: {results['updated']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Skipped: {results['skipped']}")

    if dry_run:
        logger.info("\nDRY RUN - No changes were made")
    else:
        logger.info("\n✓ Reindexing complete!")

    mongo_client.close()
    return results


async def process_batch(
    collection,
    openai_client: AsyncOpenAI,
    chunks: list,
    dry_run: bool,
) -> dict:
    """Process a batch of chunks."""
    results = {"processed": 0, "updated": 0, "failed": 0, "skipped": 0}

    for chunk in chunks:
        results["processed"] += 1
        chunk_id = chunk["_id"]
        content = chunk.get("content", "")

        if not content:
            logger.warning(f"Chunk {chunk_id} has no content, skipping")
            results["skipped"] += 1
            continue

        try:
            # Generate new embedding
            embedding = await generate_embedding(openai_client, content, EMBEDDING_MODEL)

            if dry_run:
                logger.debug(f"Would update chunk {chunk_id} with {len(embedding)}-dim embedding")
                results["updated"] += 1
            else:
                # Update chunk with new embedding
                collection.update_one(
                    {"_id": chunk_id},
                    {
                        "$set": {
                            "embedding": embedding,
                            "metadata.embedding_model": EMBEDDING_MODEL,
                            "metadata.embedding_generated_at": datetime.now().isoformat(),
                            "metadata.embedding_dimensions": len(embedding),
                        }
                    },
                )
                results["updated"] += 1

        except Exception as e:
            logger.error(f"Failed to process chunk {chunk_id}: {e}")
            results["failed"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description="Reindex chunks with new embedding model")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of chunks to process",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size for processing (default: {BATCH_SIZE})",
    )
    args = parser.parse_args()

    results = asyncio.run(
        reindex_chunks(
            dry_run=args.dry_run,
            limit=args.limit,
            batch_size=args.batch_size,
        )
    )

    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
