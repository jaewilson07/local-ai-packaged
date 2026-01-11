"""Tests for Graphiti RAG repository parsing."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from tests.conftest import MockRunContext

from server.projects.graphiti_rag.tools import parse_github_repository
from server.projects.graphiti_rag.dependencies import GraphitiRAGDeps
from server.projects.graphiti_rag.config import config as graphiti_config


@pytest.mark.asyncio
async def test_parse_github_repository(mock_graphiti_rag_deps):
    """Test parsing GitHub repository."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    repo_url = "https://github.com/user/repo.git"
    
    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, 'use_knowledge_graph', True):
        # Mock repository parser
        with patch("server.projects.graphiti_rag.tools.DirectNeo4jExtractor") as mock_extractor_class:
            mock_extractor = AsyncMock()
            mock_extractor.initialize = AsyncMock()
            mock_extractor.analyze_repository = AsyncMock()
            mock_extractor.close = AsyncMock()
            mock_extractor_class.return_value = mock_extractor
            
            # Execute
            result = await parse_github_repository(ctx, repo_url)
            
            # Assert
            assert result["success"] is True
            assert "message" in result
            assert result["repo_url"] == repo_url
            mock_extractor.analyze_repository.assert_called_once_with(repo_url)


@pytest.mark.asyncio
async def test_parse_invalid_repo(mock_graphiti_rag_deps):
    """Test parsing invalid repository URL."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    repo_url = "https://github.com/user/repo"  # Missing .git
    
    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, 'use_knowledge_graph', True):
        # Execute and expect error
        with pytest.raises(ValueError, match="must end with .git"):
            await parse_github_repository(ctx, repo_url)


@pytest.mark.asyncio
async def test_parse_feature_flag(mock_graphiti_rag_deps):
    """Test parsing checks USE_KNOWLEDGE_GRAPH flag."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    repo_url = "https://github.com/user/repo.git"
    
    # Mock feature flag disabled
    with patch.object(graphiti_config, 'use_knowledge_graph', False):
        # Execute and expect error
        with pytest.raises(ValueError, match="Knowledge graph is not enabled"):
            await parse_github_repository(ctx, repo_url)


@pytest.mark.asyncio
async def test_extract_code_structure(mock_graphiti_rag_deps):
    """Test code structure extraction."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    repo_url = "https://github.com/user/repo.git"
    
    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, 'use_knowledge_graph', True):
        # Mock extractor with detailed structure
        with patch("server.projects.graphiti_rag.tools.DirectNeo4jExtractor") as mock_extractor_class:
            mock_extractor = AsyncMock()
            mock_extractor.initialize = AsyncMock()
            mock_extractor.analyze_repository = AsyncMock()
            mock_extractor.close = AsyncMock()
            mock_extractor_class.return_value = mock_extractor
            
            # Execute
            result = await parse_github_repository(ctx, repo_url)
            
            # Assert
            assert result["success"] is True
            # Verify structure extraction was called
            mock_extractor.analyze_repository.assert_called_once_with(repo_url)


@pytest.mark.asyncio
async def test_parse_repository_error_handling(mock_graphiti_rag_deps):
    """Test error handling during repository parsing."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    repo_url = "https://github.com/user/repo.git"
    
    # Mock config to enable knowledge graph
    with patch.object(graphiti_config, 'use_knowledge_graph', True):
        # Mock extractor error
        with patch("server.projects.graphiti_rag.tools.DirectNeo4jExtractor") as mock_extractor_class:
            mock_extractor = AsyncMock()
            mock_extractor.initialize = AsyncMock()
            mock_extractor.analyze_repository = AsyncMock(side_effect=Exception("Extraction error"))
            mock_extractor.close = AsyncMock()
            mock_extractor_class.return_value = mock_extractor
            
            # Execute
            result = await parse_github_repository(ctx, repo_url)
            
            # Assert - should return error in result
            assert result["success"] is False
            assert "error" in result
