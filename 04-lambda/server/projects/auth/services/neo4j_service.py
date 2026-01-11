"""Neo4j user provisioning service."""

import logging
from typing import Optional
from neo4j import AsyncGraphDatabase

from server.projects.auth.config import AuthConfig

logger = logging.getLogger(__name__)


class Neo4jService:
    """Service for Neo4j user provisioning and management."""
    
    def __init__(self, config: AuthConfig):
        """
        Initialize Neo4j service.
        
        Args:
            config: Auth configuration with Neo4j settings
        """
        self.config = config
        self.driver = None
    
    async def _get_driver(self):
        """Get or create Neo4j driver."""
        if self.driver is None:
            self.driver = AsyncGraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password)
            )
            logger.info("Created Neo4j driver connection")
        
        return self.driver
    
    async def user_exists(self, email: str) -> bool:
        """
        Check if user node exists in Neo4j.
        
        Args:
            email: User email address
            
        Returns:
            True if user exists, False otherwise
        """
        driver = await self._get_driver()
        
        async with driver.session() as session:
            result = await session.run(
                "MATCH (u:User {email: $email}) RETURN u LIMIT 1",
                email=email
            )
            record = await result.single()
            return record is not None
    
    async def provision_user(self, email: str) -> None:
        """
        Create user node in Neo4j if it doesn't exist (JIT provisioning).
        
        Uses MERGE to ensure idempotency.
        
        Args:
            email: User email address
        """
        driver = await self._get_driver()
        
        async with driver.session() as session:
            # Use MERGE to create if not exists (idempotent)
            await session.run(
                """
                MERGE (u:User {email: $email})
                ON CREATE SET u.created_at = datetime()
                RETURN u
                """,
                email=email
            )
            
            logger.info(f"Provisioned Neo4j user node for {email}")
    
    async def get_user_anchored_query(self, base_query: str, email: str, is_admin: bool = False) -> str:
        """
        Wrap a Cypher query to anchor it to a specific user.
        
        For admin users, returns the original query (no anchoring).
        For regular users, ensures query starts with user match.
        
        Args:
            base_query: Base Cypher query to anchor
            email: User email address
            is_admin: Whether user is an admin (skip anchoring if True)
            
        Returns:
            Anchored query string
        """
        if is_admin:
            return base_query
        
        # Ensure query starts with user match
        if "MATCH (u:User {email:" not in base_query.upper():
            # Prepend user match
            anchored = f"MATCH (u:User {{email: '{email}'}})\n{base_query}"
            return anchored
        
        return base_query
    
    async def close(self) -> None:
        """Close Neo4j driver."""
        if self.driver:
            await self.driver.close()
            self.driver = None
            logger.info("Closed Neo4j driver")
