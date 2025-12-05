"""Custom exceptions for YouTube Downloader."""

from .errors import (
    DownloaderException,
    URLValidationError,
    NetworkError,
    DiskSpaceError,
    AuthenticationError,
    RateLimitError,
    DownloadError,
    ConfigurationError,
    FileSystemError,
    ExtractionError,
    PostProcessingError,
)

__all__ = [
    'DownloaderException',
    'URLValidationError',
    'NetworkError',
    'DiskSpaceError',
    'AuthenticationError',
    'RateLimitError',
    'DownloadError',
    'ConfigurationError',
    'FileSystemError',
    'ExtractionError',
    'PostProcessingError',
]
