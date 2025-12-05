"""Playlist filter for YouTube playlists.

Provides functionality to fetch playlist info and filter videos.
"""

import threading
import re
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from datetime import datetime


@dataclass
class PlaylistVideoInfo:
    """Information about a video in a playlist.

    Attributes:
        index: Position in playlist (1-based)
        video_id: YouTube video ID
        url: Full video URL
        title: Video title
        duration: Duration in seconds
        duration_str: Formatted duration string
        upload_date: Upload date (YYYYMMDD format)
        uploader: Channel/uploader name
        view_count: Number of views
        thumbnail: Thumbnail URL
        is_available: Whether video is available
    """
    index: int
    video_id: str
    url: str
    title: str
    duration: int = 0
    duration_str: str = ""
    upload_date: str = ""
    uploader: str = ""
    view_count: int = 0
    thumbnail: str = ""
    is_available: bool = True

    def __post_init__(self):
        """Format duration string if not set."""
        if not self.duration_str and self.duration:
            hours, remainder = divmod(self.duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                self.duration_str = f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
            else:
                self.duration_str = f"{int(minutes)}:{int(seconds):02d}"

    @property
    def formatted_date(self) -> str:
        """Get formatted upload date."""
        if self.upload_date and len(self.upload_date) == 8:
            try:
                date = datetime.strptime(self.upload_date, "%Y%m%d")
                return date.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return self.upload_date or "Unknown"

    @property
    def formatted_views(self) -> str:
        """Get formatted view count."""
        if not self.view_count:
            return "Unknown"

        if self.view_count >= 1_000_000_000:
            return f"{self.view_count / 1_000_000_000:.1f}B"
        elif self.view_count >= 1_000_000:
            return f"{self.view_count / 1_000_000:.1f}M"
        elif self.view_count >= 1_000:
            return f"{self.view_count / 1_000:.1f}K"
        return str(self.view_count)


@dataclass
class PlaylistInfo:
    """Information about a YouTube playlist.

    Attributes:
        playlist_id: YouTube playlist ID
        title: Playlist title
        uploader: Channel/uploader name
        video_count: Total number of videos
        videos: List of videos in playlist
        error: Error message if fetch failed
    """
    playlist_id: str
    title: str = ""
    uploader: str = ""
    video_count: int = 0
    videos: List[PlaylistVideoInfo] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def total_duration(self) -> int:
        """Get total duration of all videos in seconds."""
        return sum(v.duration for v in self.videos if v.duration)

    @property
    def total_duration_str(self) -> str:
        """Get formatted total duration."""
        total = self.total_duration
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{int(hours)}h {int(minutes)}m"
        return f"{int(minutes)}m {int(seconds)}s"


class PlaylistFilter:
    """Fetches and filters playlist videos.

    Features:
    - Fetch playlist information
    - Filter by duration
    - Filter by date
    - Filter by index range
    - Search by title
    - Async fetching with callback

    Usage:
        filter = PlaylistFilter()
        info = filter.get_playlist_info("https://youtube.com/playlist?list=...")

        # Filter videos under 10 minutes
        short_videos = filter.filter_by_duration(info.videos, max_seconds=600)
    """

    # Regex patterns for playlist detection
    PLAYLIST_PATTERNS = [
        r'[?&]list=([a-zA-Z0-9_-]+)',
        r'youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
    ]

    def __init__(self):
        """Initialize playlist filter."""
        self._fetch_lock = threading.Lock()

    @classmethod
    def is_playlist_url(cls, url: str) -> bool:
        """Check if URL is a playlist URL.

        Args:
            url: URL to check

        Returns:
            True if URL is a playlist
        """
        for pattern in cls.PLAYLIST_PATTERNS:
            if re.search(pattern, url):
                return True
        return False

    @classmethod
    def extract_playlist_id(cls, url: str) -> Optional[str]:
        """Extract playlist ID from URL.

        Args:
            url: URL to extract from

        Returns:
            Playlist ID or None
        """
        for pattern in cls.PLAYLIST_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_playlist_info(self, url: str) -> PlaylistInfo:
        """Get playlist information.

        Args:
            url: YouTube playlist URL

        Returns:
            PlaylistInfo with video list
        """
        try:
            import yt_dlp

            playlist_id = self.extract_playlist_id(url) or ""

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',
                'skip_download': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return PlaylistInfo(
                        playlist_id=playlist_id,
                        error="Could not extract playlist information"
                    )

                videos = []
                entries = info.get('entries', [])

                for idx, entry in enumerate(entries, 1):
                    if entry is None:
                        # Private or unavailable video
                        videos.append(PlaylistVideoInfo(
                            index=idx,
                            video_id="",
                            url="",
                            title="[Unavailable Video]",
                            is_available=False
                        ))
                        continue

                    video_id = entry.get('id', '')
                    video_info = PlaylistVideoInfo(
                        index=idx,
                        video_id=video_id,
                        url=entry.get('url', f"https://www.youtube.com/watch?v={video_id}"),
                        title=entry.get('title', 'Unknown'),
                        duration=entry.get('duration', 0) or 0,
                        upload_date=entry.get('upload_date', ''),
                        uploader=entry.get('uploader', entry.get('channel', '')),
                        view_count=entry.get('view_count', 0) or 0,
                        thumbnail=entry.get('thumbnail', ''),
                        is_available=True
                    )
                    videos.append(video_info)

                return PlaylistInfo(
                    playlist_id=playlist_id,
                    title=info.get('title', 'Unknown Playlist'),
                    uploader=info.get('uploader', info.get('channel', '')),
                    video_count=len(videos),
                    videos=videos
                )

        except Exception as e:
            return PlaylistInfo(
                playlist_id=self.extract_playlist_id(url) or "",
                error=str(e)
            )

    def filter_by_duration(
        self,
        videos: List[PlaylistVideoInfo],
        min_seconds: int = 0,
        max_seconds: int = 0
    ) -> List[PlaylistVideoInfo]:
        """Filter videos by duration.

        Args:
            videos: List of videos to filter
            min_seconds: Minimum duration (0 = no minimum)
            max_seconds: Maximum duration (0 = no maximum)

        Returns:
            Filtered list of videos
        """
        filtered = []

        for video in videos:
            if not video.is_available:
                continue

            if min_seconds > 0 and video.duration < min_seconds:
                continue
            if max_seconds > 0 and video.duration > max_seconds:
                continue

            filtered.append(video)

        return filtered

    def filter_by_date(
        self,
        videos: List[PlaylistVideoInfo],
        after: Optional[str] = None,
        before: Optional[str] = None
    ) -> List[PlaylistVideoInfo]:
        """Filter videos by upload date.

        Args:
            videos: List of videos to filter
            after: Only include videos after this date (YYYYMMDD)
            before: Only include videos before this date (YYYYMMDD)

        Returns:
            Filtered list of videos
        """
        filtered = []

        for video in videos:
            if not video.is_available:
                continue

            if not video.upload_date:
                # Include videos with unknown date
                filtered.append(video)
                continue

            if after and video.upload_date < after:
                continue
            if before and video.upload_date > before:
                continue

            filtered.append(video)

        return filtered

    def filter_by_index(
        self,
        videos: List[PlaylistVideoInfo],
        start: int = 1,
        end: int = 0
    ) -> List[PlaylistVideoInfo]:
        """Filter videos by playlist index.

        Args:
            videos: List of videos to filter
            start: Start index (1-based, default 1)
            end: End index (0 = no limit)

        Returns:
            Filtered list of videos
        """
        filtered = []

        for video in videos:
            if video.index < start:
                continue
            if end > 0 and video.index > end:
                continue

            filtered.append(video)

        return filtered

    def search_by_title(
        self,
        videos: List[PlaylistVideoInfo],
        query: str,
        case_sensitive: bool = False
    ) -> List[PlaylistVideoInfo]:
        """Search videos by title.

        Args:
            videos: List of videos to search
            query: Search query
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of matching videos
        """
        if not query:
            return videos

        if not case_sensitive:
            query = query.lower()

        filtered = []
        for video in videos:
            title = video.title if case_sensitive else video.title.lower()
            if query in title:
                filtered.append(video)

        return filtered

    def get_available_videos(
        self,
        videos: List[PlaylistVideoInfo]
    ) -> List[PlaylistVideoInfo]:
        """Get only available videos.

        Args:
            videos: List of videos

        Returns:
            List of available videos
        """
        return [v for v in videos if v.is_available]

    def get_playlist_info_async(
        self,
        url: str,
        on_complete: Callable[[PlaylistInfo], None],
        on_progress: Optional[Callable[[str], None]] = None
    ) -> threading.Thread:
        """Get playlist info asynchronously.

        Args:
            url: YouTube playlist URL
            on_complete: Callback when fetch completes
            on_progress: Optional progress callback

        Returns:
            Thread running the fetch
        """
        def fetch_task():
            if on_progress:
                on_progress("Fetching playlist information...")

            result = self.get_playlist_info(url)

            if on_progress:
                if result.error:
                    on_progress(f"Error: {result.error}")
                else:
                    on_progress(f"Found {len(result.videos)} videos")

            on_complete(result)

        thread = threading.Thread(target=fetch_task, daemon=True)
        thread.start()
        return thread
