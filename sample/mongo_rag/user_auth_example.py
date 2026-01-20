#!/usr/bin/env python3
"""User-based authentication example for MongoDB RAG.

This example demonstrates:
1. Creating dependencies with user context
2. User-based MongoDB connection (simulated)
3. Document ingestion with user ownership
4. Search with user-scoped results

Prerequisites:
- MongoDB running
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, EMBEDDING_BASE_URL)
"""

import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

# Set environment variables for host execution
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
if "MONGODB_URI" not in os.environ:
    os.environ[
        "MONGODB_URI"
    ] = "mongodb://admin:admin123@localhost:27017/?directConnection=true&authSource=admin"

# Add server to path
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from capabilities.retrieval.mongo_rag.dependencies import AgentDependencies  # noqa: E402
from capabilities.retrieval.mongo_rag.ingestion.pipeline import (  # noqa: E402
    DocumentIngestionPipeline,
    IngestionConfig,
)

from shared.context_helpers import create_run_context  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def demonstrate_user_auth():
    """Demonstrate user-based authentication."""

    # Simulate user authentication (in real app, this comes from JWT)
    user_id = str(uuid4())
    user_email = "demo@example.com"
    is_admin = False
    user_groups = ["developers"]

    logger.info("=" * 60)
    logger.info("MongoDB User-Based Authentication Demonstration")
    logger.info("=" * 60)
    logger.info(f"User ID: {user_id}")
    logger.info(f"User Email: {user_email}")
    logger.info(f"Is Admin: {is_admin}")
    logger.info(f"Groups: {user_groups}")

    # Create dependencies with user context
    logger.info("\n1. Creating dependencies with user context...")
    deps = AgentDependencies.from_settings(
        user_id=user_id, user_email=user_email, is_admin=is_admin, user_groups=user_groups
    )
    await deps.initialize()

    try:
        logger.info(f"   MongoDB connected: {deps.mongo_client is not None}")
        logger.info(f"   Current user ID: {deps.current_user_id}")
        logger.info(f"   Current user email: {deps.current_user_email}")
        logger.info(f"   Is admin: {deps.is_admin}")
        logger.info(f"   User groups: {deps.user_groups}")

        # Create a test document with user ownership
        logger.info("\n2. Creating document with user ownership...")
        documents_collection = deps.db["documents"]
        test_doc = {
            "_id": uuid4(),
            "title": "User's Test Document",
            "content": "This document belongs to the authenticated user.",
            "source": "user_auth_example",
            "user_id": user_id,
            "user_email": user_email,
            "is_public": False,
            "shared_with": [],
            "group_ids": [],
            "created_at": "2024-01-01T00:00:00Z",
        }
        await documents_collection.insert_one(test_doc)
        logger.info(f"   Created document: {test_doc['title']}")
        logger.info(f"   Document user_id: {test_doc['user_id']}")

        # Verify document ownership
        logger.info("\n3. Verifying document ownership...")
        found_doc = await documents_collection.find_one({"_id": test_doc["_id"]})
        if found_doc:
            logger.info(f"   Found document: {found_doc['title']}")
            logger.info(f"   Owner user_id: {found_doc.get('user_id')}")
            logger.info(f"   Owner email: {found_doc.get('user_email')}")
            assert found_doc.get("user_id") == user_id, "Document ownership mismatch!"
            logger.info("   ✓ Document ownership verified")

        # Demonstrate ingestion pipeline with user context
        logger.info("\n4. Demonstrating document ingestion with user context...")
        logger.info("   (Note: This requires actual document files)")

        # Create a simple test document file
        sample_dir = Path(__file__).parent / "sample_data"
        sample_dir.mkdir(exist_ok=True)
        test_file = sample_dir / "user_auth_test.md"
        test_file.write_text(
            "# User Auth Test Document\n\nThis document was ingested with user context."
        )

        config = IngestionConfig()
        pipeline = DocumentIngestionPipeline(
            config=config,
            documents_folder=str(sample_dir),
            clean_before_ingest=False,
            user_id=user_id,
            user_email=user_email,
        )

        try:
            await pipeline.initialize()
            logger.info("   Pipeline initialized with user context")
            logger.info(f"   User ID: {pipeline.user_id}")
            logger.info(f"   User Email: {pipeline.user_email}")

            # Note: Actual ingestion would require embeddings, so we'll skip it
            # results = await pipeline.ingest_documents()  # noqa: ERA001
            logger.info("   (Skipping actual ingestion - requires embeddings)")

        finally:
            await pipeline.close()

        # Demonstrate search with user context
        logger.info("\n5. Demonstrating search with user context...")
        ctx = create_run_context(deps)

        # Note: Actual search would require embeddings and vector index
        logger.info("   Search would use RLS filters based on user context:")
        logger.info(f"     - user_id: {deps.current_user_id}")
        logger.info(f"     - user_email: {deps.current_user_email}")
        logger.info(f"     - is_admin: {deps.is_admin}")
        logger.info(f"     - user_groups: {deps.user_groups}")
        logger.info("   (Skipping actual search - requires embeddings and vector index)")

        # Demonstrate admin context
        logger.info("\n6. Demonstrating admin user context...")
        admin_deps = AgentDependencies.from_settings(
            user_id=str(uuid4()), user_email="admin@example.com", is_admin=True, user_groups=[]
        )
        await admin_deps.initialize()

        try:
            logger.info(f"   Admin user ID: {admin_deps.current_user_id}")
            logger.info(f"   Admin email: {admin_deps.current_user_email}")
            logger.info(f"   Is admin: {admin_deps.is_admin}")
            logger.info("   Admin users bypass RLS filtering (see all documents)")
        finally:
            await admin_deps.cleanup()

        logger.info("\n" + "=" * 60)
        logger.info("User Authentication Demonstration Complete!")
        logger.info("=" * 60)

        # Verify via API
        from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
        from sample.shared.verification_helpers import verify_rag_data

        api_base_url = get_api_base_url()
        headers = get_auth_headers()

        logger.info("\n" + "=" * 60)
        logger.info("Verification")
        logger.info("=" * 60)

        success, message = verify_rag_data(
            api_base_url=api_base_url,
            headers=headers,
            expected_documents_min=1,
        )
        logger.info(message)

        if success:
            logger.info("\n✅ Verification passed!")
            sys.exit(0)
        else:
            logger.warning("\n❌ Verification failed (data may need time to propagate)")
            sys.exit(1)
    finally:
        await deps.cleanup()


if __name__ == "__main__":
    asyncio.run(demonstrate_user_auth())
