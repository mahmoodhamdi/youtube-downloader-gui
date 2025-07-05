import json
import queue
import threading
import os
import re
import yt_dlp
import shutil  # New: For cross-platform disk space checking
from typing import List, Dict, Any
from pathlib import Path
from .config import Config
from .logger import Logger

class DownloadManager:
    """Manages the download queue and performs video downloads."""
    
    def __init__(self, config: Config, logger: Logger):
        """
        Initialize the DownloadManager with configuration and logger.

        Args:
            config (Config): Configuration object.
            logger (Logger): Logger object for logging messages.
        """
        self.config = config
        self.logger = logger
        self.download_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.video_queue: List[Dict[str, Any]] = []
        self.is_downloading = False
        self.current_download_thread = None
        self.load_queue()  # Load persisted queue

    def add_to_queue(self, url: str) -> None:
        """
        Add a URL to the download queue after extracting video info.

        Args:
            url (str): YouTube URL to download.
        """
        videos = self.extract_video_info(url)
        if videos:
            for video in videos:
                video_id = len(self.video_queue)
                video_entry = {
                    'id': video_id,
                    'url': video['url'],
                    'title': video['title'],
                    'duration': video['duration'],
                    'status': 'Queued',
                    'playlist_title': video.get('playlist_title'),
                    'playlist_index': video.get('playlist_index'),
                    'estimated_size': video.get('estimated_size', 0)  # Estimated size for disk space check
                }
                self.video_queue.append(video_entry)
                self.progress_queue.put(('video_added', video_entry))
            self.logger.log(message=f"Added {len(videos)} video(s) to queue")
            self.save_queue()  # Save queue after adding
        else:
            self.logger.log(message="Failed to extract video information", level="ERROR")

    def start_downloads(self) -> None:
        """Start downloading videos from the queue."""
        if self.is_downloading:
            self.logger.log(message="Downloads already in progress", level="WARNING")
            return
        if not os.path.exists(self.config.get("download_path")):
            self.logger.log(message="Download path does not exist", level="ERROR")
            return
        if not self.check_disk_space():
            self.logger.log(message="Insufficient disk space to start downloads", level="ERROR")
            return
        self.is_downloading = True
        self.current_download_thread = threading.Thread(target=self._download_worker, daemon=True)
        self.current_download_thread.start()

    def stop_downloads(self) -> None:
        """Stop all ongoing downloads."""
        self.is_downloading = False
        self.logger.log(message="Downloads stopped")
        self.save_queue()  # Save queue on stop

    def extract_video_info(self, url: str) -> List[Dict[str, Any]]:
        """
        Extract video information using yt-dlp.

        Args:
            url (str): YouTube URL to extract info from.

        Returns:
            List[Dict[str, Any]]: List of video info dictionaries.
        """
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:  # Playlist
                    playlist_title = info.get('title', 'Untitled Playlist')
                    return [{
                        'url': entry.get('webpage_url', url),
                        'title': entry.get('title', 'Unknown Title'),
                        'duration': self.format_duration(entry.get('duration', 0)),
                        'playlist_title': playlist_title,
                        'playlist_index': entry.get('playlist_index', 0),
                        'estimated_size': entry.get('tbr', 1000) * entry.get('duration', 300) / 8  # Estimate size (kbps * seconds / 8 = bytes)
                    } for entry in info['entries'] if entry]
                else:  # Single video
                    return [{
                        'url': url,
                        'title': info.get('title', 'Unknown Title'),
                        'duration': self.format_duration(info.get('duration', 0)),
                        'playlist_title': None,
                        'playlist_index': None,
                        'estimated_size': info.get('tbr', 1000) * info.get('duration', 300) / 8  # Estimate size
                    }]
        except Exception as e:
            self.logger.log(message=f"Error extracting info for {url}: {str(e)}", level="ERROR")
            return []

    def format_duration(self, seconds: int) -> str:
        """
        Format duration in seconds to MM:SS or HH:MM:SS.

        Args:
            seconds (int): Duration in seconds.

        Returns:
            str: Formatted duration string.
        """
        if not seconds:
            return "Unknown"
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

    def check_disk_space(self) -> bool:
        """
        Check if there is sufficient disk space for queued downloads.

        Returns:
            bool: True if sufficient space, False otherwise.
        """
        try:
            total_size = sum(video.get('estimated_size', 0) for video in self.video_queue if video['status'] == 'Queued')
            total_size_bytes = total_size * 1.2  # Add 20% buffer
            download_path = Path(self.config.get("download_path"))
            usage = shutil.disk_usage(download_path)  # Use shutil.disk_usage for cross-platform support
            free_space = usage.free
            if free_space < total_size_bytes:
                self.logger.log(message=f"Insufficient disk space: {free_space / (1024*1024):.1f} MB available, "
                                       f"{total_size_bytes / (1024*1024):.1f} MB needed", level="ERROR")
                return False
            self.logger.log(message=f"Sufficient disk space: {free_space / (1024*1024):.1f} MB available, "
                                   f"{total_size_bytes / (1024*1024):.1f} MB needed", level="INFO")
            return True
        except Exception as e:
            self.logger.log(message=f"Error checking disk space: {str(e)}", level="ERROR")
            return False

    def load_queue(self) -> None:
        """Load the download queue from a file."""
        queue_file = self.config.get("queue_file")
        try:
            if Path(queue_file).exists():
                with open(queue_file, 'r') as f:
                    saved_queue = json.load(f)
                for video in saved_queue:
                    if video['status'] in ['Queued', 'Error']:  # Only reload Queued or Error videos
                        video['id'] = len(self.video_queue)  # Reassign ID to avoid conflicts
                        self.video_queue.append(video)
                        self.progress_queue.put(('video_added', video))
                self.logger.log(message=f"Loaded {len(self.video_queue)} video(s) from queue file")
        except Exception as e:
            self.logger.log(message=f"Error loading queue: {str(e)}", level="ERROR")

    def save_queue(self) -> None:
        """Save the current download queue to a file."""
        queue_file = self.config.get("queue_file")
        try:
            active_videos = [v for v in self.video_queue if v['status'] in ['Queued', 'Error']]
            with open(queue_file, 'w') as f:
                json.dump(active_videos, f, indent=2)
            self.logger.log(message=f"Saved {len(active_videos)} video(s) to queue file")
        except Exception as e:
            self.logger.log(message=f"Error saving queue: {str(e)}", level="ERROR")

    def _download_worker(self) -> None:
        """Background worker for downloading videos."""
        active_videos = [v for v in self.video_queue if v['status'] == 'Queued']
        for video in active_videos:
            if not self.is_downloading:
                break
            retries = self.config.get("max_retries", 3)
            attempt = 0
            while attempt <= retries:
                try:
                    video['status'] = 'Downloading'
                    self.progress_queue.put(('status', video['id'], 'Downloading'))
                    self.progress_queue.put(('current_file', f"Downloading: {video['title']} (Attempt {attempt + 1}/{retries + 1})"))

                    outtmpl = self._get_output_template(video)
                    file_path = Path(outtmpl % {'title': video['title'], 'ext': 'mp4'})
                    if file_path.exists() and file_path.stat().st_size > 0:
                        self.logger.log(message=f"File already exists: {file_path}", level="INFO")
                        video['status'] = 'Completed'
                        self.progress_queue.put(('status', video['id'], 'Completed'))
                        self.progress_queue.put(('log', f"Skipped download (already exists): {video['title']}", 'SUCCESS'))
                        break

                    ydl_opts = {
                        'outtmpl': str(outtmpl),
                        'format': self._get_format_selector(),
                        'progress_hooks': [lambda d: self._progress_hook(d, video['id'])],
                    }
                    if self.config.get("include_subtitles"):
                        ydl_opts.update({
                            'writesubtitles': True,
                            'writeautomaticsub': True,
                            'subtitleslangs': self.config.get('subtitle_langs', ['en']),
                        })
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([video['url']])
                    
                    video['status'] = 'Completed'
                    self.progress_queue.put(('status', video['id'], 'Completed'))
                    self.progress_queue.put(('log', f"Successfully downloaded: {video['title']}", 'SUCCESS'))
                    break
                except Exception as e:
                    attempt += 1
                    if attempt > retries:
                        video['status'] = 'Error'
                        self.progress_queue.put(('status', video['id'], 'Error'))
                        self.progress_queue.put(('log', f"Failed to download {video['title']} after {retries} retries: {str(e)}", 'ERROR'))
                    else:
                        self.logger.log(message=f"Retrying download for {video['title']} (Attempt {attempt}/{retries}): {str(e)}", level="WARNING")
                        self.progress_queue.put(('current_file', f"Retrying: {video['title']} (Attempt {attempt + 1}/{retries + 1})"))
        self.progress_queue.put(('download_complete',))
        self.save_queue()  # Save queue after completion

    def _get_output_template(self, video: Dict[str, Any]) -> str:
        """
        Get output template for file naming based on video info.

        Args:
            video (Dict[str, Any]): Video information dictionary.

        Returns:
            str: Output template path.
        """
        if video.get('playlist_title'):
            playlist_folder = re.sub(r'[^\w\-_\. ]', '_', video['playlist_title'])
            download_dir = os.path.join(self.config.get("download_path"), playlist_folder)
            os.makedirs(download_dir, exist_ok=True)
            index = f"{video['playlist_index']:03d} - " if video.get('playlist_index') is not None else ""
            return os.path.join(download_dir, f"{index}%(title)s.%(ext)s")
        return os.path.join(self.config.get("download_path"), '%(title)s.%(ext)s')

    def _get_format_selector(self) -> str:
        """
        Get yt-dlp format selector based on quality setting.

        Returns:
            str: Format selector string.
        """
        quality = self.config.get("quality")
        format_map = {
            'best': 'best[ext=mp4]/best',
            'worst': 'worst[ext=mp4]/worst',
            '720p': 'best[height<=720][ext=mp4]/best[height<=720]',
            '480p': 'best[height<=480][ext=mp4]/best[height<=480]',
            '360p': 'best[height<=360][ext=mp4]/best[height<=360]',
            'audio_only': 'bestaudio[ext=m4a]/bestaudio'
        }
        return format_map.get(quality, 'best[ext=mp4]/best')

    def _progress_hook(self, d: Dict[str, Any], video_id: int) -> None:
        """
        Progress hook for yt-dlp to update download progress.

        Args:
            d (Dict[str, Any]): Progress data from yt-dlp.
            video_id (int): ID of the video being downloaded.
        """
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total and total > 0:
                percent = (d.get('downloaded_bytes', 0) / total) * 100
                self.progress_queue.put(('progress', percent))
                speed = f"{d.get('speed', 0)/1024/1024:.1f} MB/s" if d.get('speed') else "Unknown"
                eta = f"{d.get('eta', 0)}s" if d.get('eta') else "Unknown"
                self.progress_queue.put(('current_file', f"Downloading: {percent:.1f}% - Speed: {speed} - ETA: {eta}"))
        elif d['status'] == 'finished':
            self.progress_queue.put(('progress', 100))
            self.progress_queue.put(('current_file', f"Finished downloading: {d['filename']}"))