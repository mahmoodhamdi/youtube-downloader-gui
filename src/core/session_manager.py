"""Download session management for resume capability.

This module provides functionality to track and resume interrupted downloads.
"""

import os
import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class SessionData:
    """Data for a download session.

    Attributes:
        video_id: Unique identifier for the video
        url: Original download URL
        output_path: Target output path
        temp_file: Path to temporary/partial file
        downloaded_bytes: Bytes downloaded so far
        total_bytes: Total file size in bytes
        format_id: Selected format ID
        timestamp: When session was last updated
        status: Current status (downloading, paused, interrupted)
    """
    video_id: str
    url: str
    output_path: str
    temp_file: Optional[str] = None
    downloaded_bytes: int = 0
    total_bytes: int = 0
    format_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "downloading"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'SessionData':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class DownloadSession:
    """Track download progress for resume capability.

    This class manages download sessions, allowing interrupted downloads
    to be resumed from where they left off.

    Features:
    - Persist session data to JSON file
    - Track partial downloads with .part files
    - Thread-safe operations
    - Automatic cleanup of completed sessions

    Usage:
        session_manager = DownloadSession()

        # Save progress
        session_manager.save_session("video123", {
            'url': 'https://...',
            'output_path': '/downloads/video.mp4',
            'downloaded_bytes': 50000000,
            'total_bytes': 100000000,
        })

        # Check for resumable session
        session = session_manager.get_session("video123")
        if session:
            # Resume download
            pass

        # Remove completed session
        session_manager.remove_session("video123")
    """

    def __init__(self, session_file: str = "download_sessions.json"):
        """Initialize session manager.

        Args:
            session_file: Path to session persistence file
        """
        self.session_file = session_file
        self._lock = threading.RLock()
        self.sessions: Dict[str, SessionData] = self._load_sessions()

    def _load_sessions(self) -> Dict[str, SessionData]:
        """Load sessions from file.

        Returns:
            Dictionary of video_id -> SessionData
        """
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        vid: SessionData.from_dict(sess)
                        for vid, sess in data.items()
                    }
        except (json.JSONDecodeError, IOError, KeyError):
            pass
        return {}

    def _save_to_file(self):
        """Save sessions to file."""
        try:
            data = {
                vid: sess.to_dict()
                for vid, sess in self.sessions.items()
            }
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    def save_session(self, video_id: str, data: Dict[str, Any]):
        """Save download progress.

        Args:
            video_id: Unique video identifier
            data: Session data dictionary with keys:
                - url: Download URL
                - output_path: Target file path
                - downloaded_bytes: Bytes downloaded
                - total_bytes: Total file size
                - temp_file: Path to .part file
                - format_id: Selected format
        """
        with self._lock:
            session = SessionData(
                video_id=video_id,
                url=data.get('url', ''),
                output_path=data.get('output_path', ''),
                temp_file=data.get('temp_file'),
                downloaded_bytes=data.get('downloaded_bytes', 0),
                total_bytes=data.get('total_bytes', 0),
                format_id=data.get('format_id'),
                timestamp=datetime.now().isoformat(),
                status=data.get('status', 'downloading')
            )
            self.sessions[video_id] = session
            self._save_to_file()

    def update_progress(self, video_id: str, downloaded_bytes: int,
                       total_bytes: Optional[int] = None):
        """Update download progress for a session.

        Args:
            video_id: Video identifier
            downloaded_bytes: Current downloaded bytes
            total_bytes: Total bytes (optional update)
        """
        with self._lock:
            if video_id in self.sessions:
                session = self.sessions[video_id]
                session.downloaded_bytes = downloaded_bytes
                if total_bytes is not None:
                    session.total_bytes = total_bytes
                session.timestamp = datetime.now().isoformat()
                self._save_to_file()

    def get_session(self, video_id: str) -> Optional[SessionData]:
        """Get session data for a video.

        Args:
            video_id: Video identifier

        Returns:
            SessionData if exists, None otherwise
        """
        with self._lock:
            return self.sessions.get(video_id)

    def get_resumable_sessions(self) -> Dict[str, SessionData]:
        """Get all sessions that can be resumed.

        Returns:
            Dictionary of resumable sessions
        """
        with self._lock:
            resumable = {}
            for vid, session in self.sessions.items():
                # Check if temp file still exists
                if session.temp_file and os.path.exists(session.temp_file):
                    resumable[vid] = session
                elif session.status == 'paused':
                    resumable[vid] = session
            return resumable

    def remove_session(self, video_id: str) -> bool:
        """Remove a session.

        Args:
            video_id: Video identifier

        Returns:
            True if session was removed
        """
        with self._lock:
            if video_id in self.sessions:
                del self.sessions[video_id]
                self._save_to_file()
                return True
            return False

    def mark_completed(self, video_id: str):
        """Mark a session as completed and remove it.

        Args:
            video_id: Video identifier
        """
        self.remove_session(video_id)

    def mark_interrupted(self, video_id: str):
        """Mark a session as interrupted.

        Args:
            video_id: Video identifier
        """
        with self._lock:
            if video_id in self.sessions:
                self.sessions[video_id].status = 'interrupted'
                self._save_to_file()

    def mark_paused(self, video_id: str):
        """Mark a session as paused.

        Args:
            video_id: Video identifier
        """
        with self._lock:
            if video_id in self.sessions:
                self.sessions[video_id].status = 'paused'
                self._save_to_file()

    def cleanup_stale_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than specified age.

        Args:
            max_age_hours: Maximum session age in hours
        """
        with self._lock:
            now = datetime.now()
            stale = []

            for vid, session in self.sessions.items():
                try:
                    timestamp = datetime.fromisoformat(session.timestamp)
                    age_hours = (now - timestamp).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        stale.append(vid)
                except (ValueError, TypeError):
                    stale.append(vid)

            for vid in stale:
                del self.sessions[vid]

            if stale:
                self._save_to_file()

    def cleanup_orphaned_temp_files(self, temp_dir: Optional[str] = None):
        """Remove .part files that don't have active sessions.

        Args:
            temp_dir: Directory to search for temp files
        """
        if not temp_dir:
            return

        with self._lock:
            active_temps = {
                session.temp_file
                for session in self.sessions.values()
                if session.temp_file
            }

            try:
                for file in Path(temp_dir).glob("*.part"):
                    if str(file) not in active_temps:
                        try:
                            file.unlink()
                        except OSError:
                            pass
            except OSError:
                pass

    def get_ydl_resume_opts(self) -> dict:
        """Get yt-dlp options for resume support.

        Returns:
            Dictionary of yt-dlp options enabling resume
        """
        return {
            'continuedl': True,      # Continue partial downloads
            'nopart': False,         # Use .part files for partial downloads
            'retries': 10,           # Retry on errors
            'fragment_retries': 10,  # Retry fragments
            'skip_unavailable_fragments': True,  # Skip unavailable fragments
            'keepvideo': True,       # Keep video when extracting audio
        }

    def __len__(self) -> int:
        """Get number of active sessions."""
        with self._lock:
            return len(self.sessions)

    def __contains__(self, video_id: str) -> bool:
        """Check if session exists."""
        with self._lock:
            return video_id in self.sessions
