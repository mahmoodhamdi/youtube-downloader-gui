"""Pytest configuration and shared fixtures."""

import pytest
import sys
import os
import tempfile
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_config_file(temp_dir):
    """Create a temporary config file."""
    config_path = os.path.join(temp_dir, "test_config.json")
    with open(config_path, 'w') as f:
        json.dump({
            "download_path": temp_dir,
            "quality": "best",
            "max_concurrent_downloads": 2
        }, f)
    return config_path


@pytest.fixture
def sample_youtube_url():
    """Sample YouTube video URL."""
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def sample_playlist_url():
    """Sample YouTube playlist URL."""
    return "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"


@pytest.fixture
def sample_video_info():
    """Sample video information dictionary."""
    return {
        "id": "test123",
        "title": "Test Video Title",
        "duration": 300,
        "uploader": "Test Channel",
        "view_count": 1000000,
        "like_count": 50000,
        "description": "Test description",
        "thumbnail": "https://example.com/thumb.jpg",
        "formats": [
            {
                "format_id": "22",
                "ext": "mp4",
                "height": 720,
                "width": 1280,
                "vcodec": "avc1",
                "acodec": "mp4a",
                "filesize": 100000000,
            },
            {
                "format_id": "137",
                "ext": "mp4",
                "height": 1080,
                "width": 1920,
                "vcodec": "avc1",
                "acodec": "none",
                "filesize": 200000000,
            },
            {
                "format_id": "140",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a",
                "filesize": 5000000,
            }
        ]
    }


# Skip markers for tests requiring network
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "network: marks tests as requiring network (deselect with '-m \"not network\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "gui: marks tests as requiring GUI (deselect with '-m \"not gui\"')"
    )
