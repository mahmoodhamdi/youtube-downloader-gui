"""Input validation utilities for YouTube Downloader.

This module provides comprehensive validation for all user inputs including
URLs, file paths, and configuration values.
"""

import os
import re
import shutil
from typing import Tuple, Optional, List, Any, Dict
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from src.exceptions import (
    URLValidationError,
    FileSystemError,
    ConfigurationError,
)


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        is_valid: Whether validation passed
        error_message: Error message if validation failed
        sanitized_value: Cleaned/normalized value (if applicable)
        warnings: Non-fatal warnings about the input
    """
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_value: Any = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def __bool__(self) -> bool:
        return self.is_valid


class URLValidator:
    """Validator for YouTube URLs.

    Supports:
        - Video URLs (youtube.com/watch?v=, youtu.be/)
        - Playlist URLs (youtube.com/playlist?list=)
        - Channel URLs (youtube.com/channel/, youtube.com/c/, youtube.com/@)
        - Shorts URLs (youtube.com/shorts/)
        - Live URLs (youtube.com/live/)
    """

    # Video ID pattern (11 characters)
    VIDEO_ID_PATTERN = r'[a-zA-Z0-9_-]{11}'

    # Playlist ID pattern (variable length)
    PLAYLIST_ID_PATTERN = r'[a-zA-Z0-9_-]+'

    # All supported URL patterns
    URL_PATTERNS = [
        # Standard video URLs
        (r'^https?://(?:www\.)?youtube\.com/watch\?.*v=(' + VIDEO_ID_PATTERN + r')',
         'video'),

        # Short URLs
        (r'^https?://youtu\.be/(' + VIDEO_ID_PATTERN + r')',
         'video'),

        # Embedded URLs
        (r'^https?://(?:www\.)?youtube\.com/embed/(' + VIDEO_ID_PATTERN + r')',
         'video'),

        # Shorts
        (r'^https?://(?:www\.)?youtube\.com/shorts/(' + VIDEO_ID_PATTERN + r')',
         'video'),

        # Live
        (r'^https?://(?:www\.)?youtube\.com/live/(' + VIDEO_ID_PATTERN + r')',
         'video'),

        # Playlist URLs
        (r'^https?://(?:www\.)?youtube\.com/playlist\?.*list=(' + PLAYLIST_ID_PATTERN + r')',
         'playlist'),

        # Channel URLs (various formats)
        (r'^https?://(?:www\.)?youtube\.com/channel/([a-zA-Z0-9_-]+)',
         'channel'),

        (r'^https?://(?:www\.)?youtube\.com/c/([a-zA-Z0-9_-]+)',
         'channel'),

        (r'^https?://(?:www\.)?youtube\.com/@([a-zA-Z0-9_.-]+)',
         'channel'),

        # User URLs (legacy)
        (r'^https?://(?:www\.)?youtube\.com/user/([a-zA-Z0-9_-]+)',
         'channel'),
    ]

    # Compiled patterns for efficiency
    _compiled_patterns = None

    @classmethod
    def _get_patterns(cls):
        """Get compiled regex patterns (lazy initialization)."""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = [
                (re.compile(pattern, re.IGNORECASE), url_type)
                for pattern, url_type in cls.URL_PATTERNS
            ]
        return cls._compiled_patterns

    @classmethod
    def validate(cls, url: str) -> ValidationResult:
        """Validate a YouTube URL.

        Args:
            url: The URL to validate

        Returns:
            ValidationResult with validation status and details
        """
        if not url:
            return ValidationResult(
                is_valid=False,
                error_message="URL cannot be empty"
            )

        url = url.strip()

        # Basic URL structure check
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                # Try adding https://
                url = f"https://{url}"
                parsed = urlparse(url)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid URL format: {str(e)}"
            )

        # Check if it's a YouTube domain
        valid_domains = [
            'youtube.com', 'www.youtube.com',
            'youtu.be', 'www.youtu.be',
            'm.youtube.com',
            'music.youtube.com'
        ]

        if parsed.netloc.lower() not in valid_domains:
            return ValidationResult(
                is_valid=False,
                error_message=f"Not a YouTube URL. Domain: {parsed.netloc}"
            )

        # Match against patterns
        for pattern, url_type in cls._get_patterns():
            match = pattern.match(url)
            if match:
                return ValidationResult(
                    is_valid=True,
                    sanitized_value={
                        'url': url,
                        'type': url_type,
                        'id': match.group(1)
                    }
                )

        return ValidationResult(
            is_valid=False,
            error_message="URL format not recognized. Please provide a valid YouTube video, playlist, or channel URL."
        )

    @classmethod
    def extract_video_id(cls, url: str) -> Optional[str]:
        """Extract video ID from a URL.

        Args:
            url: YouTube video URL

        Returns:
            Video ID if found, None otherwise
        """
        result = cls.validate(url)
        if result.is_valid and result.sanitized_value.get('type') == 'video':
            return result.sanitized_value.get('id')
        return None

    @classmethod
    def extract_playlist_id(cls, url: str) -> Optional[str]:
        """Extract playlist ID from a URL.

        Args:
            url: YouTube playlist URL

        Returns:
            Playlist ID if found, None otherwise
        """
        result = cls.validate(url)
        if result.is_valid and result.sanitized_value.get('type') == 'playlist':
            return result.sanitized_value.get('id')

        # Also check query params for list= in video URLs
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if 'list' in query_params:
                return query_params['list'][0]
        except Exception:
            pass

        return None

    @classmethod
    def is_playlist(cls, url: str) -> bool:
        """Check if URL is a playlist."""
        result = cls.validate(url)
        if result.is_valid:
            return result.sanitized_value.get('type') == 'playlist'
        return False

    @classmethod
    def normalize_url(cls, url: str) -> Optional[str]:
        """Normalize a YouTube URL to a standard format.

        Args:
            url: The URL to normalize

        Returns:
            Normalized URL or None if invalid
        """
        result = cls.validate(url)
        if not result.is_valid:
            return None

        info = result.sanitized_value
        url_type = info.get('type')
        url_id = info.get('id')

        if url_type == 'video':
            return f"https://www.youtube.com/watch?v={url_id}"
        elif url_type == 'playlist':
            return f"https://www.youtube.com/playlist?list={url_id}"
        elif url_type == 'channel':
            # Keep original format for channels
            return info.get('url')

        return info.get('url')


class PathValidator:
    """Validator for file system paths."""

    # Windows reserved characters
    WINDOWS_RESERVED_CHARS = '<>:"/\\|?*'

    # Windows reserved names
    WINDOWS_RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
        'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5',
        'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }

    @classmethod
    def validate_directory(
        cls,
        path: str,
        check_writable: bool = True,
        check_space: bool = True,
        min_space_bytes: int = 100 * 1024 * 1024  # 100 MB
    ) -> ValidationResult:
        """Validate a directory path.

        Args:
            path: Directory path to validate
            check_writable: Whether to check write permissions
            check_space: Whether to check available disk space
            min_space_bytes: Minimum required space in bytes

        Returns:
            ValidationResult with validation status
        """
        warnings = []

        if not path:
            return ValidationResult(
                is_valid=False,
                error_message="Path cannot be empty"
            )

        path = os.path.expanduser(path)
        path = os.path.abspath(path)

        # Check if path exists
        if not os.path.exists(path):
            return ValidationResult(
                is_valid=False,
                error_message=f"Directory does not exist: {path}"
            )

        # Check if it's a directory
        if not os.path.isdir(path):
            return ValidationResult(
                is_valid=False,
                error_message=f"Path is not a directory: {path}"
            )

        # Check write permissions
        if check_writable:
            if not os.access(path, os.W_OK):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"No write permission for directory: {path}"
                )

            # Try to actually create a test file
            try:
                test_file = os.path.join(path, '.write_test_temp')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Cannot write to directory: {str(e)}"
                )

        # Check disk space
        if check_space:
            try:
                total, used, free = shutil.disk_usage(path)
                if free < min_space_bytes:
                    free_mb = free / (1024 * 1024)
                    required_mb = min_space_bytes / (1024 * 1024)
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Insufficient disk space. Available: {free_mb:.1f} MB, Required: {required_mb:.1f} MB"
                    )

                # Warn if space is low (less than 1 GB)
                if free < 1024 * 1024 * 1024:
                    warnings.append(f"Low disk space warning: {free / (1024**3):.1f} GB remaining")

            except Exception as e:
                warnings.append(f"Could not check disk space: {str(e)}")

        return ValidationResult(
            is_valid=True,
            sanitized_value=path,
            warnings=warnings
        )

    @classmethod
    def sanitize_filename(
        cls,
        filename: str,
        max_length: int = 200,
        replacement: str = '_'
    ) -> str:
        """Sanitize a filename to be safe for all operating systems.

        Args:
            filename: The filename to sanitize
            max_length: Maximum allowed length
            replacement: Character to replace invalid characters with

        Returns:
            Sanitized filename
        """
        if not filename:
            return "untitled"

        # Remove null bytes
        filename = filename.replace('\x00', '')

        # Replace invalid characters (for all OS)
        for char in cls.WINDOWS_RESERVED_CHARS:
            filename = filename.replace(char, replacement)

        # Remove control characters (0-31)
        filename = ''.join(
            c if ord(c) >= 32 else replacement
            for c in filename
        )

        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')

        # Handle empty result
        if not filename:
            return "untitled"

        # Handle Windows reserved names
        name_without_ext = filename.rsplit('.', 1)[0].upper()
        if name_without_ext in cls.WINDOWS_RESERVED_NAMES:
            filename = f"_{filename}"

        # Truncate if too long (preserve extension)
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            if ext:
                max_name_length = max_length - len(ext)
                filename = name[:max_name_length] + ext
            else:
                filename = filename[:max_length]

        # Replace multiple consecutive replacement chars
        while replacement * 2 in filename:
            filename = filename.replace(replacement * 2, replacement)

        return filename

    @classmethod
    def get_unique_path(cls, path: str) -> str:
        """Get a unique file path by adding a number suffix if needed.

        Args:
            path: The desired file path

        Returns:
            A unique path that doesn't exist
        """
        if not os.path.exists(path):
            return path

        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)

        counter = 1
        while True:
            new_filename = f"{name} ({counter}){ext}"
            new_path = os.path.join(directory, new_filename)
            if not os.path.exists(new_path):
                return new_path
            counter += 1


class ConfigValidator:
    """Validator for configuration values."""

    # Configuration schema with validation rules
    CONFIG_SCHEMA = {
        'download_path': {
            'type': str,
            'required': True,
            'validator': lambda v: PathValidator.validate_directory(v, check_space=False)
        },
        'quality': {
            'type': str,
            'required': True,
            'allowed': ['best', 'worst', '1080p', '720p', '480p', '360p', 'audio_only'],
            'default': 'best'
        },
        'max_concurrent_downloads': {
            'type': int,
            'required': False,
            'min': 1,
            'max': 10,
            'default': 2
        },
        'bandwidth_limit': {
            'type': int,
            'required': False,
            'min': 0,
            'max': 100000,  # 100 MB/s
            'default': 0
        },
        'retry_attempts': {
            'type': int,
            'required': False,
            'min': 0,
            'max': 10,
            'default': 3
        },
        'retry_delay': {
            'type': int,
            'required': False,
            'min': 1,
            'max': 60,
            'default': 5
        },
        'include_subtitles': {
            'type': bool,
            'required': False,
            'default': False
        },
        'subtitle_langs': {
            'type': list,
            'required': False,
            'default': ['en']
        },
        'auto_clear_completed': {
            'type': bool,
            'required': False,
            'default': False
        },
        'check_disk_space': {
            'type': bool,
            'required': False,
            'default': True
        },
        'min_disk_space_gb': {
            'type': float,
            'required': False,
            'min': 0.1,
            'max': 100.0,
            'default': 1.0
        },
        'proxy': {
            'type': str,
            'required': False,
            'default': ''
        },
        'theme': {
            'type': str,
            'required': False,
            'allowed': ['light', 'dark', 'system'],
            'default': 'system'
        }
    }

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> ValidationResult:
        """Validate an entire configuration dictionary.

        Args:
            config: Configuration dictionary to validate

        Returns:
            ValidationResult with validated/sanitized config
        """
        errors = []
        warnings = []
        sanitized = {}

        for key, schema in cls.CONFIG_SCHEMA.items():
            value = config.get(key)

            # Check required fields
            if schema.get('required', False) and value is None:
                errors.append(f"Missing required config: {key}")
                continue

            # Use default if not provided
            if value is None:
                sanitized[key] = schema.get('default')
                continue

            # Type validation
            expected_type = schema.get('type')
            if expected_type and not isinstance(value, expected_type):
                try:
                    value = expected_type(value)
                except (ValueError, TypeError):
                    errors.append(
                        f"Invalid type for {key}: expected {expected_type.__name__}"
                    )
                    sanitized[key] = schema.get('default')
                    continue

            # Allowed values
            allowed = schema.get('allowed')
            if allowed and value not in allowed:
                warnings.append(
                    f"Invalid value for {key}: {value}. Using default."
                )
                sanitized[key] = schema.get('default')
                continue

            # Range validation for numbers
            if isinstance(value, (int, float)):
                min_val = schema.get('min')
                max_val = schema.get('max')
                if min_val is not None and value < min_val:
                    value = min_val
                    warnings.append(f"{key} was below minimum, set to {min_val}")
                if max_val is not None and value > max_val:
                    value = max_val
                    warnings.append(f"{key} was above maximum, set to {max_val}")

            # Custom validator
            custom_validator = schema.get('validator')
            if custom_validator:
                result = custom_validator(value)
                if not result.is_valid:
                    errors.append(f"{key}: {result.error_message}")
                    continue
                if result.warnings:
                    warnings.extend(result.warnings)

            sanitized[key] = value

        # Add any extra keys from original config
        for key, value in config.items():
            if key not in cls.CONFIG_SCHEMA:
                sanitized[key] = value

        if errors:
            return ValidationResult(
                is_valid=False,
                error_message="; ".join(errors),
                sanitized_value=sanitized,
                warnings=warnings
            )

        return ValidationResult(
            is_valid=True,
            sanitized_value=sanitized,
            warnings=warnings
        )

    @classmethod
    def validate_single(
        cls,
        key: str,
        value: Any
    ) -> ValidationResult:
        """Validate a single configuration value.

        Args:
            key: Configuration key
            value: Value to validate

        Returns:
            ValidationResult
        """
        if key not in cls.CONFIG_SCHEMA:
            return ValidationResult(
                is_valid=True,
                sanitized_value=value,
                warnings=[f"Unknown config key: {key}"]
            )

        return cls.validate_config({key: value})


class InputValidator:
    """Unified input validator combining all validation types."""

    url = URLValidator
    path = PathValidator
    config = ConfigValidator

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, str]:
        """Quick URL validation returning (is_valid, error_message).

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        result = cls.url.validate(url)
        return result.is_valid, result.error_message or ""

    @classmethod
    def validate_path(cls, path: str) -> Tuple[bool, str]:
        """Quick path validation returning (is_valid, error_message).

        Args:
            path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        result = cls.path.validate_directory(path)
        return result.is_valid, result.error_message or ""

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize a filename for safe file system use.

        Args:
            filename: Filename to sanitize

        Returns:
            Sanitized filename
        """
        return cls.path.sanitize_filename(filename)
