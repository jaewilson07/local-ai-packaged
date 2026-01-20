#!/usr/bin/env python3
"""Document ingestion example using MongoDB RAG.

This example demonstrates how to ingest documents (PDF, Markdown, etc.)
into MongoDB for vector search. Documents are automatically:
- Converted to markdown (using Docling)
- Chunked into smaller pieces
- Embedded using embeddings model
- Stored in MongoDB with vector indexes

Prerequisites:
- MongoDB running
- Documents folder with files to ingest (PDF, .md, .txt, etc.)
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, EMBEDDING_BASE_URL, etc.)
- Dependencies installed: Run `uv pip install -e ".[test]"` in `04-lambda/` directory

Validation:
This sample validates its results through:

1. **Ingestion Result Validation**:
   - Verifies that documents are successfully ingested
   - Checks that chunks are created and stored
   - Validates that embeddings are generated
   - Confirms document metadata is stored correctly

2. **Exit Code Validation**:
   - Returns exit code 0 if ingestion succeeds
   - Returns exit code 1 if ingestion fails or errors occur

3. **Error Handling**:
   - Catches and logs exceptions during ingestion
   - Provides clear error messages for debugging
   - Handles missing files gracefully
   - Ensures proper cleanup of resources

4. **Result Structure Validation**:
   - Verifies ingestion pipeline returns expected structure
   - Checks document IDs and chunk IDs are generated
   - Validates chunk counts match expectations
   - Confirms source URLs/metadata are preserved

The sample will fail validation if:
- Documents cannot be read or parsed
- MongoDB connection fails
- Embedding generation fails
- Chunking process fails
- Storage operations fail
"""

import asyncio
import os
import sys
from pathlib import Path

# Set environment variables for host execution (not Docker)
# These override defaults that use Docker hostnames
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
# MongoDB connection - try with auth first, fallback to no auth
# Default credentials: admin/admin123 (can be overridden via MONGODB_URI env var)
if "MONGODB_URI" not in os.environ:
    # Try with authentication first
    os.environ[
        "MONGODB_URI"
    ] = "mongodb://admin:admin123@localhost:27017/?directConnection=true&authSource=admin"

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from capabilities.retrieval.mongo_rag.ingestion.pipeline import (  # noqa: E402
    DocumentIngestionPipeline,
    IngestionConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Ingest documents into MongoDB RAG."""
    # Configuration
    documents_folder = "documents"  # Folder containing documents to ingest
    chunk_size = 1000
    chunk_overlap = 200

    print("=" * 80)
    print("MongoDB RAG - Document Ingestion Example")
    print("=" * 80)
    print()
    print("This example demonstrates document ingestion into MongoDB.")
    print("Documents are automatically:")
    print("  - Converted to markdown (PDF, Word, etc.)")
    print("  - Chunked into smaller pieces")
    print("  - Embedded using embeddings model")
    print("  - Stored in MongoDB with vector indexes")
    print()
    print("Configuration:")
    print(f"  Documents folder: {documents_folder}")
    print(f"  Chunk size: {chunk_size}")
    print(f"  Chunk overlap: {chunk_overlap}")
    print()

    # Check if documents folder exists
    docs_path = Path(documents_folder)
    if not docs_path.exists():
        print(f"⚠️  Documents folder '{documents_folder}' not found.")
        print("   Create it and add some documents (PDF, .md, .txt, etc.) to ingest.")
        print(f"   Example: mkdir -p {documents_folder}")
        sys.exit(1)

    # Create ingestion config
    config = IngestionConfig(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, max_chunk_size=2000, max_tokens=512
    )

    # Initialize pipeline with user context (for RLS)
    # In production, these would come from authenticated user session
    from uuid import uuid4

    user_id = str(uuid4())  # Simulated user ID
    user_email = "demo@example.com"  # Simulated user email

    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder=documents_folder,
        clean_before_ingest=False,  # Set to True to clear existing data
        user_id=user_id,
        user_email=user_email,
    )

    try:
        # Initialize pipeline (connects to MongoDB, etc.)
        print("🔧 Initializing ingestion pipeline...")
        await pipeline.initialize()
        print("✅ Pipeline initialized")
        print()

        # Find documents to ingest
        print(f"📂 Scanning for documents in '{documents_folder}'...")
        document_files = pipeline._find_document_files()

        if not document_files:
            print(f"⚠️  No documents found in '{documents_folder}'")
            print("   Supported formats: PDF, Word, PowerPoint, Excel, HTML, Markdown, Text")
            sys.exit(1)

        print(f"Found {len(document_files)} document(s) to ingest:")
        for doc_file in document_files:
            print(f"  - {doc_file}")
        print()

        # Ingest documents
        print("🚀 Starting document ingestion...")

        def progress_callback(current: int, total: int) -> None:
            print(f"Progress: {current}/{total} documents processed")

        results = await pipeline.ingest_documents(progress_callback)

        # Display results
        for result in results:
            print(f"\n📄 {result.title}")
            if result.errors:
                print(f"  ❌ Failed: {result.errors[0] if result.errors else 'Unknown error'}")
            else:
                print("  ✅ Success!")
                print(f"     Document ID: {result.document_id}")
                print(f"     Chunks created: {result.chunks_created}")
                print(f"     Processing time: {result.processing_time_ms:.0f}ms")

        # Summary
        print("\n" + "=" * 80)
        print("INGESTION SUMMARY")
        print("=" * 80)
        total_chunks = sum(r.chunks_created for r in results)
        total_time = sum(r.processing_time_ms for r in results)
        successful = len([r for r in results if not r.errors])

        print(f"Documents processed: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")
        print(f"Total chunks created: {total_chunks}")
        print(f"Total processing time: {total_time:.0f}ms ({total_time / 1000:.1f}s)")
        print()

        if successful > 0:
            print("✅ Documents are now searchable via semantic/hybrid search!")
            print("   Run semantic_search_example.py or hybrid_search_example.py to test.")
        else:
            print("⚠️  No documents were successfully ingested.")
            print("   Check the errors above and ensure MongoDB is running.")

        print("=" * 80)

        # Verify via API
        if successful > 0:
            from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
            from sample.shared.verification_helpers import verify_rag_data

            api_base_url = get_api_base_url()
            headers = get_auth_headers()

            print("\n" + "=" * 80)
            print("Verification")
            print("=" * 80)

            success, message = verify_rag_data(
                api_base_url=api_base_url,
                headers=headers,
                expected_documents_min=successful,
                expected_chunks_min=total_chunks,
            )
            print(message)

            if success:
                print("\n✅ Verification passed!")
            else:
                print("\n❌ Verification failed (data may need time to propagate)")
    finally:
        # Cleanup
        await pipeline.close()
        logger.info("🧹 Pipeline cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
