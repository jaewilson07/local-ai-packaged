#!/usr/bin/env python3
"""
Sample script demonstrating extraction of Graphiti nodes from ingested YouTube videos.

This script shows how to:
1. Search for YouTube-related episodes in Graphiti
2. Extract entities and relationships from the knowledge graph
3. Display the temporal structure of ingested video content

Usage:
    python sample/youtube_rag/extract_graphiti_nodes.py [--video-id VIDEO_ID] [--query QUERY]

Examples:
    # List all YouTube episodes
    python sample/youtube_rag/extract_graphiti_nodes.py

    # Search for specific video
    python sample/youtube_rag/extract_graphiti_nodes.py --video-id A3DKwLORVe4

    # Search by query
    python sample/youtube_rag/extract_graphiti_nodes.py --query "machine learning"
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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def list_youtube_episodes(video_id: str | None = None) -> list[dict]:
    """
    List YouTube episodes in Graphiti.

    Args:
        video_id: Optional video ID to filter by

    Returns:
        List of episode dictionaries
    """
    try:
        from capabilities.retrieval.graphiti_rag.config import config as graphiti_config
        from capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps
    except ImportError:
        print("❌ Graphiti dependencies not available")
        print("   Make sure graphiti_core is installed: pip install graphiti-core")
        return []

    logger.info("Connecting to Graphiti...")

    deps = GraphitiRAGDeps.from_settings()
    await deps.initialize()

    try:
        if not deps.graphiti:
            print("❌ Graphiti not initialized - check NEO4J configuration")
            return []

        # Build Cypher query to find YouTube episodes
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

        print("\n" + "=" * 70)
        print("🔗 Graphiti YouTube Episodes")
        print("=" * 70)

        # Execute query via Neo4j driver directly from Graphiti
        # Graphiti internally uses neo4j driver
        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                graphiti_config.neo4j_uri,
                auth=(graphiti_config.neo4j_user, graphiti_config.neo4j_password),
            )

            async with driver.session() as session:
                result = await session.run(query)
                records = [record.data() async for record in result]

            await driver.close()

            if not records:
                print("📭 No YouTube episodes found in Graphiti")
                if video_id:
                    print(f"   Try ingesting video {video_id} first:")
                    print(
                        f"   python sample/youtube_rag/ingest_video.py --url 'https://youtube.com/watch?v={video_id}'"
                    )
                return []

            episodes = []
            for record in records:
                episode = {
                    "name": record.get("name"),
                    "description": record.get("description"),
                    "timestamp": str(record.get("timestamp")),
                    "created_at": str(record.get("created_at")),
                }
                episodes.append(episode)

                # Parse episode name
                parts = episode["name"].split(":") if episode["name"] else []
                if len(parts) >= 3:
                    vid = parts[1]
                    ep_type = parts[2] if len(parts) > 2 else "unknown"
                    ep_title = ":".join(parts[3:]) if len(parts) > 3 else ""

                    print(f"\n📺 Video: {vid}")
                    print(f"   Type: {ep_type}")
                    if ep_title:
                        print(f"   Title: {ep_title}")
                    print(f"   Description: {episode['description']}")
                    print(f"   Timestamp: {episode['timestamp']}")

            print("\n" + "-" * 70)
            print(f"📊 Total episodes found: {len(episodes)}")
            print("=" * 70)

            return episodes

        except ImportError:
            print("❌ neo4j package not installed. Run: pip install neo4j")
            return []
        except Exception as e:
            print(f"❌ Neo4j query failed: {e}")
            return []

    finally:
        await deps.cleanup()


async def search_graphiti_knowledge(query: str, match_count: int = 10) -> list[dict]:
    """
    Search Graphiti knowledge graph for YouTube content.

    Args:
        query: Search query
        match_count: Number of results to return

    Returns:
        List of search results
    """
    try:
        from capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps
        from capabilities.retrieval.graphiti_rag.search.graph_search import graphiti_search
    except ImportError:
        print("❌ Graphiti dependencies not available")
        return []

    logger.info(f"Searching Graphiti for: {query}")

    deps = GraphitiRAGDeps.from_settings()
    await deps.initialize()

    try:
        if not deps.graphiti:
            print("❌ Graphiti not initialized")
            return []

        # Use Graphiti search directly (bypasses RunContext requirement)
        search_results = await graphiti_search(
            graphiti=deps.graphiti,
            query=query,
            match_count=match_count,
        )

        print("\n" + "=" * 70)
        print(f"🔍 Graphiti Search Results for: '{query}'")
        print("=" * 70)

        if not search_results:
            print("📭 No results found")
            return []

        results = []
        for i, result in enumerate(search_results, 1):
            print(f"\n--- Result {i} ---")
            result_dict = {
                "chunk_id": result.chunk_id,
                "content": result.content,
                "similarity": result.similarity,
                "metadata": result.metadata,
            }
            results.append(result_dict)
            print(f"  Content: {result.content[:200]}...")
            print(f"  Similarity: {result.similarity:.3f}")
            if result.metadata:
                print(f"  Metadata: {result.metadata}")

        print("\n" + "=" * 70)
        print(f"📊 Total results: {len(results)}")
        return results

    finally:
        await deps.cleanup()


async def extract_entities_and_relationships(video_id: str) -> dict:
    """
    Extract entities and relationships for a specific video.

    Args:
        video_id: YouTube video ID

    Returns:
        Dictionary with entities and relationships
    """
    try:
        from capabilities.retrieval.graphiti_rag.config import config as graphiti_config
        from capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps
    except ImportError:
        print("❌ Graphiti dependencies not available")
        return {"entities": [], "relationships": []}

    logger.info(f"Extracting entities for video: {video_id}")

    deps = GraphitiRAGDeps.from_settings()
    await deps.initialize()

    try:
        # Query for entities connected to this video's episodes
        entity_query = f"""
        MATCH (e:Episode)-[:MENTIONS]->(entity)
        WHERE e.name STARTS WITH 'youtube:{video_id}'
        RETURN DISTINCT labels(entity) as type,
               entity.name as name,
               count(*) as mentions
        ORDER BY mentions DESC
        LIMIT 30
        """

        # Query for relationships
        relationship_query = f"""
        MATCH (e:Episode)-[:MENTIONS]->(a)-[r]->(b)
        WHERE e.name STARTS WITH 'youtube:{video_id}'
        RETURN DISTINCT type(r) as relationship,
               a.name as source,
               b.name as target
        LIMIT 30
        """

        print("\n" + "=" * 70)
        print(f"🔗 Entities & Relationships for Video: {video_id}")
        print("=" * 70)

        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                graphiti_config.neo4j_uri,
                auth=(graphiti_config.neo4j_user, graphiti_config.neo4j_password),
            )

            async with driver.session() as session:
                # Get entities
                entities = []
                entity_result = await session.run(entity_query)
                entity_records = [record.data() async for record in entity_result]

                if entity_records:
                    print("\n📌 Entities:")
                    for record in entity_records:
                        entity = {
                            "type": (
                                record.get("type", ["Unknown"])[0]
                                if record.get("type")
                                else "Unknown"
                            ),
                            "name": record.get("name"),
                            "mentions": record.get("mentions", 0),
                        }
                        entities.append(entity)
                        print(
                            f"   • {entity['name']} ({entity['type']}) - {entity['mentions']} mentions"
                        )

                # Get relationships
                relationships = []
                rel_result = await session.run(relationship_query)
                rel_records = [record.data() async for record in rel_result]

                if rel_records:
                    print("\n🔀 Relationships:")
                    for record in rel_records:
                        rel = {
                            "source": record.get("source"),
                            "relationship": record.get("relationship"),
                            "target": record.get("target"),
                        }
                        relationships.append(rel)
                        print(f"   • {rel['source']} --[{rel['relationship']}]--> {rel['target']}")

            await driver.close()

            if not entities and not relationships:
                print("📭 No entities or relationships found for this video")
                print("   The video may not have been ingested with entity extraction enabled.")
                print("   Try: python sample/youtube_rag/ingest_video.py --extract-entities")

            print("\n" + "=" * 70)
            print(f"📊 Summary: {len(entities)} entities, {len(relationships)} relationships")
            print("=" * 70)

            return {"entities": entities, "relationships": relationships}

        except ImportError:
            print("❌ neo4j package not installed. Run: pip install neo4j")
            return {"entities": [], "relationships": []}
        except Exception as e:
            print(f"❌ Neo4j query failed: {e}")
            return {"entities": [], "relationships": []}

    finally:
        await deps.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract Graphiti nodes from ingested YouTube videos"
    )
    parser.add_argument(
        "--video-id",
        type=str,
        default=None,
        help="YouTube video ID to filter by",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Search query for knowledge graph",
    )
    parser.add_argument(
        "--entities",
        action="store_true",
        help="Extract entities and relationships for a video (requires --video-id)",
    )
    parser.add_argument(
        "--match-count",
        type=int,
        default=10,
        help="Number of results to return for search queries",
    )

    args = parser.parse_args()

    if args.query:
        asyncio.run(search_graphiti_knowledge(args.query, args.match_count))
    elif args.entities and args.video_id:
        asyncio.run(extract_entities_and_relationships(args.video_id))
    else:
        asyncio.run(list_youtube_episodes(args.video_id))
