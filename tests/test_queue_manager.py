"""Unit tests for QueueManager."""

import pytest
import threading
import time
from src.core.queue_manager import QueueManager, VideoItem, VideoStatus


class TestVideoItem:
    """Tests for VideoItem dataclass."""

    def test_video_item_creation(self):
        """Test creating a VideoItem."""
        item = VideoItem(
            url="https://youtube.com/watch?v=test123",
            title="Test Video"
        )
        assert item.url == "https://youtube.com/watch?v=test123"
        assert item.title == "Test Video"
        assert item.status == VideoStatus.QUEUED
        assert item.id is not None  # Auto-generated

    def test_video_item_default_values(self):
        """Test VideoItem default values."""
        item = VideoItem(url="https://example.com")
        assert item.progress == 0.0
        assert item.filesize == 0
        assert item.speed == 0.0
        assert item.eta == 0
        assert item.error_message is None
        assert item.title == "Extracting..."

    def test_video_item_with_all_fields(self):
        """Test VideoItem with all fields populated."""
        item = VideoItem(
            url="https://youtube.com/watch?v=vid123",
            id="custom_id",
            title="Full Test Video",
            duration=300,
            thumbnail_url="https://example.com/thumb.jpg",
            status=VideoStatus.DOWNLOADING,
            progress=50.0,
            filesize=100000000,
            speed=1000000.0,
            eta=50,
            output_path="/downloads/video.mp4"
        )
        assert item.id == "custom_id"
        assert item.duration == 300
        assert item.status == VideoStatus.DOWNLOADING
        assert item.progress == 50.0

    def test_video_item_to_dict(self):
        """Test VideoItem serialization."""
        item = VideoItem(
            url="https://youtube.com/watch?v=test",
            title="Test"
        )
        data = item.to_dict()
        assert 'id' in data
        assert 'url' in data
        assert 'title' in data
        assert 'status' in data


