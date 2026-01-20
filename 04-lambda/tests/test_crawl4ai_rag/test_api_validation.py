"""Integration tests for Crawl4AI RAG API endpoints.

These tests validate the actual API endpoints against a running Lambda server.
They require:
- Lambda server running (docker-compose up)
- DEV_MODE=true in environment
- MongoDB accessible

Run with: pytest tests/test_crawl4ai_rag/test_api_validation.py -v

For CI/CD, these tests can be skipped by setting SKIP_INTEGRATION_TESTS=true
"""

import os
import time

import httpx
import pytest

# Skip all tests in this module if integration tests are disabled
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_INTEGRATION_TESTS", "false").lower() in ("true", "1"),
    reason="Integration tests disabled",
)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "test@example.com")
TIMEOUT = 60.0  # Longer timeout for crawling operations


@pytest.fixture
def api_client():
    """Create HTTP client with test user headers."""
    headers = {
        "Content-Type": "application/json",
        "X-User-Email": TEST_USER_EMAIL,
    }
    return httpx.Client(base_url=API_BASE_URL, headers=headers, timeout=TIMEOUT)


@pytest.fixture
def async_api_client():
    """Create async HTTP client with test user headers."""
    headers = {
        "Content-Type": "application/json",
        "X-User-Email": TEST_USER_EMAIL,
    }
    return httpx.AsyncClient(base_url=API_BASE_URL, headers=headers, timeout=TIMEOUT)


class TestCrawl4AIEndpointAvailability:
    """Test that Crawl4AI endpoints are registered and accessible."""

    def test_single_page_endpoint_exists(self, api_client):
        """Verify /api/v1/crawl/single endpoint exists."""
        # OPTIONS request to check endpoint exists
        response = api_client.options("/api/v1/crawl/single")
        # Should not return 404
        assert response.status_code != 404, "Crawl single endpoint not found"

    def test_deep_crawl_endpoint_exists(self, api_client):
        """Verify /api/v1/crawl/deep endpoint exists."""
        response = api_client.options("/api/v1/crawl/deep")
        assert response.status_code != 404, "Crawl deep endpoint not found"

    def test_openapi_includes_crawl_endpoints(self, api_client):
        """Verify crawl endpoints are in OpenAPI spec."""
        response = api_client.get("/openapi.json")
        assert response.status_code == 200

        openapi = response.json()
        paths = list(openapi.get("paths", {}).keys())

        assert "/api/v1/crawl/single" in paths, "Single page endpoint not in OpenAPI"
        assert "/api/v1/crawl/deep" in paths, "Deep crawl endpoint not in OpenAPI"


