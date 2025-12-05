"""Format selector for YouTube videos.

Provides functionality to fetch and filter available video formats.
"""

import threading
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum


class FormatType(Enum):
    """Type of media format."""
    VIDEO_AUDIO = "video+audio"
    VIDEO_ONLY = "video"
    AUDIO_ONLY = "audio"


@dataclass
class FormatInfo:
    """Information about a video format.

    Attributes:
        format_id: yt-dlp format identifier
        ext: File extension (mp4, webm, etc.)
        resolution: Resolution string (e.g., "1920x1080")
        width: Video width in pixels
        height: Video height in pixels
        fps: Frames per second
        vcodec: Video codec
        acodec: Audio codec
        filesize: Estimated file size in bytes
        filesize_approx: Approximate file size if exact unknown
        tbr: Total bitrate
        vbr: Video bitrate
        abr: Audio bitrate
        format_note: Additional format information
        has_video: Whether format has video stream
        has_audio: Whether format has audio stream
    """
    format_id: str
    ext: str
    resolution: str = ""
    width: int = 0
    height: int = 0
    fps: Optional[float] = None
    vcodec: str = "none"
    acodec: str = "none"
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    tbr: Optional[float] = None
    vbr: Optional[float] = None
    abr: Optional[float] = None
    format_note: str = ""
    has_video: bool = False
    has_audio: bool = False

    @property
    def format_type(self) -> FormatType:
        """Get the type of this format."""
        if self.has_video and self.has_audio:
            return FormatType.VIDEO_AUDIO
        elif self.has_video:
            return FormatType.VIDEO_ONLY
        else:
            return FormatType.AUDIO_ONLY

    @property
    def quality_label(self) -> str:
        """Get human-readable quality label."""
        if self.has_video:
            if self.height >= 2160:
                return "4K"
            elif self.height >= 1440:
                return "2K"
            elif self.height >= 1080:
                return "1080p"
            elif self.height >= 720:
                return "720p"
            elif self.height >= 480:
                return "480p"
            elif self.height >= 360:
                return "360p"
            elif self.height > 0:
                return f"{self.height}p"
            else:
                return self.resolution or "Unknown"
        else:
            # Audio only
            if self.abr:
                return f"{int(self.abr)}kbps"
            return "Audio"

    @property
    def size_str(self) -> str:
        """Get formatted file size string."""
        size = self.filesize or self.filesize_approx
        if not size:
            return "Unknown"

        if size >= 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
        elif size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        elif size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    @property
    def bitrate_str(self) -> str:
        """Get formatted bitrate string."""
        br = self.tbr or (self.vbr or 0) + (self.abr or 0)
        if br:
            if br >= 1000:
                return f"{br / 1000:.1f} Mbps"
            return f"{int(br)} kbps"
        return "Unknown"


@dataclass
class VideoFormats:
    """Container for video information and available formats.

    Attributes:
        video_id: YouTube video ID
        title: Video title
        duration: Duration in seconds
        thumbnail: Thumbnail URL
        formats: List of available formats
        error: Error message if fetch failed
    """
    video_id: str
    title: str = ""
    duration: int = 0
    thumbnail: str = ""
    formats: List[FormatInfo] = field(default_factory=list)
    error: Optional[str] = None


