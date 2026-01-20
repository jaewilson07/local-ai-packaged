#!/usr/bin/env python3
"""Verify YouTube video was ingested into MongoDB and Neo4j."""

import asyncio
import sys
from pathlib import Path

# Setup path
project_root = Path(__file__).parent.parent.parent
lambda_src = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_src))


async def verify_mongodb():
    """Check MongoDB for ingested data."""
    print("=" * 60)
    print(" MONGODB VERIFICATION")
    print("=" * 60)

    from capabilities.retrieval.mongo_rag.config import config
    from pymongo import AsyncMongoClient

    client = AsyncMongoClient(config.mongodb_uri)
    db = client[config.mongodb_database]

    try:
        # Check documents
        docs_collection = db[config.mongodb_collection_documents]

        # Find by video_id
        doc = await docs_collection.find_one({"metadata.video_id": "A3DKwLORVe4"})

        if doc:
            print("Document found!")
            print(f"   Title: {doc.get('title')}")
            print(f"   Source: {doc.get('source')}")
            print(f"   Source Type: {doc.get('metadata', {}).get('source_type')}")
            print(f"   Video ID: {doc.get('metadata', {}).get('video_id')}")
            print(f"   Document ID: {doc.get('_id')}")
        else:
            print("Document not found by video_id")
            # List all docs
            cursor = docs_collection.find({})
            docs = await cursor.to_list(length=10)
            print(f"\nFound {len(docs)} documents total:")
            for d in docs:
                print(f"   - {d.get('title', 'N/A')} ({d.get('_id')})")

        # Check chunks
        chunks_collection = db[config.mongodb_collection_chunks]
        total_chunks = await chunks_collection.count_documents({})
        print(f"\nTotal chunks in collection: {total_chunks}")

        if doc:
            doc_id = str(doc.get("_id"))
            doc_chunks = await chunks_collection.count_documents({"document_id": doc_id})
            print(f"Chunks for this document: {doc_chunks}")

            # Sample chunk
            sample = await chunks_collection.find_one({"document_id": doc_id})
            if sample:
                content = sample.get("content", "")[:300]
                print("\nSample chunk preview:")
                print(f"   {content}...")
                has_embedding = sample.get("embedding") is not None
                embedding_len = len(sample.get("embedding", [])) if has_embedding else 0
                print(f"   Has embedding: {has_embedding} (dim={embedding_len})")

    finally:
        client.close()


async def verify_neo4j():
    """Check Neo4j for Graphiti episodes."""
    print("\n" + "=" * 60)
    print(" NEO4J/GRAPHITI VERIFICATION")
    print("=" * 60)

    try:
        from capabilities.retrieval.graphiti_rag.config import config
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
        )

        async with driver.session() as session:
            # Count total episodes
            result = await session.run("MATCH (e:Episode) RETURN count(e) as count")
            record = await result.single()
            total_episodes = record["count"] if record else 0
            print(f"Total Episode nodes: {total_episodes}")

            # Find YouTube episodes
            result = await session.run(
                """
                MATCH (e:Episode)
                WHERE e.name STARTS WITH 'youtube:'
                RETURN e.name as name, e.source_description as desc
                LIMIT 10
                """
            )
            episodes = [r.data() async for r in result]

            if episodes:
                print(f"\nYouTube episodes found: {len(episodes)}")
                for ep in episodes:
                    print(f"   - {ep.get('name')}")
            else:
                print("\nNo YouTube episodes found")

            # Check for any Entity nodes related to our video
            result = await session.run(
                """
                MATCH (n)
                WHERE any(label in labels(n) WHERE label IN ['Entity', 'Fact', 'Episode'])
                RETURN labels(n) as labels, count(n) as count
                """
            )
            counts = [r.data() async for r in result]
            print("\nGraphiti node counts:")
            for c in counts:
                print(f"   {c['labels']}: {c['count']}")

        await driver.close()

    except ImportError:
        print("neo4j package not installed")
    except Exception as e:
        print(f"Neo4j connection error: {e}")


async def main():
    await verify_mongodb()
    await verify_neo4j()


if __name__ == "__main__":
    asyncio.run(main())
