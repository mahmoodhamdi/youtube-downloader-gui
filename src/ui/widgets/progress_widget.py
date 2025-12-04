"""Progress display widget for YouTube Downloader.

Shows download progress with speed, ETA, and statistics.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from dataclasses import dataclass


@dataclass
class ProgressInfo:
    """Progress information for display."""
    current_percent: float = 0.0
    overall_percent: float = 0.0
    speed: str = "--"
    eta: str = "--"
    downloaded: str = "0 MB"
    current_title: str = "Ready to download..."
    active_downloads: int = 0
    queued_count: int = 0
    completed_count: int = 0


class ProgressWidget(ttk.Frame):
    """Widget displaying download progress.

    Features:
    - Current file progress bar
    - Overall progress bar
    - Speed and ETA display
    - Download statistics
    - Status message

    Usage:
        progress = ProgressWidget(parent)
        progress.update_progress(ProgressInfo(...))
        progress.pack(fill=tk.X)
    """

    def __init__(self, parent, **kwargs):
        """Initialize progress widget.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._build_ui()

    def _build_ui(self):
        """Build the widget UI."""
        self.columnconfigure(1, weight=1)

        # Current progress section
        current_frame = ttk.LabelFrame(self, text="Current Download", padding=10)
        current_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        current_frame.columnconfigure(1, weight=1)

        # Current progress bar
        ttk.Label(current_frame, text="Progress:").grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.current_progress = ttk.Progressbar(
            current_frame,
            mode="determinate",
            length=400
        )
        self.current_progress.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.current_percent_label = ttk.Label(current_frame, text="0%", width=6)
        self.current_percent_label.grid(row=0, column=2, sticky="e")

        # Current file name
        self.current_title_label = ttk.Label(
            current_frame,
            text="Ready to download...",
            style="Subtitle.TLabel"
        )
        self.current_title_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))

        # Statistics row
        stats_frame = ttk.Frame(current_frame)
        stats_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        self.speed_label = ttk.Label(stats_frame, text="Speed: --")
        self.speed_label.pack(side=tk.LEFT)

        ttk.Separator(stats_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=15)

        self.eta_label = ttk.Label(stats_frame, text="ETA: --")
        self.eta_label.pack(side=tk.LEFT)

        ttk.Separator(stats_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=15)

        self.downloaded_label = ttk.Label(stats_frame, text="Downloaded: 0 MB")
        self.downloaded_label.pack(side=tk.LEFT)

        # Overall progress section
        overall_frame = ttk.LabelFrame(self, text="Overall Progress", padding=10)
        overall_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        overall_frame.columnconfigure(1, weight=1)

        # Overall progress bar
        ttk.Label(overall_frame, text="Progress:").grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.overall_progress = ttk.Progressbar(
            overall_frame,
            mode="determinate",
            length=400
        )
        self.overall_progress.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        self.overall_percent_label = ttk.Label(overall_frame, text="0%", width=6)
        self.overall_percent_label.grid(row=0, column=2, sticky="e")

        # Queue statistics
        queue_stats_frame = ttk.Frame(overall_frame)
        queue_stats_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        self.active_label = ttk.Label(queue_stats_frame, text="Active: 0")
        self.active_label.pack(side=tk.LEFT)

        ttk.Separator(queue_stats_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=15)

        self.queued_label = ttk.Label(queue_stats_frame, text="Queued: 0")
        self.queued_label.pack(side=tk.LEFT)

        ttk.Separator(queue_stats_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=15)

        self.completed_label = ttk.Label(queue_stats_frame, text="Completed: 0", style="Success.TLabel")
        self.completed_label.pack(side=tk.LEFT)

    def update_progress(self, info: ProgressInfo):
        """Update progress display.

        Args:
            info: Progress information
        """
        # Current progress
        self.current_progress["value"] = info.current_percent
        self.current_percent_label.configure(text=f"{info.current_percent:.1f}%")

        # Current title (truncate if too long)
        title = info.current_title
        if len(title) > 60:
            title = title[:57] + "..."
        self.current_title_label.configure(text=title)

        # Statistics
        self.speed_label.configure(text=f"Speed: {info.speed}")
        self.eta_label.configure(text=f"ETA: {info.eta}")
        self.downloaded_label.configure(text=f"Downloaded: {info.downloaded}")

        # Overall progress
        self.overall_progress["value"] = info.overall_percent
        self.overall_percent_label.configure(text=f"{info.overall_percent:.1f}%")

        # Queue stats
        self.active_label.configure(text=f"Active: {info.active_downloads}")
        self.queued_label.configure(text=f"Queued: {info.queued_count}")
        self.completed_label.configure(text=f"Completed: {info.completed_count}")

    def set_current_progress(self, percent: float):
        """Set current progress percentage.

        Args:
            percent: Progress (0-100)
        """
        self.current_progress["value"] = percent
        self.current_percent_label.configure(text=f"{percent:.1f}%")

    def set_overall_progress(self, percent: float):
        """Set overall progress percentage.

        Args:
            percent: Progress (0-100)
        """
        self.overall_progress["value"] = percent
        self.overall_percent_label.configure(text=f"{percent:.1f}%")

    def set_status(self, message: str):
        """Set status message.

        Args:
            message: Status message
        """
        self.current_title_label.configure(text=message)

    def set_speed(self, speed: str):
        """Set speed display.

        Args:
            speed: Speed string (e.g., "5.2 MB/s")
        """
        self.speed_label.configure(text=f"Speed: {speed}")

    def set_eta(self, eta: str):
        """Set ETA display.

        Args:
            eta: ETA string (e.g., "2m 30s")
        """
        self.eta_label.configure(text=f"ETA: {eta}")

    def reset(self):
        """Reset progress to initial state."""
        self.current_progress["value"] = 0
        self.overall_progress["value"] = 0
        self.current_percent_label.configure(text="0%")
        self.overall_percent_label.configure(text="0%")
        self.current_title_label.configure(text="Ready to download...")
        self.speed_label.configure(text="Speed: --")
        self.eta_label.configure(text="ETA: --")
        self.downloaded_label.configure(text="Downloaded: 0 MB")
        self.active_label.configure(text="Active: 0")
        self.queued_label.configure(text="Queued: 0")
        self.completed_label.configure(text="Completed: 0")
