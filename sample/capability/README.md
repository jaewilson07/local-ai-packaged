# Sample Capability Tests

This directory contains sample scripts and tests demonstrating various capabilities of the local-ai-packaged system.

## Available Scripts

### 1. `test_crawl_bluesmuse.py`
Test script that crawls a single page from https://www.bluesmuse.dance/ using crawl4ai.

**Usage:**
```bash
python sample/capability/test_crawl_bluesmuse.py
```

### 2. `deep_crawl_bluesmuse.py`
Performs a deep crawl of https://www.bluesmuse.dance/ and ingests all discovered pages into MongoDB and Graphiti.

**Usage:**
```bash
python sample/capability/deep_crawl_bluesmuse.py
```

### 3. `query_graphiti_data.py`
Query and explore Graphiti-imported data in Neo4j, and search the knowledge graph.

**Usage:**
```bash
# Run example queries
python sample/capability/query_graphiti_data.py explore

# Interactive search
python sample/capability/query_graphiti_data.py search

# Direct search
python sample/capability/query_graphiti_data.py search "Blues Muse"

# Execute Cypher query
python sample/capability/query_graphiti_data.py cypher "MATCH (n) RETURN labels(n), count(n) LIMIT 10"
```

## Documentation

### `query_graphiti_neo4j.md`
Complete guide on:
- Accessing Neo4j to view Graphiti data
- Useful Cypher queries for exploring the knowledge graph
- Using REST API endpoints to search and query
- Chatting with ingested data

## Viewing Graphiti Data in Neo4j

### Option 1: Neo4j Browser (Web UI)

1. **Check if Neo4j Browser is exposed:**
   ```bash
   docker compose -p localai-data ps neo4j
   ```

2. **Access Neo4j Browser:**
   - URL: `http://localhost:7474` (if port is exposed)
   - Default credentials: `neo4j` / `password` (check your `.env` file)

3. **Or connect via Docker:**
   ```bash
   docker exec -it neo4j cypher-shell -u neo4j -p password
   ```

### Option 2: Via REST API

Use the `/api/v1/graphiti/knowledge-graph/query` endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/graphiti/knowledge-graph/query \
  -H "Content-Type: application/json" \
  -d '{"command": "query MATCH (n) RETURN labels(n), count(n) LIMIT 10"}'
```

## Chatting with Ingested Data

### Via REST API Search

```bash
curl -X POST http://localhost:8000/api/v1/graphiti/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Blues Muse?",
    "match_count": 10
  }'
```

### Via Python Script

```bash
python sample/capability/query_graphiti_data.py search "Blues Muse event"
```

### Via MCP Tools

If you have MCP access, use the `search_graphiti` tool in your conversations.

## Quick Reference

### View All Node Types
```cypher
MATCH (n) RETURN DISTINCT labels(n) as node_type, count(n) as count ORDER BY count DESC
```

### View Facts
```cypher
MATCH (f:Fact) RETURN f.fact as fact LIMIT 20
```

### View Entities
```cypher
MATCH (e:Entity) RETURN e.name as name, e.type as type LIMIT 20
```

### Search for Specific Topic
```cypher
MATCH (f:Fact) WHERE f.fact CONTAINS 'Blues Muse' RETURN f.fact as fact LIMIT 10
```

## Notes

- Graphiti is **enabled by default** for crawl4ai RAG flow
- All crawled content is automatically ingested into Graphiti
- Use natural language search for queries
- Use Cypher queries for specific graph exploration
- See `query_graphiti_neo4j.md` for complete documentation
