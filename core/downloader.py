# Enhanced downloader.py with improved progress feedback
import json
import queue
import threading
import os
import re
import yt_dlp
import shutil
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from .config import Config
from .logger import Logger

class ProgressTracker:
    """Tracks detailed progress information for downloads."""
    
    def __init__(self):
        self.start_time = None
        self.last_update_time = None
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.speed_samples = []
        self.max_speed_samples = 10
        self.last_downloaded = 0
        self.stalled_threshold = 5.0  # seconds
        
    def start(self, total_bytes: int = 0):
        """Start tracking progress."""
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.total_bytes = total_bytes
        self.downloaded_bytes = 0
        self.speed_samples = []
        self.last_downloaded = 0
        
    def update(self, downloaded_bytes: int, total_bytes: int = None):
        """Update progress with new download data."""
        current_time = time.time()
        
        if total_bytes:
            self.total_bytes = total_bytes
            
        self.downloaded_bytes = downloaded_bytes
        
        # Calculate speed based on time difference
        if self.last_update_time:
            time_diff = current_time - self.last_update_time
            if time_diff > 0:
                bytes_diff = downloaded_bytes - self.last_downloaded
                speed = bytes_diff / time_diff
                
                # Store speed samples for smoothing
                self.speed_samples.append(speed)
                if len(self.speed_samples) > self.max_speed_samples:
                    self.speed_samples.pop(0)
        
        self.last_update_time = current_time
        self.last_downloaded = downloaded_bytes
        
    def get_progress_percent(self) -> float:
        """Get download progress as percentage."""
        if self.total_bytes > 0:
            return (self.downloaded_bytes / self.total_bytes) * 100
        return 0.0
        
    def get_speed(self) -> float:
        """Get average download speed in bytes per second."""
        if not self.speed_samples:
            return 0.0
        return sum(self.speed_samples) / len(self.speed_samples)
        
    def get_formatted_speed(self) -> str:
        """Get formatted speed string."""
        speed = self.get_speed()
        if speed == 0:
            return "-- B/s"
        elif speed < 1024:
            return f"{speed:.1f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed/1024:.1f} KB/s"
        elif speed < 1024 * 1024 * 1024:
            return f"{speed/(1024*1024):.1f} MB/s"
        else:
            return f"{speed/(1024*1024*1024):.1f} GB/s"
            
    def get_eta(self) -> Optional[int]:
        """Get estimated time remaining in seconds."""
        if self.total_bytes == 0 or self.downloaded_bytes == 0:
            return None
            
        speed = self.get_speed()
        if speed == 0:
            return None
            
        remaining_bytes = self.total_bytes - self.downloaded_bytes
        return int(remaining_bytes / speed)
        
    def get_formatted_eta(self) -> str:
        """Get formatted ETA string."""
        eta_seconds = self.get_eta()
        if eta_seconds is None:
            return "Unknown"
            
        if eta_seconds < 60:
            return f"{eta_seconds}s"
        elif eta_seconds < 3600:
            minutes = eta_seconds // 60
            seconds = eta_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = eta_seconds // 3600
            minutes = (eta_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
            
    def get_elapsed_time(self) -> str:
        """Get elapsed time since start."""
        if not self.start_time:
            return "0s"
            
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            return f"{int(elapsed)}s"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            return f"{hours}h {minutes}m"
            
    def is_stalled(self) -> bool:
        """Check if download appears to be stalled."""
        if not self.last_update_time:
            return False
        return (time.time() - self.last_update_time) > self.stalled_threshold
        
    def get_formatted_size(self, bytes_size: int) -> str:
        """Format byte size to human readable format."""
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size/1024:.1f} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size/(1024*1024):.1f} MB"
        else:
            return f"{bytes_size/(1024*1024*1024):.1f} GB"

