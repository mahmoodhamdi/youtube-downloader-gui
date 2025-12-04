"""Thread-safe logging system for YouTube Downloader.

This module provides a comprehensive logging system that supports:
- Thread-safe logging from multiple threads
- Multiple output destinations (console, file, GUI)
- Log levels with color coding
- Log rotation and size management
- Structured logging with timestamps
"""

import os
import sys
import threading
import logging
import queue
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Callable, List, Dict, Any
from pathlib import Path
from logging.handlers import RotatingFileHandler


class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = auto()
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

    def to_logging_level(self) -> int:
        """Convert to standard logging level."""
        mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.SUCCESS: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(self, logging.INFO)


class LogEntry:
    """Represents a single log entry.

    Attributes:
        level: Log level
        message: Log message
        timestamp: When the log was created
        source: Source module/component
        extra: Additional context data
    """

    def __init__(
        self,
        level: LogLevel,
        message: str,
        source: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        self.level = level
        self.message = message
        self.timestamp = datetime.now()
        self.source = source
        self.extra = extra or {}

    def format(self, include_source: bool = True) -> str:
        """Format the log entry as a string.

        Args:
            include_source: Whether to include the source in output

        Returns:
            Formatted log string
        """
        time_str = self.timestamp.strftime("%H:%M:%S")
        level_str = self.level.name

        if include_source and self.source:
            return f"[{time_str}] [{level_str}] [{self.source}] {self.message}"
        return f"[{time_str}] [{level_str}] {self.message}"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'level': self.level.name,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'extra': self.extra,
        }


