"""Thread-safe queue management for video downloads.

This module provides a thread-safe queue system for managing video downloads,
including adding, removing, reordering, and status tracking of videos.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Optional, Callable, Iterator, Dict, Any
from collections import OrderedDict


class VideoStatus(Enum):
    """Status states for a video in the queue."""
    QUEUED = auto()
    EXTRACTING = auto()
    WAITING = auto()
    DOWNLOADING = auto()
    POST_PROCESSING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    ERROR = auto()
    CANCELLED = auto()

    def is_active(self) -> bool:
        """Check if this status represents an active download."""
        return self in (
            VideoStatus.EXTRACTING,
            VideoStatus.DOWNLOADING,
            VideoStatus.POST_PROCESSING
        )

    def is_final(self) -> bool:
        """Check if this status represents a final state."""
        return self in (
            VideoStatus.COMPLETED,
            VideoStatus.ERROR,
            VideoStatus.CANCELLED
        )

    def can_start(self) -> bool:
        """Check if download can be started from this status."""
        return self in (
            VideoStatus.QUEUED,
            VideoStatus.WAITING,
            VideoStatus.PAUSED
        )


@dataclass
class VideoItem:
    """Represents a video item in the download queue.

    Attributes:
        id: Unique identifier for this queue item
        url: The video URL
        title: Video title (may be updated after extraction)
        duration: Video duration in seconds
        filesize: Estimated file size in bytes
        thumbnail_url: URL to video thumbnail
        status: Current download status
        progress: Download progress (0-100)
        speed: Current download speed in bytes/second
        eta: Estimated time remaining in seconds
        error_message: Error message if status is ERROR
        retry_count: Number of retry attempts
        playlist_title: Title of parent playlist (if any)
        playlist_index: Index in playlist (if any)
        output_path: Final output file path
        created_at: Timestamp when added to queue
        started_at: Timestamp when download started
        completed_at: Timestamp when download completed
        metadata: Additional metadata from extraction
    """
    url: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = "Extracting..."
    duration: int = 0
    filesize: int = 0
    thumbnail_url: Optional[str] = None
    status: VideoStatus = VideoStatus.QUEUED
    progress: float = 0.0
    speed: float = 0.0
    eta: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    playlist_title: Optional[str] = None
    playlist_index: Optional[int] = None
    output_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'duration': self.duration,
            'filesize': self.filesize,
            'thumbnail_url': self.thumbnail_url,
            'status': self.status.name,
            'progress': self.progress,
            'speed': self.speed,
            'eta': self.eta,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'playlist_title': self.playlist_title,
            'playlist_index': self.playlist_index,
            'output_path': self.output_path,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'VideoItem':
        """Create VideoItem from dictionary."""
        item = cls(url=data['url'])
        item.id = data.get('id', item.id)
        item.title = data.get('title', item.title)
        item.duration = data.get('duration', 0)
        item.filesize = data.get('filesize', 0)
        item.thumbnail_url = data.get('thumbnail_url')
        item.status = VideoStatus[data.get('status', 'QUEUED')]
        item.progress = data.get('progress', 0.0)
        item.error_message = data.get('error_message')
        item.retry_count = data.get('retry_count', 0)
        item.playlist_title = data.get('playlist_title')
        item.playlist_index = data.get('playlist_index')
        item.output_path = data.get('output_path')

        if data.get('created_at'):
            item.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            item.started_at = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            item.completed_at = datetime.fromisoformat(data['completed_at'])

        return item

    def can_retry(self) -> bool:
        """Check if this item can be retried."""
        return (
            self.status == VideoStatus.ERROR and
            self.retry_count < self.max_retries
        )

    def format_duration(self) -> str:
        """Format duration as HH:MM:SS or MM:SS."""
        if not self.duration:
            return "--:--"

        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def format_filesize(self) -> str:
        """Format filesize in human readable format."""
        if not self.filesize:
            return "Unknown"

        size = self.filesize
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def format_speed(self) -> str:
        """Format download speed."""
        if not self.speed:
            return "--"

        speed = self.speed
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024:
                return f"{speed:.1f} {unit}"
            speed /= 1024
        return f"{speed:.1f} TB/s"

    def format_eta(self) -> str:
        """Format ETA in human readable format."""
        if not self.eta or self.eta < 0:
            return "--"

        if self.eta < 60:
            return f"{self.eta}s"
        elif self.eta < 3600:
            minutes = self.eta // 60
            seconds = self.eta % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = self.eta // 3600
            minutes = (self.eta % 3600) // 60
            return f"{hours}h {minutes}m"


class QueueManager:
    """Thread-safe manager for the video download queue.

    This class provides all operations for managing the download queue
    with proper thread synchronization to prevent race conditions.

    Attributes:
        max_queue_size: Maximum number of items allowed in queue (0 = unlimited)

    Events/Callbacks:
        on_item_added: Called when item is added
        on_item_removed: Called when item is removed
        on_item_updated: Called when item status changes
        on_queue_cleared: Called when queue is cleared
    """

    def __init__(self, max_queue_size: int = 0):
        self._queue: OrderedDict[str, VideoItem] = OrderedDict()
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self.max_queue_size = max_queue_size

        # Callbacks
        self.on_item_added: Optional[Callable[[VideoItem], None]] = None
        self.on_item_removed: Optional[Callable[[VideoItem], None]] = None
        self.on_item_updated: Optional[Callable[[VideoItem], None]] = None
        self.on_queue_cleared: Optional[Callable[[], None]] = None

    def add(self, video: VideoItem) -> bool:
        """Add a video to the queue.

        Args:
            video: The VideoItem to add

        Returns:
            True if added successfully, False if queue is full or duplicate

        Thread-safe: Yes
        """
        with self._lock:
            # Check queue size limit
            if self.max_queue_size > 0 and len(self._queue) >= self.max_queue_size:
                return False

            # Check for duplicates (same URL with non-final status)
            for existing in self._queue.values():
                if (existing.url == video.url and
                    not existing.status.is_final()):
                    return False

            self._queue[video.id] = video
            self._condition.notify_all()

        # Callback outside lock to prevent deadlocks
        if self.on_item_added:
            self.on_item_added(video)

        return True

    def add_multiple(self, videos: List[VideoItem]) -> List[VideoItem]:
        """Add multiple videos to the queue.

        Args:
            videos: List of VideoItems to add

        Returns:
            List of successfully added videos

        Thread-safe: Yes
        """
        added = []
        with self._lock:
            for video in videos:
                if self.max_queue_size > 0 and len(self._queue) >= self.max_queue_size:
                    break

                # Check for duplicates
                is_duplicate = False
                for existing in self._queue.values():
                    if (existing.url == video.url and
                        not existing.status.is_final()):
                        is_duplicate = True
                        break

                if not is_duplicate:
                    self._queue[video.id] = video
                    added.append(video)

            if added:
                self._condition.notify_all()

        # Callbacks outside lock
        for video in added:
            if self.on_item_added:
                self.on_item_added(video)

        return added

    def remove(self, video_id: str) -> Optional[VideoItem]:
        """Remove a video from the queue.

        Args:
            video_id: ID of the video to remove

        Returns:
            The removed VideoItem, or None if not found

        Thread-safe: Yes
        """
        removed = None
        with self._lock:
            if video_id in self._queue:
                removed = self._queue.pop(video_id)
                self._condition.notify_all()

        if removed and self.on_item_removed:
            self.on_item_removed(removed)

        return removed

    def remove_multiple(self, video_ids: List[str]) -> List[VideoItem]:
        """Remove multiple videos from the queue.

        Args:
            video_ids: List of video IDs to remove

        Returns:
            List of removed VideoItems

        Thread-safe: Yes
        """
        removed = []
        with self._lock:
            for video_id in video_ids:
                if video_id in self._queue:
                    removed.append(self._queue.pop(video_id))

            if removed:
                self._condition.notify_all()

        for video in removed:
            if self.on_item_removed:
                self.on_item_removed(video)

        return removed

    def get(self, video_id: str) -> Optional[VideoItem]:
        """Get a video by ID.

        Args:
            video_id: ID of the video to get

        Returns:
            The VideoItem, or None if not found

        Thread-safe: Yes
        """
        with self._lock:
            return self._queue.get(video_id)

    def get_by_url(self, url: str) -> Optional[VideoItem]:
        """Get a video by URL.

        Args:
            url: URL of the video to find

        Returns:
            The VideoItem, or None if not found

        Thread-safe: Yes
        """
        with self._lock:
            for video in self._queue.values():
                if video.url == url:
                    return video
            return None

    def get_all(self) -> List[VideoItem]:
        """Get all videos in the queue.

        Returns:
            List of all VideoItems in order

        Thread-safe: Yes
        """
        with self._lock:
            return list(self._queue.values())

    def get_by_status(self, status: VideoStatus) -> List[VideoItem]:
        """Get all videos with a specific status.

        Args:
            status: The status to filter by

        Returns:
            List of VideoItems with the given status

        Thread-safe: Yes
        """
        with self._lock:
            return [v for v in self._queue.values() if v.status == status]

    def get_next_queued(self) -> Optional[VideoItem]:
        """Get the next video ready for download.

        Returns:
            The next VideoItem with QUEUED status, or None

        Thread-safe: Yes
        """
        with self._lock:
            for video in self._queue.values():
                if video.status == VideoStatus.QUEUED:
                    return video
            return None

    def get_active_downloads(self) -> List[VideoItem]:
        """Get all currently downloading videos.

        Returns:
            List of VideoItems with active download status

        Thread-safe: Yes
        """
        with self._lock:
            return [v for v in self._queue.values() if v.status.is_active()]

    def update_status(
        self,
        video_id: str,
        status: VideoStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """Update the status of a video.

        Args:
            video_id: ID of the video to update
            status: New status
            error_message: Error message (if status is ERROR)

        Returns:
            True if updated successfully

        Thread-safe: Yes
        """
        video = None
        with self._lock:
            if video_id not in self._queue:
                return False

            video = self._queue[video_id]
            video.status = status

            if status == VideoStatus.ERROR:
                video.error_message = error_message
                video.retry_count += 1

            if status == VideoStatus.DOWNLOADING and not video.started_at:
                video.started_at = datetime.now()

            if status == VideoStatus.COMPLETED:
                video.completed_at = datetime.now()
                video.progress = 100.0

            self._condition.notify_all()

        if video and self.on_item_updated:
            self.on_item_updated(video)

        return True

    def update_progress(
        self,
        video_id: str,
        progress: float,
        speed: float = 0,
        eta: int = 0
    ) -> bool:
        """Update download progress for a video.

        Args:
            video_id: ID of the video
            progress: Download progress (0-100)
            speed: Download speed in bytes/second
            eta: Estimated time remaining in seconds

        Returns:
            True if updated successfully

        Thread-safe: Yes
        """
        video = None
        with self._lock:
            if video_id not in self._queue:
                return False

            video = self._queue[video_id]
            video.progress = min(100.0, max(0.0, progress))
            video.speed = speed
            video.eta = eta

        if video and self.on_item_updated:
            self.on_item_updated(video)

        return True

    def update_info(
        self,
        video_id: str,
        title: Optional[str] = None,
        duration: Optional[int] = None,
        filesize: Optional[int] = None,
        thumbnail_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update video information after extraction.

        Args:
            video_id: ID of the video
            title: Video title
            duration: Duration in seconds
            filesize: File size in bytes
            thumbnail_url: Thumbnail URL
            metadata: Additional metadata

        Returns:
            True if updated successfully

        Thread-safe: Yes
        """
        video = None
        with self._lock:
            if video_id not in self._queue:
                return False

            video = self._queue[video_id]

            if title is not None:
                video.title = title
            if duration is not None:
                video.duration = duration
            if filesize is not None:
                video.filesize = filesize
            if thumbnail_url is not None:
                video.thumbnail_url = thumbnail_url
            if metadata is not None:
                video.metadata.update(metadata)

        if video and self.on_item_updated:
            self.on_item_updated(video)

        return True

    def reorder(self, video_id: str, new_index: int) -> bool:
        """Move a video to a new position in the queue.

        Args:
            video_id: ID of the video to move
            new_index: New position (0-based)

        Returns:
            True if moved successfully

        Thread-safe: Yes
        """
        with self._lock:
            if video_id not in self._queue:
                return False

            # Get current order
            items = list(self._queue.items())
            current_index = next(
                (i for i, (k, _) in enumerate(items) if k == video_id),
                None
            )

            if current_index is None:
                return False

            # Remove and reinsert at new position
            item = items.pop(current_index)
            new_index = max(0, min(new_index, len(items)))
            items.insert(new_index, item)

            # Rebuild queue
            self._queue = OrderedDict(items)

            return True

    def move_to_top(self, video_id: str) -> bool:
        """Move a video to the top of the queue.

        Thread-safe: Yes
        """
        return self.reorder(video_id, 0)

    def move_to_bottom(self, video_id: str) -> bool:
        """Move a video to the bottom of the queue.

        Thread-safe: Yes
        """
        with self._lock:
            return self.reorder(video_id, len(self._queue))

    def move_up(self, video_id: str) -> bool:
        """Move a video up one position.

        Thread-safe: Yes
        """
        with self._lock:
            items = list(self._queue.keys())
            try:
                current_index = items.index(video_id)
                if current_index > 0:
                    return self.reorder(video_id, current_index - 1)
            except ValueError:
                pass
            return False

    def move_down(self, video_id: str) -> bool:
        """Move a video down one position.

        Thread-safe: Yes
        """
        with self._lock:
            items = list(self._queue.keys())
            try:
                current_index = items.index(video_id)
                if current_index < len(items) - 1:
                    return self.reorder(video_id, current_index + 1)
            except ValueError:
                pass
            return False

    def clear(self, keep_active: bool = True) -> List[VideoItem]:
        """Clear the queue.

        Args:
            keep_active: If True, keep currently downloading items

        Returns:
            List of removed items

        Thread-safe: Yes
        """
        removed = []
        with self._lock:
            if keep_active:
                # Keep active downloads
                to_remove = [
                    vid for vid, v in self._queue.items()
                    if not v.status.is_active()
                ]
                for video_id in to_remove:
                    removed.append(self._queue.pop(video_id))
            else:
                removed = list(self._queue.values())
                self._queue.clear()

            self._condition.notify_all()

        if self.on_queue_cleared:
            self.on_queue_cleared()

        return removed

    def clear_completed(self) -> List[VideoItem]:
        """Remove all completed downloads from queue.

        Returns:
            List of removed items

        Thread-safe: Yes
        """
        removed = []
        with self._lock:
            to_remove = [
                vid for vid, v in self._queue.items()
                if v.status == VideoStatus.COMPLETED
            ]
            for video_id in to_remove:
                removed.append(self._queue.pop(video_id))

            self._condition.notify_all()

        for video in removed:
            if self.on_item_removed:
                self.on_item_removed(video)

        return removed

    def clear_errors(self) -> List[VideoItem]:
        """Remove all errored downloads from queue.

        Returns:
            List of removed items

        Thread-safe: Yes
        """
        removed = []
        with self._lock:
            to_remove = [
                vid for vid, v in self._queue.items()
                if v.status == VideoStatus.ERROR
            ]
            for video_id in to_remove:
                removed.append(self._queue.pop(video_id))

            self._condition.notify_all()

        for video in removed:
            if self.on_item_removed:
                self.on_item_removed(video)

        return removed

    def retry_failed(self) -> List[VideoItem]:
        """Reset all failed downloads for retry.

        Returns:
            List of videos reset for retry

        Thread-safe: Yes
        """
        retried = []
        with self._lock:
            for video in self._queue.values():
                if video.can_retry():
                    video.status = VideoStatus.QUEUED
                    video.progress = 0.0
                    video.error_message = None
                    retried.append(video)

            if retried:
                self._condition.notify_all()

        for video in retried:
            if self.on_item_updated:
                self.on_item_updated(video)

        return retried

    def retry_single(self, video_id: str) -> bool:
        """Reset a single failed download for retry.

        Args:
            video_id: ID of the video to retry

        Returns:
            True if reset successfully

        Thread-safe: Yes
        """
        video = None
        with self._lock:
            if video_id not in self._queue:
                return False

            video = self._queue[video_id]
            if not video.can_retry():
                return False

            video.status = VideoStatus.QUEUED
            video.progress = 0.0
            video.error_message = None
            self._condition.notify_all()

        if video and self.on_item_updated:
            self.on_item_updated(video)

        return True

    def wait_for_item(self, timeout: Optional[float] = None) -> Optional[VideoItem]:
        """Wait for a queued item to become available.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            A VideoItem ready for download, or None if timeout

        Thread-safe: Yes
        """
        with self._condition:
            while True:
                # Check for queued item
                for video in self._queue.values():
                    if video.status == VideoStatus.QUEUED:
                        return video

                # Wait for notification
                if not self._condition.wait(timeout):
                    return None  # Timeout

    def __len__(self) -> int:
        """Get the number of items in the queue."""
        with self._lock:
            return len(self._queue)

    def __iter__(self) -> Iterator[VideoItem]:
        """Iterate over queue items."""
        with self._lock:
            return iter(list(self._queue.values()))

    def __contains__(self, video_id: str) -> bool:
        """Check if a video ID is in the queue."""
        with self._lock:
            return video_id in self._queue

    def get_statistics(self) -> dict:
        """Get queue statistics.

        Returns:
            Dictionary with queue statistics

        Thread-safe: Yes
        """
        with self._lock:
            total = len(self._queue)
            by_status = {}
            total_size = 0
            completed_size = 0

            for video in self._queue.values():
                status_name = video.status.name
                by_status[status_name] = by_status.get(status_name, 0) + 1
                total_size += video.filesize or 0
                if video.status == VideoStatus.COMPLETED:
                    completed_size += video.filesize or 0

            return {
                'total': total,
                'by_status': by_status,
                'total_size_bytes': total_size,
                'completed_size_bytes': completed_size,
                'queued': by_status.get('QUEUED', 0),
                'downloading': by_status.get('DOWNLOADING', 0),
                'completed': by_status.get('COMPLETED', 0),
                'errors': by_status.get('ERROR', 0),
            }
