"""Centralized error handling for YouTube Downloader.

This module provides a unified error handling system that:
- Maps exceptions to user-friendly messages
- Provides recovery suggestions
- Logs errors appropriately
- Supports error callbacks for UI notifications
"""

import sys
import traceback
import threading
from typing import Optional, Callable, Dict, Type, Any, Tuple
from dataclasses import dataclass
from enum import Enum, auto

from src.exceptions import (
    DownloaderException,
    URLValidationError,
    NetworkError,
    DiskSpaceError,
    AuthenticationError,
    RateLimitError,
    DownloadError,
    ConfigurationError,
    FileSystemError,
)


class ErrorSeverity(Enum):
    """Error severity levels for UI display."""
    INFO = auto()       # Informational, no action needed
    WARNING = auto()    # Warning, operation may continue
    ERROR = auto()      # Error, operation failed but app continues
    CRITICAL = auto()   # Critical, may require app restart


@dataclass
class ErrorInfo:
    """Structured error information for handling and display.

    Attributes:
        error_type: Type of error
        message: User-friendly error message
        details: Technical details for debugging
        severity: Error severity level
        recoverable: Whether the error can be recovered from
        recovery_suggestion: Suggested action for the user
        error_code: Optional error code for reference
        original_exception: The original exception if any
    """
    error_type: str
    message: str
    details: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    recoverable: bool = True
    recovery_suggestion: Optional[str] = None
    error_code: Optional[str] = None
    original_exception: Optional[Exception] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'error_type': self.error_type,
            'message': self.message,
            'details': self.details,
            'severity': self.severity.name,
            'recoverable': self.recoverable,
            'recovery_suggestion': self.recovery_suggestion,
            'error_code': self.error_code,
        }

    def format_for_user(self) -> str:
        """Format error message for user display."""
        lines = [self.message]

        if self.recovery_suggestion:
            lines.append(f"\nSuggestion: {self.recovery_suggestion}")

        if self.error_code:
            lines.append(f"\nError Code: {self.error_code}")

        return "\n".join(lines)

    def format_for_log(self) -> str:
        """Format error message for logging."""
        lines = [
            f"[{self.error_type}] {self.message}",
        ]

        if self.details:
            lines.append(f"Details: {self.details}")

        if self.original_exception:
            lines.append(f"Exception: {type(self.original_exception).__name__}: {self.original_exception}")

        return " | ".join(lines)


