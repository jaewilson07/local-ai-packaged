"""Tests for utility functions."""

import pytest
from bot.utils import format_file_size, get_immich_gallery_url, is_valid_media_file


@pytest.mark.unit
def test_is_valid_media_file_valid_extensions():
    """Test valid media file extensions."""
    assert is_valid_media_file("test.jpg") is True
    assert is_valid_media_file("test.jpeg") is True
    assert is_valid_media_file("test.png") is True
    assert is_valid_media_file("test.mp4") is True
    assert is_valid_media_file("test.mov") is True


@pytest.mark.unit
def test_is_valid_media_file_invalid_extensions():
    """Test invalid media file extensions."""
    assert is_valid_media_file("test.pdf") is False
    assert is_valid_media_file("test.txt") is False
    assert is_valid_media_file("test.doc") is False
    assert is_valid_media_file("test.exe") is False


@pytest.mark.unit
def test_is_valid_media_file_case_insensitive():
    """Test file extension check is case-insensitive."""
    assert is_valid_media_file("test.JPG") is True
    assert is_valid_media_file("test.JPEG") is True
    assert is_valid_media_file("test.PNG") is True
    assert is_valid_media_file("test.MP4") is True
    assert is_valid_media_file("test.MOV") is True


@pytest.mark.unit
def test_format_file_size_bytes():
    """Test file size formatting for bytes."""
    assert format_file_size(512) == "512.0 B"
    assert format_file_size(1023) == "1023.0 B"


@pytest.mark.unit
def test_format_file_size_kb():
    """Test file size formatting for kilobytes."""
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(2048) == "2.0 KB"
    assert format_file_size(1536) == "1.5 KB"


@pytest.mark.unit
def test_format_file_size_mb():
    """Test file size formatting for megabytes."""
    assert format_file_size(1024 * 1024) == "1.0 MB"
    assert format_file_size(2 * 1024 * 1024) == "2.0 MB"
    assert format_file_size(1.5 * 1024 * 1024) == "1.5 MB"


@pytest.mark.unit
def test_format_file_size_gb():
    """Test file size formatting for gigabytes."""
    assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
    assert format_file_size(2 * 1024 * 1024 * 1024) == "2.0 GB"


@pytest.mark.unit
def test_get_immich_gallery_url_http():
    """Test gallery URL generation with HTTP base URL."""
    url = get_immich_gallery_url("asset123", "http://immich-server:2283")
    assert "asset123" in url
    assert "/photos/" in url


@pytest.mark.unit
def test_get_immich_gallery_url_https():
    """Test gallery URL generation with HTTPS base URL."""
    url = get_immich_gallery_url("asset123", "https://immich.example.com")
    assert "asset123" in url
    assert "/photos/" in url


@pytest.mark.unit
def test_get_immich_gallery_url_no_protocol():
    """Test gallery URL generation without protocol."""
    url = get_immich_gallery_url("asset123", "immich-server:2283")
    assert "asset123" in url
    assert "/photos/" in url