class DownloadManager:
    """Enhanced DownloadManager with improved progress tracking."""
    
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.download_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.video_queue: List[Dict[str, Any]] = []
        self.is_downloading = False
        self.current_download_thread = None
        self.progress_tracker = ProgressTracker()
        self.current_video_info = {}
        self.download_stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_bytes_downloaded': 0,
            'session_start_time': time.time()
        }
        self.load_queue()

    def add_to_queue(self, url: str) -> None:
        """Add a URL to the download queue after extracting video info."""
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
                    'estimated_size': video.get('estimated_size', 0),
                    'actual_size': 0,
                    'download_time': 0,
                    'retry_count': 0
                }
                self.video_queue.append(video_entry)
                self.progress_queue.put(('video_added', video_entry))
            self.logger.log(message=f"Added {len(videos)} video(s) to queue")
            self.save_queue()
        else:
            self.logger.log(message="Failed to extract video information", level="ERROR")

    def extract_video_info(self, url: str) -> List[Dict[str, Any]]:
        """Extract video information using yt-dlp with enhanced info."""
        try:
            ydl_opts = {
                'quiet': True, 
                'no_warnings': True, 
                'extract_flat': False,
                'format': self._get_format_selector()
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:  # Playlist
                    playlist_title = info.get('title', 'Untitled Playlist')
                    videos = []
                    
                    for entry in info['entries']:
                        if entry:
                            # Get more detailed size estimation
                            formats = entry.get('formats', [])
                            best_format = self._get_best_format(formats)
                            estimated_size = self._estimate_file_size(entry, best_format)
                            
                            videos.append({
                                'url': entry.get('webpage_url', url),
                                'title': entry.get('title', 'Unknown Title'),
                                'duration': self.format_duration(entry.get('duration', 0)),
                                'playlist_title': playlist_title,
                                'playlist_index': entry.get('playlist_index', 0),
                                'estimated_size': estimated_size,
                                'uploader': entry.get('uploader', 'Unknown'),
                                'upload_date': entry.get('upload_date', 'Unknown'),
                                'view_count': entry.get('view_count', 0)
                            })
                    return videos
                else:  # Single video
                    formats = info.get('formats', [])
                    best_format = self._get_best_format(formats)
                    estimated_size = self._estimate_file_size(info, best_format)
                    
                    return [{
                        'url': url,
                        'title': info.get('title', 'Unknown Title'),
                        'duration': self.format_duration(info.get('duration', 0)),
                        'playlist_title': None,
                        'playlist_index': None,
                        'estimated_size': estimated_size,
                        'uploader': info.get('uploader', 'Unknown'),
                        'upload_date': info.get('upload_date', 'Unknown'),
                        'view_count': info.get('view_count', 0)
                    }]
        except Exception as e:
            self.logger.log(message=f"Error extracting info for {url}: {str(e)}", level="ERROR")
            return []

    def _get_best_format(self, formats: List[Dict]) -> Dict:
        """Get the best format based on current quality settings."""
        if not formats:
            return {}
            
        quality = self.config.get("quality", "best")
        
        if quality == "best":
            return max(formats, key=lambda f: f.get('tbr', 0) or 0)
        elif quality == "worst":
            return min(formats, key=lambda f: f.get('tbr', 0) or float('inf'))
        else:
            # For specific quality (720p, 480p, etc.)
            height_map = {'720p': 720, '480p': 480, '360p': 360}
            target_height = height_map.get(quality, 720)
            
            # Find closest match
            suitable_formats = [f for f in formats if f.get('height', 0) <= target_height]
            if suitable_formats:
                return max(suitable_formats, key=lambda f: f.get('height', 0))
            else:
                return min(formats, key=lambda f: f.get('height', 0) or float('inf'))

    def _estimate_file_size(self, info: Dict, format_info: Dict) -> int:
        """Estimate file size more accurately."""
        # Try to get filesize from format info
        if format_info.get('filesize'):
            return format_info['filesize']
        
        # Estimate based on bitrate and duration
        duration = info.get('duration', 0)
        tbr = format_info.get('tbr') or info.get('tbr', 1000)
        
        if duration and tbr:
            # Convert kbps to bytes: (kbps * 1000 * duration) / 8
            return int((tbr * 1000 * duration) / 8)
        
        # Fallback estimation
        return 50 * 1024 * 1024  # 50MB default

    def format_duration(self, seconds: int) -> str:
        """Format duration in seconds to HH:MM:SS or MM:SS."""
        if not seconds:
            return "Unknown"
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

    def check_disk_space(self) -> bool:
        """Check if there is sufficient disk space for queued downloads."""
        try:
            total_size = sum(video.get('estimated_size', 0) for video in self.video_queue 
                           if video['status'] == 'Queued')
            total_size_bytes = total_size * 1.5  # Add 50% buffer
            
            download_path = Path(self.config.get("download_path"))
            usage = shutil.disk_usage(download_path)
            free_space = usage.free
            
            if free_space < total_size_bytes:
                self.logger.log(
                    message=f"Insufficient disk space: {self.progress_tracker.get_formatted_size(free_space)} available, "
                           f"{self.progress_tracker.get_formatted_size(int(total_size_bytes))} needed", 
                    level="ERROR"
                )
                return False
                
            self.logger.log(
                message=f"Sufficient disk space: {self.progress_tracker.get_formatted_size(free_space)} available, "
                       f"{self.progress_tracker.get_formatted_size(int(total_size_bytes))} needed"
            )
            return True
        except Exception as e:
            self.logger.log(message=f"Error checking disk space: {str(e)}", level="ERROR")
            return False

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
        self.download_stats['session_start_time'] = time.time()
        self.current_download_thread = threading.Thread(target=self._download_worker, daemon=True)
        self.current_download_thread.start()

    def stop_downloads(self) -> None:
        """Stop all ongoing downloads."""
        self.is_downloading = False
        self.logger.log(message="Downloads stopped")
        self.save_queue()

    def _download_worker(self) -> None:
        """Enhanced background worker for downloading videos."""
        active_videos = [v for v in self.video_queue if v['status'] == 'Queued']
        
        for video in active_videos:
            if not self.is_downloading:
                break
                
            self.current_video_info = video
            self.download_stats['total_downloads'] += 1
            
            retries = self.config.get("max_retries", 3)
            video['retry_count'] = 0
            
            while video['retry_count'] <= retries:
                try:
                    video['status'] = 'Downloading'
                    self.progress_queue.put(('status', video['id'], 'Downloading'))
                    
                    # Initialize progress tracker
                    self.progress_tracker.start(video.get('estimated_size', 0))
                    
                    attempt_info = f"Attempt {video['retry_count'] + 1}/{retries + 1}"
                    self.progress_queue.put(('current_file', f"Downloading: {video['title']} ({attempt_info})"))
                    
                    # Check if file already exists
                    outtmpl = self._get_output_template(video)
                    file_path = Path(outtmpl % {'title': video['title'], 'ext': 'mp4'})
                    
                    if file_path.exists() and file_path.stat().st_size > 0:
                        self.logger.log(message=f"File already exists: {file_path}", level="INFO")
                        video['status'] = 'Completed'
                        video['actual_size'] = file_path.stat().st_size
                        self.progress_queue.put(('status', video['id'], 'Completed'))
                        self.progress_queue.put(('log', f"Skipped download (already exists): {video['title']}", 'SUCCESS'))
                        self.download_stats['successful_downloads'] += 1
                        break

                    # Setup yt-dlp options
                    ydl_opts = {
                        'outtmpl': str(outtmpl),
                        'format': self._get_format_selector(),
                        'progress_hooks': [lambda d: self._enhanced_progress_hook(d, video['id'])],
                        'noplaylist': True,
                    }
                    
                    # Add subtitle options
                    if self.config.get("include_subtitles"):
                        ydl_opts.update({
                            'writesubtitles': True,
                            'writeautomaticsub': True,
                            'subtitleslangs': self.config.get('subtitle_langs', ['en']),
                        })
                    
                    # Add thumbnail and description options
                    if self.config.get("download_thumbnails"):
                        ydl_opts['writethumbnail'] = True
                    if self.config.get("download_description"):
                        ydl_opts['writedescription'] = True
                    
                    # Start download
                    download_start_time = time.time()
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([video['url']])
                    
                    # Calculate download time and update stats
                    video['download_time'] = time.time() - download_start_time
                    
                    if file_path.exists():
                        video['actual_size'] = file_path.stat().st_size
                        self.download_stats['total_bytes_downloaded'] += video['actual_size']
                    
                    video['status'] = 'Completed'
                    self.progress_queue.put(('status', video['id'], 'Completed'))
                    self.progress_queue.put(('log', f"Successfully downloaded: {video['title']}", 'SUCCESS'))
                    self.download_stats['successful_downloads'] += 1
                    break
                    
                except Exception as e:
                    video['retry_count'] += 1
                    error_msg = str(e)
                    
                    if video['retry_count'] > retries:
                        video['status'] = 'Error'
                        self.progress_queue.put(('status', video['id'], 'Error'))
                        self.progress_queue.put(('log', f"Failed to download {video['title']} after {retries} retries: {error_msg}", 'ERROR'))
                        self.download_stats['failed_downloads'] += 1
                    else:
                        retry_delay = self.config.get('retry_delay', 2)
                        self.logger.log(
                            message=f"Retrying download for {video['title']} (Attempt {video['retry_count']}/{retries}): {error_msg}", 
                            level="WARNING"
                        )
                        self.progress_queue.put(('current_file', f"Retrying in {retry_delay}s: {video['title']}"))
                        time.sleep(retry_delay)
        
        # Send completion message with statistics
        self._send_completion_stats()
        self.progress_queue.put(('download_complete',))
        self.save_queue()

    def _enhanced_progress_hook(self, d: Dict[str, Any], video_id: int) -> None:
        """Enhanced progress hook with detailed feedback."""
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            # Update progress tracker
            self.progress_tracker.update(downloaded_bytes, total_bytes)
            
            # Calculate progress percentage
            percent = self.progress_tracker.get_progress_percent()
            
            # Get speed and ETA
            speed_str = self.progress_tracker.get_formatted_speed()
            eta_str = self.progress_tracker.get_formatted_eta()
            elapsed_str = self.progress_tracker.get_elapsed_time()
            
            # Format downloaded and total sizes
            downloaded_size = self.progress_tracker.get_formatted_size(downloaded_bytes)
            total_size = self.progress_tracker.get_formatted_size(total_bytes) if total_bytes else "Unknown"
            
            # Send progress update
            self.progress_queue.put(('progress', percent))
            
            # Check for stalled download
            status_indicator = " [STALLED]" if self.progress_tracker.is_stalled() else ""
            
            # Create detailed progress message
            progress_msg = (
                f"Downloading: {percent:.1f}% ({downloaded_size}/{total_size}) | "
                f"Speed: {speed_str} | ETA: {eta_str} | Elapsed: {elapsed_str}{status_indicator}"
            )
            
            self.progress_queue.put(('current_file', progress_msg))
            
            # Send detailed progress info
            progress_info = {
                'video_id': video_id,
                'percent': percent,
                'downloaded_bytes': downloaded_bytes,
                'total_bytes': total_bytes,
                'speed': self.progress_tracker.get_speed(),
                'eta_seconds': self.progress_tracker.get_eta(),
                'elapsed_seconds': time.time() - self.progress_tracker.start_time if self.progress_tracker.start_time else 0,
                'is_stalled': self.progress_tracker.is_stalled()
            }
            self.progress_queue.put(('detailed_progress', progress_info))
            
        elif d['status'] == 'finished':
            filename = d.get('filename', 'Unknown file')
            file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
            
            self.progress_queue.put(('progress', 100))
            self.progress_queue.put(('current_file', f"Finished: {os.path.basename(filename)} ({self.progress_tracker.get_formatted_size(file_size)})"))
            
        elif d['status'] == 'error':
            self.progress_queue.put(('current_file', f"Error occurred during download"))

    def _send_completion_stats(self) -> None:
        """Send download completion statistics."""
        session_time = time.time() - self.download_stats['session_start_time']
        
        stats_msg = (
            f"Download session completed! "
            f"Total: {self.download_stats['total_downloads']} | "
            f"Successful: {self.download_stats['successful_downloads']} | "
            f"Failed: {self.download_stats['failed_downloads']} | "
            f"Downloaded: {self.progress_tracker.get_formatted_size(self.download_stats['total_bytes_downloaded'])} | "
            f"Session time: {self._format_time(session_time)}"
        )
        
        self.progress_queue.put(('log', stats_msg, 'INFO'))

    def _format_time(self, seconds: float) -> str:
        """Format time duration."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def _get_output_template(self, video: Dict[str, Any]) -> str:
        """Get output template for file naming based on video info."""
        if video.get('playlist_title') and self.config.get('create_playlist_folders', True):
            playlist_folder = re.sub(r'[^\w\-_\. ]', '_', video['playlist_title'])
            download_dir = os.path.join(self.config.get("download_path"), playlist_folder)
            os.makedirs(download_dir, exist_ok=True)
            index = f"{video['playlist_index']:03d} - " if video.get('playlist_index') is not None else ""
            return os.path.join(download_dir, f"{index}%(title)s.%(ext)s")
        return os.path.join(self.config.get("download_path"), '%(title)s.%(ext)s')

    def _get_format_selector(self) -> str:
        """Get yt-dlp format selector based on quality setting."""
        quality = self.config.get("quality", "best")
        prefer_mp4 = self.config.get("prefer_mp4", True)
        
        if prefer_mp4:
            format_map = {
                'best': 'best[ext=mp4]/best',
                'worst': 'worst[ext=mp4]/worst',
                '720p': 'best[height<=720][ext=mp4]/best[height<=720]',
                '480p': 'best[height<=480][ext=mp4]/best[height<=480]',
                '360p': 'best[height<=360][ext=mp4]/best[height<=360]',
                'audio_only': 'bestaudio[ext=m4a]/bestaudio'
            }
        else:
            format_map = {
                'best': 'best',
                'worst': 'worst',
                '720p': 'best[height<=720]',
                '480p': 'best[height<=480]',
                '360p': 'best[height<=360]',
                'audio_only': 'bestaudio'
            }
        
        return format_map.get(quality, 'best[ext=mp4]/best' if prefer_mp4 else 'best')

    def load_queue(self) -> None:
        """Load the download queue from a file."""
        queue_file = self.config.get("queue_file")
        try:
            if Path(queue_file).exists():
                with open(queue_file, 'r') as f:
                    saved_queue = json.load(f)
                for video in saved_queue:
                    if video['status'] in ['Queued', 'Error']:
                        video['id'] = len(self.video_queue)
                        # Ensure all new fields exist
                        video.setdefault('actual_size', 0)
                        video.setdefault('download_time', 0)
                        video.setdefault('retry_count', 0)
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

    def get_download_stats(self) -> Dict[str, Any]:
        """Get current download statistics."""
        return self.download_stats.copy()

    def reset_download_stats(self) -> None:
        """Reset download statistics."""
        self.download_stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_bytes_downloaded': 0,
            'session_start_time': time.time()
        }