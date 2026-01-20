#!/usr/bin/env python3
"""
Verify YouTube data in MongoDB and Neo4j databases.

This is a standalone script that doesn't rely on the Lambda server imports.

Usage:
    python sample/youtube_rag/verify_databases.py [--video-id VIDEO_ID]
"""

import argparse
import asyncio
import os
from pathlib import Path

# Load .env from project root
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")


def print_section(title: str, char: str = "=") -> None:
    """Print a section header."""
    width = 70
    print(f"\n{char * width}")
    print(f" {title}")
    print(f"{char * width}")


async def verify_mongodb(video_id: str | None = None) -> dict:
    """
    Verify YouTube data in MongoDB.
    """
    print_section("MONGODB YOUTUBE DATA")

    try:
        from pymongo import AsyncMongoClient

        # Get connection from env or use default
        # Use localhost for local testing (outside Docker), mongodb:27017 is for inside Docker
        mongodb_uri = os.getenv(
            "MONGODB_URI",
            "mongodb://admin:admin123@localhost:27017/?directConnection=true&authSource=admin",
        )
        # Override if we're running locally and the URI has the Docker hostname
        if "@mongodb:" in mongodb_uri and not os.getenv("RUNNING_IN_DOCKER"):
            mongodb_uri = mongodb_uri.replace("@mongodb:", "@localhost:")
        mongodb_database = os.getenv("MONGODB_DATABASE", "rag_db")

        print(f"Connecting to: {mongodb_uri.split('@')[1] if '@' in mongodb_uri else mongodb_uri}")

        client = AsyncMongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        db = client[mongodb_database]

        # List collections
        collections = await db.list_collection_names()
        print(f"📁 Collections: {collections}")

        # Check documents collection
        docs_collection = db.get_collection("documents")

        # Find YouTube documents
        if video_id:
            query = {
                "$or": [
                    {"metadata.video_id": video_id},
                    {"source": {"$regex": video_id}},
                ]
            }
        else:
            query = {"metadata.source_type": "youtube"}

        cursor = docs_collection.find(query)
        docs = await cursor.to_list(length=100)

        print(f"\n📊 YouTube Documents Found: {len(docs)}")

        results = []
        for doc in docs:
            video_id_found = doc.get("metadata", {}).get("video_id", "N/A")
            title = doc.get("title", "N/A")
            doc_id = str(doc.get("_id"))
            created = doc.get("created_at", "N/A")

            print(f"\n   📺 Video ID: {video_id_found}")
            print(f"      Title: {title}")
            print(f"      Document ID: {doc_id}")
            print(f"      Created: {created}")

            # Count chunks for this document
            chunks_collection = db.get_collection("chunks")
            chunk_count = await chunks_collection.count_documents({"document_id": doc_id})
            print(f"      Chunks: {chunk_count}")

            results.append(
                {
                    "video_id": video_id_found,
                    "title": title,
                    "document_id": doc_id,
                    "chunk_count": chunk_count,
                }
            )

        if not docs:
            print("   ❌ No YouTube documents found")
            if video_id:
                print(f"      Searched for video_id: {video_id}")

        client.close()
        return {"documents": results, "total": len(docs)}

    except Exception as e:
        print(f"❌ MongoDB Error: {e}")
        return {"error": str(e), "documents": [], "total": 0}


async def verify_neo4j(video_id: str | None = None) -> dict:
    """
    Verify YouTube episodes in Neo4j/Graphiti.
    """
    print_section("NEO4J/GRAPHITI YOUTUBE EPISODES")

    try:
        from neo4j import AsyncGraphDatabase

        # Get connection from env or use default
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

        print(f"Connecting to: {neo4j_uri}")

        driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
        )

        async with driver.session() as session:
            # Query for YouTube episodes
            if video_id:
                query = f"""
                MATCH (e:Episode)
                WHERE e.name STARTS WITH 'youtube:{video_id}'
                RETURN e.name as name,
                       e.source_description as description,
                       e.reference_time as timestamp,
                       e.created_at as created_at
                ORDER BY e.reference_time
                """
            else:
                query = """
                MATCH (e:Episode)
                WHERE e.name STARTS WITH 'youtube:'
                RETURN e.name as name,
                       e.source_description as description,
                       e.reference_time as timestamp,
                       e.created_at as created_at
                ORDER BY e.created_at DESC
                LIMIT 50
                """

            result = await session.run(query)
            episodes = [record.data() async for record in result]

            print(f"\n📊 YouTube Episodes Found: {len(episodes)}")

            for ep in episodes:
                name = ep.get("name", "N/A")
                desc = ep.get("description", "N/A")
                timestamp = ep.get("timestamp", "N/A")

                # Parse video ID from name
                parts = name.split(":") if name else []
                vid = parts[1] if len(parts) > 1 else "N/A"
                ep_type = parts[2] if len(parts) > 2 else "N/A"

                print(f"\n   📺 Video: {vid}")
                print(f"      Type: {ep_type}")
                print(f"      Description: {desc}")
                print(f"      Timestamp: {timestamp}")

            if not episodes:
                print("   ❌ No YouTube episodes found")

                # Check total Episode count
                count_result = await session.run("MATCH (e:Episode) RETURN count(e) as count")
                count_record = await count_result.single()
                total = count_record["count"] if count_record else 0
                print(f"\n   📊 Total Episode nodes in database: {total}")

                # Check if Graphiti is enabled
                if total == 0:
                    print("   ℹ️  No Episode nodes exist - Graphiti may not be initialized")
                    print("      Check if USE_GRAPHITI=true in your .env file")

        await driver.close()
        return {"episodes": episodes, "total": len(episodes)}

    except ImportError:
        print("❌ neo4j package not installed")
        print("   Run: pip install neo4j")
        return {"error": "neo4j not installed", "episodes": [], "total": 0}
    except Exception as e:
        print(f"❌ Neo4j Error: {e}")
        return {"error": str(e), "episodes": [], "total": 0}


async def main(video_id: str | None = None) -> None:
    """
    Main verification function.
    """
    print("\n" + "═" * 70)
    print(" 🔍 YOUTUBE DATA VERIFICATION")
    print("═" * 70)
    if video_id:
        print(f"Searching for Video ID: {video_id}")
    else:
        print("Searching for all YouTube content")
    print("═" * 70)

    # Verify both databases
    mongo_result = await verify_mongodb(video_id)
    neo4j_result = await verify_neo4j(video_id)

    # Summary
    print_section("SUMMARY")
    mongo_count = mongo_result.get("total", 0)
    neo4j_count = neo4j_result.get("total", 0)

    print(f"📊 MongoDB:  {mongo_count} YouTube document(s)")
    print(f"📊 Neo4j:    {neo4j_count} YouTube episode(s)")

    if mongo_count == 0 and neo4j_count == 0:
        print("\n⚠️  No YouTube data found in either database!")
        print("   To ingest a video, run:")
        print(
            "   python sample/youtube_rag/ingest_video.py --url 'https://youtube.com/watch?v=VIDEO_ID'"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify YouTube data in MongoDB and Neo4j")
    parser.add_argument(
        "--video-id",
        type=str,
        default=None,
        help="Specific video ID to search for (optional)",
    )

    args = parser.parse_args()
    asyncio.run(main(args.video_id))
