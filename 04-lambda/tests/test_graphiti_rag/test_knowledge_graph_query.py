"""Tests for Graphiti RAG knowledge graph querying."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from server.projects.graphiti_rag.config import config as graphiti_config
from server.projects.graphiti_rag.tools import query_knowledge_graph

from tests.conftest import MockRunContext


@pytest.mark.asyncio
async def test_query_repos(mock_graphiti_rag_deps):
    """Test querying repository list."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    command = "repos"

    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, "use_knowledge_graph", True):
        # Mock DirectNeo4jExtractor
        with patch(
            "server.projects.graphiti_rag.tools.DirectNeo4jExtractor"
        ) as mock_extractor_class:
            mock_extractor = AsyncMock()
            mock_extractor.initialize = AsyncMock()
            mock_extractor.close = AsyncMock()

            # Mock session and query result
            from tests.conftest import async_iter

            mock_record = {"name": "repo1"}
            mock_result = AsyncMock()

            async def mock_aiter():
                async for item in async_iter([mock_record]):
                    yield item

            mock_result.__aiter__ = lambda self: mock_aiter()
            mock_result.single = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.run = AsyncMock(return_value=mock_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_driver = Mock()
            mock_driver.session = Mock(return_value=mock_session)
            mock_extractor.driver = mock_driver

            mock_extractor_class.return_value = mock_extractor

            # Execute
            result = await query_knowledge_graph(ctx, command)

            # Assert
            assert result["success"] is True
            assert "data" in result
            assert "repositories" in result["data"]


@pytest.mark.asyncio
async def test_query_explore(mock_graphiti_rag_deps):
    """Test exploring a repository."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    command = "explore repo1"

    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, "use_knowledge_graph", True):
        # Mock DirectNeo4jExtractor
        with patch(
            "server.projects.graphiti_rag.tools.DirectNeo4jExtractor"
        ) as mock_extractor_class:
            mock_extractor = AsyncMock()
            mock_extractor.initialize = AsyncMock()
            mock_extractor.close = AsyncMock()

            # Mock session and query result
            mock_record = {"files": 5, "classes": 10, "methods": 50, "functions": 20}
            mock_result = AsyncMock()

            async def mock_result_iter():
                yield mock_record

            mock_result.__aiter__ = mock_result_iter
            mock_result.single = AsyncMock(return_value=mock_record)

            mock_session = AsyncMock()
            mock_session.run = AsyncMock(return_value=mock_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_driver = Mock()
            mock_driver.session = Mock(return_value=mock_session)
            mock_extractor.driver = mock_driver

            mock_extractor_class.return_value = mock_extractor

            # Execute
            result = await query_knowledge_graph(ctx, command)

            # Assert
            assert result["success"] is True
            assert "data" in result
            assert "repository" in result["data"]


@pytest.mark.asyncio
async def test_query_cypher(mock_graphiti_rag_deps):
    """Test executing Cypher query."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    command = "query MATCH (c:Class) RETURN c.name LIMIT 5"

    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, "use_knowledge_graph", True):
        # Mock DirectNeo4jExtractor
        with patch(
            "server.projects.graphiti_rag.tools.DirectNeo4jExtractor"
        ) as mock_extractor_class:
            mock_extractor = AsyncMock()
            mock_extractor.initialize = AsyncMock()
            mock_extractor.close = AsyncMock()

            # Mock session and query result
            from tests.conftest import async_iter

            mock_records = [{"c.name": "User"}, {"c.name": "Auth"}]
            mock_result = AsyncMock()

            async def mock_aiter():
                async for item in async_iter(mock_records):
                    yield item

            mock_result.__aiter__ = lambda self: mock_aiter()
            mock_result.single = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.run = AsyncMock(return_value=mock_result)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_driver = Mock()
            mock_driver.session = Mock(return_value=mock_session)
            mock_extractor.driver = mock_driver

            mock_extractor_class.return_value = mock_extractor

            # Execute
            result = await query_knowledge_graph(ctx, command)

            # Assert
            assert result["success"] is True
            assert "data" in result
            assert "results" in result["data"]
            # Verify Cypher query was executed
            call_args = mock_session.run.call_args
            assert "MATCH" in call_args[0][0]


@pytest.mark.asyncio
async def test_query_invalid_command(mock_graphiti_rag_deps):
    """Test error handling for invalid command."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    command = "invalid_command"

    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, "use_knowledge_graph", True):
        # Mock DirectNeo4jExtractor
        with patch(
            "server.projects.graphiti_rag.tools.DirectNeo4jExtractor"
        ) as mock_extractor_class:
            mock_extractor = AsyncMock()
            mock_extractor.initialize = AsyncMock()
            mock_extractor.close = AsyncMock()

            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_driver = Mock()
            mock_driver.session = Mock(return_value=mock_session)
            mock_extractor.driver = mock_driver

            mock_extractor_class.return_value = mock_extractor

            # Execute
            result = await query_knowledge_graph(ctx, command)

            # Assert - should handle gracefully
            assert result["success"] is False
            assert "error" in result


@pytest.mark.asyncio
async def test_query_feature_flag(mock_graphiti_rag_deps):
    """Test query checks USE_KNOWLEDGE_GRAPH flag."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    command = "repos"

    # Mock feature flag disabled
    with patch.object(graphiti_config, "use_knowledge_graph", False):
        # Execute and expect error
        with pytest.raises(ValueError, match="Knowledge graph is not enabled"):
            await query_knowledge_graph(ctx, command)


@pytest.mark.asyncio
async def test_query_error_handling(mock_graphiti_rag_deps):
    """Test error handling during query execution."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    command = "repos"

    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, "use_knowledge_graph", True):
        # Mock DirectNeo4jExtractor with error
        with patch(
            "server.projects.graphiti_rag.tools.DirectNeo4jExtractor"
        ) as mock_extractor_class:
            mock_extractor = AsyncMock()
            mock_extractor.initialize = AsyncMock(side_effect=Exception("Neo4j connection error"))
            mock_extractor.close = AsyncMock()

            mock_extractor_class.return_value = mock_extractor

            # Execute
            result = await query_knowledge_graph(ctx, command)

            # Assert - should return error in result
            assert result["success"] is False
            assert "error" in result
