"""Tests for FastAPI dependencies."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException
from uuid import uuid4

from server.projects.auth.dependencies import get_current_user
from server.projects.auth.models import User
from server.projects.auth.config import config


@pytest.mark.asyncio
async def test_get_current_user_success():
    """Test get_current_user with valid JWT."""
    mock_email = "test@example.com"
    mock_user = User(
        id=uuid4(),
        email=mock_email,
        role="user",
        tier="free"
    )
    
    with patch("server.projects.auth.dependencies.JWTService") as mock_jwt_class:
        mock_jwt_service = Mock()
        mock_jwt_service.validate_and_extract_email = AsyncMock(return_value=mock_email)
        mock_jwt_class.return_value = mock_jwt_service
        
        with patch("server.projects.auth.dependencies.SupabaseService") as mock_supabase_class:
            mock_supabase_service = Mock()
            mock_supabase_service.get_user_by_email = AsyncMock(return_value=mock_user)  # Existing user
            mock_supabase_service.get_or_provision_user = AsyncMock(return_value=mock_user)
            mock_supabase_class.return_value = mock_supabase_service
            
            with patch("server.projects.auth.dependencies.Neo4jService") as mock_neo4j_class:
                mock_neo4j_service = Mock()
                mock_neo4j_service.provision_user = AsyncMock()
                mock_neo4j_class.return_value = mock_neo4j_service
                
                with patch("server.projects.auth.dependencies.MinIOService") as mock_minio_class:
                    mock_minio_service = Mock()
                    mock_minio_service.provision_user = AsyncMock()
                    mock_minio_class.return_value = mock_minio_service
                    
                    user = await get_current_user(cf_jwt="valid.jwt.token")
                    
                    assert user.email == mock_email
                    assert user.role == "user"
                    mock_supabase_service.get_or_provision_user.assert_called_once_with(mock_email)


@pytest.mark.asyncio
async def test_get_current_user_missing_header():
    """Test get_current_user raises 403 when header missing."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(cf_jwt=None)
    
    assert exc_info.value.status_code == 403
    assert "Missing" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_invalid_jwt():
    """Test get_current_user raises 401 when JWT invalid."""
    with patch("server.projects.auth.dependencies.JWTService") as mock_jwt_class:
        mock_jwt_service = Mock()
        mock_jwt_service.validate_and_extract_email = AsyncMock(
            side_effect=ValueError("Invalid token")
        )
        mock_jwt_class.return_value = mock_jwt_service
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(cf_jwt="invalid.jwt.token")
        
        assert exc_info.value.status_code == 401
        assert "Invalid" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_jit_provisioning():
    """Test get_current_user triggers JIT provisioning for new user."""
    mock_email = "new@example.com"
    mock_user = User(
        id=uuid4(),
        email=mock_email,
        role="user",
        tier="free"
    )
    
    with patch("server.projects.auth.dependencies.JWTService") as mock_jwt_class:
        mock_jwt_service = Mock()
        mock_jwt_service.validate_and_extract_email = AsyncMock(return_value=mock_email)
        mock_jwt_class.return_value = mock_jwt_service
        
        with patch("server.projects.auth.dependencies.SupabaseService") as mock_supabase_class:
            mock_supabase_service = Mock()
            mock_supabase_service.get_user_by_email = AsyncMock(return_value=None)  # New user
            mock_supabase_service.get_or_provision_user = AsyncMock(return_value=mock_user)
            mock_supabase_class.return_value = mock_supabase_service
            
            with patch("server.projects.auth.dependencies.Neo4jService") as mock_neo4j_class:
                mock_neo4j_service = Mock()
                mock_neo4j_service.provision_user = AsyncMock()
                mock_neo4j_class.return_value = mock_neo4j_service
                
                with patch("server.projects.auth.dependencies.MinIOService") as mock_minio_class:
                    mock_minio_service = Mock()
                    mock_minio_service.provision_user = AsyncMock()
                    mock_minio_class.return_value = mock_minio_service
                    
                    user = await get_current_user(cf_jwt="valid.jwt.token")
                    
                    # Should provision in all services
                    mock_supabase_service.get_or_provision_user.assert_called_once()
                    mock_neo4j_service.provision_user.assert_called_once_with(mock_email)
                    mock_minio_service.provision_user.assert_called_once_with(user.id, mock_email)