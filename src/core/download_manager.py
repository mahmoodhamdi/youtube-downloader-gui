"""Download manager for YouTube Downloader.

This module provides the core download functionality including:
- Video information extraction
- Download execution with yt-dlp
- Progress tracking
- Concurrent download management
- Retry mechanism with exponential backoff
"""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Callable, List, Dict, Any
from pathlib import Path

import yt_dlp

from .queue_manager import QueueManager, VideoItem, VideoStatus
from src.config.validators import PathValidator
from src.exceptions import (
    DownloadError,
    NetworkError,
    AuthenticationError,
    ExtractionError,
)


class DownloadState(Enum):
    """State of the download manager."""
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()


@dataclass
class DownloadProgress:
    """Download progress information.

    Attributes:
        video_id: ID of the video being downloaded
        status: Current status
        progress: Percentage complete (0-100)
        speed: Download speed in bytes/second
        eta: Estimated time remaining in seconds
        downloaded_bytes: Bytes downloaded so far
        total_bytes: Total file size in bytes
        filename: Current filename being downloaded
    """
    video_id: str
    status: str
    progress: float = 0.0
    speed: float = 0.0
    eta: int = 0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    filename: Optional[str] = None


@dataclass
class DownloadOptions:
    """Download configuration options.

    Attributes:
        output_path: Base output directory
        quality: Video quality setting
        format_selector: Custom format selector for yt-dlp
        include_subtitles: Download subtitles
        subtitle_langs: List of subtitle languages
        embed_subtitles: Embed subtitles in video
        embed_thumbnail: Embed thumbnail as cover art
        add_metadata: Add metadata to file
        bandwidth_limit: Max bandwidth in bytes/second (0 = unlimited)
        max_retries: Maximum retry attempts
        retry_delay: Initial delay between retries in seconds
        cookies_file: Path to cookies file
        proxy: Proxy URL
    """
    output_path: str
    quality: str = "best"
    format_selector: Optional[str] = None
    include_subtitles: bool = False
    subtitle_langs: List[str] = field(default_factory=lambda: ["en"])
    embed_subtitles: bool = False
    embed_thumbnail: bool = False
    add_metadata: bool = True
    bandwidth_limit: int = 0
    max_retries: int = 3
    retry_delay: float = 2.0
    cookies_file: Optional[str] = None
    proxy: Optional[str] = None