class TestQueueManager:
    """Tests for QueueManager class."""

    @pytest.fixture
    def queue_manager(self):
        """Create a fresh QueueManager for each test."""
        return QueueManager()

    @pytest.fixture
    def sample_video(self):
        """Create a sample VideoItem."""
        return VideoItem(
            url="https://youtube.com/watch?v=sample123",
            id="sample123",
            title="Sample Video"
        )

    def test_add_video(self, queue_manager, sample_video):
        """Test adding a video to the queue."""
        result = queue_manager.add(sample_video)
        assert result is True
        assert len(queue_manager) == 1
        assert queue_manager.get("sample123") == sample_video

    def test_add_duplicate_video(self, queue_manager, sample_video):
        """Test that duplicate videos are not added."""
        queue_manager.add(sample_video)
        result = queue_manager.add(sample_video)
        assert result is False
        assert len(queue_manager) == 1

    def test_remove_video(self, queue_manager, sample_video):
        """Test removing a video from the queue."""
        queue_manager.add(sample_video)
        removed = queue_manager.remove("sample123")
        assert removed == sample_video
        assert len(queue_manager) == 0

    def test_remove_nonexistent_video(self, queue_manager):
        """Test removing a video that doesn't exist."""
        removed = queue_manager.remove("nonexistent")
        assert removed is None

    def test_get_video(self, queue_manager, sample_video):
        """Test getting a video by ID."""
        queue_manager.add(sample_video)
        retrieved = queue_manager.get("sample123")
        assert retrieved == sample_video

    def test_get_nonexistent_video(self, queue_manager):
        """Test getting a video that doesn't exist."""
        retrieved = queue_manager.get("nonexistent")
        assert retrieved is None

    def test_update_status(self, queue_manager, sample_video):
        """Test updating video status."""
        queue_manager.add(sample_video)
        queue_manager.update_status("sample123", VideoStatus.DOWNLOADING)
        video = queue_manager.get("sample123")
        assert video.status == VideoStatus.DOWNLOADING

    def test_update_progress(self, queue_manager, sample_video):
        """Test updating video progress."""
        queue_manager.add(sample_video)
        queue_manager.update_progress(
            "sample123",
            progress=75.5,
            speed=2000000.0,
            eta=12
        )
        video = queue_manager.get("sample123")
        assert video.progress == 75.5
        assert video.speed == 2000000.0

    def test_get_next_queued(self, queue_manager):
        """Test getting the next queued video."""
        video1 = VideoItem(url="url1", id="v1", title="Video 1")
        video2 = VideoItem(url="url2", id="v2", title="Video 2")
        video3 = VideoItem(url="url3", id="v3", title="Video 3")

        queue_manager.add(video1)
        queue_manager.add(video2)
        queue_manager.add(video3)

        # Mark first as downloading
        queue_manager.update_status("v1", VideoStatus.DOWNLOADING)

        next_video = queue_manager.get_next_queued()
        assert next_video.id == "v2"

    def test_get_all(self, queue_manager):
        """Test getting all videos."""
        video1 = VideoItem(url="url1", id="v1", title="Video 1")
        video2 = VideoItem(url="url2", id="v2", title="Video 2")

        queue_manager.add(video1)
        queue_manager.add(video2)

        all_videos = queue_manager.get_all()
        assert len(all_videos) == 2

    def test_get_by_status(self, queue_manager):
        """Test getting videos by status."""
        video1 = VideoItem(url="url1", id="v1", title="Video 1")
        video2 = VideoItem(url="url2", id="v2", title="Video 2")
        video3 = VideoItem(url="url3", id="v3", title="Video 3")

        queue_manager.add(video1)
        queue_manager.add(video2)
        queue_manager.add(video3)

        # Update statuses
        queue_manager.update_status("v2", VideoStatus.DOWNLOADING)
        queue_manager.update_status("v3", VideoStatus.COMPLETED)

        queued = queue_manager.get_by_status(VideoStatus.QUEUED)
        assert len(queued) == 1
        assert queued[0].id == "v1"

    def test_clear_queue(self, queue_manager):
        """Test clearing the queue."""
        video1 = VideoItem(url="url1", id="v1", title="Video 1")
        video2 = VideoItem(url="url2", id="v2", title="Video 2")

        queue_manager.add(video1)
        queue_manager.add(video2)

        queue_manager.clear(keep_active=False)
        assert len(queue_manager) == 0

    def test_is_empty(self, queue_manager, sample_video):
        """Test empty queue check."""
        assert len(queue_manager) == 0

        queue_manager.add(sample_video)
        assert len(queue_manager) == 1

    def test_thread_safety(self, queue_manager):
        """Test thread-safe operations."""
        errors = []

        def add_videos(start_id):
            try:
                for i in range(50):
                    video = VideoItem(
                        url=f"url_{start_id}_{i}",
                        id=f"v{start_id}_{i}",
                        title=f"Video {i}"
                    )
                    queue_manager.add(video)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_videos, args=(1,)),
            threading.Thread(target=add_videos, args=(2,)),
            threading.Thread(target=add_videos, args=(3,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Should have 150 unique videos
        assert len(queue_manager) == 150


class TestVideoStatus:
    """Tests for VideoStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert VideoStatus.QUEUED is not None
        assert VideoStatus.DOWNLOADING is not None
        assert VideoStatus.COMPLETED is not None
        assert VideoStatus.ERROR is not None
        assert VideoStatus.PAUSED is not None
        assert VideoStatus.CANCELLED is not None

    def test_is_active(self):
        """Test is_active method."""
        assert VideoStatus.DOWNLOADING.is_active() is True
        assert VideoStatus.QUEUED.is_active() is False
        assert VideoStatus.COMPLETED.is_active() is False

    def test_is_final(self):
        """Test is_final method."""
        assert VideoStatus.COMPLETED.is_final() is True
        assert VideoStatus.ERROR.is_final() is True
        assert VideoStatus.DOWNLOADING.is_final() is False

    def test_can_start(self):
        """Test can_start method."""
        assert VideoStatus.QUEUED.can_start() is True
        assert VideoStatus.PAUSED.can_start() is True
        assert VideoStatus.DOWNLOADING.can_start() is False
