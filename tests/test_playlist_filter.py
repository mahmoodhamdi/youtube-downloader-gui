"""Unit tests for PlaylistFilter."""

import pytest
from src.core.playlist_filter import (
    PlaylistFilter, PlaylistInfo, PlaylistVideoInfo
)


class TestPlaylistVideoInfo:
    """Tests for PlaylistVideoInfo dataclass."""

    def test_video_info_creation(self):
        """Test creating PlaylistVideoInfo."""
        info = PlaylistVideoInfo(
            index=1,
            video_id="abc123",
            url="https://youtube.com/watch?v=abc123",
            title="Test Video",
            duration=300
        )
        assert info.index == 1
        assert info.video_id == "abc123"
        assert info.duration == 300

    def test_duration_str_auto_format(self):
        """Test automatic duration string formatting."""
        info = PlaylistVideoInfo(
            index=1, video_id="id", url="url", title="Test",
            duration=3661  # 1 hour, 1 minute, 1 second
        )
        assert "1:01:01" in info.duration_str

    def test_duration_str_minutes(self):
        """Test duration string for minutes only."""
        info = PlaylistVideoInfo(
            index=1, video_id="id", url="url", title="Test",
            duration=125  # 2 minutes, 5 seconds
        )
        assert "2:05" in info.duration_str

    def test_formatted_date(self):
        """Test formatted date."""
        info = PlaylistVideoInfo(
            index=1, video_id="id", url="url", title="Test",
            upload_date="20240115"
        )
        assert info.formatted_date == "2024-01-15"

    def test_formatted_date_invalid(self):
        """Test formatted date with invalid input."""
        info = PlaylistVideoInfo(
            index=1, video_id="id", url="url", title="Test",
            upload_date="invalid"
        )
        assert info.formatted_date == "invalid"

    def test_formatted_views_millions(self):
        """Test formatted views in millions."""
        info = PlaylistVideoInfo(
            index=1, video_id="id", url="url", title="Test",
            view_count=5500000
        )
        assert "M" in info.formatted_views

    def test_formatted_views_thousands(self):
        """Test formatted views in thousands."""
        info = PlaylistVideoInfo(
            index=1, video_id="id", url="url", title="Test",
            view_count=75000
        )
        assert "K" in info.formatted_views

    def test_is_available_default(self):
        """Test default availability."""
        info = PlaylistVideoInfo(
            index=1, video_id="id", url="url", title="Test"
        )
        assert info.is_available is True


class TestPlaylistInfo:
    """Tests for PlaylistInfo dataclass."""

    def test_playlist_info_creation(self):
        """Test creating PlaylistInfo."""
        info = PlaylistInfo(
            playlist_id="PLxyz",
            title="Test Playlist",
            uploader="Test Channel",
            video_count=10
        )
        assert info.playlist_id == "PLxyz"
        assert info.title == "Test Playlist"
        assert info.video_count == 10

    def test_total_duration(self):
        """Test total duration calculation."""
        videos = [
            PlaylistVideoInfo(1, "v1", "url1", "Video 1", duration=300),
            PlaylistVideoInfo(2, "v2", "url2", "Video 2", duration=600),
            PlaylistVideoInfo(3, "v3", "url3", "Video 3", duration=150),
        ]
        info = PlaylistInfo("pl", videos=videos)
        assert info.total_duration == 1050  # 300 + 600 + 150

    def test_total_duration_str(self):
        """Test total duration string."""
        videos = [
            PlaylistVideoInfo(1, "v1", "url1", "Video 1", duration=3600),  # 1 hour
            PlaylistVideoInfo(2, "v2", "url2", "Video 2", duration=1800),  # 30 min
        ]
        info = PlaylistInfo("pl", videos=videos)
        assert "1h" in info.total_duration_str

    def test_empty_playlist(self):
        """Test empty playlist."""
        info = PlaylistInfo("pl")
        assert info.total_duration == 0
        assert len(info.videos) == 0