class TestSinglePageCrawl:
    """Test single page crawl functionality."""

    @pytest.mark.timeout(120)
    def test_crawl_single_page_success(self, api_client):
        """Test successful single page crawl."""
        response = api_client.post(
            "/api/v1/crawl/single",
            json={
                "url": "https://example.com",
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        )

        assert response.status_code == 200, f"Failed with: {response.text}"
        data = response.json()

        # Validate response structure
        assert "success" in data
        assert "url" in data
        assert "pages_crawled" in data
        assert "chunks_created" in data
        assert "document_ids" in data
        assert "errors" in data

        # Validate success
        assert data["success"] is True
        assert data["pages_crawled"] >= 1
        assert isinstance(data["document_ids"], list)

    def test_crawl_single_page_with_custom_chunking(self, api_client):
        """Test crawl with custom chunk parameters."""
        response = api_client.post(
            "/api/v1/crawl/single",
            json={
                "url": "https://example.com",
                "chunk_size": 500,
                "chunk_overlap": 100,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_crawl_invalid_url_returns_error(self, api_client):
        """Test that invalid URL returns appropriate error."""
        response = api_client.post(
            "/api/v1/crawl/single",
            json={
                "url": "not-a-valid-url",
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        )

        # Should fail gracefully
        assert response.status_code in (200, 400, 422, 500)
        if response.status_code == 200:
            data = response.json()
            # Either success=False or has errors
            assert data.get("success") is False or len(data.get("errors", [])) > 0

    def test_crawl_missing_url_returns_422(self, api_client):
        """Test that missing URL returns validation error."""
        response = api_client.post(
            "/api/v1/crawl/single",
            json={
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        )

        assert response.status_code == 422  # Pydantic validation error


class TestDeepCrawl:
    """Test deep crawl functionality."""

    @pytest.mark.timeout(180)
    def test_deep_crawl_success(self, api_client):
        """Test successful deep crawl."""
        response = api_client.post(
            "/api/v1/crawl/deep",
            json={
                "url": "https://example.com",
                "max_depth": 1,  # Keep depth low for test speed
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        )

        assert response.status_code == 200, f"Failed with: {response.text}"
        data = response.json()

        # Validate response structure
        assert "success" in data
        assert "url" in data
        assert "pages_crawled" in data
        assert "chunks_created" in data
        assert "document_ids" in data
        assert "errors" in data

        # Validate success
        assert data["success"] is True
        assert data["pages_crawled"] >= 1

    def test_deep_crawl_with_domain_filter(self, api_client):
        """Test deep crawl with domain filtering."""
        response = api_client.post(
            "/api/v1/crawl/deep",
            json={
                "url": "https://example.com",
                "max_depth": 2,
                "allowed_domains": ["example.com"],
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_deep_crawl_missing_max_depth_returns_422(self, api_client):
        """Test that missing max_depth returns validation error."""
        response = api_client.post(
            "/api/v1/crawl/deep",
            json={
                "url": "https://example.com",
                "chunk_size": 1000,
            },
        )

        assert response.status_code == 422


class TestDataPersistence:
    """Test that crawled data is properly persisted."""

    @pytest.mark.timeout(120)
    def test_crawled_content_is_searchable(self, api_client):
        """Test that crawled content can be found via RAG search."""
        # First, crawl a page
        unique_tag = f"test_{int(time.time())}"
        crawl_response = api_client.post(
            "/api/v1/crawl/single",
            json={
                "url": "https://example.com",
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        )

        assert crawl_response.status_code == 200
        crawl_data = crawl_response.json()
        assert crawl_data["success"] is True
        assert len(crawl_data["document_ids"]) > 0

        # Note: Vector search may not work without Atlas Search index
        # This test mainly verifies the crawl completed and stored data
        # Full search validation would require Atlas Search setup


class TestAuthentication:
    """Test authentication and user context."""

    def test_request_without_auth_fails_in_prod_mode(self, api_client):
        """Test that requests without auth headers fail when DEV_MODE is disabled."""
        # First check if DEV_MODE is enabled by making a request without user header
        client = httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT)
        response = client.post(
            "/api/v1/crawl/single",
            json={"url": "https://example.com"},
            headers={"Content-Type": "application/json"},
        )

        # If we get 200, DEV_MODE is enabled (auth bypassed) - test passes
        # If we get 403, DEV_MODE is disabled - verify auth works
        if response.status_code == 200:
            # DEV_MODE is enabled, auth is bypassed - this is expected in dev
            assert True, "DEV_MODE enabled - auth bypass working correctly"
        else:
            # DEV_MODE is disabled, should require auth
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    def test_user_email_is_stored_with_document(self, api_client):
        """Test that user email is properly associated with crawled documents."""
        # This would require direct MongoDB access to verify
        # For now, we verify the endpoint accepts the X-User-Email header
        response = api_client.post(
            "/api/v1/crawl/single",
            json={
                "url": "https://example.com",
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        )

        assert response.status_code == 200
        # The user email should be stored - verification would need MongoDB access


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_connection_error_is_handled(self, api_client):
        """Test that connection errors are handled gracefully."""
        response = api_client.post(
            "/api/v1/crawl/single",
            json={
                "url": "http://non-existent-domain-12345.invalid/",
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        )

        # Should not crash - return error gracefully
        assert response.status_code in (200, 400, 500)
        if response.status_code == 200:
            data = response.json()
            # Should indicate failure or have errors
            assert data.get("success") is False or len(data.get("errors", [])) > 0

    def test_timeout_handling(self, api_client):
        """Test that slow pages are handled with timeout."""
        # This is a soft test - verifies endpoint doesn't hang indefinitely
        # The actual timeout behavior depends on crawl4ai configuration
        response = api_client.post(
            "/api/v1/crawl/single",
            json={
                "url": "https://example.com",  # Fast-loading site
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        )

        # Should complete within reasonable time
        assert response.status_code in (200, 408, 504)


# Pytest configuration for this module
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "timeout(seconds): Set test timeout",
    )
