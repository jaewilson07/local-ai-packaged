"""Async Neo4j client for knowledge graph operations.

Provides a minimal wrapper around the Neo4j async driver to create entities,
relationships, and perform simple traversal queries. Designed to be used by
ingestion and agent tools.
"""

from __future__ import annotations

from typing import Optional, List, Dict
from dataclasses import dataclass
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel


@dataclass
class Neo4jConfig:
    """Configuration for connecting to Neo4j."""

    uri: str
    username: str
    password: str


class GraphEntity(BaseModel):
    """Simplified entity for traversal responses."""

    id: str
    name: str
    type: str
    confidence: float | None = None
    properties: Dict[str, str] = {}


class Neo4jClient:
    """Async client encapsulating common graph operations.

    Methods are intentionally simple to keep ingestion and agent tooling
    readable while maintaining full async behavior.
    """

    def __init__(self, config: Neo4jConfig) -> None:
        self._config = config
        self._driver: Optional[AsyncGraphDatabase.driver] = None

    async def connect(self) -> None:
        """Open connection to Neo4j cluster and validate with a noop query."""
        self._driver = AsyncGraphDatabase.driver(
            self._config.uri, auth=(self._config.username, self._config.password)
        )
        async with self._driver.session() as session:
            await session.run("RETURN 1")

    async def close(self) -> None:
        """Close driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def create_entity(
        self, name: str, entity_type: str, properties: Dict[str, str] | None = None, confidence: float | None = None
    ) -> str:
        """Create or merge an entity node.

        Args:
            name: Canonical entity name
            entity_type: Node label for entity type
            properties: Optional property dict
            confidence: Optional confidence score

        Returns:
            Neo4j elementId for the created/merged node
        """
        props = properties or {}
        async with self._driver.session() as session:
            result = await session.run(
                f"""
                MERGE (e:Entity:{entity_type} {{name: $name}})
                SET e += $props
                SET e.type = $type
                SET e.confidence = coalesce($confidence, e.confidence)
                RETURN elementId(e) as id
                """,
                name=name,
                type=entity_type,
                props=props,
                confidence=confidence,
            )
            record = await result.single()
            return record["id"]

    async def create_relationship(
        self,
        source_element_id: str,
        target_element_id: str,
        rel_type: str,
        properties: Dict[str, str] | None = None,
    ) -> None:
        """Create a relationship between two existing nodes.

        Args:
            source_element_id: elementId of source node
            target_element_id: elementId of target node
            rel_type: Relationship type label
            properties: Optional property dict
        """
        props = properties or {}
        async with self._driver.session() as session:
            await session.run(
                f"""
                MATCH (a), (b)
                WHERE elementId(a) = $src AND elementId(b) = $dst
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $props
                """,
                src=source_element_id,
                dst=target_element_id,
                props=props,
            )

    async def link_entity_to_chunk(self, entity_element_id: str, chunk_id: str) -> None:
        """Link an entity to a Chunk node by ID, creating the Chunk if missing."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (c:Chunk {id: $chunk_id})
                MATCH (e) WHERE elementId(e) = $eid
                MERGE (e)-[:MENTIONED_IN]->(c)
                """,
                chunk_id=chunk_id,
                eid=entity_element_id,
            )

    async def find_related_entities(self, name: str, depth: int = 1) -> List[GraphEntity]:
        """Find entities related to the given entity name up to a certain depth.

        Args:
            name: Seed entity name
            depth: Traversal depth (1-3 recommended)

        Returns:
            List of related entities with basic properties
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {name: $name})-[:RELATED_TO*1..$depth]->(r:Entity)
                RETURN elementId(r) as id, r.name as name, r.type as type, r.confidence as confidence, r as node
                LIMIT 50
                """,
                name=name,
                depth=depth,
            )
            rows = await result.to_list()
            return [
                GraphEntity(
                    id=row["id"],
                    name=row["name"],
                    type=row["type"],
                    confidence=row.get("confidence"),
                    properties={k: v for k, v in row["node"].items() if k not in {"name", "type", "confidence"}},
                )
                for row in rows
            ]

    async def get_entity_timeline(self, name: str) -> List[Dict[str, str]]:
        """Return temporal events/relationships for the entity by name.

        Returns simplified records including relationship type and timestamps.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {name: $name})-[r]->(x)
                RETURN type(r) as rel_type, properties(r) as rel_props, properties(x) as target_props
                ORDER BY r.valid_from
                LIMIT 100
                """,
                name=name,
            )
            rows = await result.to_list()
            return [
                {
                    "relation": row["rel_type"],
                    "valid_from": str(row["rel_props"].get("valid_from", "")),
                    "valid_to": str(row["rel_props"].get("valid_to", "")),
                    "target": row["target_props"].get("name", ""),
                }
                for row in rows
            ]


__all__ = ["Neo4jClient", "Neo4jConfig", "GraphEntity"]