class ErrorHandler:
    """Centralized error handler with user-friendly messages.

    This class provides:
    - Mapping from exceptions to user-friendly messages
    - Recovery suggestions for common errors
    - Error logging and notification callbacks
    - Thread-safe error handling

    Usage:
        handler = ErrorHandler(logger)
        error_info = handler.handle(exception)
        print(error_info.format_for_user())
    """

    # Error message mappings
    ERROR_MESSAGES: Dict[Type[Exception], Tuple[str, str, ErrorSeverity]] = {
        # (message, recovery_suggestion, severity)
        URLValidationError: (
            "The URL you entered is not valid.",
            "Please check the URL and make sure it's a valid YouTube link.",
            ErrorSeverity.WARNING
        ),
        NetworkError: (
            "A network error occurred.",
            "Please check your internet connection and try again.",
            ErrorSeverity.ERROR
        ),
        DiskSpaceError: (
            "Not enough disk space available.",
            "Free up some disk space or choose a different download location.",
            ErrorSeverity.ERROR
        ),
        AuthenticationError: (
            "Authentication is required for this content.",
            "Try importing your browser cookies or logging in.",
            ErrorSeverity.ERROR
        ),
        RateLimitError: (
            "Too many requests. YouTube has temporarily blocked access.",
            "Wait a few minutes before trying again, or use a different IP/VPN.",
            ErrorSeverity.WARNING
        ),
        DownloadError: (
            "Download failed.",
            "Try again or check if the video is still available.",
            ErrorSeverity.ERROR
        ),
        ConfigurationError: (
            "Invalid configuration detected.",
            "Check your settings and correct any invalid values.",
            ErrorSeverity.WARNING
        ),
        FileSystemError: (
            "A file system error occurred.",
            "Check file permissions and path validity.",
            ErrorSeverity.ERROR
        ),
        ConnectionRefusedError: (
            "Could not connect to the server.",
            "Check your internet connection or try again later.",
            ErrorSeverity.ERROR
        ),
        TimeoutError: (
            "The request timed out.",
            "Your internet connection may be slow. Try again.",
            ErrorSeverity.WARNING
        ),
        PermissionError: (
            "Permission denied.",
            "Check that you have write access to the download folder.",
            ErrorSeverity.ERROR
        ),
        FileNotFoundError: (
            "File or directory not found.",
            "Make sure the path exists and is accessible.",
            ErrorSeverity.ERROR
        ),
        MemoryError: (
            "System is running low on memory.",
            "Close other applications and try again.",
            ErrorSeverity.CRITICAL
        ),
        KeyboardInterrupt: (
            "Operation was cancelled.",
            None,
            ErrorSeverity.INFO
        ),
    }

    # yt-dlp specific error patterns
    YTDLP_ERROR_PATTERNS = [
        ("Video unavailable", "This video is not available.",
         "The video may have been removed or is private.",
         ErrorSeverity.ERROR),

        ("Private video", "This video is private.",
         "You need to sign in with an account that has access.",
         ErrorSeverity.ERROR),

        ("Sign in", "This content requires authentication.",
         "Import your browser cookies to access this content.",
         ErrorSeverity.ERROR),

        ("age", "This content is age-restricted.",
         "Import your browser cookies to verify your age.",
         ErrorSeverity.ERROR),

        ("copyright", "This video is blocked due to copyright.",
         "This video cannot be downloaded due to copyright restrictions.",
         ErrorSeverity.ERROR),

        ("country", "This video is not available in your country.",
         "Try using a VPN to access content from a different region.",
         ErrorSeverity.ERROR),

        ("429", "Too many requests (rate limited).",
         "Wait a few minutes before trying again.",
         ErrorSeverity.WARNING),

        ("403", "Access forbidden.",
         "The video may be restricted. Try using cookies or a VPN.",
         ErrorSeverity.ERROR),

        ("404", "Video not found.",
         "Check if the URL is correct and the video still exists.",
         ErrorSeverity.ERROR),

        ("live", "Cannot download ongoing live streams.",
         "Wait for the stream to end, then try again.",
         ErrorSeverity.WARNING),

        ("members only", "This content is for channel members only.",
         "You need to be a member of this channel to access this content.",
         ErrorSeverity.ERROR),

        ("premium", "This content requires YouTube Premium.",
         "A YouTube Premium subscription is required for this content.",
         ErrorSeverity.ERROR),
    ]

    def __init__(self, logger=None):
        """Initialize the error handler.

        Args:
            logger: Optional logger instance for error logging
        """
        self.logger = logger
        self._lock = threading.Lock()
        self._error_callbacks: list = []
        self._error_history: list = []
        self._max_history = 100

    def handle(
        self,
        error: Exception,
        context: Optional[str] = None,
        video_id: Optional[str] = None
    ) -> ErrorInfo:
        """Handle an exception and return structured error info.

        Args:
            error: The exception to handle
            context: Optional context about what was happening
            video_id: Optional video ID related to the error

        Returns:
            ErrorInfo with user-friendly error details
        """
        error_info = self._create_error_info(error, context, video_id)

        with self._lock:
            # Add to history
            self._error_history.append(error_info)
            if len(self._error_history) > self._max_history:
                self._error_history = self._error_history[-self._max_history:]

        # Log the error
        if self.logger:
            log_method = self._get_log_method(error_info.severity)
            log_method(error_info.format_for_log())

        # Notify callbacks
        for callback in self._error_callbacks:
            try:
                callback(error_info)
            except Exception:
                pass

        return error_info

    def _create_error_info(
        self,
        error: Exception,
        context: Optional[str],
        video_id: Optional[str]
    ) -> ErrorInfo:
        """Create ErrorInfo from an exception."""
        error_type = type(error).__name__

        # Check for known exception types
        for exc_type, (message, suggestion, severity) in self.ERROR_MESSAGES.items():
            if isinstance(error, exc_type):
                # Get additional details from custom exceptions
                details = None
                if isinstance(error, DownloaderException):
                    details = error.details

                return ErrorInfo(
                    error_type=error_type,
                    message=message,
                    details=details or str(error),
                    severity=severity,
                    recoverable=getattr(error, 'recoverable', True),
                    recovery_suggestion=suggestion,
                    error_code=f"E_{error_type.upper()}",
                    original_exception=error
                )

        # Check for yt-dlp error patterns in error message
        error_str = str(error).lower()
        for pattern, message, suggestion, severity in self.YTDLP_ERROR_PATTERNS:
            if pattern.lower() in error_str:
                return ErrorInfo(
                    error_type="YTDLPError",
                    message=message,
                    details=str(error),
                    severity=severity,
                    recoverable=severity != ErrorSeverity.CRITICAL,
                    recovery_suggestion=suggestion,
                    error_code=f"E_YTDLP_{pattern.upper().replace(' ', '_')}",
                    original_exception=error
                )

        # Generic error handling
        return ErrorInfo(
            error_type=error_type,
            message=f"An unexpected error occurred: {str(error)[:100]}",
            details=str(error),
            severity=ErrorSeverity.ERROR,
            recoverable=True,
            recovery_suggestion="Try again. If the problem persists, please report this issue.",
            error_code=f"E_UNKNOWN_{error_type.upper()[:20]}",
            original_exception=error
        )

    def _get_log_method(self, severity: ErrorSeverity):
        """Get the appropriate log method for severity level."""
        if not self.logger:
            return lambda x: None

        mapping = {
            ErrorSeverity.INFO: self.logger.info,
            ErrorSeverity.WARNING: self.logger.warning,
            ErrorSeverity.ERROR: self.logger.error,
            ErrorSeverity.CRITICAL: self.logger.critical,
        }
        return mapping.get(severity, self.logger.error)

    def add_callback(self, callback: Callable[[ErrorInfo], None]):
        """Add an error callback for notifications.

        Args:
            callback: Function to call when errors occur
        """
        with self._lock:
            self._error_callbacks.append(callback)

    def remove_callback(self, callback: Callable[[ErrorInfo], None]):
        """Remove an error callback.

        Args:
            callback: Callback to remove
        """
        with self._lock:
            if callback in self._error_callbacks:
                self._error_callbacks.remove(callback)

    def get_error_history(self, limit: int = 50) -> list:
        """Get recent error history.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of recent ErrorInfo objects
        """
        with self._lock:
            return self._error_history[-limit:]

    def clear_history(self):
        """Clear error history."""
        with self._lock:
            self._error_history.clear()

    @staticmethod
    def format_exception(error: Exception) -> str:
        """Format an exception with full traceback.

        Args:
            error: Exception to format

        Returns:
            Formatted exception string with traceback
        """
        return ''.join(traceback.format_exception(
            type(error), error, error.__traceback__
        ))

    def create_error_report(self) -> str:
        """Create a detailed error report for debugging.

        Returns:
            Formatted error report string
        """
        lines = [
            "=" * 50,
            "Error Report",
            "=" * 50,
            f"Generated: {datetime.now().isoformat()}",
            f"Python Version: {sys.version}",
            f"Platform: {sys.platform}",
            "",
            "Recent Errors:",
            "-" * 30,
        ]

        with self._lock:
            for i, error_info in enumerate(self._error_history[-20:], 1):
                lines.append(f"\n{i}. {error_info.error_type}")
                lines.append(f"   Message: {error_info.message}")
                if error_info.details:
                    lines.append(f"   Details: {error_info.details[:200]}")
                lines.append(f"   Severity: {error_info.severity.name}")

        lines.append("\n" + "=" * 50)
        return "\n".join(lines)


# Import datetime for error report
from datetime import datetime


# Global error handler instance
_global_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance.

    Returns:
        Global ErrorHandler instance
    """
    global _global_handler
    if _global_handler is None:
        _global_handler = ErrorHandler()
    return _global_handler


def set_error_handler(handler: ErrorHandler):
    """Set the global error handler instance.

    Args:
        handler: ErrorHandler instance to use globally
    """
    global _global_handler
    _global_handler = handler
