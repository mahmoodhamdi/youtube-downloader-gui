"""Integration tests for YouTube Downloader.

These tests verify that different components work together correctly.
"""

import pytest
import tempfile
import os
import json
import threading
import time

from src.core.queue_manager import QueueManager, VideoItem, VideoStatus
from src.core.download_manager import DownloadManager, DownloadOptions
from src.config.config_manager import ConfigManager
from src.core.format_selector import FormatSelector
from src.core.playlist_filter import PlaylistFilter
from src.core.update_manager import UpdateManager


class TestQueueDownloadIntegration:
    """Test integration between QueueManager and DownloadManager."""

    @pytest.fixture
    def queue_manager(self):
        """Create QueueManager instance."""
        return QueueManager()

    @pytest.fixture
    def download_options(self, temp_dir):
        """Create DownloadOptions with temp directory."""
        return DownloadOptions(output_path=temp_dir)

    @pytest.fixture
    def download_manager(self, queue_manager, download_options):
        """Create DownloadManager instance."""
        return DownloadManager(queue_manager, download_options)

    def test_queue_to_download_flow(self, queue_manager, download_manager):
        """Test adding items to queue and processing."""
        # Add items to queue
        for i in range(3):
            video = VideoItem(
                id=f"video_{i}",
                url=f"https://youtube.com/watch?v=test{i}",
                title=f"Test Video {i}"
            )
            queue_manager.add(video)

        assert len(queue_manager) == 3

        # Get next queued item
        next_video = queue_manager.get_next_queued()
        assert next_video is not None
        assert next_video.status == VideoStatus.QUEUED

        # Simulate download starting
        queue_manager.update_status(next_video.id, VideoStatus.DOWNLOADING)
        assert queue_manager.get(next_video.id).status == VideoStatus.DOWNLOADING

        # Get next queued (should skip downloading one)
        next_video2 = queue_manager.get_next_queued()
        assert next_video2.id != next_video.id

    def test_concurrent_queue_access(self, queue_manager):
        """Test concurrent access to queue."""
        errors = []
        results = []

        def worker(worker_id):
            try:
                for i in range(10):
                    # Add - use unique URL per worker to avoid duplicate detection
                    video = VideoItem(
                        id=f"w{worker_id}_v{i}",
                        url=f"url_{worker_id}_{i}",
                        title=f"Video {i}"
                    )
                    queue_manager.add(video)

                    # Get
                    retrieved = queue_manager.get(f"w{worker_id}_v{i}")
                    if retrieved:
                        results.append(retrieved.id)

                    # Update
                    queue_manager.update_progress(
                        f"w{worker_id}_v{i}",
                        progress=float(i * 10),
                        speed=1000.0
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(queue_manager) == 50  # 5 workers * 10 videos


class TestConfigIntegration:
    """Test configuration integration with other components."""

    @pytest.fixture
    def temp_config(self, temp_dir):
        """Create temp config."""
        config_file = os.path.join(temp_dir, "config.json")
        manager = ConfigManager(config_file)
        manager.load()
        return manager

    def test_config_affects_download_options(self, temp_config, temp_dir):
        """Test that config can be used to build download options."""
        temp_config.update({"max_concurrent_downloads": 3})
        temp_config.update({"download_path": temp_dir})

        # Build options from config
        options = DownloadOptions(
            output_path=temp_config.get("download_path"),
            quality=temp_config.get("quality", "best")
        )
        assert options.output_path == temp_dir

    def test_config_persistence_across_sessions(self, temp_dir):
        """Test config persists across manager instances."""
        config_file = os.path.join(temp_dir, "config.json")

        # First session
        config1 = ConfigManager(config_file)
        config1.load()
        config1.update({"max_concurrent_downloads": 5})
        config1.save()

        # Second session (new instance, same file)
        config2 = ConfigManager(config_file)
        config2.load()
        assert config2.get("max_concurrent_downloads") == 5


class TestFilterIntegration:
    """Test integration between filters and other components."""

    def test_format_filter_chain(self):
        """Test chaining multiple format filters."""
        selector = FormatSelector()

        # Create formats
        from src.core.format_selector import FormatInfo
        formats = [
            FormatInfo("1", "mp4", height=1080, has_video=True, has_audio=True, filesize=100),
            FormatInfo("2", "mp4", height=720, has_video=True, has_audio=True, filesize=80),
            FormatInfo("3", "mp4", height=1080, has_video=True, has_audio=False, filesize=90),
            FormatInfo("4", "webm", height=1080, has_video=True, has_audio=True, filesize=95),
            FormatInfo("5", "m4a", has_video=False, has_audio=True, filesize=10),
        ]

        # Chain filters: mp4, video+audio, 720p+
        result = selector.filter_formats(formats, extensions=["mp4"])
        result = [f for f in result if f.has_video and f.has_audio]
        result = selector.filter_formats(result, min_height=720)

        assert len(result) == 2  # formats 1 and 2
        assert all(f.ext == "mp4" for f in result)
        assert all(f.has_video and f.has_audio for f in result)

    def test_playlist_to_queue_flow(self):
        """Test flow from playlist filtering to queue."""
        from src.core.playlist_filter import PlaylistVideoInfo

        # Create playlist videos
        videos = [
            PlaylistVideoInfo(1, "v1", "url1", "Short Video", duration=60),
            PlaylistVideoInfo(2, "v2", "url2", "Medium Video", duration=300),
            PlaylistVideoInfo(3, "v3", "url3", "Long Video", duration=3600),
        ]

        # Filter for videos under 10 minutes
        pf = PlaylistFilter()
        filtered = pf.filter_by_duration(videos, max_seconds=600)

        # Add filtered to queue
        queue = QueueManager()
        for video in filtered:
            item = VideoItem(
                id=video.video_id,
                url=video.url,
                title=video.title,
                duration=video.duration
            )
            queue.add(item)

        assert len(queue) == 2  # Short and Medium videos


class TestUpdateManagerIntegration:
    """Test UpdateManager integration."""

    def test_version_comparison(self):
        """Test version comparison logic."""
        manager = UpdateManager()

        # Test comparisons
        assert manager._compare_versions("2024.01.01", "2024.01.02") < 0
        assert manager._compare_versions("2024.01.02", "2024.01.01") > 0
        assert manager._compare_versions("2024.01.01", "2024.01.01") == 0
        assert manager._compare_versions("2024.12.03", "2024.12.03") == 0

    def test_get_current_version(self):
        """Test getting current yt-dlp version."""
        manager = UpdateManager()
        version = manager.get_current_version()

        # Should return a version string or "Unknown"
        assert isinstance(version, str)
        assert len(version) > 0


class TestStatisticsIntegration:
    """Test statistics integration."""

    @pytest.fixture
    def stats_manager(self, temp_dir):
        """Create StatisticsManager with temp file."""
        from src.ui.tabs.statistics_tab import StatisticsManager
        stats_file = os.path.join(temp_dir, "stats.json")
        return StatisticsManager(stats_file)

    def test_record_and_retrieve_stats(self, stats_manager):
        """Test recording and retrieving statistics."""
        # Record some downloads
        stats_manager.record_download(
            success=True,
            bytes_downloaded=100000000,
            duration_seconds=300,
            quality="1080p",
            channel="Test Channel"
        )

        stats_manager.record_download(
            success=True,
            bytes_downloaded=50000000,
            duration_seconds=150,
            quality="720p",
            channel="Test Channel"
        )

        stats_manager.record_download(
            success=False,
            quality="1080p"
        )

        # Verify stats
        stats = stats_manager.stats
        assert stats.total_downloads == 3
        assert stats.successful_downloads == 2
        assert stats.failed_downloads == 1
        assert stats.total_bytes_downloaded == 150000000
        assert "1080p" in stats.downloads_by_quality
        assert "Test Channel" in stats.most_downloaded_channels

    def test_stats_persistence(self, temp_dir):
        """Test statistics persist to file."""
        from src.ui.tabs.statistics_tab import StatisticsManager
        stats_file = os.path.join(temp_dir, "stats.json")

        # First session
        manager1 = StatisticsManager(stats_file)
        manager1.record_download(success=True, bytes_downloaded=100)

        # Second session
        manager2 = StatisticsManager(stats_file)
        assert manager2.stats.total_downloads == 1
        assert manager2.stats.total_bytes_downloaded == 100


class TestQueueFilterIntegration:
    """Test queue filter widget integration."""

    def test_filter_applies_to_queue_items(self):
        """Test that QueueFilter correctly filters VideoItems."""
        from src.ui.widgets.queue_search import QueueFilter

        # Create queue items
        items = [
            VideoItem(id="v1", url="url1", title="Python Tutorial", status=VideoStatus.QUEUED),
            VideoItem(id="v2", url="url2", title="JavaScript Guide", status=VideoStatus.DOWNLOADING),
            VideoItem(id="v3", url="url3", title="Python Advanced", status=VideoStatus.COMPLETED),
            VideoItem(id="v4", url="url4", title="Web Development", status=VideoStatus.ERROR),
        ]

        # Test search filter
        filtered = QueueFilter.filter_by_search(items, "Python")
        assert len(filtered) == 2

        # Test status filter
        filtered = QueueFilter.filter_by_status(items, "completed")
        assert len(filtered) == 1
        assert filtered[0].id == "v3"

        # Test combined filters
        filtered = QueueFilter.apply(items, search_text="Python", status="queued")
        assert len(filtered) == 1
        assert filtered[0].id == "v1"


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_complete_download_workflow(self, temp_dir):
        """Test complete workflow from URL to completion."""
        # Setup
        queue = QueueManager()
        options = DownloadOptions(output_path=temp_dir)

        # 1. Add URL to queue
        video = VideoItem(
            id="test_video",
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            duration=300
        )
        queue.add(video)
        assert len(queue) == 1

        # 2. Start download (simulate)
        next_video = queue.get_next_queued()
        assert next_video is not None

        queue.update_status(next_video.id, VideoStatus.DOWNLOADING)
        assert queue.get(next_video.id).status == VideoStatus.DOWNLOADING

        # 3. Update progress
        for progress in [25, 50, 75, 100]:
            queue.update_progress(
                next_video.id,
                progress=float(progress),
                speed=5000000.0
            )

        # 4. Mark complete
        queue.update_status(next_video.id, VideoStatus.COMPLETED)
        completed = queue.get(next_video.id)
        assert completed.status == VideoStatus.COMPLETED
        assert completed.progress == 100.0

        # 5. Verify queue state
        queued = queue.get_by_status(VideoStatus.QUEUED)
        assert len(queued) == 0

        completed_list = queue.get_by_status(VideoStatus.COMPLETED)
        assert len(completed_list) == 1
