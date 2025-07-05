import os
import queue
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import subprocess
import sys
import re
from typing import List, Dict, Any
from core.config import Config
from core.logger import Logger
from core.downloader import DownloadManager

class YouTubeDownloaderGUI:
    """Enhanced GUI for YouTube Downloader with detailed progress feedback."""
    
    def __init__(self, root: tk.Tk):
        """
        Initialize the GUI with a Tkinter root window.

        Args:
            root (tk.Tk): Tkinter root window.
        """
        self.root = root
        self.root.title("YouTube Downloader Pro")
        self.root.minsize(800, 600)
        
        self.config = Config("downloader_config.json")
        self.status_text = scrolledtext.ScrolledText(self.root, height=8, wrap=tk.WORD)
        self.logger = Logger(self.status_text, log_file="downloader.log")
        self.download_manager = DownloadManager(self.config, self.logger)
        self.video_queue: List[Dict[str, Any]] = []
        
        self.setup_gui()
        self.setup_styles()
        self.root.after(100, self.check_progress_queue)
        self.logger.log(message="YouTube Downloader Pro initialized. Ready to download videos!")

    def setup_styles(self) -> None:
        """Setup custom styles for the application."""
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Arial", 12, "bold"))
        style.configure("Status.TLabel", font=("Arial", 9))
        style.configure("Success.TLabel", foreground="green")
        style.configure("Error.TLabel", foreground="red")
        style.configure("Stalled.TLabel", foreground="orange")

    def setup_gui(self) -> None:
        """Setup the main GUI layout with enhanced sections."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        ttk.Label(main_frame, text="YouTube Downloader Pro", style="Title.TLabel").grid(row=0, column=0, columnspan=3, pady=(0, 20))
        self.setup_url_section(main_frame, 1)
        self.setup_settings_section(main_frame, 2)
        self.setup_queue_section(main_frame, 3)
        self.setup_progress_section(main_frame, 4)
        self.setup_control_buttons(main_frame, 5)
        self.setup_stats_section(main_frame, 6)
        self.setup_status_section(main_frame, 7)
        
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(7, weight=1)

    def setup_url_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup URL input section."""
        url_frame = ttk.LabelFrame(parent, text="Video URLs", padding="10")
        url_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(1, weight=1)
        
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.url_entry.bind('<Return>', lambda e: self.add_to_queue())
        ttk.Button(url_frame, text="Add to Queue", command=self.add_to_queue).grid(row=0, column=2, padx=(5, 0))
        
        ttk.Label(url_frame, text="Multiple URLs (one per line):").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=(10, 0), padx=(0, 5))
        self.multi_url_text = tk.Text(url_frame, height=4, width=50)
        self.multi_url_text.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0), padx=(0, 5))
        ttk.Button(url_frame, text="Add All", command=self.add_multiple_urls).grid(row=1, column=2, sticky=tk.N, pady=(10, 0), padx=(5, 0))
        
        self.extracting_label = ttk.Label(url_frame, text="", style="Status.TLabel")
        self.extracting_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

    def setup_settings_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup enhanced download settings section."""
        settings_frame = ttk.LabelFrame(parent, text="Download Settings", padding="10")
        settings_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        
        ttk.Label(settings_frame, text="Download Path:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.path_var = tk.StringVar(value=self.config.get("download_path"))
        ttk.Entry(settings_frame, textvariable=self.path_var, state="readonly").grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(settings_frame, text="Browse", command=self.browse_download_path).grid(row=0, column=2, padx=(5, 0))
        ttk.Button(settings_frame, text="Open Folder", command=self.open_download_folder).grid(row=0, column=3, padx=(5, 0))
        
        ttk.Label(settings_frame, text="Quality:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        self.quality_var = tk.StringVar(value=self.config.get("quality"))
        ttk.Combobox(settings_frame, textvariable=self.quality_var, values=["best", "worst", "720p", "480p", "360p", "audio_only"], 
                     state="readonly", width=15).grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        
        self.subtitle_var = tk.BooleanVar(value=self.config.get("include_subtitles"))
        ttk.Checkbutton(settings_frame, text="Download Subtitles", variable=self.subtitle_var).grid(row=1, column=2, pady=(10, 0), padx=(5, 0))
        
        ttk.Label(settings_frame, text="Subtitle Languages:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        self.subtitle_langs_var = tk.StringVar(value=",".join(self.config.get('subtitle_langs', ['en'])))
        ttk.Entry(settings_frame, textvariable=self.subtitle_langs_var, width=20).grid(row=2, column=1, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        
        self.thumbnail_var = tk.BooleanVar(value=self.config.get("download_thumbnails", False))
        ttk.Checkbutton(settings_frame, text="Download Thumbnails", variable=self.thumbnail_var).grid(row=2, column=2, pady=(5, 0), padx=(5, 0))
        
        self.description_var = tk.BooleanVar(value=self.config.get("download_description", False))
        ttk.Checkbutton(settings_frame, text="Download Description", variable=self.description_var).grid(row=3, column=2, pady=(5, 0), padx=(5, 0))
        
        self.playlist_folders_var = tk.BooleanVar(value=self.config.get("create_playlist_folders", True))
        ttk.Checkbutton(settings_frame, text="Create Playlist Folders", variable=self.playlist_folders_var).grid(row=3, column=1, pady=(5, 0), padx=(5, 0))
        
        self.prefer_mp4_var = tk.BooleanVar(value=self.config.get("prefer_mp4", True))
        ttk.Checkbutton(settings_frame, text="Prefer MP4 Format", variable=self.prefer_mp4_var).grid(row=4, column=1, pady=(5, 0), padx=(5, 0))
        
        ttk.Label(settings_frame, text="Retry Delay (s):").grid(row=4, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        self.retry_delay_var = tk.StringVar(value=str(self.config.get("retry_delay", 2)))
        ttk.Entry(settings_frame, textvariable=self.retry_delay_var, width=10).grid(row=4, column=2, sticky=tk.W, pady=(5, 0), padx=(5, 0))

    def setup_queue_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup enhanced download queue display with additional metadata."""
        queue_frame = ttk.LabelFrame(parent, text="Download Queue", padding="10")
        queue_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)
        
        columns = ("URL", "Title", "Duration", "Status", "Uploader", "Upload Date", "Views")
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, show="tree headings", height=8)
        self.queue_tree.heading("#0", text="ID")
        self.queue_tree.column("#0", width=50, minwidth=50)
        for col in columns:
            self.queue_tree.heading(col, text=col)
            self.queue_tree.column(col, width=300 if col == "URL" else 250 if col == "Title" else 80 if col == "Duration" else 100 if col == "Status" else 150, minwidth=100)
        self.queue_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview).grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.queue_tree.configure(yscrollcommand=lambda f, l: None)
        
        queue_button_frame = ttk.Frame(queue_frame)
        queue_button_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(queue_button_frame, text="Remove Selected", command=self.remove_from_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_button_frame, text="Clear Queue", command=self.clear_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_button_frame, text="Refresh Info", command=self.refresh_queue_info).pack(side=tk.LEFT)
    def setup_progress_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup enhanced download progress display section with detailed metrics."""
        progress_frame = ttk.LabelFrame(parent, text="Download Progress", padding="10")
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        
        # Current download progress
        ttk.Label(progress_frame, text="Current Download:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.current_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.current_progress.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.current_percent_label = ttk.Label(progress_frame, text="0%", width=6)
        self.current_percent_label.grid(row=0, column=2, padx=(5, 0))
        
        # Overall queue progress
        ttk.Label(progress_frame, text="Overall Queue:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        self.overall_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.overall_progress.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(5, 0), padx=(0, 5))
        self.overall_percent_label = ttk.Label(progress_frame, text="0%", width=6)
        self.overall_percent_label.grid(row=1, column=2, pady=(5, 0), padx=(5, 0))
        
        # Current file status with enhanced styling
        self.current_file_label = ttk.Label(progress_frame, text="Ready to download...", 
                                        style="Status.TLabel", wraplength=600)
        self.current_file_label.grid(row=2, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))
        
        # Enhanced progress details frame
        details_frame = ttk.Frame(progress_frame)
        details_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        details_frame.columnconfigure(1, weight=1)
        details_frame.columnconfigure(3, weight=1)
        details_frame.columnconfigure(5, weight=1)
        
        # Download speed
        ttk.Label(details_frame, text="Speed:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.speed_label = ttk.Label(details_frame, text="-- B/s", style="Status.TLabel")
        self.speed_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 15))
        
        # ETA (Estimated Time of Arrival)
        ttk.Label(details_frame, text="ETA:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.eta_label = ttk.Label(details_frame, text="--", style="Status.TLabel")
        self.eta_label.grid(row=0, column=3, sticky=tk.W, padx=(0, 15))
        
        # Elapsed time
        ttk.Label(details_frame, text="Elapsed:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.elapsed_label = ttk.Label(details_frame, text="--", style="Status.TLabel")
        self.elapsed_label.grid(row=0, column=5, sticky=tk.W)
        
        # File size information
        size_frame = ttk.Frame(progress_frame)
        size_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        size_frame.columnconfigure(1, weight=1)
        size_frame.columnconfigure(3, weight=1)
        
        ttk.Label(size_frame, text="Downloaded:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.downloaded_size_label = ttk.Label(size_frame, text="0 B", style="Status.TLabel")
        self.downloaded_size_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 15))
        
        ttk.Label(size_frame, text="Total Size:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.total_size_label = ttk.Label(size_frame, text="Unknown", style="Status.TLabel")
        self.total_size_label.grid(row=0, column=3, sticky=tk.W)
        
        # Queue status frame
        queue_status_frame = ttk.Frame(progress_frame)
        queue_status_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        queue_status_frame.columnconfigure(1, weight=1)
        queue_status_frame.columnconfigure(3, weight=1)
        queue_status_frame.columnconfigure(5, weight=1)
        
        ttk.Label(queue_status_frame, text="Queue Status:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.queue_status_label = ttk.Label(queue_status_frame, text="0 / 0", style="Status.TLabel")
        self.queue_status_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 15))
        
        ttk.Label(queue_status_frame, text="Remaining:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.remaining_label = ttk.Label(queue_status_frame, text="0", style="Status.TLabel")
        self.remaining_label.grid(row=0, column=3, sticky=tk.W, padx=(0, 15))
        
        ttk.Label(queue_status_frame, text="Errors:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.errors_label = ttk.Label(queue_status_frame, text="0", style="Status.TLabel", foreground="red")
        self.errors_label.grid(row=0, column=5, sticky=tk.W)
        
        # Current video info frame (expandable)
        self.video_info_frame = ttk.LabelFrame(progress_frame, text="Current Video Info", padding="5")
        self.video_info_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        self.video_info_frame.columnconfigure(1, weight=1)
        
        # Video title
        ttk.Label(self.video_info_frame, text="Title:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.video_title_label = ttk.Label(self.video_info_frame, text="--", style="Status.TLabel", wraplength=500)
        self.video_title_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # Video duration and quality
        info_sub_frame = ttk.Frame(self.video_info_frame)
        info_sub_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        info_sub_frame.columnconfigure(1, weight=1)
        info_sub_frame.columnconfigure(3, weight=1)
        
        ttk.Label(info_sub_frame, text="Duration:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.video_duration_label = ttk.Label(info_sub_frame, text="--", style="Status.TLabel")
        self.video_duration_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 15))
        
        ttk.Label(info_sub_frame, text="Quality:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.video_quality_label = ttk.Label(info_sub_frame, text="--", style="Status.TLabel")
        self.video_quality_label.grid(row=0, column=3, sticky=tk.W)
        
        # Retry information
        retry_frame = ttk.Frame(progress_frame)
        retry_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        retry_frame.columnconfigure(1, weight=1)
        
        ttk.Label(retry_frame, text="Retry Info:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.retry_info_label = ttk.Label(retry_frame, text="No retries", style="Status.TLabel")
        self.retry_info_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        
        # Hide video info frame initially
        self.video_info_frame.grid_remove()
        
        # Toggle button for detailed view
        self.toggle_details_var = tk.BooleanVar(value=False)
        self.toggle_details_btn = ttk.Checkbutton(progress_frame, text="Show detailed video info", 
                                                variable=self.toggle_details_var,
                                                command=self.toggle_video_info)
        self.toggle_details_btn.grid(row=8, column=0, columnspan=3, pady=(10, 0))

    def toggle_video_info(self) -> None:
        """Toggle the visibility of detailed video information."""
        if self.toggle_details_var.get():
            self.video_info_frame.grid()
        else:
            self.video_info_frame.grid_remove()

    def update_detailed_progress(self, progress_info: Dict[str, Any]) -> None:
        """Update GUI with detailed progress information."""
        # Basic progress update
        percent = progress_info.get('percent', 0)
        self.current_progress['value'] = percent
        self.current_percent_label.config(text=f"{percent:.1f}%")
        
        # Size information
        downloaded_size = progress_info.get('downloaded_bytes', 0)
        total_size = progress_info.get('total_bytes', 0)
        self.downloaded_size_label.config(text=self.format_size(downloaded_size))
        self.total_size_label.config(text=self.format_size(total_size) if total_size else "Unknown")
        
        # Speed and timing
        speed = progress_info.get('speed', 0)
        eta_seconds = progress_info.get('eta_seconds')
        elapsed_seconds = progress_info.get('elapsed_seconds', 0)
        
        self.speed_label.config(text=self.format_speed(speed))
        self.eta_label.config(text=self.format_time(eta_seconds) if eta_seconds else "Unknown")
        self.elapsed_label.config(text=self.format_time(elapsed_seconds))
        
        # Current file status with enhanced styling
        is_stalled = progress_info.get('is_stalled', False)
        filename = progress_info.get('filename', 'Unknown file')
        
        if is_stalled:
            status_text = f"[STALLED] {filename}"
            self.current_file_label.config(text=status_text, style="Stalled.TLabel")
            self.speed_label.config(text="0 B/s [STALLED]", style="Stalled.TLabel")
        else:
            status_text = f"Downloading: {filename}"
            self.current_file_label.config(text=status_text, style="Status.TLabel")
            self.speed_label.config(style="Status.TLabel")
        
        # Video information (if detailed view is enabled)
        if self.toggle_details_var.get():
            video_info = progress_info.get('video_info', {})
            self.video_title_label.config(text=video_info.get('title', 'Unknown'))
            self.video_duration_label.config(text=video_info.get('duration', 'Unknown'))
            self.video_quality_label.config(text=video_info.get('quality', 'Unknown'))
        
        # Retry information
        retry_count = progress_info.get('retry_count', 0)
        max_retries = progress_info.get('max_retries', 0)
        if retry_count > 0:
            self.retry_info_label.config(text=f"Retry {retry_count}/{max_retries}", style="Error.TLabel")
        else:
            self.retry_info_label.config(text="No retries", style="Status.TLabel")

    def update_queue_progress_info(self) -> None:
        """Update queue-specific progress information."""
        total_videos = len(self.video_queue)
        completed_videos = len([v for v in self.video_queue if v['status'] == 'Completed'])
        failed_videos = len([v for v in self.video_queue if v['status'] == 'Failed'])
        remaining_videos = total_videos - completed_videos - failed_videos
        
        # Update queue status labels
        self.queue_status_label.config(text=f"{completed_videos} / {total_videos}")
        self.remaining_label.config(text=str(remaining_videos))
        self.errors_label.config(text=str(failed_videos))
        
        # Update overall progress
        if total_videos > 0:
            overall_percent = (completed_videos / total_videos) * 100
            self.overall_progress['value'] = overall_percent
            self.overall_percent_label.config(text=f"{overall_percent:.1f}%")
        else:
            self.overall_progress['value'] = 0
            self.overall_percent_label.config(text="0%")

    def reset_progress_display(self) -> None:
        """Reset all progress displays to initial state."""
        self.current_progress['value'] = 0
        self.current_percent_label.config(text="0%")
        self.overall_progress['value'] = 0
        self.overall_percent_label.config(text="0%")
        
        self.current_file_label.config(text="Ready to download...", style="Status.TLabel")
        self.speed_label.config(text="-- B/s", style="Status.TLabel")
        self.eta_label.config(text="--", style="Status.TLabel")
        self.elapsed_label.config(text="--", style="Status.TLabel")
        self.downloaded_size_label.config(text="0 B", style="Status.TLabel")
        self.total_size_label.config(text="Unknown", style="Status.TLabel")
        
        self.queue_status_label.config(text="0 / 0", style="Status.TLabel")
        self.remaining_label.config(text="0", style="Status.TLabel")
        self.errors_label.config(text="0", style="Status.TLabel")
        
        self.video_title_label.config(text="--", style="Status.TLabel")
        self.video_duration_label.config(text="--", style="Status.TLabel")
        self.video_quality_label.config(text="--", style="Status.TLabel")
        self.retry_info_label.config(text="No retries", style="Status.TLabel")

    def update_progress_colors(self) -> None:
        """Update progress bar colors based on status."""
        # You can customize progress bar colors here
        style = ttk.Style()
        
        # Define custom progress bar styles
        style.configure("Success.Horizontal.TProgressbar", 
                    troughcolor="lightgray", 
                    background="green",
                    lightcolor="lightgreen",
                    darkcolor="darkgreen")
        
        style.configure("Warning.Horizontal.TProgressbar", 
                    troughcolor="lightgray", 
                    background="orange",
                    lightcolor="lightyellow",
                    darkcolor="darkorange")
        
        style.configure("Error.Horizontal.TProgressbar", 
                    troughcolor="lightgray", 
                    background="red",
                    lightcolor="lightcoral",
                    darkcolor="darkred")
        
        # Apply styles based on current status
        if hasattr(self, 'current_progress'):
            current_value = self.current_progress['value']
            if current_value >= 100:
                self.current_progress.configure(style="Success.Horizontal.TProgressbar")
            elif current_value > 0:
                self.current_progress.configure(style="TProgressbar")  # Default style
            else:
                self.current_progress.configure(style="TProgressbar")  # Default style
    def setup_stats_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup new statistics display section."""
        stats_frame = ttk.LabelFrame(parent, text="Download Statistics", padding="10")
        stats_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        stats_frame.columnconfigure(1, weight=1)
        
        ttk.Label(stats_frame, text="Total Downloads:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.total_downloads_label = ttk.Label(stats_frame, text="0")
        self.total_downloads_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        
        ttk.Label(stats_frame, text="Successful:").grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        self.successful_downloads_label = ttk.Label(stats_frame, text="0")
        self.successful_downloads_label.grid(row=0, column=3, sticky=tk.W)
        
        ttk.Label(stats_frame, text="Failed:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        self.failed_downloads_label = ttk.Label(stats_frame, text="0")
        self.failed_downloads_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        
        ttk.Label(stats_frame, text="Total Downloaded:").grid(row=1, column=2, sticky=tk.W, pady=(5, 0), padx=(5, 0))
        self.total_bytes_label = ttk.Label(stats_frame, text="0 B")
        self.total_bytes_label.grid(row=1, column=3, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(stats_frame, text="Session Time:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        self.session_time_label = ttk.Label(stats_frame, text="0s")
        self.session_time_label.grid(row=2, column=1, sticky=tk.W, pady=(5, 0), padx=(0, 5))

    def setup_control_buttons(self, parent: ttk.Frame, row: int) -> None:
        """Setup control buttons for starting/stopping downloads."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="Start Downloads", command=self.start_downloads, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        self.pause_button = ttk.Button(button_frame, text="Pause", command=self.pause_downloads, state="disabled")
        self.pause_button.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_downloads, state="disabled")
        self.stop_button.pack(side=tk.LEFT)

    def setup_status_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup status log section."""
        status_frame = ttk.LabelFrame(parent, text="Status Log", padding="10")
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=8, wrap=tk.WORD)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def browse_download_path(self) -> None:
        """Browse and set the download directory."""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)
            self.config.set("download_path", path)
            self.config.save_config()
            self.logger.log(message=f"Download path changed to: {path}")

    def open_download_folder(self) -> None:
        """Open the download folder in the system file explorer."""
        path = self.path_var.get()
        if os.path.exists(path):
            subprocess.run(["explorer" if sys.platform == "win32" else "open" if sys.platform == "darwin" else "xdg-open", path])
        else:
            messagebox.showerror("Error", "Download path does not exist")

    def validate_url(self, url: str) -> bool:
        """
        Validate if a URL is a valid YouTube URL.

        Args:
            url (str): URL to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})|'
            r'(https?://)?(www\.)?youtube\.com/playlist\?list=([^&=%\?]+)'
        )
        return bool(youtube_regex.match(url))

    def add_to_queue(self) -> None:
        """Add a single URL to the download queue."""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL")
            return
        if not self.validate_url(url):
            messagebox.showerror("Error", "Invalid YouTube URL")
            return
        self.extracting_label.config(text="Extracting video info...")
        self.logger.log(message=f"Extracting info for: {url}")
        threading.Thread(target=lambda: self._add_url(url), daemon=True).start()
        self.url_var.set("")

    def add_multiple_urls(self) -> None:
        """Add multiple URLs from the text area to the queue."""
        urls_text = self.multi_url_text.get(1.0, tk.END).strip()
        if not urls_text:
            messagebox.showwarning("Warning", "Please enter URLs")
            return
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        valid_urls = [url for url in urls if self.validate_url(url) or self.logger.log(message=f"Skipping invalid URL: {url}", level="WARNING")]
        if not valid_urls:
            messagebox.showerror("Error", "No valid YouTube URLs found")
            return
        self.extracting_label.config(text="Extracting info for multiple URLs...")
        self.logger.log(message=f"Processing {len(valid_urls)} URLs...")
        threading.Thread(target=lambda: [self._add_url(url) for url in valid_urls], daemon=True).start()
        self.multi_url_text.delete(1.0, tk.END)

    def _add_url(self, url: str) -> None:
        """Helper to add URL in background thread."""
        self.download_manager.add_to_queue(url)
        self.root.after(0, lambda: self.extracting_label.config(text=""))

    def remove_from_queue(self) -> None:
        """Remove selected items from the queue."""
        selected_items = self.queue_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select items to remove")
            return
        selected_ids = [int(self.queue_tree.item(item, 'text')) for item in selected_items]
        for video in self.video_queue:
            if video['id'] in selected_ids:
                video['status'] = 'Removed'
        for item in selected_items:
            self.queue_tree.delete(item)
        self.logger.log(message=f"Removed {len(selected_items)} item(s) from queue")
        self.download_manager.save_queue()
        self.update_overall_progress()

    def clear_queue(self) -> None:
        """Clear all items from the queue."""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the entire queue?"):
            self.video_queue.clear()
            for item in self.queue_tree.get_children():
                self.queue_tree.delete(item)
            self.logger.log(message="Queue cleared")
            self.download_manager.save_queue()
            self.update_overall_progress()
            self.update_stats_display()

    def refresh_queue_info(self) -> None:
        """Refresh video information for queued items."""
        if not self.video_queue:
            self.logger.log(message="No videos in queue to refresh", level="WARNING")
            return
        self.logger.log(message="Refreshing queue information...")
        for video in self.video_queue:
            if video['status'] == 'Queued':
                self.download_manager.add_to_queue(video['url'])
        self.logger.log(message="Queue information refreshed")

    def start_downloads(self) -> None:
        """Start downloading queued videos."""
        active_videos = [v for v in self.video_queue if v['status'] == 'Queued']
        if not active_videos:
            messagebox.showwarning("Warning", "No videos in queue to download")
            return
        if not os.path.exists(self.path_var.get()):
            messagebox.showerror("Error", "Download path does not exist")
            return
        if not self.download_manager.check_disk_space():
            messagebox.showerror("Error", "Insufficient disk space to start downloads")
            return
        try:
            retry_delay = float(self.retry_delay_var.get())
            if retry_delay < 0:
                raise ValueError("Retry delay must be non-negative")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid retry delay: {str(e)}")
            return
        self.config.set("download_path", self.path_var.get())
        self.config.set("quality", self.quality_var.get())
        self.config.set("include_subtitles", self.subtitle_var.get())
        self.config.set("subtitle_langs", [lang.strip() for lang in self.subtitle_langs_var.get().split(',') if lang.strip()])
        self.config.set("download_thumbnails", self.thumbnail_var.get())
        self.config.set("download_description", self.description_var.get())
        self.config.set("create_playlist_folders", self.playlist_folders_var.get())
        self.config.set("prefer_mp4", self.prefer_mp4_var.get())
        self.config.set("retry_delay", float(self.retry_delay_var.get()))
        self.config.save_config()
        self.start_button.config(state="disabled")
        self.pause_button.config(state="normal")
        self.stop_button.config(state="normal")
        self.download_manager.reset_download_stats()
        self.update_stats_display()
        self.logger.log(message=f"Starting download of {len(active_videos)} video(s)")
        self.download_manager.start_downloads()

    def pause_downloads(self) -> None:
        """Placeholder for pause functionality."""
        messagebox.showinfo("Info", "Pause functionality is not available with yt-dlp. Use Stop to cancel downloads.")

    def stop_downloads(self) -> None:
        """Stop all downloads."""
        self.download_manager.stop_downloads()
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.current_progress['value'] = 0
        self.current_percent_label.config(text="0%")
        self.current_file_label.config(text="Downloads stopped")
        self.update_stats_display()
        self.download_manager.save_queue()

    def check_progress_queue(self) -> None:
        """Check for progress updates from the download manager."""
        try:
            while True:
                item = self.download_manager.progress_queue.get_nowait()
                if item[0] == 'video_added':
                    self.video_queue.append(item[1])
                    # Safely handle missing metadata fields
                    uploader = item[1].get('uploader', 'Unknown')[:20] + '...' if len(item[1].get('uploader', 'Unknown')) > 20 else item[1].get('uploader', 'Unknown')
                    upload_date = item[1].get('upload_date', 'Unknown')
                    view_count = f"{item[1].get('view_count', 0):,}"
                    self.queue_tree.insert('', 'end', text=str(item[1]['id']), values=(
                        item[1]['url'][:50] + '...' if len(item[1]['url']) > 50 else item[1]['url'],
                        item[1]['title'][:40] + '...' if len(item[1]['title']) > 40 else item[1]['title'],
                        item[1]['duration'],
                        item[1]['status'],
                        uploader,
                        upload_date,
                        view_count
                    ))
                    self.update_overall_progress()
                elif item[0] == 'progress':
                    self.current_progress['value'] = item[1]
                    self.current_percent_label.config(text=f"{item[1]:.1f}%")
                elif item[0] == 'status':
                    self.update_video_status(item[1], item[2])
                    self.update_overall_progress()
                elif item[0] == 'current_file':
                    style = "Stalled.TLabel" if "[STALLED]" in item[1] else "Status.TLabel"
                    self.current_file_label.config(text=item[1], style=style)
                elif item[0] == 'log':
                    self.logger.log(message=item[1], level=item[2] if len(item) > 2 else 'INFO')
                    if item[2] == 'ERROR':
                        messagebox.showerror("Error", item[1])
                elif item[0] == 'detailed_progress':
                    self.update_detailed_progress(item[1])
                elif item[0] == 'download_complete':
                    self.download_complete()
        except queue.Empty:
            pass
        self.update_stats_display()
        self.root.after(100, self.check_progress_queue)

    def update_detailed_progress(self, progress_info: Dict[str, Any]) -> None:
        """Update GUI with detailed progress information."""
        percent = progress_info['percent']
        downloaded_size = self.format_size(progress_info['downloaded_bytes'])
        total_size = self.format_size(progress_info['total_bytes']) if progress_info['total_bytes'] else "Unknown"
        speed = self.format_speed(progress_info['speed'])
        eta = self.format_time(progress_info['eta_seconds'])
        elapsed = self.format_time(progress_info['elapsed_seconds'])
        stalled = " [STALLED]" if progress_info['is_stalled'] else ""
        
        progress_msg = (
            f"Downloading: {percent:.1f}% ({downloaded_size}/{total_size}) | "
            f"Speed: {speed} | ETA: {eta} | Elapsed: {elapsed}{stalled}"
        )
        style = "Stalled.TLabel" if stalled else "Status.TLabel"
        self.current_file_label.config(text=progress_msg, style=style)

    def format_size(self, bytes_size: int) -> str:
        """Format byte size to human-readable string."""
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size/1024:.1f} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size/(1024*1024):.1f} MB"
        else:
            return f"{bytes_size/(1024*1024*1024):.1f} GB"

    def format_speed(self, speed: float) -> str:
        """Format speed to human-readable string."""
        if speed == 0:
            return "-- B/s"
        elif speed < 1024:
            return f"{speed:.1f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed/1024:.1f} KB/s"
        elif speed < 1024 * 1024 * 1024:
            return f"{speed/(1024*1024):.1f} MB/s"
        else:
            return f"{speed/(1024*1024*1024):.1f} GB/s"

    def format_time(self, seconds: float) -> str:
        """Format time duration to human-readable string."""
        if seconds is None:
            return "Unknown"
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def update_video_status(self, video_id: int, status: str) -> None:
        """
        Update video status in the treeview.

        Args:
            video_id (int): ID of the video.
            status (str): New status to set.
        """
        for item in self.queue_tree.get_children():
            if int(self.queue_tree.item(item, 'text')) == video_id:
                current_values = list(self.queue_tree.item(item, 'values'))
                current_values[3] = status
                self.queue_tree.item(item, values=current_values)
                break

    def update_overall_progress(self) -> None:
        """Update the overall progress bar."""
        active_videos = [v for v in self.video_queue if v['status'] != 'Removed']
        if not active_videos:
            self.overall_progress['value'] = 0
            self.overall_percent_label.config(text="0%")
            return
        completed = len([v for v in active_videos if v['status'] == 'Completed'])
        progress_percent = (completed / len(active_videos)) * 100 if active_videos else 0
        self.overall_progress['value'] = progress_percent
        self.overall_percent_label.config(text=f"{progress_percent:.1f}%")

    def update_stats_display(self) -> None:
        """Update the statistics display with current download stats."""
        stats = self.download_manager.get_download_stats()
        session_time = time.time() - stats['session_start_time']
        self.total_downloads_label.config(text=str(stats['total_downloads']))
        self.successful_downloads_label.config(text=str(stats['successful_downloads']))
        self.failed_downloads_label.config(text=str(stats['failed_downloads']))
        self.total_bytes_label.config(text=self.format_size(stats['total_bytes_downloaded']))
        self.session_time_label.config(text=self.format_time(session_time))

    def download_complete(self) -> None:
        """Handle download completion."""
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.current_progress['value'] = 0
        self.current_percent_label.config(text="0%")
        self.current_file_label.config(text="All downloads completed!")
        stats = self.download_manager.get_download_stats()
        completed_count = stats['successful_downloads']
        messagebox.showinfo("Downloads Complete", f"Successfully downloaded {completed_count} video(s)!")
        self.update_stats_display()
        self.download_manager.save_queue()

    def on_closing(self) -> None:
        """Handle application closing."""
        self.config.set("window_geometry", self.root.geometry())
        self.config.save_config()
        if self.download_manager.is_downloading:
            self.download_manager.stop_downloads()
        self.download_manager.save_queue()
        self.root.destroy()