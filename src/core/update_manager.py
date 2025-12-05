"""Update manager for yt-dlp auto-updates.

Handles checking for updates and updating yt-dlp automatically.
"""

import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Optional, Callable
import re


@dataclass
class UpdateInfo:
    """Information about available update."""
    current_version: str
    latest_version: str
    update_available: bool
    error: Optional[str] = None


class UpdateManager:
    """Manages yt-dlp updates.

    Features:
    - Check current installed version
    - Check for available updates from PyPI
    - Update yt-dlp using pip
    - Async update with progress callback

    Usage:
        manager = UpdateManager()
        info = manager.check_for_updates()
        if info.update_available:
            success = manager.update_ytdlp()
    """

    def __init__(self):
        """Initialize update manager."""
        self._update_lock = threading.Lock()
        self._is_updating = False

    def get_current_version(self) -> str:
        """Get the currently installed yt-dlp version.

        Returns:
            Version string (e.g., "2024.12.03") or "Unknown" if not found
        """
        try:
            import yt_dlp
            return yt_dlp.version.__version__
        except (ImportError, AttributeError):
            # Try command line as fallback
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "yt_dlp", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
        return "Unknown"

    def get_latest_version(self) -> Optional[str]:
        """Get the latest available yt-dlp version from PyPI.

        Returns:
            Latest version string or None if check failed
        """
        try:
            # Use pip index to get latest version
            result = subprocess.run(
                [sys.executable, "-m", "pip", "index", "versions", "yt-dlp"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Parse output to find latest version
                # Output format: "yt-dlp (2024.12.03)"
                match = re.search(r'yt-dlp \(([^\)]+)\)', result.stdout)
                if match:
                    return match.group(1)

            # Fallback: try pip show with upgrade check
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--dry-run", "--upgrade", "yt-dlp"],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Parse for version info
            for line in result.stdout.split('\n'):
                if 'yt-dlp' in line.lower():
                    match = re.search(r'yt-dlp-([0-9.]+)', line)
                    if match:
                        return match.group(1)

        except Exception:
            pass

        return None

    def check_for_updates(self) -> UpdateInfo:
        """Check if updates are available for yt-dlp.

        Returns:
            UpdateInfo with current version, latest version, and update status
        """
        current = self.get_current_version()
        latest = self.get_latest_version()

        if latest is None:
            return UpdateInfo(
                current_version=current,
                latest_version="Unknown",
                update_available=False,
                error="Could not check for updates. Please check your internet connection."
            )

        # Compare versions
        update_available = self._compare_versions(current, latest) < 0

        return UpdateInfo(
            current_version=current,
            latest_version=latest,
            update_available=update_available
        )

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings.

        Args:
            v1: First version string
            v2: Second version string

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        if v1 == "Unknown" or v2 == "Unknown":
            return 0

        try:
            # Split by dots and compare numerically
            parts1 = [int(x) for x in re.split(r'[.-]', v1) if x.isdigit()]
            parts2 = [int(x) for x in re.split(r'[.-]', v2) if x.isdigit()]

            # Pad shorter list
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))

            for p1, p2 in zip(parts1, parts2):
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1

            return 0
        except Exception:
            return 0

    def update_ytdlp(
        self,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> tuple[bool, str]:
        """Update yt-dlp to the latest version.

        Args:
            progress_callback: Optional callback for progress messages

        Returns:
            Tuple of (success: bool, message: str)
        """
        with self._update_lock:
            if self._is_updating:
                return False, "Update already in progress"
            self._is_updating = True

        try:
            if progress_callback:
                progress_callback("Starting yt-dlp update...")

            # Run pip upgrade
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                # Verify update
                new_version = self.get_current_version()
                if progress_callback:
                    progress_callback(f"Successfully updated to version {new_version}")
                return True, f"Successfully updated yt-dlp to version {new_version}"
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                if progress_callback:
                    progress_callback(f"Update failed: {error_msg}")
                return False, f"Update failed: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "Update timed out. Please try again."
        except Exception as e:
            return False, f"Update error: {str(e)}"
        finally:
            with self._update_lock:
                self._is_updating = False

    def update_ytdlp_async(
        self,
        on_complete: Optional[Callable[[bool, str], None]] = None,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> threading.Thread:
        """Update yt-dlp asynchronously.

        Args:
            on_complete: Callback when update completes (success, message)
            on_progress: Callback for progress messages

        Returns:
            Thread object running the update
        """
        def _update_task():
            success, message = self.update_ytdlp(progress_callback=on_progress)
            if on_complete:
                on_complete(success, message)

        thread = threading.Thread(target=_update_task, daemon=True)
        thread.start()
        return thread

    @property
    def is_updating(self) -> bool:
        """Check if an update is currently in progress."""
        return self._is_updating
