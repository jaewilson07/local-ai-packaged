"""Tests for JWT validation service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidSignatureError,
)

from server.projects.auth.config import AuthConfig
from server.projects.auth.services.jwt_service import JWTService


@pytest.fixture
def auth_config():
    """Create AuthConfig for testing."""
    config = AuthConfig()
    config.cloudflare_auth_domain = "https://test.cloudflareaccess.com"
    config.cloudflare_aud_tag = "test-aud-tag"
    return config


@pytest.fixture
def jwt_service(auth_config):
    """Create JWTService instance for testing."""
    return JWTService(auth_config)


@pytest.fixture
def mock_public_keys_response():
    """Mock Cloudflare public keys response."""
    return {
        "keys": [
            {"kid": "test-key-1", "kty": "RSA", "use": "sig", "n": "test-n-value", "e": "AQAB"}
        ]
    }


@pytest.mark.asyncio
async def test_fetch_public_keys_success(jwt_service, mock_public_keys_response):
    """Test successful public key fetching."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = Mock()
        mock_response.json = Mock(return_value=mock_public_keys_response)
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch("jwt.algorithms.RSAAlgorithm.from_jwk") as mock_from_jwk:
            mock_key = Mock()
            mock_from_jwk.return_value = mock_key

            keys = await jwt_service._get_public_keys()

            assert len(keys) == 1
            assert keys[0] == mock_key
            mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_public_keys_caching(jwt_service, mock_public_keys_response):
    """Test public key caching (1-hour TTL)."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_response = Mock()
        mock_response.json = Mock(return_value=mock_public_keys_response)
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch("jwt.algorithms.RSAAlgorithm.from_jwk") as mock_from_jwk:
            mock_key = Mock()
            mock_from_jwk.return_value = mock_key

            # First call - should fetch
            keys1 = await jwt_service._get_public_keys()
            assert mock_client.get.call_count == 1

            # Second call within TTL - should use cache
            keys2 = await jwt_service._get_public_keys()
            assert mock_client.get.call_count == 1  # Still 1, not 2
            assert keys1 == keys2


@pytest.mark.asyncio
async def test_fetch_public_keys_failure(jwt_service):
    """Test network failure handling."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        mock_client_class.return_value = mock_client

        # No cached keys - should raise
        with pytest.raises(Exception):
            await jwt_service._get_public_keys()


@pytest.mark.asyncio
async def test_validate_jwt_success(jwt_service):
    """Test valid JWT with correct audience."""
    # Create a mock token (we'll mock jwt.decode to avoid needing real keys)
    mock_token = "valid.jwt.token"
    mock_email = "test@example.com"

    with patch.object(jwt_service, "_get_public_keys") as mock_get_keys:
        mock_key = Mock()
        mock_get_keys.return_value = [mock_key]

        with patch("jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "email": mock_email,
                "aud": "test-aud-tag",
                "iss": "https://test.cloudflareaccess.com",
                "exp": 9999999999,
            }

            email = await jwt_service.validate_and_extract_email(mock_token)

            assert email == mock_email
            mock_decode.assert_called_once()
            # Verify audience and issuer are checked
            call_kwargs = mock_decode.call_args[1]
            assert call_kwargs["audience"] == "test-aud-tag"
            assert call_kwargs["issuer"] == "https://test.cloudflareaccess.com"


@pytest.mark.asyncio
async def test_validate_jwt_invalid_signature(jwt_service):
    """Test JWT with invalid signature."""
    mock_token = "invalid.jwt.token"

    with patch.object(jwt_service, "_get_public_keys") as mock_get_keys:
        mock_key = Mock()
        mock_get_keys.return_value = [mock_key]

        with patch("jwt.decode") as mock_decode:
            mock_decode.side_effect = InvalidSignatureError("Invalid signature")

            with pytest.raises(ValueError, match="Token validation failed"):
                await jwt_service.validate_and_extract_email(mock_token)


@pytest.mark.asyncio
async def test_validate_jwt_wrong_audience(jwt_service):
    """Test JWT with wrong audience tag."""
    mock_token = "wrong.audience.token"

    with patch.object(jwt_service, "_get_public_keys") as mock_get_keys:
        mock_key = Mock()
        mock_get_keys.return_value = [mock_key]

        with patch("jwt.decode") as mock_decode:
            mock_decode.side_effect = InvalidAudienceError("Wrong audience")

            with pytest.raises(ValueError, match="Token audience does not match"):
                await jwt_service.validate_and_extract_email(mock_token)


@pytest.mark.asyncio
async def test_validate_jwt_expired(jwt_service):
    """Test expired JWT token."""
    mock_token = "expired.jwt.token"

    with patch.object(jwt_service, "_get_public_keys") as mock_get_keys:
        mock_key = Mock()
        mock_get_keys.return_value = [mock_key]

        with patch("jwt.decode") as mock_decode:
            mock_decode.side_effect = ExpiredSignatureError("Token expired")

            with pytest.raises(ValueError, match="Token has expired"):
                await jwt_service.validate_and_extract_email(mock_token)


@pytest.mark.asyncio
async def test_validate_jwt_missing_email(jwt_service):
    """Test JWT without email claim."""
    mock_token = "no.email.token"

    with patch.object(jwt_service, "_get_public_keys") as mock_get_keys:
        mock_key = Mock()
        mock_get_keys.return_value = [mock_key]

        with patch("jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "aud": "test-aud-tag",
                "iss": "https://test.cloudflareaccess.com",
                # Missing email
            }

            with pytest.raises(ValueError, match="missing 'email' claim"):
                await jwt_service.validate_and_extract_email(mock_token)


@pytest.mark.asyncio
async def test_audience_validation_success(jwt_service):
    """Test correct audience accepted."""
    mock_token = "valid.jwt.token"

    with patch.object(jwt_service, "_get_public_keys") as mock_get_keys:
        mock_key = Mock()
        mock_get_keys.return_value = [mock_key]

        with patch("jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "email": "test@example.com",
                "aud": "test-aud-tag",  # Matches config
                "iss": "https://test.cloudflareaccess.com",
            }

            email = await jwt_service.validate_and_extract_email(mock_token)
            assert email == "test@example.com"


@pytest.mark.asyncio
async def test_audience_validation_failure(jwt_service):
    """Test wrong audience rejected."""
    mock_token = "wrong.audience.token"

    with patch.object(jwt_service, "_get_public_keys") as mock_get_keys:
        mock_key = Mock()
        mock_get_keys.return_value = [mock_key]

        with patch("jwt.decode") as mock_decode:
            mock_decode.side_effect = InvalidAudienceError("Wrong audience")

            with pytest.raises(ValueError, match="Token audience does not match"):
                await jwt_service.validate_and_extract_email(mock_token)


@pytest.mark.asyncio
async def test_missing_audience_config(jwt_service):
    """Test error when audience not configured."""
    jwt_service.audience = ""

    with pytest.raises(ValueError, match="Missing required audience"):
        await jwt_service.validate_and_extract_email("token")


@pytest.mark.asyncio
async def test_missing_team_domain_config(jwt_service):
    """Test error when team domain not configured."""
    jwt_service.team_domain = ""

    with pytest.raises(ValueError, match="Missing required team domain"):
        await jwt_service.validate_and_extract_email("token")
