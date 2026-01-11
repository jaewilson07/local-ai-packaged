# Querying Graphiti Data in Neo4j

This guide shows you how to view and query Graphiti-imported data in Neo4j.

## Accessing Neo4j

### Option 1: Neo4j Browser (Web UI)

1. **Access Neo4j Browser**:
   - URL: `http://localhost:7474` (if exposed) or via Docker port mapping
   - Default credentials: `neo4j` / `password` (check your `.env` file)

2. **Direct Connection**:
   ```bash
   # If Neo4j is running in Docker
   docker exec -it neo4j cypher-shell -u neo4j -p password
   ```

### Option 2: Via REST API

Use the `/api/v1/graphiti/knowledge-graph/query` endpoint to execute Cypher queries:

```bash
curl -X POST http://localhost:8000/api/v1/graphiti/knowledge-graph/query \
  -H "Content-Type: application/json" \
  -d '{"command": "query MATCH (n) RETURN labels(n), count(n) LIMIT 10"}'
```

## Graphiti Data Structure

Graphiti stores data in Neo4j with the following structure:

### Node Labels

- **Facts**: Temporal facts extracted from text
- **Entities**: Extracted entities (people, places, organizations, etc.)
- **Source**: Source documents/chunks

### Common Relationships

- `RELATES_TO`: Relationships between entities
- `HAS_FACT`: Links entities to facts
- `FROM_SOURCE`: Links facts to source documents

## Useful Cypher Queries

### 1. View All Node Types

```cypher
MATCH (n)
RETURN DISTINCT labels(n) as node_type, count(n) as count
ORDER BY count DESC
```

### 2. View All Facts

```cypher
MATCH (f:Fact)
RETURN f.fact as fact, f.valid_from as valid_from, f.valid_to as valid_to
LIMIT 20
```

### 3. View All Entities

```cypher
MATCH (e:Entity)
RETURN e.name as name, e.type as type, e.confidence as confidence
LIMIT 20
```

### 4. Find Facts Related to a Topic

```cypher
MATCH (f:Fact)
WHERE f.fact CONTAINS 'Blues Muse'
RETURN f.fact as fact, f.valid_from as valid_from
LIMIT 10
```

### 5. View Entity Relationships

```cypher
MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
RETURN e1.name as from, type(r) as relationship, e2.name as to
LIMIT 20
```

### 6. Find Facts from Crawled Content

```cypher
MATCH (s:Source)-[:FROM_SOURCE]->(f:Fact)
WHERE s.source CONTAINS 'bluesmuse.dance'
RETURN f.fact as fact, s.source as source
LIMIT 20
```

### 7. View Graph Statistics

```cypher
MATCH (n)
RETURN 
  labels(n)[0] as node_type,
  count(n) as count,
  collect(DISTINCT keys(n))[0] as properties
ORDER BY count DESC
```

### 8. Find Connected Entities

```cypher
MATCH (e:Entity {name: 'Blues Muse'})-[r*1..2]-(connected)
RETURN DISTINCT labels(connected)[0] as type, connected.name as name
LIMIT 20
```

## Using the REST API

### Search Graphiti Knowledge Graph

```bash
# Natural language search
curl -X POST http://localhost:8000/api/v1/graphiti/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Blues Muse dance event",
    "match_count": 10
  }'
```

### Execute Custom Cypher Query

```bash
# Query Neo4j directly
curl -X POST http://localhost:8000/api/v1/graphiti/knowledge-graph/query \
  -H "Content-Type: application/json" \
  -d '{
    "command": "query MATCH (f:Fact) WHERE f.fact CONTAINS \"Blues Muse\" RETURN f LIMIT 10"
  }'
```

## Using MCP Tools

If you're using MCP (Model Context Protocol), you can use:

- `search_graphiti(query, match_count)` - Search the knowledge graph
- `query_knowledge_graph(command)` - Execute Cypher queries

## Chatting with Graphiti Data

### Via REST API Search

The `/api/v1/graphiti/search` endpoint allows natural language queries:

```bash
# Natural language search
curl -X POST http://localhost:8000/api/v1/graphiti/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Blues Muse?",
    "match_count": 10
  }'
```

### Via MCP Tools

If you have MCP access, you can use the `search_graphiti` tool in your conversations:

```python
# In an MCP-enabled chat interface
search_graphiti("What is Blues Muse?", match_count=10)
```

### Via Python Script

Use the provided `query_graphiti_data.py` script:

```bash
# Interactive search
python sample/capability/query_graphiti_data.py search

# Direct search
python sample/capability/query_graphiti_data.py search "Blues Muse event"
```

## Example: Querying Blues Muse Data

After crawling `https://www.bluesmuse.dance/`, you can query:

```cypher
// Find all facts about Blues Muse
MATCH (f:Fact)
WHERE f.fact CONTAINS 'Blues Muse' OR f.fact CONTAINS 'blues dancing'
RETURN f.fact as fact
LIMIT 20

// Find entities related to the event
MATCH (e:Entity)
WHERE e.name CONTAINS 'Blues' OR e.name CONTAINS 'Muse'
RETURN e.name as name, e.type as type

// Find relationships
MATCH (e1:Entity)-[r]->(e2:Entity)
WHERE e1.name CONTAINS 'Blues' OR e2.name CONTAINS 'Blues'
RETURN e1.name as from, type(r) as rel, e2.name as to
```

## Notes

- Graphiti automatically extracts entities and relationships from crawled content
- Facts are stored with temporal information (valid_from, valid_to)
- Source metadata links facts back to original documents/chunks
- Use the search endpoint for natural language queries
- Use Cypher queries for specific graph exploration
