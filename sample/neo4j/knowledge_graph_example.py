#!/usr/bin/env python3
"""Knowledge graph example using Neo4j.

This example demonstrates building a knowledge graph in Neo4j
with entities, relationships, and properties. This is useful
for understanding how Graphiti RAG uses Neo4j for code structure
analysis and hallucination detection.

Prerequisites:
- Neo4j running and configured
- Environment variables configured (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, etc.)
"""

import asyncio
import sys
import os
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

from neo4j import AsyncGraphDatabase
from server.core.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate knowledge graph operations."""
    print("="*80)
    print("Neo4j - Knowledge Graph Example")
    print("="*80)
    print()
    print("This example demonstrates knowledge graph operations:")
    print("  - Creating entities (nodes) with properties")
    print("  - Creating relationships between entities")
    print("  - Querying graph patterns")
    print("  - Traversing relationships")
    print()
    
    # Initialize Neo4j driver
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    try:
        async with driver.session() as session:
            # 1. Create a knowledge graph structure
            print("="*80)
            print("1. CREATING KNOWLEDGE GRAPH")
            print("="*80)
            
            # Create entities and relationships
            result = await session.run(
                """
                // Create repository
                CREATE (r:Repository {name: 'example-repo', url: 'https://github.com/example/repo.git'})
                
                // Create files
                CREATE (f1:File {name: 'main.py', path: 'src/main.py'})
                CREATE (f2:File {name: 'utils.py', path: 'src/utils.py'})
                
                // Create classes
                CREATE (c1:Class {name: 'MainClass', full_name: 'src.main.MainClass'})
                CREATE (c2:Class {name: 'HelperClass', full_name: 'src.utils.HelperClass'})
                
                // Create methods
                CREATE (m1:Method {name: 'process', full_name: 'src.main.MainClass.process'})
                CREATE (m2:Method {name: 'helper', full_name: 'src.utils.HelperClass.helper'})
                
                // Create relationships
                CREATE (r)-[:CONTAINS]->(f1)
                CREATE (r)-[:CONTAINS]->(f2)
                CREATE (f1)-[:DEFINES]->(c1)
                CREATE (f2)-[:DEFINES]->(c2)
                CREATE (c1)-[:HAS_METHOD]->(m1)
                CREATE (c2)-[:HAS_METHOD]->(m2)
                CREATE (m1)-[:CALLS]->(m2)
                
                RETURN r, f1, f2, c1, c2, m1, m2
                """
            )
            await result.consume()
            print("✅ Created knowledge graph structure:")
            print("   Repository -> Files -> Classes -> Methods")
            print("   Method calls relationship")
            print()
            
            # 2. Query graph patterns
            print("="*80)
            print("2. QUERYING GRAPH PATTERNS")
            print("="*80)
            
            result = await session.run(
                """
                MATCH (r:Repository)-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)-[:HAS_METHOD]->(m:Method)
                RETURN r.name AS repo, f.name AS file, c.name AS class, m.name AS method
                """
            )
            records = [record async for record in result]
            
            print("✅ Found code structure:")
            for record in records:
                print(f"   {record['repo']} -> {record['file']} -> {record['class']} -> {record['method']}")
            print()
            
            # 3. Traverse relationships
            print("="*80)
            print("3. TRAVERSING RELATIONSHIPS")
            print("="*80)
            
            result = await session.run(
                """
                MATCH path = (m1:Method)-[:CALLS]->(m2:Method)
                RETURN m1.full_name AS caller, m2.full_name AS callee
                """
            )
            records = [record async for record in result]
            
            print("✅ Found method calls:")
            for record in records:
                print(f"   {record['caller']} calls {record['callee']}")
            print()
            
            # 4. Complex graph query
            print("="*80)
            print("4. COMPLEX GRAPH QUERY")
            print("="*80)
            
            result = await session.run(
                """
                MATCH (r:Repository)-[:CONTAINS*]->(n)
                WHERE n:Class OR n:Method
                RETURN labels(n)[0] AS type, n.name AS name, count(*) AS count
                ORDER BY count DESC
                """
            )
            records = [record async for record in result]
            
            print("✅ Graph statistics:")
            for record in records:
                print(f"   {record['type']}: {record['name']} (count: {record['count']})")
            print()
            
            # 5. Cleanup (optional)
            print("="*80)
            print("5. CLEANUP (Optional)")
            print("="*80)
            print("To clean up the test data, uncomment the cleanup section.")
            # Uncomment to clean up:
            # await session.run("MATCH (n) DETACH DELETE n")
            # print("✅ Cleaned up test data")
        
        print("="*80)
        print("✅ Knowledge graph examples completed!")
        print("="*80)
        print()
        print("This demonstrates how Graphiti RAG uses Neo4j to:")
        print("  - Store code structure (repositories, files, classes, methods)")
        print("  - Track relationships (contains, defines, calls)")
        print("  - Query code patterns for hallucination detection")
        print("="*80)
        
    except Exception as e:
        logger.exception(f"❌ Error during knowledge graph operations: {e}")
        print(f"\n❌ Fatal error: {e}")
        print("\nNote: Make sure Neo4j is running and credentials are correct.")
        sys.exit(1)
    finally:
        # Close driver
        await driver.close()
        logger.info("🧹 Neo4j driver closed")


if __name__ == "__main__":
    asyncio.run(main())
