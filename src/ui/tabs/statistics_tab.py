"""Statistics tab for YouTube Downloader.

Displays download statistics and analytics.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import os


@dataclass
class DownloadStats:
    """Statistics for downloads."""
    total_downloads: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    total_bytes_downloaded: int = 0
    total_duration_seconds: int = 0
    average_speed_bps: float = 0.0
    downloads_by_quality: Dict[str, int] = field(default_factory=dict)
    downloads_by_day: Dict[str, int] = field(default_factory=dict)
    most_downloaded_channels: Dict[str, int] = field(default_factory=dict)
    last_download_time: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'total_downloads': self.total_downloads,
            'successful_downloads': self.successful_downloads,
            'failed_downloads': self.failed_downloads,
            'total_bytes_downloaded': self.total_bytes_downloaded,
            'total_duration_seconds': self.total_duration_seconds,
            'average_speed_bps': self.average_speed_bps,
            'downloads_by_quality': self.downloads_by_quality,
            'downloads_by_day': self.downloads_by_day,
            'most_downloaded_channels': self.most_downloaded_channels,
            'last_download_time': self.last_download_time,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DownloadStats':
        """Create from dictionary."""
        return cls(
            total_downloads=data.get('total_downloads', 0),
            successful_downloads=data.get('successful_downloads', 0),
            failed_downloads=data.get('failed_downloads', 0),
            total_bytes_downloaded=data.get('total_bytes_downloaded', 0),
            total_duration_seconds=data.get('total_duration_seconds', 0),
            average_speed_bps=data.get('average_speed_bps', 0.0),
            downloads_by_quality=data.get('downloads_by_quality', {}),
            downloads_by_day=data.get('downloads_by_day', {}),
            most_downloaded_channels=data.get('most_downloaded_channels', {}),
            last_download_time=data.get('last_download_time'),
        )


class StatisticsManager:
    """Manager for download statistics.

    Handles loading, saving, and updating statistics.
    """

    def __init__(self, stats_file: str = "download_stats.json"):
        """Initialize statistics manager.

        Args:
            stats_file: Path to statistics file
        """
        self.stats_file = stats_file
        self.stats = self._load_stats()

    def _load_stats(self) -> DownloadStats:
        """Load statistics from file."""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return DownloadStats.from_dict(data)
            except Exception:
                pass
        return DownloadStats()

    def save_stats(self):
        """Save statistics to file."""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats.to_dict(), f, indent=2)
        except Exception:
            pass

    def record_download(
        self,
        success: bool,
        bytes_downloaded: int = 0,
        duration_seconds: int = 0,
        speed_bps: float = 0.0,
        quality: str = "unknown",
        channel: str = ""
    ):
        """Record a download completion.

        Args:
            success: Whether download succeeded
            bytes_downloaded: Size in bytes
            duration_seconds: Video duration in seconds
            speed_bps: Average download speed
            quality: Video quality
            channel: Channel name
        """
        self.stats.total_downloads += 1

        if success:
            self.stats.successful_downloads += 1
        else:
            self.stats.failed_downloads += 1

        self.stats.total_bytes_downloaded += bytes_downloaded
        self.stats.total_duration_seconds += duration_seconds

        # Update average speed (exponential moving average)
        if speed_bps > 0:
            if self.stats.average_speed_bps == 0:
                self.stats.average_speed_bps = speed_bps
            else:
                self.stats.average_speed_bps = (
                    0.9 * self.stats.average_speed_bps + 0.1 * speed_bps
                )

        # Update quality stats
        if quality:
            self.stats.downloads_by_quality[quality] = (
                self.stats.downloads_by_quality.get(quality, 0) + 1
            )

        # Update daily stats
        today = datetime.now().strftime("%Y-%m-%d")
        self.stats.downloads_by_day[today] = (
            self.stats.downloads_by_day.get(today, 0) + 1
        )

        # Update channel stats
        if channel:
            self.stats.most_downloaded_channels[channel] = (
                self.stats.most_downloaded_channels.get(channel, 0) + 1
            )

        self.stats.last_download_time = datetime.now().isoformat()

        self.save_stats()

    def reset_stats(self):
        """Reset all statistics."""
        self.stats = DownloadStats()
        self.save_stats()


class StatisticsTab(ttk.Frame):
    """Statistics dashboard tab.

    Features:
    - Overview cards (total, success, failed)
    - Download size and duration stats
    - Quality distribution
    - Daily download chart
    - Top channels

    Usage:
        tab = StatisticsTab(notebook, stats_manager)
    """

    def __init__(self, parent, stats_manager: Optional[StatisticsManager] = None, **kwargs):
        """Initialize statistics tab.

        Args:
            parent: Parent widget
            stats_manager: Statistics manager instance
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self.stats_manager = stats_manager or StatisticsManager()

        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        """Build the tab UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Header
        header = ttk.Frame(self, padding=15)
        header.grid(row=0, column=0, sticky="ew")

        ttk.Label(
            header,
            text="Download Statistics",
            font=("", 14, "bold")
        ).pack(side=tk.LEFT)

        ttk.Button(
            header,
            text="Refresh",
            command=self.refresh_stats
        ).pack(side=tk.RIGHT, padx=(10, 0))

        ttk.Button(
            header,
            text="Reset Stats",
            command=self._reset_stats
        ).pack(side=tk.RIGHT)

        # Main content with scrollable frame
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)

        self.content_frame = ttk.Frame(canvas)
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.columnconfigure(1, weight=1)

        self.content_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        # Build sections
        self._build_overview_cards()
        self._build_size_duration_section()
        self._build_quality_section()
        self._build_daily_section()
        self._build_channels_section()

    def _build_overview_cards(self):
        """Build overview statistics cards."""
        cards_frame = ttk.Frame(self.content_frame)
        cards_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        for i in range(4):
            cards_frame.columnconfigure(i, weight=1)

        # Total downloads card
        self._create_stat_card(cards_frame, 0, "total_card", "Total Downloads", "0", "#3498db")

        # Successful downloads card
        self._create_stat_card(cards_frame, 1, "success_card", "Successful", "0", "#2ecc71")

        # Failed downloads card
        self._create_stat_card(cards_frame, 2, "failed_card", "Failed", "0", "#e74c3c")

        # Success rate card
        self._create_stat_card(cards_frame, 3, "rate_card", "Success Rate", "0%", "#9b59b6")

    def _create_stat_card(self, parent, column: int, name: str, title: str, value: str, color: str):
        """Create a statistics card.

        Args:
            parent: Parent frame
            column: Grid column
            name: Card identifier
            title: Card title
            value: Initial value
            color: Accent color (not used directly in ttk)
        """
        card = ttk.LabelFrame(parent, text=title, padding=15)
        card.grid(row=0, column=column, sticky="nsew", padx=5)

        value_label = ttk.Label(
            card,
            text=value,
            font=("", 24, "bold")
        )
        value_label.pack()

        setattr(self, f"{name}_value", value_label)

    def _build_size_duration_section(self):
        """Build size and duration statistics section."""
        section = ttk.LabelFrame(
            self.content_frame,
            text="Data Statistics",
            padding=15
        )
        section.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        section.columnconfigure(1, weight=1)

        # Total size
        ttk.Label(section, text="Total Downloaded:").grid(row=0, column=0, sticky="w", pady=5)
        self.size_label = ttk.Label(section, text="0 B", font=("", 11, "bold"))
        self.size_label.grid(row=0, column=1, sticky="w", pady=5)

        # Total duration
        ttk.Label(section, text="Total Video Duration:").grid(row=1, column=0, sticky="w", pady=5)
        self.duration_label = ttk.Label(section, text="0h 0m", font=("", 11, "bold"))
        self.duration_label.grid(row=1, column=1, sticky="w", pady=5)

        # Average speed
        ttk.Label(section, text="Average Speed:").grid(row=2, column=0, sticky="w", pady=5)
        self.speed_label = ttk.Label(section, text="0 B/s", font=("", 11, "bold"))
        self.speed_label.grid(row=2, column=1, sticky="w", pady=5)

        # Last download
        ttk.Label(section, text="Last Download:").grid(row=3, column=0, sticky="w", pady=5)
        self.last_label = ttk.Label(section, text="Never", font=("", 11))
        self.last_label.grid(row=3, column=1, sticky="w", pady=5)

    def _build_quality_section(self):
        """Build quality distribution section."""
        section = ttk.LabelFrame(
            self.content_frame,
            text="Quality Distribution",
            padding=15
        )
        section.grid(row=1, column=1, sticky="nsew", padx=10, pady=(0, 10))
        section.columnconfigure(0, weight=1)

        self.quality_frame = ttk.Frame(section)
        self.quality_frame.pack(fill=tk.BOTH, expand=True)

    def _build_daily_section(self):
        """Build daily downloads section."""
        section = ttk.LabelFrame(
            self.content_frame,
            text="Downloads (Last 7 Days)",
            padding=15
        )
        section.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        section.columnconfigure(0, weight=1)

        self.daily_frame = ttk.Frame(section)
        self.daily_frame.pack(fill=tk.X, expand=True)

    def _build_channels_section(self):
        """Build top channels section."""
        section = ttk.LabelFrame(
            self.content_frame,
            text="Top Channels",
            padding=15
        )
        section.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        section.columnconfigure(0, weight=1)

        self.channels_frame = ttk.Frame(section)
        self.channels_frame.pack(fill=tk.X, expand=True)

    def refresh_stats(self):
        """Refresh statistics display."""
        stats = self.stats_manager.stats

        # Update overview cards
        self.total_card_value.config(text=str(stats.total_downloads))
        self.success_card_value.config(text=str(stats.successful_downloads))
        self.failed_card_value.config(text=str(stats.failed_downloads))

        rate = 0
        if stats.total_downloads > 0:
            rate = (stats.successful_downloads / stats.total_downloads) * 100
        self.rate_card_value.config(text=f"{rate:.1f}%")

        # Update size/duration
        self.size_label.config(text=self._format_size(stats.total_bytes_downloaded))
        self.duration_label.config(text=self._format_duration(stats.total_duration_seconds))
        self.speed_label.config(text=self._format_speed(stats.average_speed_bps))

        if stats.last_download_time:
            try:
                dt = datetime.fromisoformat(stats.last_download_time)
                self.last_label.config(text=dt.strftime("%Y-%m-%d %H:%M"))
            except Exception:
                self.last_label.config(text="Unknown")
        else:
            self.last_label.config(text="Never")

        # Update quality distribution
        self._update_quality_chart(stats.downloads_by_quality)

        # Update daily chart
        self._update_daily_chart(stats.downloads_by_day)

        # Update channels list
        self._update_channels_list(stats.most_downloaded_channels)

    def _format_size(self, bytes_val: int) -> str:
        """Format bytes to human-readable size."""
        if bytes_val >= 1024 ** 3:
            return f"{bytes_val / (1024 ** 3):.2f} GB"
        elif bytes_val >= 1024 ** 2:
            return f"{bytes_val / (1024 ** 2):.2f} MB"
        elif bytes_val >= 1024:
            return f"{bytes_val / 1024:.2f} KB"
        return f"{bytes_val} B"

    def _format_duration(self, seconds: int) -> str:
        """Format seconds to human-readable duration."""
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)

        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m"
        elif minutes > 0:
            return f"{int(minutes)}m {int(secs)}s"
        return f"{int(secs)}s"

    def _format_speed(self, bps: float) -> str:
        """Format bytes per second to human-readable speed."""
        if bps >= 1024 ** 2:
            return f"{bps / (1024 ** 2):.2f} MB/s"
        elif bps >= 1024:
            return f"{bps / 1024:.2f} KB/s"
        return f"{int(bps)} B/s"

    def _update_quality_chart(self, data: Dict[str, int]):
        """Update quality distribution display."""
        # Clear existing
        for widget in self.quality_frame.winfo_children():
            widget.destroy()

        if not data:
            ttk.Label(
                self.quality_frame,
                text="No data yet",
                foreground="gray"
            ).pack(pady=20)
            return

        total = sum(data.values())

        # Sort by count descending
        sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)

        for quality, count in sorted_items[:5]:
            row = ttk.Frame(self.quality_frame)
            row.pack(fill=tk.X, pady=2)

            ttk.Label(row, text=quality, width=15).pack(side=tk.LEFT)

            # Progress bar
            pct = (count / total) * 100
            progress = ttk.Progressbar(
                row,
                length=150,
                mode="determinate",
                value=pct
            )
            progress.pack(side=tk.LEFT, padx=5)

            ttk.Label(row, text=f"{count} ({pct:.1f}%)").pack(side=tk.LEFT)

    def _update_daily_chart(self, data: Dict[str, int]):
        """Update daily downloads display."""
        # Clear existing
        for widget in self.daily_frame.winfo_children():
            widget.destroy()

        # Get last 7 days
        today = datetime.now()
        days = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            days.append((day.strftime("%a"), data.get(day_str, 0)))

        if not any(count for _, count in days):
            ttk.Label(
                self.daily_frame,
                text="No downloads in the last 7 days",
                foreground="gray"
            ).pack(pady=20)
            return

        max_count = max(count for _, count in days) or 1

        chart_frame = ttk.Frame(self.daily_frame)
        chart_frame.pack(fill=tk.X, pady=10)

        for i, (day_name, count) in enumerate(days):
            col = ttk.Frame(chart_frame)
            col.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

            # Bar
            bar_height = int((count / max_count) * 80) if count > 0 else 2
            bar = tk.Canvas(col, width=30, height=100, highlightthickness=0)
            bar.pack()
            bar.create_rectangle(
                5, 100 - bar_height, 25, 100,
                fill="#3498db", outline=""
            )

            # Count label
            ttk.Label(col, text=str(count), font=("", 9)).pack()

            # Day label
            ttk.Label(col, text=day_name, foreground="gray").pack()

    def _update_channels_list(self, data: Dict[str, int]):
        """Update top channels display."""
        # Clear existing
        for widget in self.channels_frame.winfo_children():
            widget.destroy()

        if not data:
            ttk.Label(
                self.channels_frame,
                text="No data yet",
                foreground="gray"
            ).pack(pady=20)
            return

        # Sort by count descending and take top 5
        sorted_channels = sorted(data.items(), key=lambda x: x[1], reverse=True)[:5]

        for i, (channel, count) in enumerate(sorted_channels, 1):
            row = ttk.Frame(self.channels_frame)
            row.pack(fill=tk.X, pady=2)

            ttk.Label(row, text=f"{i}.", width=3).pack(side=tk.LEFT)
            ttk.Label(row, text=channel[:40] + ("..." if len(channel) > 40 else "")).pack(side=tk.LEFT)
            ttk.Label(row, text=f"({count})", foreground="gray").pack(side=tk.RIGHT)

    def _reset_stats(self):
        """Reset statistics after confirmation."""
        from tkinter import messagebox

        if messagebox.askyesno(
            "Reset Statistics",
            "Are you sure you want to reset all statistics?\nThis cannot be undone."
        ):
            self.stats_manager.reset_stats()
            self.refresh_stats()