class DownloadManager:
    """Manages video downloads with concurrent execution.

    This class handles:
    - Video information extraction
    - Download execution
    - Progress tracking
    - Concurrent download management
    - Pause/Resume/Stop functionality

    Usage:
        manager = DownloadManager(queue_manager, options, logger)
        manager.on_progress = progress_callback
        manager.start()
    """

    # Quality to format selector mapping
    QUALITY_MAP = {
        'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'worst': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst',
        '2160p': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160][ext=mp4]/best[height<=2160]',
        '1440p': 'bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440][ext=mp4]/best[height<=1440]',
        '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]',
        '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]',
        '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]',
        '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]',
        'audio_only': 'bestaudio[ext=m4a]/bestaudio/best[acodec!=none]',
    }

    def __init__(
        self,
        queue: QueueManager,
        options: DownloadOptions,
        logger=None,
        max_concurrent: int = 2
    ):
        """Initialize download manager.

        Args:
            queue: Queue manager instance
            options: Download options
            logger: Logger instance
            max_concurrent: Maximum concurrent downloads
        """
        self.queue = queue
        self.options = options
        self.logger = logger
        self.max_concurrent = max_concurrent

        # State management
        self._state = DownloadState.IDLE
        self._state_lock = threading.Lock()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._stop_event = threading.Event()

        # Thread pool
        self._executor: Optional[ThreadPoolExecutor] = None
        self._active_futures: Dict[str, Future] = {}
        self._futures_lock = threading.Lock()

        # Download tracking
        self._download_thread: Optional[threading.Thread] = None
        self._active_downloads: Dict[str, VideoItem] = {}

        # Callbacks
        self.on_progress: Optional[Callable[[DownloadProgress], None]] = None
        self.on_complete: Optional[Callable[[VideoItem, bool], None]] = None
        self.on_state_change: Optional[Callable[[DownloadState], None]] = None
        self.on_all_complete: Optional[Callable[[], None]] = None

    @property
    def state(self) -> DownloadState:
        """Get current download state."""
        with self._state_lock:
            return self._state

    def _set_state(self, new_state: DownloadState):
        """Set download state and notify callback."""
        with self._state_lock:
            if self._state != new_state:
                self._state = new_state
                if self.on_state_change:
                    try:
                        self.on_state_change(new_state)
                    except Exception:
                        pass

    def start(self):
        """Start processing downloads."""
        if self.state != DownloadState.IDLE:
            return

        self._log("Starting download manager")
        self._set_state(DownloadState.RUNNING)
        self._stop_event.clear()
        self._pause_event.set()

        # Create thread pool
        self._executor = ThreadPoolExecutor(max_workers=self.max_concurrent)

        # Start download processing thread
        self._download_thread = threading.Thread(
            target=self._download_loop,
            daemon=True
        )
        self._download_thread.start()

    def pause(self):
        """Pause all downloads."""
        if self.state != DownloadState.RUNNING:
            return

        self._log("Pausing downloads")
        self._set_state(DownloadState.PAUSED)
        self._pause_event.clear()

    def resume(self):
        """Resume paused downloads."""
        if self.state != DownloadState.PAUSED:
            return

        self._log("Resuming downloads")
        self._set_state(DownloadState.RUNNING)
        self._pause_event.set()

    def stop(self):
        """Stop all downloads."""
        if self.state == DownloadState.IDLE:
            return

        self._log("Stopping downloads")
        self._set_state(DownloadState.STOPPING)
        self._stop_event.set()
        self._pause_event.set()  # Release any paused threads

        # Cancel active futures
        with self._futures_lock:
            for future in self._active_futures.values():
                future.cancel()

        # Shutdown executor
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

        # Update queue status
        for video_id in list(self._active_downloads.keys()):
            self.queue.update_status(video_id, VideoStatus.QUEUED)

        self._active_downloads.clear()
        self._set_state(DownloadState.IDLE)

    def _download_loop(self):
        """Main download processing loop."""
        try:
            while not self._stop_event.is_set():
                # Wait if paused
                self._pause_event.wait()

                if self._stop_event.is_set():
                    break

                # Check if we can start more downloads
                with self._futures_lock:
                    active_count = len(self._active_downloads)

                if active_count >= self.max_concurrent:
                    time.sleep(0.5)
                    continue

                # Get next queued video
                video = self.queue.get_next_queued()
                if not video:
                    # Check if all downloads are complete
                    if active_count == 0:
                        time.sleep(0.5)
                        continue
                    else:
                        time.sleep(0.5)
                        continue

                # Start download
                self._start_download(video)

        except Exception as e:
            self._log(f"Download loop error: {e}", "ERROR")
        finally:
            self._set_state(DownloadState.IDLE)
            if self.on_all_complete and not self._stop_event.is_set():
                try:
                    self.on_all_complete()
                except Exception:
                    pass

    def _start_download(self, video: VideoItem):
        """Start downloading a single video."""
        self.queue.update_status(video.id, VideoStatus.DOWNLOADING)
        self._active_downloads[video.id] = video

        # Submit to thread pool
        future = self._executor.submit(self._download_video, video)

        with self._futures_lock:
            self._active_futures[video.id] = future

        # Add callback for completion
        future.add_done_callback(
            lambda f, vid=video.id: self._on_download_done(vid, f)
        )

    def _on_download_done(self, video_id: str, future: Future):
        """Handle download completion."""
        with self._futures_lock:
            self._active_futures.pop(video_id, None)

        video = self._active_downloads.pop(video_id, None)
        if not video:
            return

        try:
            result = future.result()
            success = result is True

            if success:
                self.queue.update_status(video_id, VideoStatus.COMPLETED)
                self._log(f"Download complete: {video.title}", "SUCCESS")
            else:
                self.queue.update_status(
                    video_id,
                    VideoStatus.ERROR,
                    error_message=str(result) if result else "Download failed"
                )
                self._log(f"Download failed: {video.title}", "ERROR")

            if self.on_complete:
                try:
                    self.on_complete(video, success)
                except Exception:
                    pass

        except Exception as e:
            self.queue.update_status(video_id, VideoStatus.ERROR, str(e))
            self._log(f"Download error: {video.title} - {e}", "ERROR")

    def _download_video(self, video: VideoItem) -> bool:
        """Download a single video with retry logic.

        Args:
            video: Video item to download

        Returns:
            True if successful, error message otherwise
        """
        retry_count = 0
        delay = self.options.retry_delay

        while retry_count <= self.options.max_retries:
            if self._stop_event.is_set():
                return False

            # Wait if paused
            self._pause_event.wait()

            try:
                # Build yt-dlp options
                ydl_opts = self._build_ydl_options(video)

                # Execute download
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video.url])

                return True

            except yt_dlp.utils.DownloadError as e:
                error_str = str(e).lower()

                # Check for non-retryable errors
                if any(x in error_str for x in [
                    'private video', 'video unavailable',
                    'copyright', 'removed', 'terminated'
                ]):
                    return str(e)

                retry_count += 1
                if retry_count <= self.options.max_retries:
                    self._log(
                        f"Retry {retry_count}/{self.options.max_retries} for {video.title}",
                        "WARNING"
                    )
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    return str(e)

            except Exception as e:
                retry_count += 1
                if retry_count <= self.options.max_retries:
                    self._log(
                        f"Retry {retry_count}/{self.options.max_retries} for {video.title}",
                        "WARNING"
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    return str(e)

        return "Max retries exceeded"

    def _build_ydl_options(self, video: VideoItem) -> dict:
        """Build yt-dlp options dictionary.

        Args:
            video: Video being downloaded

        Returns:
            yt-dlp options dictionary
        """
        # Determine output template
        output_template = self._get_output_template(video)

        # Get format selector
        format_selector = self.options.format_selector
        if not format_selector:
            format_selector = self.QUALITY_MAP.get(
                self.options.quality,
                self.QUALITY_MAP['best']
            )

        opts = {
            'format': format_selector,
            'outtmpl': output_template,
            'progress_hooks': [lambda d: self._progress_hook(d, video.id)],
            'ignoreerrors': False,
            'no_warnings': False,
            'quiet': True,
            'noprogress': True,
            'retries': 3,
            'fragment_retries': 3,
            'file_access_retries': 3,
            'continuedl': True,
        }

        # Bandwidth limit
        if self.options.bandwidth_limit > 0:
            opts['ratelimit'] = self.options.bandwidth_limit

        # Subtitles
        if self.options.include_subtitles:
            opts['writesubtitles'] = True
            opts['writeautomaticsub'] = True
            opts['subtitleslangs'] = self.options.subtitle_langs

        # Post-processors
        postprocessors = []

        if self.options.embed_subtitles:
            postprocessors.append({
                'key': 'FFmpegEmbedSubtitle',
            })

        if self.options.embed_thumbnail:
            postprocessors.append({
                'key': 'EmbedThumbnail',
            })
            opts['writethumbnail'] = True

        if self.options.add_metadata:
            postprocessors.append({
                'key': 'FFmpegMetadata',
            })

        if postprocessors:
            opts['postprocessors'] = postprocessors

        # Authentication
        if self.options.cookies_file and os.path.exists(self.options.cookies_file):
            opts['cookiefile'] = self.options.cookies_file

        # Proxy
        if self.options.proxy:
            opts['proxy'] = self.options.proxy

        return opts

    def _get_output_template(self, video: VideoItem) -> str:
        """Get output template for a video.

        Args:
            video: Video being downloaded

        Returns:
            Output template string
        """
        base_path = self.options.output_path

        # Handle playlist videos
        if video.playlist_title:
            playlist_folder = PathValidator.sanitize_filename(video.playlist_title)
            base_path = os.path.join(base_path, playlist_folder)
            os.makedirs(base_path, exist_ok=True)

            if video.playlist_index:
                return os.path.join(
                    base_path,
                    f"{video.playlist_index:03d} - %(title)s.%(ext)s"
                )

        return os.path.join(base_path, '%(title)s.%(ext)s')

    def _progress_hook(self, d: dict, video_id: str):
        """Progress hook for yt-dlp.

        Args:
            d: Progress dictionary from yt-dlp
            video_id: ID of video being downloaded
        """
        if self._stop_event.is_set():
            raise Exception("Download stopped by user")

        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)

            progress = 0.0
            if total > 0:
                progress = (downloaded / total) * 100

            # Update queue
            self.queue.update_progress(
                video_id,
                progress=progress,
                speed=d.get('speed', 0) or 0,
                eta=d.get('eta', 0) or 0
            )

            # Notify callback
            if self.on_progress:
                try:
                    self.on_progress(DownloadProgress(
                        video_id=video_id,
                        status='downloading',
                        progress=progress,
                        speed=d.get('speed', 0) or 0,
                        eta=d.get('eta', 0) or 0,
                        downloaded_bytes=downloaded,
                        total_bytes=total,
                        filename=d.get('filename')
                    ))
                except Exception:
                    pass

        elif d['status'] == 'finished':
            self.queue.update_progress(video_id, progress=100.0)

            if self.on_progress:
                try:
                    self.on_progress(DownloadProgress(
                        video_id=video_id,
                        status='finished',
                        progress=100.0,
                        filename=d.get('filename')
                    ))
                except Exception:
                    pass

    def extract_info(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """Extract video information from URL.

        Args:
            url: Video or playlist URL

        Returns:
            List of video info dictionaries, or None if error
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'ignoreerrors': True,
            }

            # Add authentication if available
            if self.options.cookies_file and os.path.exists(self.options.cookies_file):
                ydl_opts['cookiefile'] = self.options.cookies_file

            if self.options.proxy:
                ydl_opts['proxy'] = self.options.proxy

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return None

                videos = []

                if 'entries' in info:
                    # Playlist
                    playlist_title = info.get('title', 'Playlist')
                    for i, entry in enumerate(info['entries']):
                        if entry:
                            videos.append(self._format_video_info(
                                entry,
                                playlist_title=playlist_title,
                                playlist_index=i + 1
                            ))
                else:
                    # Single video
                    videos.append(self._format_video_info(info))

                return videos

        except Exception as e:
            self._log(f"Extraction error: {e}", "ERROR")
            return None

    def _format_video_info(
        self,
        info: dict,
        playlist_title: Optional[str] = None,
        playlist_index: Optional[int] = None
    ) -> dict:
        """Format video info from yt-dlp.

        Args:
            info: Info dictionary from yt-dlp
            playlist_title: Parent playlist title
            playlist_index: Index in playlist

        Returns:
            Formatted video info dictionary
        """
        return {
            'url': info.get('webpage_url') or info.get('url', ''),
            'title': info.get('title', 'Unknown'),
            'duration': info.get('duration', 0),
            'filesize': info.get('filesize') or info.get('filesize_approx', 0),
            'thumbnail': info.get('thumbnail'),
            'description': info.get('description', ''),
            'uploader': info.get('uploader', 'Unknown'),
            'upload_date': info.get('upload_date'),
            'view_count': info.get('view_count', 0),
            'playlist_title': playlist_title,
            'playlist_index': playlist_index,
        }

    def get_active_count(self) -> int:
        """Get number of active downloads."""
        return len(self._active_downloads)

    def is_running(self) -> bool:
        """Check if download manager is running."""
        return self.state in (DownloadState.RUNNING, DownloadState.PAUSED)

    def _log(self, message: str, level: str = "INFO"):
        """Log a message."""
        if self.logger:
            log_method = getattr(self.logger, level.lower(), self.logger.info)
            log_method(message)
