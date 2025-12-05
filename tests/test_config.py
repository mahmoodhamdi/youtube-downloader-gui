"""Unit tests for Configuration modules."""

import pytest
import os
import json
import tempfile
from pathlib import Path

from src.config.config_manager import ConfigManager
from src.config.validators import URLValidator, PathValidator, ConfigValidator
from src.config.defaults import (
    APP_NAME, APP_VERSION, QUALITY_OPTIONS,
    MAX_CONCURRENT_DOWNLOADS, MIN_CONCURRENT_DOWNLOADS
)


class TestConfigManager:
    """Tests for ConfigManager class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({}, f)
            return f.name

    @pytest.fixture
    def config_manager(self, temp_config_file):
        """Create ConfigManager with temp file."""
        manager = ConfigManager(config_file=temp_config_file)
        manager.load()
        yield manager
        # Cleanup
        if os.path.exists(temp_config_file):
            os.unlink(temp_config_file)

    def test_get_default_value(self, config_manager):
        """Test getting a value with default."""
        value = config_manager.get("nonexistent", "default_value")
        assert value == "default_value"

    def test_set_and_get(self, config_manager):
        """Test setting and getting a value using valid AppConfig key."""
        # Use update() which bypasses single-value validation
        config_manager.update({"max_concurrent_downloads": 5})
        assert config_manager.get("max_concurrent_downloads") == 5

    def test_set_overwrites(self, config_manager):
        """Test that update overwrites existing values."""
        config_manager.update({"max_concurrent_downloads": 3})
        config_manager.update({"max_concurrent_downloads": 4})
        assert config_manager.get("max_concurrent_downloads") == 4

    def test_persistence(self, temp_config_file):
        """Test that config persists to file."""
        # Create and save
        manager1 = ConfigManager(config_file=temp_config_file)
        manager1.load()
        manager1.update({"max_concurrent_downloads": 6})
        manager1.save()

        # Create new manager with same file
        manager2 = ConfigManager(config_file=temp_config_file)
        manager2.load()
        assert manager2.get("max_concurrent_downloads") == 6

    def test_get_all(self, config_manager):
        """Test getting all config values."""
        config_manager.update({
            "max_concurrent_downloads": 4,
            "include_subtitles": True
        })

        all_config = config_manager.get_all()
        assert "quality" in all_config
        assert "max_concurrent_downloads" in all_config
        assert all_config["max_concurrent_downloads"] == 4
        assert all_config["include_subtitles"] is True

    def test_reset_to_defaults(self, config_manager):
        """Test resetting to default values."""
        # Change a value from default
        config_manager.update({"max_concurrent_downloads": 8})
        assert config_manager.get("max_concurrent_downloads") == 8

        # Reset using reset() method
        config_manager.reset()

        # Default value should be restored
        assert config_manager.get("max_concurrent_downloads") == 2  # Default is 2


class TestURLValidator:
    """Tests for URL validation."""

    def test_valid_youtube_url(self):
        """Test valid YouTube URLs."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
            "https://youtube.com/shorts/dQw4w9WgXcQ",  # Must be 11 chars
            "https://www.youtube.com/@username",
            "https://www.youtube.com/channel/UCdQw4w9WgXcQ",  # 13 chars channel ID
        ]

        for url in valid_urls:
            result = URLValidator.validate(url)
            assert result.is_valid, f"URL should be valid: {url}"

    def test_invalid_youtube_url(self):
        """Test invalid URLs."""
        invalid_urls = [
            "",
            "not a url",
            "https://vimeo.com/123456",
            "https://example.com",
            "ftp://youtube.com/watch?v=test",
        ]

        for url in invalid_urls:
            result = URLValidator.validate(url)
            assert not result.is_valid, f"URL should be invalid: {url}"

    def test_extract_video_id(self):
        """Test video ID extraction."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]

        for url, expected_id in test_cases:
            video_id = URLValidator.extract_video_id(url)
            assert video_id == expected_id, f"Expected {expected_id} for {url}"

    def test_is_playlist(self):
        """Test playlist detection."""
        playlist_urls = [
            "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
        ]

        non_playlist_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
        ]

        for url in playlist_urls:
            assert URLValidator.is_playlist(url), f"Should be playlist: {url}"

        for url in non_playlist_urls:
            assert not URLValidator.is_playlist(url), f"Should not be playlist: {url}"

    def test_extract_playlist_id(self):
        """Test playlist ID extraction from various URL types."""
        # Pure playlist URL
        url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        playlist_id = URLValidator.extract_playlist_id(url)
        assert playlist_id == "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

        # Video URL with list parameter
        url2 = "https://youtube.com/watch?v=dQw4w9WgXcQ&list=PLxyz123abc"
        playlist_id2 = URLValidator.extract_playlist_id(url2)
        assert playlist_id2 == "PLxyz123abc"


class TestPathValidator:
    """Tests for path validation."""

    def test_valid_path(self):
        """Test valid paths."""
        # Use temp directory which exists
        temp_dir = tempfile.gettempdir()
        result = PathValidator.validate_directory(temp_dir)
        assert result.is_valid

    def test_invalid_path(self):
        """Test invalid paths."""
        result = PathValidator.validate_directory("/nonexistent/path/that/doesnt/exist")
        assert not result.is_valid

    def test_empty_path(self):
        """Test empty path."""
        result = PathValidator.validate_directory("")
        assert not result.is_valid

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            ("normal_file.mp4", "normal_file.mp4"),
            ("file/with/slashes.mp4", "file_with_slashes.mp4"),
            ("file:with:colons.mp4", "file_with_colons.mp4"),
            ("file<with>special.mp4", "file_with_special.mp4"),
            ('file"with"quotes.mp4', "file_with_quotes.mp4"),
        ]

        for input_name, expected in test_cases:
            result = PathValidator.sanitize_filename(input_name)
            # Result should not contain invalid characters
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                assert char not in result


class TestDefaults:
    """Tests for default configuration values."""

    def test_app_metadata(self):
        """Test app metadata constants."""
        assert APP_NAME == "YouTube Downloader Pro"
        assert APP_VERSION is not None
        assert len(APP_VERSION) > 0

    def test_quality_options(self):
        """Test quality options are defined."""
        assert len(QUALITY_OPTIONS) > 0
        # Should have best quality option
        qualities = [q[1] for q in QUALITY_OPTIONS]
        assert "best" in qualities

    def test_concurrent_limits(self):
        """Test concurrent download limits."""
        assert MIN_CONCURRENT_DOWNLOADS >= 1
        assert MAX_CONCURRENT_DOWNLOADS >= MIN_CONCURRENT_DOWNLOADS
        assert MAX_CONCURRENT_DOWNLOADS <= 10  # Reasonable limit
