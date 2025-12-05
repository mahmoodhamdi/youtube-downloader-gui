"""Settings tab for YouTube Downloader.

Comprehensive settings interface with all configuration options.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Callable, Dict, Any
import os

from src.config.defaults import (
    QUALITY_OPTIONS, SUBTITLE_LANGUAGES, THEME_OPTIONS,
    MAX_CONCURRENT_DOWNLOADS, MIN_CONCURRENT_DOWNLOADS,
    MAX_RETRY_ATTEMPTS, MIN_RETRY_ATTEMPTS
)


class SettingsTab(ttk.Frame):
    """Settings interface tab.

    Features:
    - Download settings (path, quality, format)
    - Network settings (concurrent, retries, proxy)
    - Subtitle settings
    - Theme settings
    - Advanced settings

    Usage:
        tab = SettingsTab(notebook, config_manager)
        tab.on_settings_changed = callback
    """

    def __init__(self, parent, config_manager, theme_manager=None, **kwargs):
        """Initialize settings tab.

        Args:
            parent: Parent widget
            config_manager: Configuration manager instance
            theme_manager: Optional theme manager instance
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self.config = config_manager
        self.theme_manager = theme_manager

        # Callbacks
        self.on_settings_changed: Optional[Callable[[str, Any], None]] = None
        self.on_theme_changed: Optional[Callable[[str], None]] = None

        # Track unsaved changes
        self._pending_changes: Dict[str, Any] = {}

        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        """Build the tab UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Create canvas for scrolling
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)

        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.columnconfigure(0, weight=1)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Build sections
        self._build_download_section()
        self._build_network_section()
        self._build_subtitle_section()
        self._build_appearance_section()
        self._build_advanced_section()
        self._build_update_section()
        self._build_buttons()

    def _build_download_section(self):
        """Build download settings section."""
        section = ttk.LabelFrame(
            self.scrollable_frame,
            text="Download Settings",
            padding=15
        )
        section.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        section.columnconfigure(1, weight=1)

        row = 0

        # Download path
        ttk.Label(section, text="Download Path:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        path_frame = ttk.Frame(section)
        path_frame.grid(row=row, column=1, sticky="ew", pady=5)
        path_frame.columnconfigure(0, weight=1)

        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        ttk.Button(
            path_frame,
            text="Browse",
            command=self._browse_path
        ).grid(row=0, column=1)

        row += 1

        # Default quality
        ttk.Label(section, text="Default Quality:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        self.quality_var = tk.StringVar()
        quality_combo = ttk.Combobox(
            section,
            textvariable=self.quality_var,
            values=QUALITY_OPTIONS,
            state="readonly",
            width=20
        )
        quality_combo.grid(row=row, column=1, sticky="w", pady=5)
        quality_combo.bind("<<ComboboxSelected>>", lambda e: self._mark_changed("quality"))

        row += 1

        # Preferred format
        ttk.Label(section, text="Preferred Format:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        self.format_var = tk.StringVar()
        format_combo = ttk.Combobox(
            section,
            textvariable=self.format_var,
            values=["mp4", "mkv", "webm", "avi", "mov"],
            state="readonly",
            width=20
        )
        format_combo.grid(row=row, column=1, sticky="w", pady=5)
        format_combo.bind("<<ComboboxSelected>>", lambda e: self._mark_changed("preferred_format"))

        row += 1

        # Audio format for audio-only downloads
        ttk.Label(section, text="Audio Format:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        self.audio_format_var = tk.StringVar()
        audio_combo = ttk.Combobox(
            section,
            textvariable=self.audio_format_var,
            values=["mp3", "m4a", "opus", "wav", "flac"],
            state="readonly",
            width=20
        )
        audio_combo.grid(row=row, column=1, sticky="w", pady=5)
        audio_combo.bind("<<ComboboxSelected>>", lambda e: self._mark_changed("audio_format"))

        row += 1

        # Filename template
        ttk.Label(section, text="Filename Template:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        template_frame = ttk.Frame(section)
        template_frame.grid(row=row, column=1, sticky="ew", pady=5)
        template_frame.columnconfigure(0, weight=1)

        self.template_var = tk.StringVar()
        self.template_entry = ttk.Entry(template_frame, textvariable=self.template_var)
        self.template_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.template_entry.bind("<FocusOut>", lambda e: self._mark_changed("filename_template"))

        ttk.Button(
            template_frame,
            text="?",
            width=3,
            command=self._show_template_help
        ).grid(row=0, column=1)

        row += 1

        # Auto-organize by uploader
        self.organize_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Organize files by uploader/channel",
            variable=self.organize_var,
            command=lambda: self._mark_changed("organize_by_uploader")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

    def _build_network_section(self):
        """Build network settings section."""
        section = ttk.LabelFrame(
            self.scrollable_frame,
            text="Network Settings",
            padding=15
        )
        section.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        section.columnconfigure(1, weight=1)

        row = 0

        # Concurrent downloads
        ttk.Label(section, text="Concurrent Downloads:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        concurrent_frame = ttk.Frame(section)
        concurrent_frame.grid(row=row, column=1, sticky="w", pady=5)

        self.concurrent_var = tk.IntVar()
        concurrent_spin = ttk.Spinbox(
            concurrent_frame,
            from_=MIN_CONCURRENT_DOWNLOADS,
            to=MAX_CONCURRENT_DOWNLOADS,
            textvariable=self.concurrent_var,
            width=10
        )
        concurrent_spin.pack(side=tk.LEFT)
        concurrent_spin.bind("<FocusOut>", lambda e: self._mark_changed("max_concurrent_downloads"))

        ttk.Label(
            concurrent_frame,
            text="(1-5 recommended)",
            style="Subtitle.TLabel"
        ).pack(side=tk.LEFT, padx=(10, 0))

        row += 1

        # Retry attempts
        ttk.Label(section, text="Retry Attempts:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        self.retry_var = tk.IntVar()
        retry_spin = ttk.Spinbox(
            section,
            from_=MIN_RETRY_ATTEMPTS,
            to=MAX_RETRY_ATTEMPTS,
            textvariable=self.retry_var,
            width=10
        )
        retry_spin.grid(row=row, column=1, sticky="w", pady=5)
        retry_spin.bind("<FocusOut>", lambda e: self._mark_changed("retry_attempts"))

        row += 1

        # Rate limit
        ttk.Label(section, text="Rate Limit (KB/s):").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        rate_frame = ttk.Frame(section)
        rate_frame.grid(row=row, column=1, sticky="w", pady=5)

        self.rate_limit_var = tk.IntVar()
        rate_spin = ttk.Spinbox(
            rate_frame,
            from_=0,
            to=100000,
            textvariable=self.rate_limit_var,
            width=10
        )
        rate_spin.pack(side=tk.LEFT)
        rate_spin.bind("<FocusOut>", lambda e: self._mark_changed("rate_limit"))

        ttk.Label(
            rate_frame,
            text="(0 = unlimited)",
            style="Subtitle.TLabel"
        ).pack(side=tk.LEFT, padx=(10, 0))

        row += 1

        # Proxy settings
        ttk.Label(section, text="Proxy:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        self.proxy_var = tk.StringVar()
        proxy_entry = ttk.Entry(section, textvariable=self.proxy_var, width=40)
        proxy_entry.grid(row=row, column=1, sticky="w", pady=5)
        proxy_entry.bind("<FocusOut>", lambda e: self._mark_changed("proxy"))

        row += 1

        ttk.Label(
            section,
            text="Example: http://user:pass@proxy:port or socks5://proxy:port",
            style="Subtitle.TLabel"
        ).grid(row=row, column=1, sticky="w")

    def _build_subtitle_section(self):
        """Build subtitle settings section."""
        section = ttk.LabelFrame(
            self.scrollable_frame,
            text="Subtitle Settings",
            padding=15
        )
        section.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        section.columnconfigure(1, weight=1)

        row = 0

        # Download subtitles
        self.subtitles_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Download subtitles when available",
            variable=self.subtitles_var,
            command=self._on_subtitles_toggled
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

        row += 1

        # Preferred language
        ttk.Label(section, text="Preferred Language:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        self.sub_lang_var = tk.StringVar()
        lang_combo = ttk.Combobox(
            section,
            textvariable=self.sub_lang_var,
            values=SUBTITLE_LANGUAGES,
            state="readonly",
            width=20
        )
        lang_combo.grid(row=row, column=1, sticky="w", pady=5)
        lang_combo.bind("<<ComboboxSelected>>", lambda e: self._mark_changed("subtitle_language"))

        row += 1

        # Auto-generated subtitles
        self.auto_subs_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Include auto-generated subtitles",
            variable=self.auto_subs_var,
            command=lambda: self._mark_changed("auto_subtitles")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

        row += 1

        # Embed subtitles
        self.embed_subs_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Embed subtitles in video file",
            variable=self.embed_subs_var,
            command=lambda: self._mark_changed("embed_subtitles")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

    def _build_appearance_section(self):
        """Build appearance settings section."""
        section = ttk.LabelFrame(
            self.scrollable_frame,
            text="Appearance",
            padding=15
        )
        section.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        section.columnconfigure(1, weight=1)

        row = 0

        # Theme selection
        ttk.Label(section, text="Theme:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        theme_frame = ttk.Frame(section)
        theme_frame.grid(row=row, column=1, sticky="w", pady=5)

        self.theme_var = tk.StringVar()
        for theme in THEME_OPTIONS:
            ttk.Radiobutton(
                theme_frame,
                text=theme.title(),
                value=theme,
                variable=self.theme_var,
                command=self._on_theme_changed
            ).pack(side=tk.LEFT, padx=(0, 15))

        row += 1

        # Window size options
        ttk.Label(section, text="Window Size:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        size_frame = ttk.Frame(section)
        size_frame.grid(row=row, column=1, sticky="w", pady=5)

        ttk.Label(size_frame, text="Width:").pack(side=tk.LEFT)
        self.width_var = tk.IntVar()
        ttk.Spinbox(
            size_frame,
            from_=800,
            to=2560,
            textvariable=self.width_var,
            width=6
        ).pack(side=tk.LEFT, padx=(5, 15))

        ttk.Label(size_frame, text="Height:").pack(side=tk.LEFT)
        self.height_var = tk.IntVar()
        ttk.Spinbox(
            size_frame,
            from_=600,
            to=1440,
            textvariable=self.height_var,
            width=6
        ).pack(side=tk.LEFT, padx=(5, 0))

        row += 1

        # Show notifications
        self.notifications_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Show desktop notifications on completion",
            variable=self.notifications_var,
            command=lambda: self._mark_changed("show_notifications")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

        row += 1

        # Minimize to tray
        self.tray_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Minimize to system tray",
            variable=self.tray_var,
            command=lambda: self._mark_changed("minimize_to_tray")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

    def _build_advanced_section(self):
        """Build advanced settings section."""
        section = ttk.LabelFrame(
            self.scrollable_frame,
            text="Advanced Settings",
            padding=15
        )
        section.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))
        section.columnconfigure(1, weight=1)

        row = 0

        # FFmpeg path
        ttk.Label(section, text="FFmpeg Path:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        ffmpeg_frame = ttk.Frame(section)
        ffmpeg_frame.grid(row=row, column=1, sticky="ew", pady=5)
        ffmpeg_frame.columnconfigure(0, weight=1)

        self.ffmpeg_var = tk.StringVar()
        ttk.Entry(ffmpeg_frame, textvariable=self.ffmpeg_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )

        ttk.Button(
            ffmpeg_frame,
            text="Browse",
            command=self._browse_ffmpeg
        ).grid(row=0, column=1)

        row += 1

        # Keep original files
        self.keep_original_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Keep original files after conversion",
            variable=self.keep_original_var,
            command=lambda: self._mark_changed("keep_original")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

        row += 1

        # Write metadata
        self.metadata_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Write video metadata to file",
            variable=self.metadata_var,
            command=lambda: self._mark_changed("write_metadata")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

        row += 1

        # Write thumbnail
        self.thumbnail_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Embed thumbnail in file",
            variable=self.thumbnail_var,
            command=lambda: self._mark_changed("embed_thumbnail")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

        row += 1

        # Cookie file
        ttk.Label(section, text="Cookie File:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        cookie_frame = ttk.Frame(section)
        cookie_frame.grid(row=row, column=1, sticky="ew", pady=5)
        cookie_frame.columnconfigure(0, weight=1)

        self.cookie_var = tk.StringVar()
        ttk.Entry(cookie_frame, textvariable=self.cookie_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )

        ttk.Button(
            cookie_frame,
            text="Browse",
            command=self._browse_cookies
        ).grid(row=0, column=1)

        row += 1

        ttk.Label(
            section,
            text="Use cookies for age-restricted or private videos",
            style="Subtitle.TLabel"
        ).grid(row=row, column=1, sticky="w")

        row += 1

        # Debug mode
        self.debug_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Enable debug logging",
            variable=self.debug_var,
            command=lambda: self._mark_changed("debug_mode")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

    def _build_update_section(self):
        """Build yt-dlp update settings section."""
        section = ttk.LabelFrame(
            self.scrollable_frame,
            text="yt-dlp Updates",
            padding=15
        )
        section.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 10))
        section.columnconfigure(1, weight=1)

        row = 0

        # Current version display
        ttk.Label(section, text="Current Version:").grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )

        version_frame = ttk.Frame(section)
        version_frame.grid(row=row, column=1, sticky="w", pady=5)

        self.ytdlp_version_label = ttk.Label(
            version_frame,
            text="Loading...",
            font=("", 9, "bold")
        )
        self.ytdlp_version_label.pack(side=tk.LEFT)

        # Load version in background
        self.after(100, self._load_ytdlp_version)

        row += 1

        # Auto-check updates
        self.auto_update_check_var = tk.BooleanVar()
        ttk.Checkbutton(
            section,
            text="Check for updates when application starts",
            variable=self.auto_update_check_var,
            command=lambda: self._mark_changed("auto_check_updates")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

        row += 1

        # Update button
        btn_frame = ttk.Frame(section)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 0))

        ttk.Button(
            btn_frame,
            text="Check for Updates",
            command=self._show_update_dialog
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(
            btn_frame,
            text="Keep yt-dlp updated for best YouTube compatibility",
            style="Subtitle.TLabel"
        ).pack(side=tk.LEFT)

    def _load_ytdlp_version(self):
        """Load yt-dlp version in background."""
        import threading

        def load_version():
            try:
                import yt_dlp
                version = yt_dlp.version.__version__
            except Exception:
                version = "Unknown"
            self.after(0, lambda: self.ytdlp_version_label.config(text=version))

        thread = threading.Thread(target=load_version, daemon=True)
        thread.start()

    def _show_update_dialog(self):
        """Show the yt-dlp update dialog."""
        from src.ui.dialogs.update_dialog import show_update_dialog
        show_update_dialog(self.winfo_toplevel())

    def _build_buttons(self):
        """Build action buttons."""
        btn_frame = ttk.Frame(self.scrollable_frame)
        btn_frame.grid(row=6, column=0, sticky="ew", padx=10, pady=(0, 20))

        # Save button
        self.save_btn = ttk.Button(
            btn_frame,
            text="Save Settings",
            command=self._save_settings,
            style="Accent.TButton"
        )
        self.save_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Reset button
        ttk.Button(
            btn_frame,
            text="Reset to Defaults",
            command=self._reset_defaults
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Export/Import buttons
        ttk.Button(
            btn_frame,
            text="Export Settings",
            command=self._export_settings
        ).pack(side=tk.RIGHT, padx=(10, 0))

        ttk.Button(
            btn_frame,
            text="Import Settings",
            command=self._import_settings
        ).pack(side=tk.RIGHT)

    def _load_settings(self):
        """Load settings from config manager."""
        # Download settings
        self.path_var.set(self.config.get("download_path", ""))
        self.quality_var.set(self.config.get("quality", "best"))
        self.format_var.set(self.config.get("preferred_format", "mp4"))
        self.audio_format_var.set(self.config.get("audio_format", "mp3"))
        self.template_var.set(self.config.get("filename_template", "%(title)s.%(ext)s"))
        self.organize_var.set(self.config.get("organize_by_uploader", False))

        # Network settings
        self.concurrent_var.set(self.config.get("max_concurrent_downloads", 2))
        self.retry_var.set(self.config.get("retry_attempts", 3))
        self.rate_limit_var.set(self.config.get("rate_limit", 0))
        self.proxy_var.set(self.config.get("proxy", ""))

        # Subtitle settings
        self.subtitles_var.set(self.config.get("include_subtitles", False))
        self.sub_lang_var.set(self.config.get("subtitle_language", "en"))
        self.auto_subs_var.set(self.config.get("auto_subtitles", True))
        self.embed_subs_var.set(self.config.get("embed_subtitles", False))

        # Appearance settings
        self.theme_var.set(self.config.get("theme", "system"))
        self.width_var.set(self.config.get("window_width", 1200))
        self.height_var.set(self.config.get("window_height", 800))
        self.notifications_var.set(self.config.get("show_notifications", True))
        self.tray_var.set(self.config.get("minimize_to_tray", False))

        # Advanced settings
        self.ffmpeg_var.set(self.config.get("ffmpeg_path", ""))
        self.keep_original_var.set(self.config.get("keep_original", False))
        self.metadata_var.set(self.config.get("write_metadata", True))
        self.thumbnail_var.set(self.config.get("embed_thumbnail", False))
        self.cookie_var.set(self.config.get("cookie_file", ""))
        self.debug_var.set(self.config.get("debug_mode", False))

        # Update settings
        self.auto_update_check_var.set(self.config.get("auto_check_updates", True))

        # Update subtitle controls state
        self._on_subtitles_toggled()

    def _save_settings(self):
        """Save all settings to config."""
        # Download settings
        self.config.set("download_path", self.path_var.get())
        self.config.set("quality", self.quality_var.get())
        self.config.set("preferred_format", self.format_var.get())
        self.config.set("audio_format", self.audio_format_var.get())
        self.config.set("filename_template", self.template_var.get())
        self.config.set("organize_by_uploader", self.organize_var.get())

        # Network settings
        self.config.set("max_concurrent_downloads", self.concurrent_var.get())
        self.config.set("retry_attempts", self.retry_var.get())
        self.config.set("rate_limit", self.rate_limit_var.get())
        self.config.set("proxy", self.proxy_var.get())

        # Subtitle settings
        self.config.set("include_subtitles", self.subtitles_var.get())
        self.config.set("subtitle_language", self.sub_lang_var.get())
        self.config.set("auto_subtitles", self.auto_subs_var.get())
        self.config.set("embed_subtitles", self.embed_subs_var.get())

        # Appearance settings
        self.config.set("theme", self.theme_var.get())
        self.config.set("window_width", self.width_var.get())
        self.config.set("window_height", self.height_var.get())
        self.config.set("show_notifications", self.notifications_var.get())
        self.config.set("minimize_to_tray", self.tray_var.get())

        # Advanced settings
        self.config.set("ffmpeg_path", self.ffmpeg_var.get())
        self.config.set("keep_original", self.keep_original_var.get())
        self.config.set("write_metadata", self.metadata_var.get())
        self.config.set("embed_thumbnail", self.thumbnail_var.get())
        self.config.set("cookie_file", self.cookie_var.get())
        self.config.set("debug_mode", self.debug_var.get())

        # Update settings
        self.config.set("auto_check_updates", self.auto_update_check_var.get())

        # Clear pending changes
        self._pending_changes.clear()

        messagebox.showinfo("Settings", "Settings saved successfully!")

    def _reset_defaults(self):
        """Reset all settings to defaults."""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            self.config.reset_to_defaults()
            self._load_settings()
            messagebox.showinfo("Settings", "Settings reset to defaults.")

    def _mark_changed(self, key: str):
        """Mark a setting as changed."""
        self._pending_changes[key] = True

        if self.on_settings_changed:
            # Get the new value
            value = self._get_setting_value(key)
            self.on_settings_changed(key, value)

    def _get_setting_value(self, key: str):
        """Get the current value of a setting."""
        mapping = {
            "quality": self.quality_var,
            "preferred_format": self.format_var,
            "audio_format": self.audio_format_var,
            "filename_template": self.template_var,
            "organize_by_uploader": self.organize_var,
            "max_concurrent_downloads": self.concurrent_var,
            "retry_attempts": self.retry_var,
            "rate_limit": self.rate_limit_var,
            "proxy": self.proxy_var,
            "include_subtitles": self.subtitles_var,
            "subtitle_language": self.sub_lang_var,
            "auto_subtitles": self.auto_subs_var,
            "embed_subtitles": self.embed_subs_var,
            "show_notifications": self.notifications_var,
            "minimize_to_tray": self.tray_var,
            "keep_original": self.keep_original_var,
            "write_metadata": self.metadata_var,
            "embed_thumbnail": self.thumbnail_var,
            "debug_mode": self.debug_var,
        }

        var = mapping.get(key)
        return var.get() if var else None

    def _browse_path(self):
        """Browse for download path."""
        current = self.path_var.get()
        path = filedialog.askdirectory(initialdir=current)

        if path:
            self.path_var.set(path)
            self._mark_changed("download_path")

    def _browse_ffmpeg(self):
        """Browse for FFmpeg executable."""
        path = filedialog.askopenfilename(
            title="Select FFmpeg executable",
            filetypes=[
                ("Executable", "*.exe"),
                ("All files", "*.*")
            ]
        )

        if path:
            self.ffmpeg_var.set(path)
            self._mark_changed("ffmpeg_path")

    def _browse_cookies(self):
        """Browse for cookie file."""
        path = filedialog.askopenfilename(
            title="Select cookie file",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )

        if path:
            self.cookie_var.set(path)
            self._mark_changed("cookie_file")

    def _show_template_help(self):
        """Show filename template help."""
        help_text = """Filename Template Variables:

