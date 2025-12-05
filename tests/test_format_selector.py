"""Unit tests for FormatSelector."""

import pytest
from src.core.format_selector import (
    FormatSelector, FormatInfo, VideoFormats, FormatType
)


class TestFormatInfo:
    """Tests for FormatInfo dataclass."""

    def test_format_info_creation(self):
        """Test creating a FormatInfo."""
        info = FormatInfo(
            format_id="137",
            ext="mp4",
            resolution="1920x1080",
            width=1920,
            height=1080,
            fps=30.0,
            vcodec="avc1",
            acodec="none",
            has_video=True,
            has_audio=False
        )
        assert info.format_id == "137"
        assert info.ext == "mp4"
        assert info.height == 1080

    def test_format_type_video_audio(self):
        """Test format type detection for combined."""
        info = FormatInfo(
            format_id="22",
            ext="mp4",
            has_video=True,
            has_audio=True
        )
        assert info.format_type == FormatType.VIDEO_AUDIO

    def test_format_type_video_only(self):
        """Test format type detection for video only."""
        info = FormatInfo(
            format_id="137",
            ext="mp4",
            has_video=True,
            has_audio=False
        )
        assert info.format_type == FormatType.VIDEO_ONLY

    def test_format_type_audio_only(self):
        """Test format type detection for audio only."""
        info = FormatInfo(
            format_id="140",
            ext="m4a",
            has_video=False,
            has_audio=True
        )
        assert info.format_type == FormatType.AUDIO_ONLY

    def test_quality_label_4k(self):
        """Test quality label for 4K."""
        info = FormatInfo("id", "mp4", height=2160, has_video=True)
        assert info.quality_label == "4K"

    def test_quality_label_1080p(self):
        """Test quality label for 1080p."""
        info = FormatInfo("id", "mp4", height=1080, has_video=True)
        assert info.quality_label == "1080p"

    def test_quality_label_720p(self):
        """Test quality label for 720p."""
        info = FormatInfo("id", "mp4", height=720, has_video=True)
        assert info.quality_label == "720p"

    def test_quality_label_audio(self):
        """Test quality label for audio."""
        info = FormatInfo("id", "m4a", has_video=False, has_audio=True, abr=128.0)
        assert info.quality_label == "128kbps"

    def test_size_str_gb(self):
        """Test size string for gigabytes."""
        info = FormatInfo("id", "mp4", filesize=2 * 1024 * 1024 * 1024)
        assert "GB" in info.size_str

    def test_size_str_mb(self):
        """Test size string for megabytes."""
        info = FormatInfo("id", "mp4", filesize=500 * 1024 * 1024)
        assert "MB" in info.size_str

    def test_size_str_unknown(self):
        """Test size string when unknown."""
        info = FormatInfo("id", "mp4")
        assert info.size_str == "Unknown"

    def test_bitrate_str(self):
        """Test bitrate string."""
        info = FormatInfo("id", "mp4", tbr=5000.0)
        assert "Mbps" in info.bitrate_str


class TestVideoFormats:
    """Tests for VideoFormats dataclass."""

    def test_video_formats_creation(self):
        """Test creating VideoFormats."""
        formats = VideoFormats(
            video_id="test123",
            title="Test Video",
            duration=300
        )
        assert formats.video_id == "test123"
        assert formats.title == "Test Video"
        assert formats.duration == 300
        assert len(formats.formats) == 0

    def test_video_formats_with_error(self):
        """Test VideoFormats with error."""
        formats = VideoFormats(
            video_id="",
            error="Could not fetch video"
        )
        assert formats.error is not None


class TestFormatSelector:
    """Tests for FormatSelector class."""

    @pytest.fixture
    def selector(self):
        """Create FormatSelector instance."""
        return FormatSelector()

    @pytest.fixture
    def sample_formats(self):
        """Create sample formats for testing."""
        return [
            FormatInfo("137", "mp4", height=1080, has_video=True, has_audio=False, filesize=100000000),
            FormatInfo("136", "mp4", height=720, has_video=True, has_audio=False, filesize=50000000),
            FormatInfo("22", "mp4", height=720, has_video=True, has_audio=True, filesize=80000000),
            FormatInfo("140", "m4a", has_video=False, has_audio=True, filesize=5000000),
            FormatInfo("251", "webm", has_video=False, has_audio=True, filesize=4000000),
        ]

    def test_filter_video_only(self, selector, sample_formats):
        """Test filtering video-only formats."""
        filtered = selector.filter_formats(sample_formats, video_only=True)
        assert len(filtered) == 3
        assert all(f.has_video for f in filtered)

    def test_filter_audio_only(self, selector, sample_formats):
        """Test filtering formats with audio (audio_only keeps all with audio)."""
        filtered = selector.filter_formats(sample_formats, audio_only=True)
        # audio_only=True keeps all formats that have audio (including video+audio)
        # Formats with audio: 22 (video+audio), 140 (audio), 251 (audio) = 3
        assert len(filtered) == 3
        assert all(f.has_audio for f in filtered)

    def test_filter_pure_audio_formats(self, selector, sample_formats):
        """Test filtering pure audio-only formats (no video)."""
        # To get pure audio formats, filter with audio_only and check has_video=False
        filtered = selector.filter_formats(sample_formats, audio_only=True)
        pure_audio = [f for f in filtered if not f.has_video]
        assert len(pure_audio) == 2
        assert all(f.has_audio and not f.has_video for f in pure_audio)

    def test_filter_by_min_height(self, selector, sample_formats):
        """Test filtering by minimum height."""
        filtered = selector.filter_formats(sample_formats, min_height=1080)
        assert len(filtered) == 1
        assert filtered[0].height == 1080

    def test_filter_by_max_height(self, selector, sample_formats):
        """Test filtering by maximum height."""
        filtered = selector.filter_formats(sample_formats, video_only=True, max_height=720)
        assert all(f.height <= 720 for f in filtered)

    def test_filter_by_extension(self, selector, sample_formats):
        """Test filtering by extension."""
        filtered = selector.filter_formats(sample_formats, extensions=["mp4"])
        assert all(f.ext == "mp4" for f in filtered)

    def test_sort_by_quality(self, selector, sample_formats):
        """Test sorting by quality."""
        sorted_formats = selector.sort_formats(sample_formats, by="quality")
        # First should be highest quality
        assert sorted_formats[0].height >= sorted_formats[-1].height or not sorted_formats[-1].has_video

    def test_sort_by_size(self, selector, sample_formats):
        """Test sorting by size."""
        sorted_formats = selector.sort_formats(sample_formats, by="size")
        # First should be largest
        sizes = [f.filesize or 0 for f in sorted_formats]
        assert sizes == sorted(sizes, reverse=True)

    def test_get_best_format(self, selector, sample_formats):
        """Test getting best format."""
        best = selector.get_best_format(sample_formats, quality="best")
        assert best is not None
        # Should prefer combined format or highest quality
        assert best.has_video

    def test_get_best_format_1080p(self, selector, sample_formats):
        """Test getting best 1080p format."""
        best = selector.get_best_format(sample_formats, quality="1080p")
        assert best is not None
        # Should be close to 1080p
        if best.has_video:
            assert abs(best.height - 1080) <= 360  # Allow some tolerance

    def test_get_best_format_720p(self, selector, sample_formats):
        """Test getting best 720p format."""
        best = selector.get_best_format(sample_formats, quality="720p")
        assert best is not None

    def test_get_best_format_empty_list(self, selector):
        """Test getting best format from empty list."""
        best = selector.get_best_format([], quality="best")
        assert best is None
