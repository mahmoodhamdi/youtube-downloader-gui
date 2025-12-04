"""Status bar widget for YouTube Downloader.

Displays application status and log messages.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from typing import Optional, List
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """Log message levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


class StatusBar(ttk.Frame):
    """Status bar with log display.

    Features:
    - Scrollable log area
    - Color-coded messages
    - Auto-scroll option
    - Log export
    - Clear functionality

    Usage:
        status = StatusBar(parent)
        status.log("Download started", LogLevel.INFO)
        status.pack(fill=tk.BOTH, expand=True)
    """

    # Color tags for different log levels
    LEVEL_COLORS = {
        LogLevel.DEBUG: "#808080",
        LogLevel.INFO: "#000000",
        LogLevel.SUCCESS: "#28a745",
        LogLevel.WARNING: "#ffc107",
        LogLevel.ERROR: "#dc3545",
    }

    def __init__(self, parent, height: int = 8, **kwargs):
        """Initialize status bar.

        Args:
            parent: Parent widget
            height: Log area height in lines
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._height = height
        self._auto_scroll = tk.BooleanVar(value=True)
        self._max_lines = 1000
        self._log_history: List[dict] = []

        self._build_ui()

    def _build_ui(self):
        """Build the widget UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Log frame
        log_frame = ttk.LabelFrame(self, text="Status Log", padding=5)
        log_frame.grid(row=0, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=self._height,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        # Configure tags for colors
        for level, color in self.LEVEL_COLORS.items():
            self.log_text.tag_configure(level.value, foreground=color)

        self.log_text.tag_configure("timestamp", foreground="#666666")

        # Control frame
        control_frame = ttk.Frame(log_frame)
        control_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))

        # Auto-scroll checkbox
        ttk.Checkbutton(
            control_frame,
            text="Auto-scroll",
            variable=self._auto_scroll
        ).pack(side=tk.LEFT)

        # Buttons
        ttk.Button(
            control_frame,
            text="Clear",
            command=self.clear
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            control_frame,
            text="Save Log",
            command=self._save_log
        ).pack(side=tk.RIGHT)

        # Status label for quick messages
        self.status_label = ttk.Label(
            self,
            text="Ready",
            style="Subtitle.TLabel"
        )
        self.status_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

    def log(self, message: str, level: LogLevel = LogLevel.INFO):
        """Add a log message.

        Args:
            message: Message to log
            level: Log level
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Store in history
        self._log_history.append({
            "timestamp": timestamp,
            "level": level.value,
            "message": message
        })

        # Format message
        formatted = f"[{timestamp}] [{level.value}] {message}\n"

        # Add to text widget
        self.log_text.configure(state=tk.NORMAL)

        # Add timestamp
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")

        # Add level and message
        self.log_text.insert(tk.END, f"[{level.value}] {message}\n", level.value)

        # Limit lines
        self._limit_lines()

        self.log_text.configure(state=tk.DISABLED)

        # Auto-scroll
        if self._auto_scroll.get():
            self.log_text.see(tk.END)

    def debug(self, message: str):
        """Log debug message."""
        self.log(message, LogLevel.DEBUG)

    def info(self, message: str):
        """Log info message."""
        self.log(message, LogLevel.INFO)

    def success(self, message: str):
        """Log success message."""
        self.log(message, LogLevel.SUCCESS)

    def warning(self, message: str):
        """Log warning message."""
        self.log(message, LogLevel.WARNING)

    def error(self, message: str):
        """Log error message."""
        self.log(message, LogLevel.ERROR)

    def set_status(self, message: str):
        """Set quick status message.

        Args:
            message: Status message
        """
        self.status_label.configure(text=message)

    def clear(self):
        """Clear the log."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self._log_history.clear()

    def _limit_lines(self):
        """Limit log to max lines."""
        line_count = int(self.log_text.index("end-1c").split(".")[0])

        if line_count > self._max_lines:
            # Delete oldest lines
            delete_to = line_count - self._max_lines
            self.log_text.delete("1.0", f"{delete_to}.0")

    def _save_log(self):
        """Save log to file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("Log files", "*.log"),
                ("All files", "*.*")
            ],
            title="Save Log"
        )

        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    for entry in self._log_history:
                        f.write(f"[{entry['timestamp']}] [{entry['level']}] {entry['message']}\n")

                self.success(f"Log saved to {filepath}")
            except Exception as e:
                self.error(f"Failed to save log: {e}")

    def get_log_text(self) -> str:
        """Get all log text.

        Returns:
            Log text content
        """
        return self.log_text.get("1.0", tk.END)

    def set_height(self, height: int):
        """Set log area height.

        Args:
            height: Height in lines
        """
        self.log_text.configure(height=height)
