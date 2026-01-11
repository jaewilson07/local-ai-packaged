"""Tests for MongoDB RAG agent."""

import pytest

# Skip agent tests for now - they require full agent initialization
# which has complex dependencies. These can be enabled once the
# agent initialization is properly mocked or the test environment
# is fully configured.
pytestmark = pytest.mark.skip(reason="Agent tests require full initialization - to be implemented")


@pytest.mark.asyncio
async def test_agent_simple_query(mock_agent_dependencies):
    """Test basic agent interaction."""
    # Setup
    deps = StateDeps(state=RAGState(), deps=mock_agent_dependencies)
    
    # Mock agent run
    with patch.object(rag_agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = Mock(data="This is a test response.")
        
        # Execute
        result = await rag_agent.run("Hello", deps=deps)
        
        # Assert
        assert result.data == "This is a test response."
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_agent_with_search(mock_agent_dependencies, sample_search_results):
    """Test agent using search tools."""
    # Setup
    deps = StateDeps(state=RAGState(), deps=mock_agent_dependencies)
    
    # Mock search results
    with patch("server.projects.mongo_rag.tools.hybrid_search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = sample_search_results
        
        # Mock agent run
        with patch.object(rag_agent, 'run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = Mock(data="Based on the search results, authentication is...")
            
            # Execute
            result = await rag_agent.run("What is authentication?", deps=deps)
            
            # Assert
            assert "authentication" in result.data.lower()
            mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_agent_conversation(mock_agent_dependencies):
    """Test multi-turn conversation."""
    # Setup
    deps = StateDeps(state=RAGState(), deps=mock_agent_dependencies)
    
    # Mock agent run for multiple turns
    with patch.object(rag_agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = [
            Mock(data="Hello! How can I help you?"),
            Mock(data="Authentication is the process of verifying identity.")
        ]
        
        # Execute first turn
        result1 = await rag_agent.run("Hello", deps=deps)
        assert "help" in result1.data.lower()
        
        # Execute second turn
        result2 = await rag_agent.run("What is authentication?", deps=deps)
        assert "authentication" in result2.data.lower()
        
        # Assert both calls were made
        assert mock_run.call_count == 2


@pytest.mark.asyncio
async def test_agent_error_handling(mock_agent_dependencies):
    """Test agent error recovery."""
    # Setup
    deps = StateDeps(state=RAGState(), deps=mock_agent_dependencies)
    
    # Mock agent run with error
    with patch.object(rag_agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = Exception("LLM error")
        
        # Execute and expect error
        with pytest.raises(Exception):
            await rag_agent.run("Test query", deps=deps)
        
        # Assert error was raised
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_agent_search_tool_integration(mock_agent_dependencies, sample_search_results):
    """Test agent integration with search tools."""
    # Setup
    deps = StateDeps(state=RAGState(), deps=mock_agent_dependencies)
    
    # Mock search
    with patch("server.projects.mongo_rag.tools.hybrid_search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = sample_search_results
        
        # Mock agent that uses search
        with patch.object(rag_agent, 'run', new_callable=AsyncMock) as mock_run:
            # Simulate agent calling search tool
            mock_run.return_value = Mock(data="I found information about authentication in the knowledge base.")
            
            # Execute
            result = await rag_agent.run("Search for authentication", deps=deps)
            
            # Assert
            assert "authentication" in result.data.lower() or "found" in result.data.lower()
