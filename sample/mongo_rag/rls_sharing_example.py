#!/usr/bin/env python3
"""Row-Level Security (RLS) and sharing example for MongoDB RAG.

This example demonstrates:
1. Creating documents with different sharing configurations
2. Searching with RLS filtering (users only see accessible documents)
3. Sharing documents with other users
4. Making documents public
5. Group-based sharing

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
from capabilities.retrieval.mongo_rag.rls import (  # noqa: E402
    add_sharing_to_document,
    build_access_filter,
    can_access_document,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def demonstrate_rls():
    """Demonstrate RLS functionality."""

    # Create two user contexts
    user1_id = str(uuid4())
    user1_email = "user1@example.com"

    user2_id = str(uuid4())
    user2_email = "user2@example.com"

    logger.info("=" * 60)
    logger.info("MongoDB RLS and Sharing Demonstration")
    logger.info("=" * 60)

    # Initialize dependencies for user1
    deps_user1 = AgentDependencies.from_settings(
        user_id=user1_id, user_email=user1_email, is_admin=False, user_groups=["team-alpha"]
    )
    await deps_user1.initialize()

    try:
        # Create a private document for user1
        logger.info("\n1. Creating private document for user1...")
        documents_collection = deps_user1.db["documents"]
        private_doc = {
            "_id": uuid4(),
            "title": "User1 Private Document",
            "content": "This is a private document that only user1 can see.",
            "user_id": user1_id,
            "user_email": user1_email,
            "is_public": False,
            "shared_with": [],
            "group_ids": [],
            "created_at": "2024-01-01T00:00:00Z",
        }
        await documents_collection.insert_one(private_doc)
        logger.info(f"   Created document: {private_doc['title']}")

        # Create a public document
        logger.info("\n2. Creating public document...")
        public_doc = {
            "_id": uuid4(),
            "title": "Public Document",
            "content": "This is a public document that everyone can see.",
            "user_id": user1_id,
            "user_email": user1_email,
            "is_public": True,
            "shared_with": [],
            "group_ids": [],
            "created_at": "2024-01-01T00:00:00Z",
        }
        await documents_collection.insert_one(public_doc)
        logger.info(f"   Created document: {public_doc['title']}")

        # Create a document shared with user2
        logger.info("\n3. Creating document shared with user2...")
        shared_doc = {
            "_id": uuid4(),
            "title": "Shared with User2",
            "content": "This document is shared directly with user2.",
            "user_id": user1_id,
            "user_email": user1_email,
            "is_public": False,
            "shared_with": [user2_id, user2_email],
            "group_ids": [],
            "created_at": "2024-01-01T00:00:00Z",
        }
        await documents_collection.insert_one(shared_doc)
        logger.info(f"   Created document: {shared_doc['title']}")

        # Create a group-shared document
        logger.info("\n4. Creating group-shared document...")
        group_doc = {
            "_id": uuid4(),
            "title": "Team Alpha Document",
            "content": "This document is shared with team-alpha group.",
            "user_id": user1_id,
            "user_email": user1_email,
            "is_public": False,
            "shared_with": [],
            "group_ids": ["team-alpha"],
            "created_at": "2024-01-01T00:00:00Z",
        }
        await documents_collection.insert_one(group_doc)
        logger.info(f"   Created document: {group_doc['title']}")

        # Test RLS filter for user1
        logger.info("\n5. Testing RLS filter for user1...")
        filter_user1 = build_access_filter(
            current_user_id=user1_id,
            current_user_email=user1_email,
            user_groups=["team-alpha"],
            is_admin=False,
        )
        logger.info(f"   RLS Filter: {filter_user1}")

        # Query documents accessible to user1
        accessible_docs = await documents_collection.find(filter_user1).to_list(length=10)
        logger.info(f"   User1 can access {len(accessible_docs)} documents:")
        for doc in accessible_docs:
            logger.info(f"     - {doc['title']}")

        # Test RLS filter for user2
        logger.info("\n6. Testing RLS filter for user2...")
        filter_user2 = build_access_filter(
            current_user_id=user2_id, current_user_email=user2_email, user_groups=[], is_admin=False
        )
        logger.info(f"   RLS Filter: {filter_user2}")

        # Query documents accessible to user2
        accessible_docs_user2 = await documents_collection.find(filter_user2).to_list(length=10)
        logger.info(f"   User2 can access {len(accessible_docs_user2)} documents:")
        for doc in accessible_docs_user2:
            logger.info(f"     - {doc['title']}")

        # Test document access check
        logger.info("\n7. Testing document access checks...")
        can_access = can_access_document(
            private_doc, current_user_id=user1_id, current_user_email=user1_email
        )
        logger.info(f"   User1 can access own private document: {can_access}")

        can_access_other = can_access_document(
            private_doc, current_user_id=user2_id, current_user_email=user2_email
        )
        logger.info(f"   User2 can access user1's private document: {can_access_other}")

        can_access_public = can_access_document(
            public_doc, current_user_id=user2_id, current_user_email=user2_email
        )
        logger.info(f"   User2 can access public document: {can_access_public}")

        # Demonstrate sharing modification
        logger.info("\n8. Demonstrating sharing modification...")
        updated_doc = add_sharing_to_document(
            private_doc.copy(), is_public=True, shared_with=[user2_email]
        )
        logger.info("   Updated document sharing:")
        logger.info(f"     is_public: {updated_doc.get('is_public')}")
        logger.info(f"     shared_with: {updated_doc.get('shared_with')}")

        logger.info("\n" + "=" * 60)
        logger.info("RLS Demonstration Complete!")
        logger.info("=" * 60)

        # Verify via API
        from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
        from sample.shared.verification_helpers import verify_mongodb_data

        api_base_url = get_api_base_url()
        headers = get_auth_headers()

        logger.info("\n" + "=" * 60)
        logger.info("Verification")
        logger.info("=" * 60)

        success, message = verify_mongodb_data(
            api_base_url=api_base_url,
            headers=headers,
            collection="documents",
            expected_count_min=1,
        )
        logger.info(message)

        if success:
            logger.info("\n✅ Verification passed!")
            sys.exit(0)
        else:
            logger.warning("\n❌ Verification failed (data may need time to propagate)")
            sys.exit(1)
    finally:
        await deps_user1.cleanup()


if __name__ == "__main__":
    asyncio.run(demonstrate_rls())
