"""Tests for SearXNG search functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

# Mock settings before importing to avoid validation errors
mock_settings = MagicMock()
mock_settings.searxng_url = "http://mock-searxng:8080"

# Patch settings before importing the module
with patch("server.config.settings", mock_settings):
    from server.api.searxng import (
        router,
        search,
        SearXNGSearchRequest,
        SearXNGSearchResponse,
        SearXNGSearchResult
    )


@pytest.fixture
def mock_searxng_response():
    """Mock SearXNG API response."""
    return {
        "results": [
            {
                "title": "Blues Muse - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Blues_Muse",
                "content": "Blues Muse is a blues music album...",
                "engine": "google",
                "score": 0.95
            },
            {
                "title": "Blues Muse Album Review",
                "url": "https://example.com/blues-muse-review",
                "content": "A comprehensive review of the Blues Muse album...",
                "engine": "bing",
                "score": 0.88
            },
            {
                "title": "Blues Muse - Music Streaming",
                "url": "https://music.example.com/blues-muse",
                "content": "Listen to Blues Muse on streaming platforms...",
                "engine": "duckduckgo",
                "score": 0.82
            }
        ],
        "number_of_results": 3
    }


@pytest.mark.asyncio
async def test_search_blues_muse_success(mock_searxng_response):
    """Test searching for 'blues muse' returns successful results."""
    # Setup
    request = SearXNGSearchRequest(
        query="blues muse",
        result_count=5
    )
    
    # Mock httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = mock_searxng_response
    mock_response.raise_for_status = MagicMock()
    
    with patch("server.api.searxng.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        # Execute
        result = await search(request)
        
        # Assert
        assert isinstance(result, SearXNGSearchResponse)
        assert result.query == "blues muse"
        assert result.success is True
        assert result.count == 3
        assert len(result.results) == 3
        
        # Verify first result
        first_result = result.results[0]
        assert isinstance(first_result, SearXNGSearchResult)
        assert "Blues Muse" in first_result.title
        assert first_result.url.startswith("http")
        assert len(first_result.content) > 0
        assert first_result.engine == "google"
        assert first_result.score == 0.95
        
        # Verify API was called correctly
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "search" in call_args[0][0]
        assert call_args[1]["params"]["q"] == "blues muse"
        assert call_args[1]["params"]["format"] == "json"


@pytest.mark.asyncio
async def test_search_blues_muse_with_limit(mock_searxng_response):
    """Test searching for 'blues muse' with result count limit."""
    # Setup
    request = SearXNGSearchRequest(
        query="blues muse",
        result_count=2  # Limit to 2 results
    )
    
    # Mock httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = mock_searxng_response
    mock_response.raise_for_status = MagicMock()
    
    with patch("server.api.searxng.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        # Execute
        result = await search(request)
        
        # Assert - should be limited to 2 results
        assert result.count == 2
        assert len(result.results) == 2


@pytest.mark.asyncio
async def test_search_blues_muse_with_engines(mock_searxng_response):
    """Test searching for 'blues muse' with engine filter."""
    # Setup
    request = SearXNGSearchRequest(
        query="blues muse",
        result_count=5,
        engines=["google", "bing"]
    )
    
    # Mock httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = mock_searxng_response
    mock_response.raise_for_status = MagicMock()
    
    with patch("server.api.searxng.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        # Execute
        result = await search(request)
        
        # Assert
        assert result.success is True
        
        # Verify engine filter was passed
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["engines"] == "google,bing"


@pytest.mark.asyncio
async def test_search_blues_muse_empty_query():
    """Test that empty query raises HTTPException."""
    from fastapi import HTTPException
    
    # Setup
    request = SearXNGSearchRequest(
        query="   ",  # Whitespace only
        result_count=5
    )
    
    # Execute & Assert
    with pytest.raises(HTTPException) as exc_info:
        await search(request)
    
    assert exc_info.value.status_code == 400
    assert "cannot be empty" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_search_blues_muse_timeout():
    """Test that timeout is handled gracefully."""
    from fastapi import HTTPException
    
    # Setup
    request = SearXNGSearchRequest(
        query="blues muse",
        result_count=5
    )
    
    # Mock httpx timeout
    with patch("server.api.searxng.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
        mock_client_class.return_value = mock_client
        
        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await search(request)
        
        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_search_blues_muse_connection_error():
    """Test that connection errors are handled gracefully."""
    from fastapi import HTTPException
    
    # Setup
    request = SearXNGSearchRequest(
        query="blues muse",
        result_count=5
    )
    
    # Mock httpx connection error
    with patch("server.api.searxng.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
        mock_client_class.return_value = mock_client
        
        # Execute & Assert
        with pytest.raises(HTTPException) as exc_info:
            await search(request)
        
        assert exc_info.value.status_code == 503
        assert "connect" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_search_blues_muse_empty_results():
    """Test handling of empty search results."""
    # Setup
    request = SearXNGSearchRequest(
        query="blues muse",
        result_count=5
    )
    
    # Mock empty response
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}  # No results
    mock_response.raise_for_status = MagicMock()
    
    with patch("server.api.searxng.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        # Execute
        result = await search(request)
        
        # Assert
        assert result.success is True
        assert result.count == 0
        assert len(result.results) == 0


@pytest.mark.asyncio
async def test_search_blues_muse_missing_fields(mock_searxng_response):
    """Test handling of results with missing optional fields."""
    # Setup - modify response to have missing fields
    incomplete_response = {
        "results": [
            {
                "title": "Blues Muse",
                "url": "https://example.com",
                # Missing content, engine, score
            }
        ]
    }
    
    request = SearXNGSearchRequest(
        query="blues muse",
        result_count=5
    )
    
    # Mock httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = incomplete_response
    mock_response.raise_for_status = MagicMock()
    
    with patch("server.api.searxng.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        # Execute
        result = await search(request)
        
        # Assert - should handle missing fields gracefully
        assert result.success is True
        assert len(result.results) == 1
        first_result = result.results[0]
        assert first_result.title == "Blues Muse"
        assert first_result.url == "https://example.com"
        assert first_result.content == ""  # Default empty string
        assert first_result.engine is None  # Default None
        assert first_result.score is None  # Default None