%(title)s - Video title
%(id)s - Video ID
%(uploader)s - Channel/uploader name
%(upload_date)s - Upload date (YYYYMMDD)
%(duration)s - Duration in seconds
%(view_count)s - View count
%(like_count)s - Like count
%(ext)s - File extension

Examples:
%(title)s.%(ext)s → Video Title.mp4
%(uploader)s - %(title)s.%(ext)s → Channel - Video Title.mp4
%(upload_date)s_%(title)s.%(ext)s → 20240101_Video Title.mp4
"""
        messagebox.showinfo("Filename Template Help", help_text)

    def _on_subtitles_toggled(self):
        """Handle subtitles checkbox toggle."""
        enabled = self.subtitles_var.get()
        state = "normal" if enabled else "disabled"

        # This would need to update the subtitle-related widgets
        self._mark_changed("include_subtitles")

    def _on_theme_changed(self):
        """Handle theme change."""
        theme = self.theme_var.get()

        if self.theme_manager:
            self.theme_manager.set_theme(theme)

        if self.on_theme_changed:
            self.on_theme_changed(theme)

        self._mark_changed("theme")

    def _export_settings(self):
        """Export settings to file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Export Settings"
        )

        if filepath:
            try:
                self.config.export_to_file(filepath)
                messagebox.showinfo("Export", f"Settings exported to {filepath}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}")

    def _import_settings(self):
        """Import settings from file."""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Import Settings"
        )

        if filepath:
            try:
                self.config.import_from_file(filepath)
                self._load_settings()
                messagebox.showinfo("Import", "Settings imported successfully!")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import: {e}")

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes.

        Returns:
            True if unsaved changes exist
        """
        return len(self._pending_changes) > 0
