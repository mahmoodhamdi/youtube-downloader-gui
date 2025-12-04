"""Custom exception classes for YouTube Downloader.

This module defines a hierarchy of exceptions for better error handling
and user-friendly error messages throughout the application.
"""

from typing import Optional


class DownloaderException(Exception):
    """Base exception for all downloader errors.

    All custom exceptions in this application should inherit from this class.
    This allows catching all application-specific errors with a single except clause.

    Attributes:
        message: Human-readable error message
        details: Additional technical details for debugging
        recoverable: Whether the error can potentially be recovered from
    """

    def __init__(
        self,
        message: str,
        details: Optional[str] = None,
        recoverable: bool = True
    ):
        self.message = message
        self.details = details
        self.recoverable = recoverable
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message

    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging/serialization."""
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'details': self.details,
            'recoverable': self.recoverable,
        }


class URLValidationError(DownloaderException):
    """Raised when URL validation fails.

    Examples:
        - Invalid URL format
        - Unsupported platform
        - Malformed video/playlist ID
    """

    def __init__(self, url: str, reason: str = "Invalid URL format"):
        self.url = url
        super().__init__(
            message=f"Invalid URL: {reason}",
            details=f"URL: {url[:100]}..." if len(url) > 100 else f"URL: {url}",
            recoverable=True
        )


class NetworkError(DownloaderException):
    """Raised for network-related errors.

    Examples:
        - Connection timeout
        - DNS resolution failure
        - SSL certificate errors
        - Server unreachable
    """

    def __init__(
        self,
        message: str = "Network error occurred",
        status_code: Optional[int] = None,
        url: Optional[str] = None
    ):
        self.status_code = status_code
        self.url = url
        details = []
        if status_code:
            details.append(f"Status: {status_code}")
        if url:
            details.append(f"URL: {url[:50]}...")

        super().__init__(
            message=message,
            details=", ".join(details) if details else None,
            recoverable=True
        )


class DiskSpaceError(DownloaderException):
    """Raised when there's insufficient disk space.

    Attributes:
        required_bytes: Space needed for the operation
        available_bytes: Currently available space
        path: The path where space is needed
    """

    def __init__(
        self,
        required_bytes: int,
        available_bytes: int,
        path: str
    ):
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes
        self.path = path

        required_mb = required_bytes / (1024 * 1024)
        available_mb = available_bytes / (1024 * 1024)

        super().__init__(
            message=f"Insufficient disk space. Need {required_mb:.1f} MB, have {available_mb:.1f} MB",
            details=f"Path: {path}",
            recoverable=True
        )


class AuthenticationError(DownloaderException):
    """Raised when authentication is required or fails.

    Examples:
        - Private video requiring login
        - Age-restricted content
        - Member-only content
        - Invalid or expired cookies
    """

    def __init__(
        self,
        message: str = "Authentication required",
        auth_type: Optional[str] = None
    ):
        self.auth_type = auth_type
        super().__init__(
            message=message,
            details=f"Auth type: {auth_type}" if auth_type else None,
            recoverable=True
        )


class RateLimitError(DownloaderException):
    """Raised when rate limited by the server.

    Attributes:
        retry_after: Suggested wait time in seconds before retrying
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        self.retry_after = retry_after
        super().__init__(
            message=message,
            details=f"Retry after: {retry_after}s" if retry_after else None,
            recoverable=True
        )


class DownloadError(DownloaderException):
    """Raised when a download fails.

    This is a general error for download failures that don't fit
    into more specific categories.

    Attributes:
        video_id: The ID of the video that failed to download
        stage: The stage at which the download failed (extraction, download, post-processing)
    """

    def __init__(
        self,
        message: str,
        video_id: Optional[str] = None,
        stage: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        self.video_id = video_id
        self.stage = stage
        self.original_error = original_error

        details_parts = []
        if video_id:
            details_parts.append(f"Video ID: {video_id}")
        if stage:
            details_parts.append(f"Stage: {stage}")
        if original_error:
            details_parts.append(f"Original: {type(original_error).__name__}")

        super().__init__(
            message=message,
            details=", ".join(details_parts) if details_parts else None,
            recoverable=True
        )


class ConfigurationError(DownloaderException):
    """Raised for configuration-related errors.

    Examples:
        - Invalid configuration value
        - Missing required configuration
        - Configuration file corruption
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None
    ):
        self.config_key = config_key
        self.expected_type = expected_type

        details_parts = []
        if config_key:
            details_parts.append(f"Key: {config_key}")
        if expected_type:
            details_parts.append(f"Expected: {expected_type}")

        super().__init__(
            message=message,
            details=", ".join(details_parts) if details_parts else None,
            recoverable=True
        )


class FileSystemError(DownloaderException):
    """Raised for file system related errors.

    Examples:
        - Permission denied
        - File not found
        - Invalid path
        - File already exists
    """

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        operation: Optional[str] = None
    ):
        self.path = path
        self.operation = operation

        details_parts = []
        if path:
            details_parts.append(f"Path: {path}")
        if operation:
            details_parts.append(f"Operation: {operation}")

        super().__init__(
            message=message,
            details=", ".join(details_parts) if details_parts else None,
            recoverable=True
        )


class ExtractionError(DownloaderException):
    """Raised when video information extraction fails.

    Examples:
        - Video unavailable
        - Private video
        - Geo-restricted content
        - Invalid video ID
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        reason: Optional[str] = None
    ):
        self.url = url
        self.reason = reason

        details_parts = []
        if url:
            details_parts.append(f"URL: {url[:50]}...")
        if reason:
            details_parts.append(f"Reason: {reason}")

        super().__init__(
            message=message,
            details=", ".join(details_parts) if details_parts else None,
            recoverable=False
        )


class PostProcessingError(DownloaderException):
    """Raised when post-processing fails.

    Examples:
        - FFmpeg not found
        - Format conversion failed
        - Subtitle embedding failed
    """

    def __init__(
        self,
        message: str,
        process: Optional[str] = None,
        file_path: Optional[str] = None
    ):
        self.process = process
        self.file_path = file_path

        details_parts = []
        if process:
            details_parts.append(f"Process: {process}")
        if file_path:
            details_parts.append(f"File: {file_path}")

        super().__init__(
            message=message,
            details=", ".join(details_parts) if details_parts else None,
            recoverable=True
        )