class TestPlaylistFilter:
    """Tests for PlaylistFilter class."""

    @pytest.fixture
    def filter(self):
        """Create PlaylistFilter instance."""
        return PlaylistFilter()

    @pytest.fixture
    def sample_videos(self):
        """Create sample videos for testing."""
        return [
            PlaylistVideoInfo(1, "v1", "url1", "Python Tutorial", duration=300, upload_date="20240101"),
            PlaylistVideoInfo(2, "v2", "url2", "JavaScript Basics", duration=600, upload_date="20240115"),
            PlaylistVideoInfo(3, "v3", "url3", "Advanced Python", duration=1200, upload_date="20240201"),
            PlaylistVideoInfo(4, "v4", "url4", "Web Development", duration=900, upload_date="20240210"),
            PlaylistVideoInfo(5, "v5", "url5", "Python Tips", duration=180, upload_date="20240220", is_available=False),
        ]

    def test_is_playlist_url_with_list(self, filter):
        """Test playlist URL detection with list parameter."""
        url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        assert PlaylistFilter.is_playlist_url(url) is True

    def test_is_playlist_url_video_with_list(self, filter):
        """Test playlist URL detection for video in playlist."""
        url = "https://www.youtube.com/watch?v=abc123&list=PLxyz"
        assert PlaylistFilter.is_playlist_url(url) is True

    def test_is_playlist_url_single_video(self, filter):
        """Test that single video is not detected as playlist."""
        url = "https://www.youtube.com/watch?v=abc123"
        assert PlaylistFilter.is_playlist_url(url) is False

    def test_extract_playlist_id(self, filter):
        """Test playlist ID extraction."""
        url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        playlist_id = PlaylistFilter.extract_playlist_id(url)
        assert playlist_id == "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

    def test_filter_by_duration_max(self, filter, sample_videos):
        """Test filtering by maximum duration."""
        filtered = filter.filter_by_duration(sample_videos, max_seconds=600)
        assert len(filtered) == 2  # 300 and 600 seconds (excluding unavailable)
        assert all(v.duration <= 600 for v in filtered)

    def test_filter_by_duration_min(self, filter, sample_videos):
        """Test filtering by minimum duration."""
        filtered = filter.filter_by_duration(sample_videos, min_seconds=600)
        assert len(filtered) == 3  # 600, 1200, and 900 seconds
        assert all(v.duration >= 600 for v in filtered)

    def test_filter_by_duration_range(self, filter, sample_videos):
        """Test filtering by duration range."""
        filtered = filter.filter_by_duration(sample_videos, min_seconds=300, max_seconds=900)
        assert len(filtered) == 3  # 300, 600, and 900 seconds

    def test_filter_by_date_after(self, filter, sample_videos):
        """Test filtering by date (after)."""
        filtered = filter.filter_by_date(sample_videos, after="20240115")
        assert len(filtered) >= 3

    def test_filter_by_date_before(self, filter, sample_videos):
        """Test filtering by date (before)."""
        filtered = filter.filter_by_date(sample_videos, before="20240201")
        assert len(filtered) >= 2

    def test_filter_by_index(self, filter, sample_videos):
        """Test filtering by index range."""
        filtered = filter.filter_by_index(sample_videos, start=2, end=4)
        assert len(filtered) == 3
        assert all(2 <= v.index <= 4 for v in filtered)

    def test_filter_by_index_start_only(self, filter, sample_videos):
        """Test filtering by start index only."""
        filtered = filter.filter_by_index(sample_videos, start=3)
        assert len(filtered) == 3
        assert all(v.index >= 3 for v in filtered)

    def test_search_by_title(self, filter, sample_videos):
        """Test searching by title."""
        filtered = filter.search_by_title(sample_videos, "Python")
        assert len(filtered) == 3  # "Python Tutorial", "Advanced Python", "Python Tips"

    def test_search_by_title_case_insensitive(self, filter, sample_videos):
        """Test case-insensitive search."""
        filtered = filter.search_by_title(sample_videos, "python")
        assert len(filtered) == 3

    def test_search_by_title_case_sensitive(self, filter, sample_videos):
        """Test case-sensitive search."""
        filtered = filter.search_by_title(sample_videos, "python", case_sensitive=True)
        assert len(filtered) == 0  # No exact lowercase match

    def test_get_available_videos(self, filter, sample_videos):
        """Test getting only available videos."""
        available = filter.get_available_videos(sample_videos)
        assert len(available) == 4
        assert all(v.is_available for v in available)

    def test_empty_search(self, filter, sample_videos):
        """Test empty search returns all."""
        filtered = filter.search_by_title(sample_videos, "")
        assert len(filtered) == len(sample_videos)