class Logger:
    """Thread-safe logger with multiple output destinations.

    This logger supports:
    - Console output with optional colors
    - File output with rotation
    - GUI callbacks for real-time display
    - Async logging to prevent blocking

    Usage:
        logger = Logger("MyApp")
        logger.info("Application started")
        logger.error("Something went wrong", extra={'error_code': 123})
    """

    # ANSI color codes for console output
    COLORS = {
        LogLevel.DEBUG: '\033[36m',     # Cyan
        LogLevel.INFO: '\033[0m',       # Default
        LogLevel.SUCCESS: '\033[32m',   # Green
        LogLevel.WARNING: '\033[33m',   # Yellow
        LogLevel.ERROR: '\033[31m',     # Red
        LogLevel.CRITICAL: '\033[35m',  # Magenta
    }
    RESET_COLOR = '\033[0m'

    def __init__(
        self,
        name: str = "YouTubeDownloader",
        log_dir: Optional[str] = None,
        log_to_console: bool = True,
        log_to_file: bool = True,
        console_colors: bool = True,
        min_level: LogLevel = LogLevel.INFO,
        max_file_size: int = 5 * 1024 * 1024,  # 5 MB
        backup_count: int = 3
    ):
        """Initialize the logger.

        Args:
            name: Logger name
            log_dir: Directory for log files (default: ./logs)
            log_to_console: Enable console output
            log_to_file: Enable file output
            console_colors: Use colors in console output
            min_level: Minimum log level to record
            max_file_size: Maximum log file size before rotation
            backup_count: Number of backup files to keep
        """
        self.name = name
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.console_colors = console_colors and sys.stdout.isatty()
        self.min_level = min_level

        # Thread safety
        self._lock = threading.RLock()
        self._log_queue: queue.Queue = queue.Queue()
        self._gui_callbacks: List[Callable[[LogEntry], None]] = []

        # Log history (limited size)
        self._history: List[LogEntry] = []
        self._max_history = 1000

        # Setup file logging
        self._file_handler = None
        if log_to_file:
            self._setup_file_logging(log_dir, max_file_size, backup_count)

        # Start async log processing
        self._running = True
        self._log_thread = threading.Thread(target=self._process_log_queue, daemon=True)
        self._log_thread.start()

    def _setup_file_logging(
        self,
        log_dir: Optional[str],
        max_size: int,
        backup_count: int
    ):
        """Setup file logging with rotation."""
        if log_dir is None:
            log_dir = os.path.join(os.getcwd(), 'logs')

        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(
            log_dir,
            f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log"
        )

        self._file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)

    def _process_log_queue(self):
        """Process logs from queue in background thread."""
        while self._running:
            try:
                entry = self._log_queue.get(timeout=0.1)
                self._write_log(entry)
            except queue.Empty:
                continue
            except Exception:
                pass

    def _write_log(self, entry: LogEntry):
        """Write log entry to all destinations."""
        with self._lock:
            # Add to history
            self._history.append(entry)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # Console output
            if self.log_to_console:
                self._write_console(entry)

            # File output
            if self.log_to_file and self._file_handler:
                self._write_file(entry)

            # GUI callbacks
            for callback in self._gui_callbacks:
                try:
                    callback(entry)
                except Exception:
                    pass

    def _write_console(self, entry: LogEntry):
        """Write to console with optional colors."""
        formatted = entry.format()

        if self.console_colors:
            color = self.COLORS.get(entry.level, '')
            print(f"{color}{formatted}{self.RESET_COLOR}")
        else:
            print(formatted)

    def _write_file(self, entry: LogEntry):
        """Write to log file."""
        try:
            record = logging.LogRecord(
                name=self.name,
                level=entry.level.to_logging_level(),
                pathname="",
                lineno=0,
                msg=entry.format(include_source=True),
                args=(),
                exc_info=None
            )
            self._file_handler.emit(record)
        except Exception:
            pass

    def log(
        self,
        level: LogLevel,
        message: str,
        source: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Log a message.

        Args:
            level: Log level
            message: Message to log
            source: Source component
            extra: Additional context
        """
        if level.value < self.min_level.value:
            return

        entry = LogEntry(level, message, source, extra)
        self._log_queue.put(entry)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log(LogLevel.INFO, message, **kwargs)

    def success(self, message: str, **kwargs):
        """Log success message."""
        self.log(LogLevel.SUCCESS, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.log(LogLevel.CRITICAL, message, **kwargs)

    def exception(self, message: str, exc: Exception, **kwargs):
        """Log an exception with traceback.

        Args:
            message: Error message
            exc: The exception
            **kwargs: Additional context
        """
        import traceback
        tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
        full_message = f"{message}\n{''.join(tb)}"
        self.error(full_message, **kwargs)

    def add_gui_callback(self, callback: Callable[[LogEntry], None]):
        """Add a callback for GUI logging.

        Args:
            callback: Function to call with each log entry
        """
        with self._lock:
            self._gui_callbacks.append(callback)

    def remove_gui_callback(self, callback: Callable[[LogEntry], None]):
        """Remove a GUI callback.

        Args:
            callback: Callback to remove
        """
        with self._lock:
            if callback in self._gui_callbacks:
                self._gui_callbacks.remove(callback)

    def get_history(
        self,
        level: Optional[LogLevel] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """Get log history.

        Args:
            level: Filter by level (None = all)
            limit: Maximum entries to return

        Returns:
            List of log entries
        """
        with self._lock:
            if level:
                filtered = [e for e in self._history if e.level == level]
            else:
                filtered = self._history.copy()

            return filtered[-limit:]

    def clear_history(self):
        """Clear log history."""
        with self._lock:
            self._history.clear()

    def export_logs(self, filepath: str, format: str = 'txt') -> bool:
        """Export logs to file.

        Args:
            filepath: Output file path
            format: Output format ('txt' or 'json')

        Returns:
            True if export successful
        """
        try:
            with self._lock:
                if format == 'json':
                    import json
                    data = [e.to_dict() for e in self._history]
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        for entry in self._history:
                            f.write(entry.format() + '\n')

            return True
        except Exception as e:
            self.error(f"Failed to export logs: {e}")
            return False

    def set_level(self, level: LogLevel):
        """Set minimum log level.

        Args:
            level: New minimum level
        """
        self.min_level = level

    def shutdown(self):
        """Shutdown the logger and flush remaining logs."""
        self._running = False

        # Process remaining logs
        while not self._log_queue.empty():
            try:
                entry = self._log_queue.get_nowait()
                self._write_log(entry)
            except queue.Empty:
                break

        # Close file handler
        if self._file_handler:
            self._file_handler.close()


# Global logger instance
_global_logger: Optional[Logger] = None


def get_logger() -> Logger:
    """Get the global logger instance.

    Returns:
        Global Logger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger()
    return _global_logger


def set_logger(logger: Logger):
    """Set the global logger instance.

    Args:
        logger: Logger instance to use globally
    """
    global _global_logger
    _global_logger = logger
