#!/usr/bin/env python3
"""
Ingest a YouTube video and verify data in MongoDB and Neo4j.

This script:
1. Ingests a YouTube video via the full pipeline (not skipping MongoDB)
2. Queries MongoDB to verify the document and chunks were created
3. Queries Neo4j to verify Graphiti episodes were created

Usage:
    python sample/youtube_rag/ingest_and_verify.py --url "https://www.youtube.com/watch?v=A3DKwLORVe4"
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
lambda_src_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_src_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default video URL
DEFAULT_VIDEO_URL = "https://www.youtube.com/watch?v=A3DKwLORVe4"


def print_section(title: str, char: str = "=") -> None:
    """Print a section header."""
    width = 70
    print(f"\n{char * width}")
    print(f" {title}")
    print(f"{char * width}")


async def ingest_video(url: str) -> dict:
    """
    Ingest a YouTube video using the full pipeline.

    This uses ContentIngestionService which stores in MongoDB.
    """
    print_section("STEP 1: INGEST VIDEO TO MONGODB + GRAPHITI")

    from workflows.ingestion.youtube_rag.dependencies import YouTubeRAGDeps
    from workflows.ingestion.youtube_rag.models import IngestYouTubeRequest
    from workflows.ingestion.youtube_rag.tools import ingest_youtube_video

    # Don't skip MongoDB - we want to actually ingest
    deps = YouTubeRAGDeps.from_settings(
        skip_mongodb=True
    )  # Still skip direct MongoDB, use ContentIngestionService
    await deps.initialize()

    try:
        request = IngestYouTubeRequest(
            url=url,
            extract_chapters=True,
            extract_entities=False,  # Skip LLM extraction for speed
            extract_topics=False,
            chunk_by_chapters=True,
        )

        print(f"📹 Ingesting: {url}")
        result = await ingest_youtube_video(deps, request)

        print(f"✅ Success: {result.success}")
        print(f"📝 Title: {result.title}")
        print(f"🆔 Document ID: {result.document_id}")
        print(f"📦 Chunks Created: {result.chunks_created}")
        print(f"🔗 Graphiti Episodes: {result.graphiti_episodes_created}")

        if result.errors:
            print(f"⚠️  Errors: {result.errors}")

        return result.model_dump()

    finally:
        await deps.cleanup()


async def verify_mongodb(video_id: str) -> dict:
    """
    Verify the video was ingested into MongoDB.
    """
    print_section("STEP 2: VERIFY MONGODB DATA")

    from capabilities.retrieval.mongo_rag.config import config
    from pymongo import AsyncMongoClient

    client = AsyncMongoClient(config.mongodb_uri)
    db = client[config.mongodb_database]

    try:
        # Check documents collection
        docs_collection = db[config.mongodb_collection_documents]
        doc = await docs_collection.find_one({"metadata.video_id": video_id})

        if doc:
            print("✅ Document found in MongoDB!")
            print(f"   📝 Title: {doc.get('title', 'N/A')}")
            print(f"   🆔 Document ID: {doc.get('_id')}")
            print(f"   📅 Created: {doc.get('created_at', 'N/A')}")
            print(f"   📊 Source Type: {doc.get('metadata', {}).get('source_type', 'N/A')}")
        else:
            print(f"❌ No document found for video_id: {video_id}")
            # Try searching by source URL
            doc = await docs_collection.find_one({"source": {"$regex": video_id}})
            if doc:
                print(f"   Found by URL match: {doc.get('title', 'N/A')}")

        # Check chunks collection
        chunks_collection = db[config.mongodb_collection_chunks]
        chunk_count = await chunks_collection.count_documents({"metadata.video_id": video_id})

        if chunk_count == 0:
            # Try by document_id
            if doc:
                chunk_count = await chunks_collection.count_documents(
                    {"document_id": str(doc.get("_id"))}
                )

        print(f"   📦 Chunks in MongoDB: {chunk_count}")

        # Get sample chunk
        if chunk_count > 0:
            sample_chunk = await chunks_collection.find_one(
                {"document_id": str(doc.get("_id"))} if doc else {}
            )
            if sample_chunk:
                print("   📄 Sample chunk content (first 200 chars):")
                content = sample_chunk.get("content", "")[:200]
                print(f"      {content}...")

        return {
            "document_found": doc is not None,
            "document_id": str(doc.get("_id")) if doc else None,
            "chunk_count": chunk_count,
        }

    finally:
        client.close()


async def verify_neo4j(video_id: str) -> dict:
    """
    Verify the video was ingested into Neo4j/Graphiti.
    """
    print_section("STEP 3: VERIFY NEO4J/GRAPHITI DATA")

    try:
        from capabilities.retrieval.graphiti_rag.config import config
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
        )

        async with driver.session() as session:
            # Query for YouTube episodes
            query = f"""
            MATCH (e:Episode)
            WHERE e.name STARTS WITH 'youtube:{video_id}'
            RETURN e.name as name,
                   e.source_description as description,
                   e.reference_time as timestamp
            ORDER BY e.reference_time
            """

            result = await session.run(query)
            episodes = [record.data() async for record in result]

            if episodes:
                print(f"✅ Found {len(episodes)} Graphiti episodes!")
                for ep in episodes:
                    print(f"   📺 {ep.get('name')}")
                    print(f"      Description: {ep.get('description')}")
            else:
                print(f"❌ No Graphiti episodes found for video_id: {video_id}")

                # Check if any Episode nodes exist at all
                count_result = await session.run("MATCH (e:Episode) RETURN count(e) as count")
                count_record = await count_result.single()
                total_episodes = count_record["count"] if count_record else 0
                print(f"   Total Episode nodes in Neo4j: {total_episodes}")

                if total_episodes == 0:
                    print("   ℹ️  Graphiti may not be initialized or USE_GRAPHITI=false")

        await driver.close()

        return {
            "episodes_found": len(episodes),
            "episodes": episodes,
        }

    except ImportError:
        print("❌ neo4j package not installed. Run: pip install neo4j")
        return {"episodes_found": 0, "error": "neo4j not installed"}
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        return {"episodes_found": 0, "error": str(e)}


async def list_all_youtube_data() -> None:
    """
    List all YouTube data in both databases.
    """
    print_section("ALL YOUTUBE DATA IN DATABASES")

    # MongoDB
    print("\n📊 MongoDB YouTube Documents:")
    try:
        from capabilities.retrieval.mongo_rag.config import config
        from pymongo import AsyncMongoClient

        client = AsyncMongoClient(config.mongodb_uri)
        db = client[config.mongodb_database]
        docs_collection = db[config.mongodb_collection_documents]

        # Find all YouTube documents
        cursor = docs_collection.find({"metadata.source_type": "youtube"})
        docs = await cursor.to_list(length=100)

        if docs:
            for doc in docs:
                video_id = doc.get("metadata", {}).get("video_id", "N/A")
                title = doc.get("title", "N/A")
                print(f"   • {video_id}: {title}")
        else:
            print("   No YouTube documents found")

        client.close()
    except Exception as e:
        print(f"   Error querying MongoDB: {e}")

    # Neo4j
    print("\n📊 Neo4j YouTube Episodes:")
    try:
        from capabilities.retrieval.graphiti_rag.config import config
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
        )

        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Episode)
                WHERE e.name STARTS WITH 'youtube:'
                RETURN e.name as name
                LIMIT 20
            """
            )
            episodes = [record.data() async for record in result]

            if episodes:
                for ep in episodes:
                    print(f"   • {ep.get('name')}")
            else:
                print("   No YouTube episodes found")

        await driver.close()
    except Exception as e:
        print(f"   Error querying Neo4j: {e}")


