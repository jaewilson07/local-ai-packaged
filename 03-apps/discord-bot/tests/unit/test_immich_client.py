"""Tests for Immich API client."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientResponseError
from bot.immich_client import ImmichClient


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_asset_success(mock_immich_response):
    """Test successful asset upload."""
    mock_immich_response.json = AsyncMock(return_value={"id": "asset123", "type": "IMAGE"})

    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.post = AsyncMock(return_value=mock_immich_response)
        mock_session.return_value = mock_context

        result = await client.upload_asset(
            file_data=b"test_image_data", filename="test.jpg", description="Test upload"
        )

        assert result["id"] == "asset123"
        mock_context.post.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_asset_without_description(mock_immich_response):
    """Test asset upload without description."""
    mock_immich_response.json = AsyncMock(return_value={"id": "asset456"})

    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.post = AsyncMock(return_value=mock_immich_response)
        mock_session.return_value = mock_context

        result = await client.upload_asset(file_data=b"test_data", filename="test.png")

        assert result["id"] == "asset456"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_asset_error(mock_immich_response):
    """Test asset upload with API error."""
    mock_immich_response.raise_for_status = AsyncMock(
        side_effect=ClientResponseError(
            request_info=None, history=None, status=500, message="Internal Server Error"
        )
    )

    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.post = AsyncMock(return_value=mock_immich_response)
        mock_session.return_value = mock_context

        with pytest.raises(ClientResponseError):
            await client.upload_asset(file_data=b"test_data", filename="test.jpg")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_people_success(mock_immich_response, sample_immich_people):
    """Test successful people search."""
    mock_immich_response.json = AsyncMock(return_value=sample_immich_people)

    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_immich_response)
        mock_session.return_value = mock_context

        results = await client.search_people("John")

        assert len(results) == 2  # John Doe and John Smith
        assert all("John" in person["name"] for person in results)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_people_no_results(mock_immich_response):
    """Test people search with no results."""
    mock_immich_response.json = AsyncMock(return_value=[])

    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_immich_response)
        mock_session.return_value = mock_context

        results = await client.search_people("NonExistent")

        assert len(results) == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_people_case_insensitive(mock_immich_response, sample_immich_people):
    """Test people search is case-insensitive."""
    mock_immich_response.json = AsyncMock(return_value=sample_immich_people)

    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_immich_response)
        mock_session.return_value = mock_context

        results_lower = await client.search_people("john")
        results_upper = await client.search_people("JOHN")

        assert len(results_lower) == len(results_upper) == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_person_thumbnail(mock_immich_response):
    """Test getting person thumbnail URL."""
    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    thumbnail_url = await client.get_person_thumbnail("person1")

    assert "person1" in thumbnail_url
    assert "thumbnail" in thumbnail_url
    assert "test-key" in thumbnail_url


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_asset_faces_success(mock_immich_response, sample_immich_faces):
    """Test getting asset faces."""
    mock_immich_response.json = AsyncMock(return_value=sample_immich_faces)

    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_immich_response)
        mock_session.return_value = mock_context

        faces = await client.get_asset_faces("asset123")

        assert len(faces) == 2
        assert all("personId" in face for face in faces)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_asset_faces_not_found(mock_immich_response):
    """Test getting asset faces when no faces detected (404)."""
    mock_immich_response.status = 404

    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_immich_response)
        mock_session.return_value = mock_context

        faces = await client.get_asset_faces("asset123")

        assert faces == []  # Should return empty list for 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_new_assets(mock_immich_response, sample_immich_asset):
    """Test listing new assets."""
    mock_immich_response.json = AsyncMock(return_value={"items": [sample_immich_asset], "total": 1})

    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_immich_response)
        mock_session.return_value = mock_context

        since = datetime.utcnow() - timedelta(hours=1)
        assets = await client.list_new_assets(since)

        assert len(assets) == 1
        assert assets[0]["id"] == "asset123"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_asset_thumbnail(mock_immich_response):
    """Test getting asset thumbnail URL."""
    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    thumbnail_url = await client.get_asset_thumbnail("asset123")

    assert "asset123" in thumbnail_url
    assert "thumbnail" in thumbnail_url
    assert "test-key" in thumbnail_url


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_asset_info(mock_immich_response, sample_immich_asset):
    """Test getting asset information."""
    mock_immich_response.json = AsyncMock(return_value=sample_immich_asset)

    client = ImmichClient(base_url="http://test:2283", api_key="test-key")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_context)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_context.get = AsyncMock(return_value=mock_immich_response)
        mock_session.return_value = mock_context

        asset_info = await client.get_asset_info("asset123")

        assert asset_info["id"] == "asset123"
        assert asset_info["type"] == "IMAGE"
