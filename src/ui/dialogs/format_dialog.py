"""Format selection dialog for YouTube videos.

Provides UI for viewing and selecting video formats.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, List

from src.core.format_selector import (
    FormatSelector, FormatInfo, VideoFormats, FormatType
)


class FormatDialog(tk.Toplevel):
    """Dialog for selecting video format.

    Features:
    - Display all available formats in a table
    - Filter by video/audio type
    - Sort by quality, size, or bitrate
    - Show format details
    - Select format for download

    Usage:
        def on_format_selected(format_id):
            print(f"Selected format: {format_id}")

        dialog = FormatDialog(
            parent,
            url="https://youtube.com/watch?v=...",
            on_select=on_format_selected
        )
    """

    def __init__(
        self,
        parent,
        url: str,
        format_selector: Optional[FormatSelector] = None,
        on_select: Optional[Callable[[str], None]] = None
    ):
        """Initialize format dialog.

        Args:
            parent: Parent window
            url: YouTube video URL
            format_selector: Optional FormatSelector instance
            on_select: Callback when format is selected (receives format_id)
        """
        super().__init__(parent)

        self.url = url
        self.format_selector = format_selector or FormatSelector()
        self.on_select = on_select

        self._video_formats: Optional[VideoFormats] = None
        self._filtered_formats: List[FormatInfo] = []
        self._selected_format: Optional[FormatInfo] = None

        self.title("Select Format")
        self.geometry("800x550")
        self.minsize(700, 450)

        # Center on parent
        self.transient(parent)

        self._build_ui()
        self._fetch_formats()

    def _build_ui(self):
        """Build the dialog UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Header with video info
        self._build_header()

        # Filter controls
        self._build_filters()

        # Format table
        self._build_format_table()

        # Buttons
        self._build_buttons()

    def _build_header(self):
        """Build header section with video info."""
        header = ttk.Frame(self, padding=15)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        # Title
        self.title_label = ttk.Label(
            header,
            text="Loading video information...",
            font=("", 12, "bold"),
            wraplength=750
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        # Video info
        self.info_label = ttk.Label(
            header,
            text="",
            foreground="gray"
        )
        self.info_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

    def _build_filters(self):
        """Build filter controls."""
        filter_frame = ttk.LabelFrame(self, text="Filters", padding=10)
        filter_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Type filter
        ttk.Label(filter_frame, text="Type:").pack(side=tk.LEFT)

        self.type_var = tk.StringVar(value="all")
        type_options = [
            ("All", "all"),
            ("Video + Audio", "combined"),
            ("Video Only", "video"),
            ("Audio Only", "audio"),
        ]

        for text, value in type_options:
            ttk.Radiobutton(
                filter_frame,
                text=text,
                value=value,
                variable=self.type_var,
                command=self._apply_filters
            ).pack(side=tk.LEFT, padx=5)

        # Separator
        ttk.Separator(filter_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=15
        )

        # Sort
        ttk.Label(filter_frame, text="Sort by:").pack(side=tk.LEFT)

        self.sort_var = tk.StringVar(value="quality")
        sort_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.sort_var,
            values=["quality", "size", "bitrate"],
            state="readonly",
            width=10
        )
        sort_combo.pack(side=tk.LEFT, padx=(5, 0))
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

    def _build_format_table(self):
        """Build the format table."""
        table_frame = ttk.Frame(self)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=10)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Columns
        columns = ("quality", "ext", "resolution", "fps", "codec", "size", "bitrate")

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # Column headings and widths
        self.tree.heading("quality", text="Quality")
        self.tree.heading("ext", text="Format")
        self.tree.heading("resolution", text="Resolution")
        self.tree.heading("fps", text="FPS")
        self.tree.heading("codec", text="Codec")
        self.tree.heading("size", text="Size")
        self.tree.heading("bitrate", text="Bitrate")

        self.tree.column("quality", width=80, anchor="center")
        self.tree.column("ext", width=60, anchor="center")
        self.tree.column("resolution", width=100, anchor="center")
        self.tree.column("fps", width=50, anchor="center")
        self.tree.column("codec", width=150, anchor="w")
        self.tree.column("size", width=80, anchor="e")
        self.tree.column("bitrate", width=80, anchor="e")

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind selection
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)
        self.tree.bind("<Double-1>", self._on_double_click)

        # Progress bar for loading
        self.progress = ttk.Progressbar(
            table_frame,
            mode="indeterminate",
            length=200
        )

    def _build_buttons(self):
        """Build action buttons."""
        btn_frame = ttk.Frame(self, padding=15)
        btn_frame.grid(row=3, column=0, sticky="ew")

        # Status label
        self.status_label = ttk.Label(btn_frame, text="")
        self.status_label.pack(side=tk.LEFT)

        # Buttons on right
        ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=(10, 0))

        self.select_btn = ttk.Button(
            btn_frame,
            text="Select Format",
            command=self._select_format,
            state="disabled"
        )
        self.select_btn.pack(side=tk.RIGHT)

    def _fetch_formats(self):
        """Fetch formats for the URL."""
        self.title_label.config(text="Loading video information...")
        self.info_label.config(text="Please wait...")

        # Show loading
        self.progress.grid(row=1, column=0, pady=20)
        self.progress.start(10)

        # Fetch async
        self.format_selector.get_formats_async(
            self.url,
            on_complete=lambda result: self.after(0, lambda: self._on_formats_loaded(result)),
            on_progress=lambda msg: self.after(0, lambda: self.status_label.config(text=msg))
        )

    def _on_formats_loaded(self, result: VideoFormats):
        """Handle formats loaded.

        Args:
            result: VideoFormats result
        """
        self.progress.stop()
        self.progress.grid_remove()

        self._video_formats = result

        if result.error:
            self.title_label.config(text="Error loading video")
            self.info_label.config(text=result.error, foreground="red")
            return

        # Update header
        self.title_label.config(text=result.title or "Unknown Title")

        # Format duration
        duration = result.duration
        if duration:
            hours, remainder = divmod(duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                duration_str = f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
            else:
                duration_str = f"{int(minutes)}:{int(seconds):02d}"
        else:
            duration_str = "Unknown"

        self.info_label.config(
            text=f"Duration: {duration_str} | {len(result.formats)} formats available",
            foreground="gray"
        )

        # Apply filters and populate table
        self._apply_filters()

    def _apply_filters(self):
        """Apply current filters and update table."""
        if not self._video_formats:
            return

        formats = self._video_formats.formats

        # Type filter
        type_filter = self.type_var.get()
        if type_filter == "combined":
            formats = [f for f in formats if f.has_video and f.has_audio]
        elif type_filter == "video":
            formats = [f for f in formats if f.has_video and not f.has_audio]
        elif type_filter == "audio":
            formats = [f for f in formats if f.has_audio and not f.has_video]

        # Sort
        sort_by = self.sort_var.get()
        formats = self.format_selector.sort_formats(formats, by=sort_by)

        self._filtered_formats = formats
        self._populate_table()

    def _populate_table(self):
        """Populate the format table."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        for fmt in self._filtered_formats:
            # Determine type icon
            if fmt.has_video and fmt.has_audio:
                type_prefix = ""  # Combined
            elif fmt.has_video:
                type_prefix = "[V] "  # Video only
            else:
                type_prefix = "[A] "  # Audio only

            # Codec info
            if fmt.has_video and fmt.has_audio:
                codec = f"{fmt.vcodec} + {fmt.acodec}"
            elif fmt.has_video:
                codec = fmt.vcodec
            else:
                codec = fmt.acodec

            # FPS
            fps = f"{int(fmt.fps)}" if fmt.fps else "-"

            values = (
                f"{type_prefix}{fmt.quality_label}",
                fmt.ext.upper(),
                fmt.resolution or "-",
                fps,
                codec,
                fmt.size_str,
                fmt.bitrate_str,
            )

            self.tree.insert("", tk.END, iid=fmt.format_id, values=values)

        # Update status
        self.status_label.config(text=f"{len(self._filtered_formats)} formats")

    def _on_selection_changed(self, event):
        """Handle table selection change."""
        selection = self.tree.selection()
        if selection:
            format_id = selection[0]
            self._selected_format = next(
                (f for f in self._filtered_formats if f.format_id == format_id),
                None
            )
            self.select_btn.config(state="normal")
        else:
            self._selected_format = None
            self.select_btn.config(state="disabled")

    def _on_double_click(self, event):
        """Handle double-click on table row."""
        if self._selected_format:
            self._select_format()

    def _select_format(self):
        """Select the current format and close dialog."""
        if not self._selected_format:
            return

        if self.on_select:
            self.on_select(self._selected_format.format_id)

        self.destroy()

    def get_selected_format(self) -> Optional[str]:
        """Get the selected format ID.

        Returns:
            Selected format ID or None
        """
        if self._selected_format:
            return self._selected_format.format_id
        return None


def show_format_dialog(
    parent,
    url: str,
    on_select: Optional[Callable[[str], None]] = None,
    format_selector: Optional[FormatSelector] = None
) -> FormatDialog:
    """Show the format selection dialog.

    Args:
        parent: Parent window
        url: YouTube video URL
        on_select: Callback when format is selected
        format_selector: Optional FormatSelector instance

    Returns:
        The dialog instance
    """
    dialog = FormatDialog(
        parent,
        url=url,
        format_selector=format_selector,
        on_select=on_select
    )
    dialog.grab_set()
    return dialog