async def main(url: str, verify_only: bool = False) -> None:
    """
    Main function to ingest and verify YouTube video.
    """
    from workflows.ingestion.youtube_rag.services.youtube_client import YouTubeClient

    video_id = YouTubeClient.extract_video_id(url)

    print("\n" + "═" * 70)
    print(" 🎬 YOUTUBE RAG INGESTION & VERIFICATION")
    print("═" * 70)
    print(f"Video URL: {url}")
    print(f"Video ID: {video_id}")
    print("═" * 70)

    if not verify_only:
        # Step 1: Ingest
        result = await ingest_video(url)

    # Step 2: Verify MongoDB
    mongo_result = await verify_mongodb(video_id)

    # Step 3: Verify Neo4j
    neo4j_result = await verify_neo4j(video_id)

    # Summary
    print_section("VERIFICATION SUMMARY")
    print(
        f"📊 MongoDB: {'✅ Document found' if mongo_result.get('document_found') else '❌ Not found'}"
    )
    print(f"   Chunks: {mongo_result.get('chunk_count', 0)}")
    print(
        f"📊 Neo4j:  {'✅ Episodes found' if neo4j_result.get('episodes_found', 0) > 0 else '❌ Not found'}"
    )
    print(f"   Episodes: {neo4j_result.get('episodes_found', 0)}")

    # List all YouTube data
    await list_all_youtube_data()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest YouTube video and verify in MongoDB/Neo4j")
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_VIDEO_URL,
        help="YouTube video URL",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing data, don't ingest",
    )

    args = parser.parse_args()
    asyncio.run(main(args.url, args.verify_only))
