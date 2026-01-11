#!/usr/bin/env python3
"""Example script to query Graphiti data in Neo4j and chat with ingested data.

This script demonstrates:
1. How to view Graphiti-imported data in Neo4j using Cypher queries
2. How to search the Graphiti knowledge graph via REST API
3. How to use the Graphiti search for natural language queries
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def search_graphiti(query: str, match_count: int = 10) -> Dict[str, Any]:
    """Search the Graphiti knowledge graph."""
    url = f"{BASE_URL}/api/v1/graphiti/search"
    payload = {
        "query": query,
        "match_count": match_count
    }
    
    print(f"\n🔍 Searching Graphiti for: '{query}'")
    print("-" * 80)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Found {result['count']} results\n")
        
        for i, item in enumerate(result['results'][:5], 1):
            print(f"{i}. Fact: {item.get('fact', 'N/A')[:200]}...")
            print(f"   Similarity: {item.get('similarity', 0):.3f}")
            if item.get('metadata'):
                metadata = item['metadata']
                if 'source' in metadata:
                    print(f"   Source: {metadata['source']}")
                if 'title' in metadata:
                    print(f"   Title: {metadata['title']}")
            print()
        
        if result['count'] > 5:
            print(f"... and {result['count'] - 5} more results\n")
        
        return result
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if e.response.status_code == 400:
            print(f"   Response: {e.response.text}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}


def query_neo4j_cypher(cypher_query: str) -> Dict[str, Any]:
    """Execute a Cypher query on Neo4j via the API."""
    url = f"{BASE_URL}/api/v1/graphiti/knowledge-graph/query"
    payload = {
        "command": f"query {cypher_query}"
    }
    
    print(f"\n📊 Executing Cypher Query:")
    print(f"   {cypher_query}")
    print("-" * 80)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            data = result.get('data', {})
            if 'results' in data:
                print(f"✅ Query returned {len(data['results'])} results\n")
                for i, record in enumerate(data['results'][:10], 1):
                    print(f"{i}. {json.dumps(record, indent=2)}")
                if len(data['results']) > 10:
                    print(f"\n... and {len(data['results']) - 10} more results")
            else:
                print(f"✅ Query result: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Query failed: {result.get('error', 'Unknown error')}")
        
        return result
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        if e.response.status_code == 400:
            print(f"   Response: {e.response.text}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}


def explore_graphiti_data():
    """Explore Graphiti data with example queries."""
    print("=" * 80)
    print("Graphiti Data Explorer")
    print("=" * 80)
    
    # Example 1: Search for Blues Muse
    print("\n📝 Example 1: Natural Language Search")
    search_graphiti("Blues Muse dance event", match_count=5)
    
    # Example 2: View all node types
    print("\n📝 Example 2: View All Node Types in Neo4j")
    query_neo4j_cypher("MATCH (n) RETURN DISTINCT labels(n) as node_type, count(n) as count ORDER BY count DESC LIMIT 20")
    
    # Example 3: View facts
    print("\n📝 Example 3: View Recent Facts")
    query_neo4j_cypher("MATCH (f:Fact) RETURN f.fact as fact, f.valid_from as valid_from LIMIT 10")
    
    # Example 4: View entities
    print("\n📝 Example 4: View Entities")
    query_neo4j_cypher("MATCH (e:Entity) RETURN e.name as name, e.type as type LIMIT 10")
    
    # Example 5: Find facts about Blues Muse
    print("\n📝 Example 5: Find Facts About Blues Muse")
    query_neo4j_cypher("MATCH (f:Fact) WHERE f.fact CONTAINS 'Blues Muse' OR f.fact CONTAINS 'blues' RETURN f.fact as fact LIMIT 10")
    
    # Example 6: View entity relationships
    print("\n📝 Example 6: View Entity Relationships")
    query_neo4j_cypher("MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity) RETURN e1.name as from, type(r) as relationship, e2.name as to LIMIT 10")
    
    print("\n" + "=" * 80)
    print("✅ Exploration complete!")
    print("=" * 80)


def interactive_search():
    """Interactive search interface."""
    print("=" * 80)
    print("Interactive Graphiti Search")
    print("=" * 80)
    print("Enter search queries (or 'quit' to exit)")
    print()
    
    while True:
        try:
            query = input("🔍 Search: ").strip()
            if not query:
                continue
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            result = search_graphiti(query, match_count=5)
            
            if result.get('success') and result.get('count', 0) > 0:
                print(f"\n💡 Found {result['count']} relevant facts!")
            else:
                print("\n⚠️  No results found or search failed")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "explore":
            explore_graphiti_data()
        elif sys.argv[1] == "search":
            if len(sys.argv) > 2:
                query = " ".join(sys.argv[2:])
                search_graphiti(query)
            else:
                interactive_search()
        elif sys.argv[1] == "cypher" and len(sys.argv) > 2:
            cypher = " ".join(sys.argv[2:])
            query_neo4j_cypher(cypher)
        else:
            print("Usage:")
            print("  python query_graphiti_data.py explore          # Run example queries")
            print("  python query_graphiti_data.py search          # Interactive search")
            print("  python query_graphiti_data.py search <query>   # Search for specific query")
            print("  python query_graphiti_data.py cypher <query>   # Execute Cypher query")
    else:
        explore_graphiti_data()


if __name__ == "__main__":
    main()
