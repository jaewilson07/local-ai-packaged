#!/usr/bin/env python3
"""
MongoDB Atlas Search Index Setup Script

Creates the required Atlas Search indexes for the RAG system.
Can be run standalone or imported as a module.

Prerequisites:
- MongoDB Atlas Local image (mongodb/mongodb-atlas-local:latest)
- Replica set initialized (rs0)
- pymongo installed

Usage:
    python setup_search_indexes.py

    # Or with custom connection string
    MONGODB_URI="mongodb://admin:password@localhost:27017/?authSource=admin" python setup_search_indexes.py

Environment Variables:
    MONGODB_URI - MongoDB connection string (default: from .env or localhost)
    MONGODB_DATABASE - Target database (default: rag_db)
    EMBEDDING_DIMENSIONS - Embedding vector dimensions (default: 768 for qwen3-embedding:4b)
"""

import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Try to load environment from .env
try:
    from dotenv import load_dotenv

    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from pymongo import MongoClient
from pymongo.errors import OperationFailure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
# Default URI uses localhost for running outside Docker
# For Docker internal use, set MONGODB_URI=mongodb://admin:password@mongodb:27017/?authSource=admin
MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv(
    "MONGODB_HOST_URI",
    "mongodb://admin:admin123@localhost:27017/?directConnection=true&authSource=admin",
)
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "rag_db")
# Embedding dimensions MUST match the model used for indexing:
#   - qwen3-embedding:4b = 2560 dimensions (default, best MTEB score)
#   - qwen3-embedding:4b = 768 dimensions
# IMPORTANT: If you change embedding models, you must re-index all data
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "2560"))

# Index definitions
INDEX_DEFINITIONS = [
    {
        "collection": "chunks",
        "name": "vector_index",
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": EMBEDDING_DIMENSIONS,
                    "similarity": "cosine",
                }
            ]
        },
    },
    {
        "collection": "chunks",
        "name": "text_index",
        "type": "search",
        "definition": {
            "mappings": {
                "dynamic": False,
                "fields": {"content": {"type": "string", "analyzer": "lucene.standard"}},
            }
        },
    },
    {
        "collection": "documents",
        "name": "documents_text_index",
        "type": "search",
        "definition": {
            "mappings": {
                "dynamic": False,
                "fields": {
                    "title": {"type": "string", "analyzer": "lucene.standard"},
                    "source": {"type": "string", "analyzer": "lucene.keyword"},
                },
            }
        },
    },
    {
        "collection": "controlnet_skeletons",
        "name": "skeleton_vector_index",
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": EMBEDDING_DIMENSIONS,
                    "similarity": "cosine",
                }
            ]
        },
    },
    {
        "collection": "controlnet_skeletons",
        "name": "skeleton_text_index",
        "type": "search",
        "definition": {
            "mappings": {
                "dynamic": False,
                "fields": {
                    "description": {"type": "string", "analyzer": "lucene.standard"},
                    "tags": {"type": "string", "analyzer": "lucene.keyword"},
                    "preprocessor_type": {"type": "string", "analyzer": "lucene.keyword"},
                },
            }
        },
    },
]


def get_search_indexes(collection) -> list[dict]:
    """Get all search indexes for a collection."""
    try:
        return list(collection.list_search_indexes())
    except OperationFailure:
        return []


def index_exists(collection, index_name: str) -> bool:
    """Check if a search index exists."""
    indexes = get_search_indexes(collection)
    return any(idx.get("name") == index_name for idx in indexes)


def get_index_status(collection, index_name: str) -> str | None:
    """Get the status of a search index."""
    indexes = get_search_indexes(collection)
    for idx in indexes:
        if idx.get("name") == index_name:
            return idx.get("status")
    return None


def wait_for_index(collection, index_name: str, max_wait_seconds: int = 60) -> bool:
    """Wait for an index to reach READY status."""
    start_time = time.time()
    while (time.time() - start_time) < max_wait_seconds:
        status = get_index_status(collection, index_name)
        if status == "READY":
            return True
        if status is None:
            return False  # Index doesn't exist
        time.sleep(1)
    return False


def create_search_index(collection, index_def: dict) -> bool:
    """Create a search index."""
    try:
        # Use the command interface for search index creation
        collection.create_search_index(
            {
                "name": index_def["name"],
                "type": index_def["type"],
                "definition": index_def["definition"],
            }
        )
        return True
    except OperationFailure as e:
        if "already exists" in str(e).lower():
            return True  # Index already exists
        logger.error(f"Failed to create index {index_def['name']}: {e}")
        return False


