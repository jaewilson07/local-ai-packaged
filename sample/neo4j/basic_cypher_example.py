#!/usr/bin/env python3
"""Basic Cypher query example using Neo4j.

This example demonstrates basic Cypher query operations using Neo4j
directly (not through Graphiti). Useful for understanding Neo4j
fundamentals and testing queries.

Prerequisites:
- Neo4j running and configured
- Environment variables configured (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, etc.)
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging

from neo4j import AsyncGraphDatabase

from server.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate basic Cypher queries."""
    print("=" * 80)
    print("Neo4j - Basic Cypher Query Example")
    print("=" * 80)
    print()
    print("This example demonstrates basic Cypher query operations:")
    print("  - Creating nodes and relationships")
    print("  - Querying nodes and relationships")
    print("  - Updating and deleting data")
    print()

    # Initialize Neo4j driver
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )

    try:
        async with driver.session() as session:
            # 1. Create nodes
            print("=" * 80)
            print("1. CREATING NODES")
            print("=" * 80)

            result = await session.run(
                """
                CREATE (p1:Person {name: 'Alice', age: 30})
                CREATE (p2:Person {name: 'Bob', age: 25})
                CREATE (c:Company {name: 'Tech Corp'})
                RETURN p1, p2, c
                """
            )
            await result.consume()
            print("✅ Created nodes: Person (Alice, Bob), Company (Tech Corp)")
            print()

            # 2. Create relationships
            print("=" * 80)
            print("2. CREATING RELATIONSHIPS")
            print("=" * 80)

            result = await session.run(
                """
                MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'})
                CREATE (a)-[:KNOWS]->(b)
                RETURN a, b
                """
            )
            await result.consume()
            print("✅ Created relationship: Alice KNOWS Bob")
            print()

            # 3. Query nodes
            print("=" * 80)
            print("3. QUERYING NODES")
            print("=" * 80)

            result = await session.run("MATCH (p:Person) RETURN p.name AS name, p.age AS age")
            records = [record async for record in result]

            print("✅ Found persons:")
            for record in records:
                print(f"   {record['name']}, age {record['age']}")
            print()

            # 4. Query relationships
            print("=" * 80)
            print("4. QUERYING RELATIONSHIPS")
            print("=" * 80)

            result = await session.run(
                """
                MATCH (a:Person)-[r:KNOWS]->(b:Person)
                RETURN a.name AS from, b.name AS to, type(r) AS relationship
                """
            )
            records = [record async for record in result]

            print("✅ Found relationships:")
            for record in records:
                print(f"   {record['from']} {record['relationship']} {record['to']}")
            print()

            # 5. Cleanup (optional)
            print("=" * 80)
            print("5. CLEANUP (Optional)")
            print("=" * 80)
            print("To clean up the test data, uncomment the cleanup section.")
            # Uncomment to clean up:
            # await session.run("MATCH (n) DETACH DELETE n")  # noqa: ERA001
            # print("✅ Cleaned up test data")  # noqa: ERA001

        print("=" * 80)
        print("✅ Basic Cypher query examples completed!")
        print("=" * 80)
        print()
        print("You can use these patterns for:")
        print("  - Creating knowledge graphs")
        print("  - Querying relationships")
        print("  - Building graph-based applications")
        print("=" * 80)

        # Verify via API
        try:
            from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
            from sample.shared.verification_helpers import verify_neo4j_data

            api_base_url = get_api_base_url()
            headers = get_auth_headers()

            print("\n" + "=" * 80)
            print("Verification")
            print("=" * 80)

            success, message = verify_neo4j_data(
                api_base_url=api_base_url,
                headers=headers,
                expected_nodes_min=1,
            )
            print(message)

            if success:
                print("\n✅ Verification passed!")
                sys.exit(0)
            else:
                print("\n⚠️  Verification failed (nodes may need time to sync)")
                sys.exit(1)
        except Exception as e:
            logger.warning(f"Verification error: {e}")
            print(f"\n⚠️  Verification error: {e}")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ Error during Cypher queries: {e}")
        print(f"\n❌ Fatal error: {e}")
        print("\nNote: Make sure Neo4j is running and credentials are correct.")
        sys.exit(1)
    finally:
        # Close driver
        await driver.close()
        logger.info("🧹 Neo4j driver closed")


if __name__ == "__main__":
    asyncio.run(main())
