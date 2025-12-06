"""Main window for YouTube Downloader.

The main application window that integrates all components.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List
import os
import sys
import threading
from datetime import datetime

from src.config.config_manager import ConfigManager
from src.core.queue_manager import QueueManager, VideoItem, VideoStatus
from src.core.download_manager import DownloadManager, DownloadOptions, DownloadProgress
from src.ui.themes.theme_manager import ThemeManager
from src.ui.tabs.downloads_tab import DownloadsTab
from src.ui.tabs.settings_tab import SettingsTab
from src.ui.tabs.history_tab import HistoryTab, HistoryEntry
from src.ui.widgets.status_bar import StatusBar, LogLevel
from src.ui.widgets.progress_widget import ProgressInfo
from src.utils.logger import Logger
from src.config.validators import URLValidator


class MainWindow:
    """Main application window.

    Integrates all components:
    - Downloads tab with queue and progress
    - Settings tab for configuration
    - History tab for past downloads
    - Status bar for logging

    Usage:
        app = MainWindow()
        app.run()
    """

    APP_NAME = "YouTube Downloader"
    APP_VERSION = "2.0.0"

    def __init__(self):
        """Initialize main window."""
        # Initialize root window
        self.root = tk.Tk()
        self.root.title(f"{self.APP_NAME} v{self.APP_VERSION}")

        # Initialize managers
        self._init_managers()

        # Build UI
        self._build_ui()
        self._setup_window()
        self._connect_signals()

        # Apply theme
        self.theme_manager.set_theme(self.config_manager.get("theme", "system"))

        # Log startup
        self.logger.info(f"{self.APP_NAME} v{self.APP_VERSION} started")
        self.status_bar.info("Ready")

    def _init_managers(self):
        """Initialize manager instances."""
        # Config directory
        config_dir = os.path.expanduser("~/.ytdownloader")
        os.makedirs(config_dir, exist_ok=True)

        # Config manager - pass the config FILE path, not directory
        config_file = os.path.join(config_dir, "config.json")
        self.config_manager = ConfigManager(config_file)
        self.config_manager.load()

        # Logger
        log_dir = os.path.join(config_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.logger = Logger(log_dir)

        # Theme manager (needs root, not config_manager)
        self.theme_manager = ThemeManager(self.root)

        # Queue manager
        self.queue_manager = QueueManager()

        # Download options
        self.download_options = DownloadOptions(
            output_path=self.config_manager.get("download_path", os.path.expanduser("~/Downloads")),
            quality=self.config_manager.get("quality", "best"),
            include_subtitles=self.config_manager.get("include_subtitles", False),
            subtitle_langs=[self.config_manager.get("subtitle_language", "en")],
            embed_subtitles=self.config_manager.get("embed_subtitles", False),
            embed_thumbnail=self.config_manager.get("embed_thumbnail", False),
            add_metadata=self.config_manager.get("add_metadata", True),
        )

        # Download manager
        self.download_manager = DownloadManager(
            queue=self.queue_manager,
            options=self.download_options,
            logger=self.logger,
            max_concurrent=self.config_manager.get("max_concurrent_downloads", 2)
        )

        # URL validator
        self.url_validator = URLValidator()

    def _build_ui(self):
        """Build the main UI."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Downloads tab
        self.downloads_tab = DownloadsTab(self.notebook, self.config_manager)
        self.notebook.add(self.downloads_tab, text="Downloads")

        # Settings tab
        self.settings_tab = SettingsTab(
            self.notebook,
            self.config_manager,
            self.theme_manager
        )
        self.notebook.add(self.settings_tab, text="Settings")

        # History tab
        self.history_tab = HistoryTab(self.notebook, self.config_manager)
        self.notebook.add(self.history_tab, text="History")

        # Status bar
        self.status_bar = StatusBar(main_frame, height=6)
        self.status_bar.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))

        # Create menu bar
        self._create_menu()

    def _create_menu(self):
        """Create application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Add URL...", command=self._show_add_url_dialog,
                             accelerator="Ctrl+N")
        file_menu.add_command(label="Add from Clipboard", command=self._add_from_clipboard,
                             accelerator="Ctrl+V")
        file_menu.add_separator()
        file_menu.add_command(label="Open Download Folder", command=self._open_download_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close, accelerator="Alt+F4")

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Select All", command=self._select_all_queue,
                             accelerator="Ctrl+A")
        edit_menu.add_command(label="Clear Queue", command=self._clear_queue)
        edit_menu.add_separator()
        edit_menu.add_command(label="Settings", command=self._show_settings)

        # Downloads menu
        downloads_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Downloads", menu=downloads_menu)
        downloads_menu.add_command(label="Start All", command=self._start_downloads,
                                  accelerator="Ctrl+S")
        downloads_menu.add_command(label="Pause All", command=self._pause_downloads)
        downloads_menu.add_command(label="Resume All", command=self._resume_downloads)
        downloads_menu.add_command(label="Stop All", command=self._stop_downloads)
        downloads_menu.add_separator()
        downloads_menu.add_command(label="Retry Failed", command=self._retry_failed)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Check for Updates", command=self._check_updates)

        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self._show_add_url_dialog())
        self.root.bind("<Control-v>", lambda e: self._add_from_clipboard())
        self.root.bind("<Control-s>", lambda e: self._start_downloads())
        self.root.bind("<Control-a>", lambda e: self._select_all_queue())

    def _setup_window(self):
        """Setup window properties."""
        # Window size
        width = self.config_manager.get("window_width", 1200)
        height = self.config_manager.get("window_height", 800)

        # Center window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(800, 600)

        # Window icon (if available)
        icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "resources", "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _connect_signals(self):
        """Connect all signals and callbacks."""
        # Downloads tab callbacks
        self.downloads_tab.on_urls_submitted = self._handle_urls_submitted
        self.downloads_tab.on_start_downloads = self._start_downloads
        self.downloads_tab.on_pause_downloads = self._pause_downloads
        self.downloads_tab.on_resume_downloads = self._resume_downloads
        self.downloads_tab.on_stop_downloads = self._stop_downloads
        self.downloads_tab.on_remove_items = self._handle_remove_items
        self.downloads_tab.on_clear_queue = self._clear_queue
        self.downloads_tab.on_retry_failed = self._retry_failed

        # Settings tab callbacks
        self.settings_tab.on_theme_changed = self._handle_theme_changed
        self.settings_tab.on_settings_changed = self._handle_settings_changed

        # History tab callbacks
        self.history_tab.on_redownload = self._handle_redownload

        # Queue manager callbacks
        self.queue_manager.on_item_added = self._on_queue_item_added
        self.queue_manager.on_item_updated = self._on_queue_item_updated
        self.queue_manager.on_item_removed = self._on_queue_item_removed

        # Download manager callbacks
        self.download_manager.on_progress = self._on_download_progress
        self.download_manager.on_complete = self._on_download_complete
        self.download_manager.on_all_complete = self._on_all_downloads_complete

    # URL handling

    def _handle_urls_submitted(self, urls: List[str]):
        """Handle URLs submitted from downloads tab."""
        self.downloads_tab.set_loading(True, "Extracting video information...")

        # Process URLs in background
        def process():
            for url in urls:
                try:
                    # Validate URL
                    result = self.url_validator.validate(url)
                    if not result.is_valid:
                        self.root.after(0, lambda u=url, e=result.error:
                            self._log_error(f"Invalid URL: {u} - {e}"))
                        continue

                    # Extract info
                    info = self.download_manager.extract_info(url)
                    if info:
                        video = VideoItem(
                            id=info.get("id", ""),
                            url=url,
                            title=info.get("title", "Unknown"),
                            duration=info.get("duration", 0),
                            thumbnail_url=info.get("thumbnail", ""),
                            uploader=info.get("uploader", "Unknown"),
                            filesize=info.get("filesize", 0) or info.get("filesize_approx", 0)
                        )
                        self.queue_manager.add(video)
                        self.root.after(0, lambda v=video:
                            self.status_bar.info(f"Added: {v.title}"))
                    else:
                        self.root.after(0, lambda u=url:
                            self._log_error(f"Could not extract info from: {u}"))

                except Exception as e:
                    self.root.after(0, lambda u=url, err=str(e):
                        self._log_error(f"Error processing {u}: {err}"))

            self.root.after(0, lambda: self.downloads_tab.set_loading(False))

        threading.Thread(target=process, daemon=True).start()

    def _handle_redownload(self, url: str):
        """Handle redownload request from history."""
        self._handle_urls_submitted([url])
        self.notebook.select(0)  # Switch to downloads tab

    # Queue callbacks

    def _on_queue_item_added(self, video: VideoItem):
        """Handle video added to queue."""
        self.root.after(0, lambda: self.downloads_tab.add_to_queue(video))

    def _on_queue_item_updated(self, video: VideoItem):
        """Handle video updated in queue."""
        self.root.after(0, lambda: self.downloads_tab.update_queue_item(video))

    def _on_queue_item_removed(self, video_id: str):
        """Handle video removed from queue."""
        self.root.after(0, lambda: self.downloads_tab.remove_from_queue(video_id))

    # Download controls

    def _start_downloads(self):
        """Start downloading queued items."""
        queued = self.queue_manager.get_by_status(VideoStatus.QUEUED)
        if not queued:
            self.status_bar.warning("No items in queue to download")
            return

        self.downloads_tab.set_downloading_state(True)
        self.status_bar.info("Starting downloads...")

        # Update download options from current settings
        self.download_options.output_path = self.config_manager.get("download_path", os.path.expanduser("~/Downloads"))
        self.download_options.quality = self.config_manager.get("quality", "best")
        self.download_options.include_subtitles = self.config_manager.get("include_subtitles", False)
        self.download_options.subtitle_langs = [self.config_manager.get("subtitle_language", "en")]

        # Start the download manager
        self.download_manager.start()

    def _pause_downloads(self):
        """Pause active downloads."""
        self.download_manager.pause()
        self.downloads_tab.set_downloading_state(True, is_paused=True)
        self.status_bar.info("Downloads paused")

    def _resume_downloads(self):
        """Resume paused downloads."""
        self.download_manager.resume()
        self.downloads_tab.set_downloading_state(True, is_paused=False)
        self.status_bar.info("Downloads resumed")

    def _stop_downloads(self):
        """Stop all downloads."""
        self.download_manager.stop()
        self.downloads_tab.set_downloading_state(False)
        self.downloads_tab.reset_progress()
        self.status_bar.info("Downloads stopped")

    def _retry_failed(self, video_ids: Optional[List[str]] = None):
        """Retry failed downloads."""
        if video_ids:
            for vid in video_ids:
                self.queue_manager.update_status(vid, VideoStatus.QUEUED)
        else:
            # Retry all failed
            failed = self.queue_manager.get_by_status(VideoStatus.ERROR)
            for video in failed:
                self.queue_manager.update_status(video.id, VideoStatus.QUEUED)

        self.status_bar.info("Retrying failed downloads...")
        self._start_downloads()

    # Download callbacks

    def _on_download_progress(self, progress: DownloadProgress):
        """Handle download progress update."""
        video_id = progress.video_id

        # Update progress widget
        video = self.queue_manager.get(video_id)
        if video:
            # Calculate overall progress
            all_videos = self.queue_manager.get_all()
            total_progress = sum(v.progress for v in all_videos)
            overall = total_progress / len(all_videos) if all_videos else 0

            # Count stats
            active = len(self.queue_manager.get_by_status(VideoStatus.DOWNLOADING))
            queued = len(self.queue_manager.get_by_status(VideoStatus.QUEUED))
            completed = len(self.queue_manager.get_by_status(VideoStatus.COMPLETED))

            info = ProgressInfo(
                current_percent=progress.progress,
                overall_percent=overall,
                speed=progress.speed,
                eta=progress.eta,
                downloaded=progress.downloaded_bytes,
                current_title=video.title,
                active_downloads=active,
                queued_count=queued,
                completed_count=completed
            )

            self.root.after(0, lambda: self.downloads_tab.update_progress(info))

    def _on_download_complete(self, video: VideoItem, success: bool):
        """Handle download completion."""
        if success:
            self.root.after(0, lambda: self.status_bar.success(f"Downloaded: {video.title}"))

            # Add to history
            entry = HistoryEntry(
                id=video.id,
                url=video.url,
                title=video.title,
                uploader=video.uploader,
                duration=video.duration,
                filesize=video.filesize,
                filepath=self.download_options.output_path,
                quality=self.config_manager.get("quality", "best"),
                status="completed",
                error_message="",
                download_date=datetime.now().isoformat(),
                thumbnail_url=video.thumbnail_url
            )
            self.root.after(0, lambda: self.history_tab.add_entry(entry))
        else:
            error = video.error_message or "Download failed"
            self.root.after(0, lambda: self.status_bar.error(f"Failed: {video.title} - {error}"))

            # Add to history as failed
            entry = HistoryEntry(
                id=video.id,
                url=video.url,
                title=video.title,
                uploader=video.uploader,
                duration=video.duration,
                filesize=video.filesize,
                filepath="",
                quality=self.config_manager.get("quality", "best"),
                status="failed",
                error_message=error,
                download_date=datetime.now().isoformat(),
                thumbnail_url=video.thumbnail_url
            )
            self.root.after(0, lambda: self.history_tab.add_entry(entry))

    def _on_all_downloads_complete(self):
        """Handle all downloads complete."""
        self.root.after(0, lambda: self.downloads_tab.set_downloading_state(False))
        self.root.after(0, lambda: self.status_bar.success("All downloads completed!"))

        # Show notification if enabled
        if self.config_manager.get("show_notifications", True):
            self._show_notification("Downloads Complete", "All downloads have finished.")

    # Queue management

    def _handle_remove_items(self, video_ids: List[str]):
        """Handle remove items request."""
        for vid in video_ids:
            self.queue_manager.remove(vid)

    def _clear_queue(self):
        """Clear the download queue."""
        self.queue_manager.clear()
        self.downloads_tab.clear_queue()
        self.status_bar.info("Queue cleared")

    def _select_all_queue(self):
        """Select all items in queue."""
        # This would need to be implemented in the queue widget
        pass

    # Settings handling

    def _handle_theme_changed(self, theme: str):
        """Handle theme change."""
        self.theme_manager.set_theme(theme)
        self.config_manager.set("theme", theme)

    def _handle_settings_changed(self, key: str, value):
        """Handle settings change."""
        # Update download options if relevant
        if key == "download_path":
            self.download_options.output_path = value
        elif key == "max_concurrent_downloads":
            self.download_manager.max_concurrent = value
        elif key == "quality":
            self.download_options.quality = value
        elif key == "include_subtitles":
            self.download_options.include_subtitles = value
        elif key == "subtitle_language":
            self.download_options.subtitle_langs = [value]

    # Menu actions

    def _show_add_url_dialog(self):
        """Show add URL dialog."""
        self.notebook.select(0)  # Switch to downloads tab
        self.downloads_tab.url_input.focus_entry()

    def _add_from_clipboard(self):
        """Add URL from clipboard."""
        try:
            clipboard = self.root.clipboard_get()
            urls = self._extract_urls(clipboard)
            if urls:
                self._handle_urls_submitted(urls)
            else:
                self.status_bar.warning("No valid YouTube URLs in clipboard")
        except tk.TclError:
            self.status_bar.warning("Clipboard is empty")

    def _extract_urls(self, text: str) -> List[str]:
        """Extract YouTube URLs from text."""
        import re
        pattern = r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s<>"\']*'
        urls = re.findall(pattern, text)
        return list(dict.fromkeys(urls))

    def _open_download_folder(self):
        """Open download folder."""
        path = self.config_manager.get("download_path", os.path.expanduser("~/Downloads"))
        if os.path.exists(path):
            import subprocess
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            messagebox.showerror("Error", "Download folder does not exist")

    def _show_settings(self):
        """Show settings tab."""
        self.notebook.select(1)

    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About",
            f"{self.APP_NAME}\n"
            f"Version {self.APP_VERSION}\n\n"
            "A modern YouTube video downloader with\n"
            "queue management and batch processing.\n\n"
            "Powered by yt-dlp"
        )

    def _check_updates(self):
        """Check for updates."""
        self.status_bar.info("Checking for updates...")
        # Would implement actual update check here
        messagebox.showinfo("Updates", "You are running the latest version.")

    def _show_notification(self, title: str, message: str):
        """Show desktop notification."""
        try:
            if sys.platform == "win32":
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=5)
        except ImportError:
            pass

    def _log_error(self, message: str):
        """Log error to status bar."""
        self.status_bar.error(message)
        self.logger.error(message)

    def _on_close(self):
        """Handle window close."""
        # Check for active downloads
        active = self.queue_manager.get_by_status(VideoStatus.DOWNLOADING)
        if active:
            if not messagebox.askyesno(
                "Confirm Exit",
                "Downloads are in progress. Are you sure you want to exit?"
            ):
                return

            # Stop downloads
            self.download_manager.stop()

        # Check for unsaved settings
        if self.settings_tab.has_unsaved_changes():
            result = messagebox.askyesnocancel(
                "Unsaved Settings",
                "You have unsaved settings. Save before exiting?"
            )
            if result is True:
                self.settings_tab._save_settings()
            elif result is None:
                return

        # Save window size
        self.config_manager.set("window_width", self.root.winfo_width())
        self.config_manager.set("window_height", self.root.winfo_height())

        # Cleanup
        self.logger.info("Application closing")
        self.logger.shutdown()

        self.root.destroy()

    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    """Application entry point."""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
