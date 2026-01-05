"""Dependencies for Graphiti RAG."""

import logging
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from graphiti_core import Graphiti
else:
    try:
        from graphiti_core import Graphiti
    except ImportError:
        Graphiti = None  # type: ignore

from server.projects.graphiti_rag.config import config

logger = logging.getLogger(__name__)


@dataclass
class GraphitiRAGDeps:
    """Dependencies for Graphiti RAG operations."""
    
    graphiti: Optional[Graphiti] = None
    _initialized: bool = False
    
    @classmethod
    def from_settings(
        cls,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        use_graphiti: Optional[bool] = None
    ) -> "GraphitiRAGDeps":
        """
        Create dependencies from application settings.
        
        Args:
            neo4j_uri: Neo4j connection URI (defaults to config)
            neo4j_user: Neo4j username (defaults to config)
            neo4j_password: Neo4j password (defaults to config)
            use_graphiti: Whether to enable Graphiti (defaults to config)
        
        Returns:
            GraphitiRAGDeps instance
        """
        return cls(
            graphiti=None,  # Will be initialized in initialize()
            _initialized=False
        )
    
    async def initialize(self) -> None:
        """Initialize Graphiti client if enabled."""
        if self._initialized:
            return
            
        if not config.use_graphiti:
            logger.info("Graphiti is disabled - skipping initialization")
            return
        
        if Graphiti is None:
            logger.warning("graphiti_core is not installed - Graphiti features will be unavailable")
            return
        
        try:
            logger.info("Initializing Graphiti client...")
            self.graphiti = Graphiti(
                config.neo4j_uri,
                config.neo4j_user,
                config.neo4j_password
            )
            
            # Build indices and constraints
            await self.graphiti.build_indices_and_constraints()
            logger.info("Graphiti client initialized successfully")
            self._initialized = True
            
        except Exception as e:
            logger.exception(f"Failed to initialize Graphiti: {e}")
            self.graphiti = None
            raise
    
    async def cleanup(self) -> None:
        """Clean up Graphiti connection."""
        if self.graphiti:
            try:
                await self.graphiti.close()
                logger.info("Graphiti connection closed")
            except Exception as e:
                logger.warning(f"Error closing Graphiti connection: {e}")
            finally:
                self.graphiti = None
                self._initialized = False

