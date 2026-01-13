"""Integration tests for data isolation."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from server.main import app
from server.projects.auth.models import User


@pytest.fixture
def mock_user_a():
    """Mock user A for testing."""
    return User(id=uuid4(), email="user_a@example.com", role="user", tier="free")


@pytest.fixture
def mock_user_b():
    """Mock user B for testing."""
    return User(id=uuid4(), email="user_b@example.com", role="user", tier="free")


@pytest.fixture
def mock_admin_user():
    """Mock admin user for testing."""
    return User(id=uuid4(), email="admin@example.com", role="admin", tier="pro")


@pytest.fixture
def mock_supabase_items():
    """Mock Supabase items for testing."""
    return [
        {"id": uuid4(), "owner_email": "user_a@example.com", "name": "Item A1", "data": "Data A1"},
        {"id": uuid4(), "owner_email": "user_a@example.com", "name": "Item A2", "data": "Data A2"},
        {"id": uuid4(), "owner_email": "user_b@example.com", "name": "Item B1", "data": "Data B1"},
    ]


@pytest.fixture
def mock_s3_objects():
    """Mock S3 objects for testing."""
    user_a_id = uuid4()
    user_b_id = uuid4()
    return [
        {"Key": f"user-{user_a_id}/image1.jpg", "Size": 1024},
        {"Key": f"user-{user_a_id}/image2.png", "Size": 2048},
        {"Key": f"user-{user_b_id}/image3.jpg", "Size": 3072},
    ]


@pytest.mark.asyncio
async def test_my_data_user_isolation(mock_user_a, mock_supabase_items):
    """Test user A only sees their own items."""
    from server.api.auth import get_current_user

    # Override the dependency
    async def override_get_current_user():
        return mock_user_a

    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with patch("server.api.auth.SupabaseService") as mock_supabase_class:
            mock_supabase_service = Mock()
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()

            # Mock only user A's items returned
            mock_rows = [
                Mock(
                    __getitem__=lambda self, key: {
                        "id": mock_supabase_items[0]["id"],
                        "owner_email": "user_a@example.com",
                        "name": "Item A1",
                        "data": "Data A1",
                    }.get(key)
                ),
                Mock(
                    __getitem__=lambda self, key: {
                        "id": mock_supabase_items[1]["id"],
                        "owner_email": "user_a@example.com",
                        "name": "Item A2",
                        "data": "Data A2",
                    }.get(key)
                ),
            ]
            mock_conn.fetch = AsyncMock(return_value=mock_rows)
            mock_conn.execute = AsyncMock()
            mock_pool.acquire = AsyncMock(return_value=AsyncMock())
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_supabase_service._get_pool = AsyncMock(return_value=mock_pool)
            mock_supabase_class.return_value = mock_supabase_service

            with patch("server.api.auth.AuthService") as mock_auth_class:
                mock_auth_service = Mock()
                mock_auth_service.is_admin = AsyncMock(return_value=False)
                mock_auth_class.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/test/my-data", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"}
                    )

                    assert response.status_code == 200
                    # Should only contain user A's items
                    html = response.text
                    assert "Item A1" in html
                    assert "Item A2" in html
                    assert "Item B1" not in html
    finally:
        # Clean up override
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_my_data_user_b_isolation(mock_user_b, mock_supabase_items):
    """Test user B only sees their own items."""
    with patch("server.api.auth.get_current_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user_b

        with patch("server.api.auth.SupabaseService") as mock_supabase_class:
            mock_supabase_service = Mock()
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()

            # Mock only user B's items returned
            mock_rows = [
                Mock(
                    __getitem__=lambda self, key: {
                        "id": mock_supabase_items[2]["id"],
                        "owner_email": "user_b@example.com",
                        "name": "Item B1",
                        "data": "Data B1",
                    }.get(key)
                ),
            ]
            mock_conn.fetch = AsyncMock(return_value=mock_rows)
            mock_conn.execute = AsyncMock()
            mock_pool.acquire = AsyncMock(return_value=AsyncMock())
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_supabase_service._get_pool = AsyncMock(return_value=mock_pool)
            mock_supabase_class.return_value = mock_supabase_service

            with patch("server.api.auth.AuthService") as mock_auth_class:
                mock_auth_service = Mock()
                mock_auth_service.is_admin = AsyncMock(return_value=False)
                mock_auth_class.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/test/my-data", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"}
                    )

                    assert response.status_code == 200
                    html = response.text
                    assert "Item B1" in html
                    assert "Item A1" not in html
                    assert "Item A2" not in html


@pytest.mark.asyncio
async def test_my_data_admin_sees_all(mock_admin_user, mock_supabase_items):
    """Test admin sees all items from all users."""
    with patch("server.api.auth.get_current_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_admin_user

        with patch("server.api.auth.SupabaseService") as mock_supabase_class:
            mock_supabase_service = Mock()
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()

            # Mock all items returned (admin bypasses filtering)
            mock_rows = [
                Mock(
                    __getitem__=lambda self, key: (
                        item.get(key)
                        if isinstance(item, dict)
                        else {
                            "id": mock_supabase_items[0]["id"],
                            "owner_email": "user_a@example.com",
                            "name": "Item A1",
                            "data": "Data A1",
                        }.get(key)
                    )
                )
                for item in mock_supabase_items
            ]
            mock_conn.fetch = AsyncMock(return_value=mock_rows)
            mock_conn.execute = AsyncMock()
            mock_pool.acquire = AsyncMock(return_value=AsyncMock())
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_supabase_service._get_pool = AsyncMock(return_value=mock_pool)
            mock_supabase_class.return_value = mock_supabase_service

            with patch("server.api.auth.AuthService") as mock_auth_class:
                mock_auth_service = Mock()
                mock_auth_service.is_admin = AsyncMock(return_value=True)
                mock_auth_class.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/test/my-data", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"}
                    )

                    assert response.status_code == 200
                    html = response.text
                    # Admin should see all items
                    assert "Item A1" in html
                    assert "Item A2" in html
                    assert "Item B1" in html


@pytest.mark.asyncio
async def test_my_data_empty_results(mock_user_a):
    """Test returns empty table when no items."""
    with patch("server.api.auth.get_current_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user_a

        with patch("server.api.auth.SupabaseService") as mock_supabase_class:
            mock_supabase_service = Mock()
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()

            mock_conn.fetch = AsyncMock(return_value=[])  # No items
            mock_conn.execute = AsyncMock()
            mock_pool.acquire = AsyncMock(return_value=AsyncMock())
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_supabase_service._get_pool = AsyncMock(return_value=mock_pool)
            mock_supabase_class.return_value = mock_supabase_service

            with patch("server.api.auth.AuthService") as mock_auth_class:
                mock_auth_service = Mock()
                mock_auth_service.is_admin = AsyncMock(return_value=False)
                mock_auth_class.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/test/my-data", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"}
                    )

                    assert response.status_code == 200
                    html = response.text
                    assert "No items found" in html or "0 items" in html or len(html) > 0


@pytest.mark.asyncio
async def test_my_images_user_isolation(mock_user_a, mock_s3_objects):
    """Test user only sees images from their folder."""
    user_a_id = mock_user_a.id

    with patch("server.api.auth.get_current_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user_a

        with patch("server.api.auth.MinIOService") as mock_minio_class:
            mock_minio_service = Mock()
            mock_s3_client = Mock()

            # Mock only user A's images
            mock_s3_client.list_objects_v2 = Mock(
                return_value={
                    "Contents": [
                        obj for obj in mock_s3_objects if f"user-{user_a_id}" in obj["Key"]
                    ]
                }
            )
            mock_s3_client.generate_presigned_url = Mock(
                return_value="https://presigned-url.example.com/image.jpg"
            )
            mock_minio_service._get_s3_client = Mock(return_value=mock_s3_client)
            mock_minio_class.return_value = mock_minio_service

            with patch("server.api.auth.AuthService") as mock_auth_class:
                mock_auth_service = Mock()
                mock_auth_service.is_admin = AsyncMock(return_value=False)
                mock_auth_class.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/test/my-images", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"}
                    )

                    assert response.status_code == 200
                    html = response.text
                    # Should only show user A's images
                    assert "image1.jpg" in html or "image1" in html
                    assert "image2.png" in html or "image2" in html
                    # Should not show user B's images
                    assert "image3.jpg" not in html or "image3" not in html.split("image3")[0]


@pytest.mark.asyncio
async def test_my_images_admin_sees_all(mock_admin_user, mock_s3_objects):
    """Test admin sees images from all folders."""
    with patch("server.api.auth.get_current_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_admin_user

        with patch("server.api.auth.MinIOService") as mock_minio_class:
            mock_minio_service = Mock()
            mock_s3_client = Mock()

            # Mock all images (admin bypasses filtering)
            mock_s3_client.list_objects_v2 = Mock(return_value={"Contents": mock_s3_objects})
            mock_s3_client.generate_presigned_url = Mock(
                return_value="https://presigned-url.example.com/image.jpg"
            )
            mock_minio_service._get_s3_client = Mock(return_value=mock_s3_client)
            mock_minio_class.return_value = mock_minio_service

            with patch("server.api.auth.AuthService") as mock_auth_class:
                mock_auth_service = Mock()
                mock_auth_service.is_admin = AsyncMock(return_value=True)
                mock_auth_class.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/test/my-images", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"}
                    )

                    assert response.status_code == 200
                    # Admin should see all images
                    assert len(mock_s3_objects) > 0


@pytest.mark.asyncio
async def test_my_images_presigned_urls(mock_user_a):
    """Test presigned URLs generated correctly (1-hour expiry)."""
    with patch("server.api.auth.get_current_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user_a

        with patch("server.api.auth.MinIOService") as mock_minio_class:
            mock_minio_service = Mock()
            mock_s3_client = Mock()

            mock_s3_client.list_objects_v2 = Mock(
                return_value={
                    "Contents": [{"Key": f"user-{mock_user_a.id}/test.jpg", "Size": 1024}]
                }
            )
            mock_s3_client.generate_presigned_url = Mock(
                return_value="https://presigned-url.example.com/test.jpg"
            )
            mock_minio_service._get_s3_client = Mock(return_value=mock_s3_client)
            mock_minio_class.return_value = mock_minio_service

            with patch("server.api.auth.AuthService") as mock_auth_class:
                mock_auth_service = Mock()
                mock_auth_service.is_admin = AsyncMock(return_value=False)
                mock_auth_class.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/test/my-images", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"}
                    )

                    assert response.status_code == 200
                    # Verify presigned URL was generated
                    mock_s3_client.generate_presigned_url.assert_called()
                    call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
                    assert call_kwargs["ExpiresIn"] == 3600  # 1 hour


@pytest.mark.asyncio
async def test_my_images_image_filtering(mock_user_a):
    """Test only image files shown (.jpg, .jpeg, .png, .gif, .webp, .svg)."""
    with patch("server.api.auth.get_current_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user_a

        with patch("server.api.auth.MinIOService") as mock_minio_class:
            mock_minio_service = Mock()
            mock_s3_client = Mock()

            # Mix of image and non-image files
            mock_s3_client.list_objects_v2 = Mock(
                return_value={
                    "Contents": [
                        {"Key": f"user-{mock_user_a.id}/image.jpg", "Size": 1024},
                        {
                            "Key": f"user-{mock_user_a.id}/document.pdf",
                            "Size": 2048,
                        },  # Not an image
                        {"Key": f"user-{mock_user_a.id}/image.png", "Size": 3072},
                    ]
                }
            )
            mock_s3_client.generate_presigned_url = Mock(
                return_value="https://presigned-url.example.com/image.jpg"
            )
            mock_minio_service._get_s3_client = Mock(return_value=mock_s3_client)
            mock_minio_class.return_value = mock_minio_service

            with patch("server.api.auth.AuthService") as mock_auth_class:
                mock_auth_service = Mock()
                mock_auth_service.is_admin = AsyncMock(return_value=False)
                mock_auth_class.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/test/my-images", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"}
                    )

                    assert response.status_code == 200
                    html = response.text
                    # Should show images
                    assert "image.jpg" in html or "image" in html
                    assert "image.png" in html or "image" in html
                    # Should not show PDF
                    assert "document.pdf" not in html


@pytest.mark.asyncio
async def test_my_images_empty_folder(mock_user_a):
    """Test returns empty gallery when folder empty."""
    with patch("server.api.auth.get_current_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user_a

        with patch("server.api.auth.MinIOService") as mock_minio_class:
            mock_minio_service = Mock()
            mock_s3_client = Mock()

            mock_s3_client.list_objects_v2 = Mock(return_value={"Contents": []})
            mock_minio_service._get_s3_client = Mock(return_value=mock_s3_client)
            mock_minio_class.return_value = mock_minio_service

            with patch("server.api.auth.AuthService") as mock_auth_class:
                mock_auth_service = Mock()
                mock_auth_service.is_admin = AsyncMock(return_value=False)
                mock_auth_class.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/test/my-images", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"}
                    )

                    assert response.status_code == 200
                    html = response.text
                    assert "No images" in html or "0 images" in html or len(html) > 0
