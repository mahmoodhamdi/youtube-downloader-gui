"""File system utilities for YouTube Downloader.

This module provides file system operations including:
- Safe file/folder creation
- File size formatting
- Disk space checking
- Path manipulation
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class DiskSpaceInfo:
    """Information about disk space.

    Attributes:
        total: Total space in bytes
        used: Used space in bytes
        free: Free space in bytes
        path: Path that was checked
    """
    total: int
    used: int
    free: int
    path: str

    @property
    def free_gb(self) -> float:
        return self.free / (1024 ** 3)

    @property
    def total_gb(self) -> float:
        return self.total / (1024 ** 3)

    @property
    def used_percent(self) -> float:
        if self.total == 0:
            return 0
        return (self.used / self.total) * 100


class FileUtils:
    """Utility class for file system operations."""

    # Size units for formatting
    SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB']

    @classmethod
    def format_size(cls, size_bytes: int) -> str:
        """Format file size in human readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 GB")
        """
        if size_bytes <= 0:
            return "0 B"

        size = float(size_bytes)
        for unit in cls.SIZE_UNITS:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024

        return f"{size:.1f} PB"

    @classmethod
    def parse_size(cls, size_str: str) -> int:
        """Parse a size string into bytes.

        Args:
            size_str: Size string (e.g., "1.5 GB", "500 MB")

        Returns:
            Size in bytes
        """
        size_str = size_str.strip().upper()

        # Extract number and unit
        number_part = ""
        unit_part = ""

        for char in size_str:
            if char.isdigit() or char == '.':
                number_part += char
            elif char.isalpha():
                unit_part += char

        if not number_part:
            return 0

        size = float(number_part)
        unit = unit_part.strip()

        # Convert to bytes
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4,
        }

        return int(size * multipliers.get(unit, 1))

    @classmethod
    def get_disk_space(cls, path: str) -> Optional[DiskSpaceInfo]:
        """Get disk space information for a path.

        Args:
            path: Path to check

        Returns:
            DiskSpaceInfo or None if error
        """
        try:
            # Resolve to existing parent if path doesn't exist
            check_path = Path(path)
            while not check_path.exists() and check_path.parent != check_path:
                check_path = check_path.parent

            if not check_path.exists():
                return None

            total, used, free = shutil.disk_usage(str(check_path))

            return DiskSpaceInfo(
                total=total,
                used=used,
                free=free,
                path=str(check_path)
            )
        except Exception:
            return None

    @classmethod
    def has_enough_space(
        cls,
        path: str,
        required_bytes: int,
        safety_margin: float = 0.1
    ) -> bool:
        """Check if there's enough disk space.

        Args:
            path: Path to check
            required_bytes: Required space in bytes
            safety_margin: Extra margin as percentage (0.1 = 10%)

        Returns:
            True if enough space available
        """
        info = cls.get_disk_space(path)
        if not info:
            return False

        required_with_margin = int(required_bytes * (1 + safety_margin))
        return info.free >= required_with_margin

    @classmethod
    def ensure_directory(cls, path: str) -> bool:
        """Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path

        Returns:
            True if directory exists or was created
        """
        try:
            os.makedirs(path, exist_ok=True)
            return os.path.isdir(path)
        except Exception:
            return False

    @classmethod
    def get_unique_path(
        cls,
        path: str,
        separator: str = " ",
        start_num: int = 1
    ) -> str:
        """Get a unique file path by adding numbers.

        Args:
            path: Desired path
            separator: Separator before number
            start_num: Starting number

        Returns:
            Unique path that doesn't exist
        """
        if not os.path.exists(path):
            return path

        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)

        counter = start_num
        while True:
            new_name = f"{name}{separator}({counter}){ext}"
            new_path = os.path.join(directory, new_name)
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    @classmethod
    def safe_delete(cls, path: str) -> bool:
        """Safely delete a file or directory.

        Args:
            path: Path to delete

        Returns:
            True if deleted successfully
        """
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            return True
        except Exception:
            return False

    @classmethod
    def get_file_hash(
        cls,
        path: str,
        algorithm: str = 'md5',
        chunk_size: int = 8192
    ) -> Optional[str]:
        """Calculate hash of a file.

        Args:
            path: File path
            algorithm: Hash algorithm (md5, sha1, sha256)
            chunk_size: Size of chunks to read

        Returns:
            Hex digest or None if error
        """
        try:
            hasher = hashlib.new(algorithm)
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(chunk_size), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    @classmethod
    def get_safe_filename(
        cls,
        filename: str,
        max_length: int = 200,
        replacement: str = '_'
    ) -> str:
        """Create a safe filename for all operating systems.

        Args:
            filename: Original filename
            max_length: Maximum length
            replacement: Replacement for invalid characters

        Returns:
            Safe filename
        """
        if not filename:
            return "untitled"

        # Characters invalid on Windows
        invalid_chars = '<>:"/\\|?*'

        # Windows reserved names
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
            'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5',
            'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        # Remove null bytes and invalid characters
        filename = filename.replace('\x00', '')
        for char in invalid_chars:
            filename = filename.replace(char, replacement)

        # Remove control characters
        filename = ''.join(c if ord(c) >= 32 else replacement for c in filename)

        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')

        # Handle empty result
        if not filename:
            return "untitled"

        # Handle reserved names
        name_part = filename.rsplit('.', 1)[0].upper()
        if name_part in reserved_names:
            filename = f"_{filename}"

        # Truncate if too long
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            max_name = max_length - len(ext)
            filename = name[:max_name] + ext

        # Clean up multiple replacements
        while replacement * 2 in filename:
            filename = filename.replace(replacement * 2, replacement)

        return filename

    @classmethod
    def open_in_explorer(cls, path: str) -> bool:
        """Open a path in the system file explorer.

        Args:
            path: Path to open

        Returns:
            True if opened successfully
        """
        try:
            if sys.platform == 'win32':
                if os.path.isfile(path):
                    # Select file in explorer
                    import subprocess
                    subprocess.run(['explorer', '/select,', path])
                else:
                    os.startfile(path)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.run(['open', path])
            else:
                import subprocess
                subprocess.run(['xdg-open', path])
            return True
        except Exception:
            return False

    @classmethod
    def get_downloads_folder(cls) -> str:
        """Get the system Downloads folder.

        Returns:
            Path to Downloads folder
        """
        if sys.platform == 'win32':
            import winreg
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
                ) as key:
                    downloads = winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
                    return downloads
            except Exception:
                pass

        # Fallback to ~/Downloads
        return str(Path.home() / "Downloads")

    @classmethod
    def clean_partial_downloads(cls, directory: str, extensions: List[str] = None) -> int:
        """Clean up partial download files.

        Args:
            directory: Directory to clean
            extensions: File extensions to look for (default: .part, .temp, .tmp)

        Returns:
            Number of files deleted
        """
        if extensions is None:
            extensions = ['.part', '.temp', '.tmp', '.ytdl', '.partial']

        deleted = 0

        try:
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    if any(filename.endswith(ext) for ext in extensions):
                        filepath = os.path.join(root, filename)
                        if cls.safe_delete(filepath):
                            deleted += 1
        except Exception:
            pass

        return deleted
