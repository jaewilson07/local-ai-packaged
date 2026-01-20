"""Tests for MinIO user provisioning service."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError
from server.projects.auth.config import AuthConfig
from server.projects.auth.services.minio_service import MinIOService


@pytest.fixture
def auth_config():
    """Create AuthConfig for testing."""
    config = AuthConfig()
    config.minio_endpoint = "http://localhost:9000"
    config.minio_access_key = "test-access"
    config.minio_secret_key = "test-secret"
    return config


@pytest.fixture
def minio_service(auth_config):
    """Create MinIOService instance for testing."""
    return MinIOService(auth_config)


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client."""
    client = Mock()
    return client


@pytest.mark.asyncio
async def test_provision_user_new(minio_service, mock_s3_client):
    """Test creates user folder structure (user-{uuid}/)."""
    user_id = uuid4()
    email = "new@example.com"

    # Mock bucket exists
    mock_s3_client.head_bucket = Mock()
    # Mock folder doesn't exist
    mock_s3_client.head_object = Mock(
        side_effect=ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
    )
    mock_s3_client.put_object = Mock()

    with patch.object(minio_service, "_get_s3_client", return_value=mock_s3_client):
        await minio_service.provision_user(user_id, email)

        # Should create placeholder file
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Key"] == f"user-{user_id}/.keep"
        assert call_kwargs["Bucket"] == "user-data"


@pytest.mark.asyncio
async def test_provision_user_existing(minio_service, mock_s3_client):
    """Test skips creation if folder exists."""
    user_id = uuid4()
    email = "existing@example.com"

    # Mock bucket exists
    mock_s3_client.head_bucket = Mock()
    # Mock folder already exists
    mock_s3_client.head_object = Mock()  # No exception = exists
    mock_s3_client.put_object = Mock()

    with patch.object(minio_service, "_get_s3_client", return_value=mock_s3_client):
        await minio_service.provision_user(user_id, email)

        # Should not create placeholder if folder exists
        mock_s3_client.put_object.assert_not_called()


@pytest.mark.asyncio
async def test_provision_user_bucket_creation(minio_service, mock_s3_client):
    """Test creates bucket if missing."""
    user_id = uuid4()
    email = "new@example.com"

    # Mock bucket doesn't exist
    mock_s3_client.head_bucket = Mock(
        side_effect=ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket")
    )
    mock_s3_client.create_bucket = Mock()
    # Mock folder doesn't exist
    mock_s3_client.head_object = Mock(
        side_effect=ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
    )
    mock_s3_client.put_object = Mock()

    with patch.object(minio_service, "_get_s3_client", return_value=mock_s3_client):
        await minio_service.provision_user(user_id, email)

        # Should create bucket
        mock_s3_client.create_bucket.assert_called_once_with(Bucket="user-data")
        # Should create placeholder
        mock_s3_client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_user_folder_exists(minio_service, mock_s3_client):
    """Test checks folder existence correctly."""
    user_id = uuid4()

    # Mock folder exists (has contents)
    mock_s3_client.list_objects_v2 = Mock(
        return_value={"Contents": [{"Key": f"user-{user_id}/image.jpg"}]}
    )

    with patch.object(minio_service, "_get_s3_client", return_value=mock_s3_client):
        exists = minio_service.user_folder_exists(user_id)

        assert exists is True
        mock_s3_client.list_objects_v2.assert_called_once_with(
            Bucket="user-data", Prefix=f"user-{user_id}/", MaxKeys=1
        )


@pytest.mark.asyncio
async def test_user_folder_not_exists(minio_service, mock_s3_client):
    """Test returns false when folder doesn't exist."""
    user_id = uuid4()

    # Mock folder doesn't exist (no contents)
    mock_s3_client.list_objects_v2 = Mock(return_value={})

    with patch.object(minio_service, "_get_s3_client", return_value=mock_s3_client):
        exists = minio_service.user_folder_exists(user_id)

        assert exists is False


@pytest.mark.asyncio
async def test_provision_user_s3_error(minio_service, mock_s3_client):
    """Test handles S3/MinIO errors."""
    user_id = uuid4()
    email = "test@example.com"

    # Mock S3 error
    mock_s3_client.head_bucket = Mock(
        side_effect=ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "HeadBucket"
        )
    )

    with patch.object(minio_service, "_get_s3_client", return_value=mock_s3_client):
        with pytest.raises(ClientError):
            await minio_service.provision_user(user_id, email)


@pytest.mark.asyncio
async def test_get_s3_client_creates_once(minio_service):
    """Test S3 client is created once and reused."""
    with patch("boto3.client") as mock_boto3_client:
        mock_client = Mock()
        mock_boto3_client.return_value = mock_client

        # First call
        client1 = minio_service._get_s3_client()

        # Second call
        client2 = minio_service._get_s3_client()

        # Should be same instance
        assert client1 is client2
        # boto3.client should only be called once
        assert mock_boto3_client.call_count == 1