def setup_search_indexes(
    uri: str = MONGODB_URI,
    database: str = DATABASE_NAME,
    wait_for_ready: bool = True,
) -> dict:
    """
    Set up all required search indexes.

    Args:
        uri: MongoDB connection string
        database: Target database name
        wait_for_ready: Whether to wait for indexes to be READY

    Returns:
        Dict with counts of created, skipped, and failed indexes
    """
    results = {"created": 0, "skipped": 0, "errors": 0, "indexes": []}

    logger.info("=" * 60)
    logger.info("MongoDB Atlas Search Index Setup")
    logger.info("=" * 60)
    logger.info(f"Database: {database}")
    logger.info(f"Embedding dimensions: {EMBEDDING_DIMENSIONS}")

    # Connect to MongoDB
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command("ping")
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        results["errors"] = len(INDEX_DEFINITIONS)
        return results

    db = client[database]

    # Create indexes
    for index_def in INDEX_DEFINITIONS:
        collection_name = index_def["collection"]
        index_name = index_def["name"]
        index_type = index_def["type"]

        logger.info(f"\n[{collection_name}] Checking {index_name}...")

        collection = db[collection_name]

        # Check if index already exists
        if index_exists(collection, index_name):
            logger.info("  ✓ Index already exists, skipping")
            results["skipped"] += 1
            results["indexes"].append(
                {"name": index_name, "collection": collection_name, "status": "exists"}
            )
            continue

        # Create the index
        logger.info(f"  Creating {index_type} index: {index_name}")
        if create_search_index(collection, index_def):
            logger.info("  ✓ Index created successfully")
            results["created"] += 1

            # Wait for index to be ready
            if wait_for_ready:
                logger.info("  Waiting for index to be ready...")
                if wait_for_index(collection, index_name, max_wait_seconds=30):
                    logger.info("  ✓ Index is READY")
                    results["indexes"].append(
                        {
                            "name": index_name,
                            "collection": collection_name,
                            "status": "ready",
                        }
                    )
                else:
                    logger.info("  ⚠ Index still building (will be available shortly)")
                    results["indexes"].append(
                        {
                            "name": index_name,
                            "collection": collection_name,
                            "status": "building",
                        }
                    )
            else:
                results["indexes"].append(
                    {"name": index_name, "collection": collection_name, "status": "created"}
                )
        else:
            logger.error("  ✗ Failed to create index")
            results["errors"] += 1
            results["indexes"].append(
                {"name": index_name, "collection": collection_name, "status": "error"}
            )

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    logger.info(f"Created: {results['created']}")
    logger.info(f"Skipped (already exist): {results['skipped']}")
    logger.info(f"Errors: {results['errors']}")

    # Verify all indexes
    logger.info("\n" + "=" * 60)
    logger.info("Current Search Indexes")
    logger.info("=" * 60)

    for index_def in INDEX_DEFINITIONS:
        collection_name = index_def["collection"]
        index_name = index_def["name"]
        collection = db[collection_name]

        status = get_index_status(collection, index_name)
        if status:
            logger.info(f"[{collection_name}] {index_name}: {status}")
        else:
            logger.info(f"[{collection_name}] {index_name}: NOT FOUND")

    logger.info("\n✓ Setup complete!")

    client.close()
    return results


def verify_indexes(uri: str = MONGODB_URI, database: str = DATABASE_NAME) -> dict:
    """
    Verify that all required search indexes exist and are ready.

    Returns:
        Dict with index statuses
    """
    results = {"all_ready": True, "indexes": []}

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client[database]

        for index_def in INDEX_DEFINITIONS:
            collection_name = index_def["collection"]
            index_name = index_def["name"]
            collection = db[collection_name]

            status = get_index_status(collection, index_name)
            is_ready = status == "READY"

            results["indexes"].append(
                {
                    "name": index_name,
                    "collection": collection_name,
                    "status": status or "NOT_FOUND",
                    "ready": is_ready,
                }
            )

            if not is_ready:
                results["all_ready"] = False

        client.close()
    except Exception as e:
        logger.error(f"Failed to verify indexes: {e}")
        results["all_ready"] = False
        results["error"] = str(e)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup MongoDB Atlas Search indexes")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify indexes without creating them",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for indexes to be ready",
    )
    args = parser.parse_args()

    if args.verify_only:
        results = verify_indexes()
        print("\nIndex Status:")
        for idx in results["indexes"]:
            status = "✓" if idx["ready"] else "✗"
            print(f"  {status} [{idx['collection']}] {idx['name']}: {idx['status']}")

        if results["all_ready"]:
            print("\n✓ All indexes are ready!")
            sys.exit(0)
        else:
            print("\n✗ Some indexes are not ready")
            sys.exit(1)
    else:
        results = setup_search_indexes(wait_for_ready=not args.no_wait)
        sys.exit(0 if results["errors"] == 0 else 1)
