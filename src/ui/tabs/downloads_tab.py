"""Downloads tab for YouTube Downloader.

Main download interface with URL input, queue, and progress.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Callable, List
import os

from src.ui.widgets.url_input import URLInputWidget
from src.ui.widgets.queue_widget import QueueWidget
from src.ui.widgets.progress_widget import ProgressWidget, ProgressInfo
from src.core.queue_manager import VideoItem, VideoStatus
from src.ui.styled_widgets import StyledEntry, StyledSpinbox, DRACULA


class DownloadsTab(ttk.Frame):
    """Main downloads interface tab.

    Features:
    - URL input (single and batch)
    - Quick settings (path, quality)
    - Download queue
    - Progress display
    - Control buttons

    Usage:
        tab = DownloadsTab(notebook, config_manager)
        tab.on_start_downloads = start_callback
    """

    def __init__(self, parent, config_manager, **kwargs):
        """Initialize downloads tab.

        Args:
            parent: Parent widget
            config_manager: Configuration manager instance
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self.config = config_manager

        # Callbacks
        self.on_urls_submitted: Optional[Callable[[List[str]], None]] = None
        self.on_start_downloads: Optional[Callable[[], None]] = None
        self.on_pause_downloads: Optional[Callable[[], None]] = None
        self.on_resume_downloads: Optional[Callable[[], None]] = None
        self.on_stop_downloads: Optional[Callable[[], None]] = None
        self.on_remove_items: Optional[Callable[[List[str]], None]] = None
        self.on_clear_queue: Optional[Callable[[], None]] = None
        self.on_retry_failed: Optional[Callable[[List[str]], None]] = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        """Build the tab UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Queue section expands

        # URL Input Section
        self.url_input = URLInputWidget(self)
        self.url_input.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # Quick Settings Section
        self._build_quick_settings()

        # Queue Section
        self.queue_widget = QueueWidget(self)
        self.queue_widget.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Progress Section
        self.progress_widget = ProgressWidget(self)
        self.progress_widget.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Control Buttons
        self._build_control_buttons()

    def _build_quick_settings(self):
        """Build quick settings section."""
        settings_frame = ttk.LabelFrame(self, text="Quick Settings", padding=10)
        settings_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)

        # Download path
        ttk.Label(settings_frame, text="Download Path:").grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )

        path_frame = ttk.Frame(settings_frame)
        path_frame.grid(row=0, column=1, sticky="ew")
        path_frame.columnconfigure(0, weight=1)

        self.path_var = tk.StringVar(value=self.config.get("download_path", ""))
        self.path_entry = StyledEntry(path_frame, textvariable=self.path_var, state="readonly")
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        ttk.Button(
            path_frame,
            text="Browse",
            command=self._browse_path
        ).grid(row=0, column=1, padx=(0, 5))

        ttk.Button(
            path_frame,
            text="Open",
            command=self._open_folder
        ).grid(row=0, column=2)

        # Quality and concurrent downloads
        options_frame = ttk.Frame(settings_frame)
        options_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        ttk.Label(options_frame, text="Quality:").pack(side=tk.LEFT, padx=(0, 5))

        self.quality_var = tk.StringVar(value=self.config.get("quality", "best"))
        quality_combo = ttk.Combobox(
            options_frame,
            textvariable=self.quality_var,
            values=["best", "1080p", "720p", "480p", "360p", "audio_only"],
            state="readonly",
            width=12
        )
        quality_combo.pack(side=tk.LEFT, padx=(0, 20))
        quality_combo.bind("<<ComboboxSelected>>", self._on_quality_changed)

        ttk.Label(options_frame, text="Concurrent:").pack(side=tk.LEFT, padx=(0, 5))

        self.concurrent_var = tk.IntVar(value=self.config.get("max_concurrent_downloads", 2))
        concurrent_spin = StyledSpinbox(
            options_frame,
            from_=1,
            to=5,
            textvariable=self.concurrent_var,
            width=5
        )
        concurrent_spin.pack(side=tk.LEFT, padx=(0, 20))
        concurrent_spin.bind("<FocusOut>", self._on_concurrent_changed)

        # Subtitles checkbox
        self.subtitles_var = tk.BooleanVar(value=self.config.get("include_subtitles", False))
        ttk.Checkbutton(
            options_frame,
            text="Download Subtitles",
            variable=self.subtitles_var,
            command=self._on_subtitles_changed
        ).pack(side=tk.LEFT, padx=(0, 15))

        # Preview Formats button
        self.preview_formats_btn = ttk.Button(
            options_frame,
            text="Preview Formats",
            command=self._show_format_preview
        )
        self.preview_formats_btn.pack(side=tk.LEFT)

    def _build_control_buttons(self):
        """Build control button section."""
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Start button
        self.start_btn = ttk.Button(
            btn_frame,
            text="▶ Start Downloads",
            command=self._on_start,
            style="Accent.TButton"
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Pause button
        self.pause_btn = ttk.Button(
            btn_frame,
            text="⏸ Pause",
            command=self._on_pause,
            state="disabled"
        )
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Resume button
        self.resume_btn = ttk.Button(
            btn_frame,
            text="▶ Resume",
            command=self._on_resume,
            state="disabled"
        )
        self.resume_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Stop button
        self.stop_btn = ttk.Button(
            btn_frame,
            text="⏹ Stop",
            command=self._on_stop,
            state="disabled"
        )
        self.stop_btn.pack(side=tk.LEFT)

    def _connect_signals(self):
        """Connect widget signals to handlers."""
        self.url_input.on_urls_submitted = self._handle_urls_submitted
        self.queue_widget.on_remove = self._handle_remove
        self.queue_widget.on_clear = self._handle_clear
        self.queue_widget.on_retry = self._handle_retry

    # Public methods for external control

    def add_to_queue(self, video: VideoItem):
        """Add a video to the queue display.

        Args:
            video: VideoItem to add
        """
        self.queue_widget.add_item(video)

    def update_queue_item(self, video: VideoItem):
        """Update a queue item.

        Args:
            video: VideoItem to update
        """
        self.queue_widget.update_item(video)

    def remove_from_queue(self, video_id: str):
        """Remove a video from the queue display.

        Args:
            video_id: ID of video to remove
        """
        self.queue_widget.remove_item(video_id)

    def clear_queue(self):
        """Clear the queue display."""
        self.queue_widget.clear()

    def update_progress(self, info: ProgressInfo):
        """Update progress display.

        Args:
            info: Progress information
        """
        self.progress_widget.update_progress(info)

    def set_downloading_state(self, is_downloading: bool, is_paused: bool = False):
        """Set UI state based on download status.

        Args:
            is_downloading: Whether downloads are active
            is_paused: Whether downloads are paused
        """
        if is_downloading:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")

            if is_paused:
                self.pause_btn.configure(state="disabled")
                self.resume_btn.configure(state="normal")
            else:
                self.pause_btn.configure(state="normal")
                self.resume_btn.configure(state="disabled")
        else:
            self.start_btn.configure(state="normal")
            self.pause_btn.configure(state="disabled")
            self.resume_btn.configure(state="disabled")
            self.stop_btn.configure(state="disabled")

    def set_loading(self, loading: bool, message: str = ""):
        """Set loading state for URL input.

        Args:
            loading: Whether loading is active
            message: Loading message
        """
        self.url_input.set_loading(loading, message)

    def reset_progress(self):
        """Reset progress display."""
        self.progress_widget.reset()

    # Event handlers

    def _browse_path(self):
        """Handle browse button click."""
        current_path = self.path_var.get()
        path = filedialog.askdirectory(initialdir=current_path)

        if path:
            self.path_var.set(path)
            self.config.set("download_path", path)

    def _open_folder(self):
        """Handle open folder button click."""
        path = self.path_var.get()
        if os.path.exists(path):
            import subprocess
            import sys

            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            messagebox.showerror("Error", "Download path does not exist")

    def _on_quality_changed(self, event=None):
        """Handle quality selection change."""
        self.config.set("quality", self.quality_var.get())

    def _on_concurrent_changed(self, event=None):
        """Handle concurrent downloads change."""
        self.config.set("max_concurrent_downloads", self.concurrent_var.get())

    def _on_subtitles_changed(self):
        """Handle subtitles checkbox change."""
        self.config.set("include_subtitles", self.subtitles_var.get())

    def _handle_urls_submitted(self, urls: List[str]):
        """Handle URLs submitted from input widget."""
        from src.core.playlist_filter import PlaylistFilter

        # Check if any URL is a playlist
        playlist_urls = []
        regular_urls = []

        for url in urls:
            if PlaylistFilter.is_playlist_url(url):
                playlist_urls.append(url)
            else:
                regular_urls.append(url)

        # Handle regular URLs immediately
        if regular_urls and self.on_urls_submitted:
            self.on_urls_submitted(regular_urls)

        # Show playlist dialog for playlist URLs
        for playlist_url in playlist_urls:
            self._show_playlist_dialog(playlist_url)

    def _show_playlist_dialog(self, url: str):
        """Show playlist selection dialog.

        Args:
            url: Playlist URL
        """
        from src.ui.dialogs.playlist_dialog import show_playlist_dialog

        def on_videos_selected(video_urls: List[str]):
            if video_urls and self.on_urls_submitted:
                self.on_urls_submitted(video_urls)

        show_playlist_dialog(
            self.winfo_toplevel(),
            url=url,
            on_select=on_videos_selected
        )

    def _handle_remove(self, video_ids: List[str]):
        """Handle remove request from queue."""
        if self.on_remove_items:
            self.on_remove_items(video_ids)

    def _handle_clear(self):
        """Handle clear queue request."""
        if self.on_clear_queue:
            self.on_clear_queue()

    def _handle_retry(self, video_ids: List[str]):
        """Handle retry request."""
        if self.on_retry_failed:
            self.on_retry_failed(video_ids)

    def _on_start(self):
        """Handle start button click."""
        if self.on_start_downloads:
            self.on_start_downloads()

    def _on_pause(self):
        """Handle pause button click."""
        if self.on_pause_downloads:
            self.on_pause_downloads()

    def _on_resume(self):
        """Handle resume button click."""
        if self.on_resume_downloads:
            self.on_resume_downloads()

    def _on_stop(self):
        """Handle stop button click."""
        if self.on_stop_downloads:
            self.on_stop_downloads()

    def _show_format_preview(self):
        """Show format preview dialog for the current URL."""
        url = self.url_input.get_url().strip()

        if not url:
            messagebox.showwarning(
                "No URL",
                "Please enter a YouTube URL first to preview available formats."
            )
            return

        from src.ui.dialogs.format_dialog import show_format_dialog

        def on_format_selected(format_id: str):
            # Store the selected format for the next download
            self._selected_format_id = format_id
            messagebox.showinfo(
                "Format Selected",
                f"Format '{format_id}' selected. Add the URL to queue to download with this format."
            )

        show_format_dialog(
            self.winfo_toplevel(),
            url=url,
            on_select=on_format_selected
        )