class FormatSelector:
    """Fetches and filters available video formats.

    Features:
    - Fetch all available formats for a URL
    - Filter by video/audio type
    - Filter by quality
    - Sort by quality or size
    - Async fetching with callback

    Usage:
        selector = FormatSelector()
        formats = selector.get_formats("https://youtube.com/watch?v=...")

        # Filter video only formats
        video_formats = selector.filter_formats(formats.formats, video_only=True)
    """

    def __init__(self):
        """Initialize format selector."""
        self._fetch_lock = threading.Lock()

    def get_formats(self, url: str) -> VideoFormats:
        """Get available formats for a URL.

        Args:
            url: YouTube video URL

        Returns:
            VideoFormats object with available formats
        """
        try:
            import yt_dlp

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return VideoFormats(
                        video_id="",
                        error="Could not extract video information"
                    )

                formats = []
                for fmt in info.get('formats', []):
                    format_info = self._parse_format(fmt)
                    if format_info:
                        formats.append(format_info)

                return VideoFormats(
                    video_id=info.get('id', ''),
                    title=info.get('title', ''),
                    duration=info.get('duration', 0),
                    thumbnail=info.get('thumbnail', ''),
                    formats=formats
                )

        except Exception as e:
            return VideoFormats(
                video_id="",
                error=str(e)
            )

    def _parse_format(self, fmt: dict) -> Optional[FormatInfo]:
        """Parse a format dictionary from yt-dlp.

        Args:
            fmt: Format dictionary from yt-dlp

        Returns:
            FormatInfo object or None if format is invalid
        """
        format_id = fmt.get('format_id')
        if not format_id:
            return None

        vcodec = fmt.get('vcodec', 'none')
        acodec = fmt.get('acodec', 'none')

        has_video = vcodec and vcodec != 'none'
        has_audio = acodec and acodec != 'none'

        # Skip formats without any streams
        if not has_video and not has_audio:
            return None

        width = fmt.get('width') or 0
        height = fmt.get('height') or 0

        resolution = fmt.get('resolution', '')
        if not resolution and width and height:
            resolution = f"{width}x{height}"

        return FormatInfo(
            format_id=format_id,
            ext=fmt.get('ext', ''),
            resolution=resolution,
            width=width,
            height=height,
            fps=fmt.get('fps'),
            vcodec=vcodec if has_video else "none",
            acodec=acodec if has_audio else "none",
            filesize=fmt.get('filesize'),
            filesize_approx=fmt.get('filesize_approx'),
            tbr=fmt.get('tbr'),
            vbr=fmt.get('vbr'),
            abr=fmt.get('abr'),
            format_note=fmt.get('format_note', ''),
            has_video=has_video,
            has_audio=has_audio,
        )

    def filter_formats(
        self,
        formats: List[FormatInfo],
        video_only: bool = False,
        audio_only: bool = False,
        min_height: int = 0,
        max_height: int = 0,
        extensions: Optional[List[str]] = None
    ) -> List[FormatInfo]:
        """Filter formats based on criteria.

        Args:
            formats: List of formats to filter
            video_only: Only include video formats
            audio_only: Only include audio formats
            min_height: Minimum video height
            max_height: Maximum video height (0 = no limit)
            extensions: List of allowed extensions

        Returns:
            Filtered list of formats
        """
        filtered = []

        for fmt in formats:
            # Type filter
            if video_only and not fmt.has_video:
                continue
            if audio_only and not fmt.has_audio:
                continue

            # Height filter
            if min_height > 0 and fmt.height < min_height:
                continue
            if max_height > 0 and fmt.height > max_height:
                continue

            # Extension filter
            if extensions and fmt.ext not in extensions:
                continue

            filtered.append(fmt)

        return filtered

    def sort_formats(
        self,
        formats: List[FormatInfo],
        by: str = "quality",
        descending: bool = True
    ) -> List[FormatInfo]:
        """Sort formats by specified criteria.

        Args:
            formats: List of formats to sort
            by: Sort criteria ("quality", "size", "bitrate")
            descending: Sort in descending order

        Returns:
            Sorted list of formats
        """
        if by == "quality":
            key = lambda f: (f.height, f.fps or 0, f.tbr or 0)
        elif by == "size":
            key = lambda f: f.filesize or f.filesize_approx or 0
        elif by == "bitrate":
            key = lambda f: f.tbr or 0
        else:
            key = lambda f: 0

        return sorted(formats, key=key, reverse=descending)

    def get_best_format(
        self,
        formats: List[FormatInfo],
        quality: str = "best",
        prefer_audio: bool = True
    ) -> Optional[FormatInfo]:
        """Get the best format matching quality preference.

        Args:
            formats: List of available formats
            quality: Quality preset (best, 1080p, 720p, etc.)
            prefer_audio: Prefer formats with audio

        Returns:
            Best matching format or None
        """
        # Filter to formats with both video and audio if possible
        if prefer_audio:
            combined = [f for f in formats if f.has_video and f.has_audio]
            if combined:
                formats = combined

        if not formats:
            return None

        # Sort by quality
        sorted_formats = self.sort_formats(formats, by="quality", descending=True)

        if quality == "best":
            return sorted_formats[0]
        elif quality == "worst":
            return sorted_formats[-1]

        # Parse quality string (e.g., "1080p" -> 1080)
        target_height = 0
        if quality.endswith('p'):
            try:
                target_height = int(quality[:-1])
            except ValueError:
                pass

        if target_height > 0:
            # Find closest match
            best_match = None
            best_diff = float('inf')

            for fmt in sorted_formats:
                if fmt.has_video:
                    diff = abs(fmt.height - target_height)
                    if diff < best_diff:
                        best_diff = diff
                        best_match = fmt

            return best_match

        return sorted_formats[0]

    def get_formats_async(
        self,
        url: str,
        on_complete: Callable[[VideoFormats], None],
        on_progress: Optional[Callable[[str], None]] = None
    ) -> threading.Thread:
        """Get formats asynchronously.

        Args:
            url: YouTube video URL
            on_complete: Callback when fetch completes
            on_progress: Optional progress callback

        Returns:
            Thread running the fetch
        """
        def fetch_task():
            if on_progress:
                on_progress("Fetching video information...")

            result = self.get_formats(url)

            if on_progress:
                if result.error:
                    on_progress(f"Error: {result.error}")
                else:
                    on_progress(f"Found {len(result.formats)} formats")

            on_complete(result)

        thread = threading.Thread(target=fetch_task, daemon=True)
        thread.start()
        return thread
