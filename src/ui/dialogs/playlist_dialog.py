"""Playlist selection dialog for YouTube playlists.

Provides UI for viewing and selecting videos from a playlist.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, List

from src.core.playlist_filter import (
    PlaylistFilter, PlaylistInfo, PlaylistVideoInfo
)
from src.ui.styled_widgets import StyledEntry, DRACULA


class PlaylistDialog(tk.Toplevel):
    """Dialog for selecting videos from a playlist.

    Features:
    - Display all videos in a table with checkboxes
    - Select All / Deselect All
    - Filter by duration, date, index
    - Search by title
    - Show total duration and count

    Usage:
        def on_videos_selected(urls):
            for url in urls:
                add_to_queue(url)

        dialog = PlaylistDialog(
            parent,
            url="https://youtube.com/playlist?list=...",
            on_select=on_videos_selected
        )
    """

    def __init__(
        self,
        parent,
        url: str,
        playlist_filter: Optional[PlaylistFilter] = None,
        on_select: Optional[Callable[[List[str]], None]] = None
    ):
        """Initialize playlist dialog.

        Args:
            parent: Parent window
            url: YouTube playlist URL
            playlist_filter: Optional PlaylistFilter instance
            on_select: Callback when videos are selected (receives list of URLs)
        """
        super().__init__(parent)

        self.url = url
        self.playlist_filter = playlist_filter or PlaylistFilter()
        self.on_select = on_select

        self._playlist_info: Optional[PlaylistInfo] = None
        self._filtered_videos: List[PlaylistVideoInfo] = []
        self._selected_indices: set = set()

        self.title("Select Videos from Playlist")
        self.geometry("900x600")
        self.minsize(800, 500)
        self.configure(bg=DRACULA["bg"])

        # Center on parent
        self.transient(parent)

        self._build_ui()
        self._fetch_playlist()

    def _build_ui(self):
        """Build the dialog UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Header
        self._build_header()

        # Filters
        self._build_filters()

        # Video table
        self._build_video_table()

        # Buttons
        self._build_buttons()

    def _build_header(self):
        """Build header section."""
        header = ttk.Frame(self, padding=15)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        # Title
        self.title_label = ttk.Label(
            header,
            text="Loading playlist...",
            font=("", 12, "bold"),
            wraplength=850
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        # Info
        self.info_label = ttk.Label(
            header,
            text="",
            foreground="gray"
        )
        self.info_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

    def _build_filters(self):
        """Build filter section."""
        filter_frame = ttk.LabelFrame(self, text="Filters", padding=10)
        filter_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        filter_frame.columnconfigure(5, weight=1)

        # Search
        ttk.Label(filter_frame, text="Search:").grid(row=0, column=0, padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_entry = StyledEntry(filter_frame, textvariable=self.search_var, width=25)
        self.search_entry.grid(row=0, column=1, padx=(0, 15))
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filters())

        # Duration filter
        ttk.Label(filter_frame, text="Duration:").grid(row=0, column=2, padx=(0, 5))

        self.duration_var = tk.StringVar(value="all")
        duration_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.duration_var,
            values=["All", "< 5 min", "< 10 min", "< 30 min", "> 30 min", "> 1 hour"],
            state="readonly",
            width=12
        )
        duration_combo.grid(row=0, column=3, padx=(0, 15))
        duration_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Index range
        ttk.Label(filter_frame, text="Range:").grid(row=0, column=4, padx=(0, 5))

        range_frame = ttk.Frame(filter_frame)
        range_frame.grid(row=0, column=5, sticky="w")

        self.start_var = tk.StringVar(value="1")
        StyledEntry(range_frame, textvariable=self.start_var, width=5).pack(side=tk.LEFT)
        ttk.Label(range_frame, text=" to ").pack(side=tk.LEFT)
        self.end_var = tk.StringVar(value="")
        StyledEntry(range_frame, textvariable=self.end_var, width=5).pack(side=tk.LEFT)
        ttk.Button(
            range_frame,
            text="Apply",
            command=self._apply_filters,
            width=6
        ).pack(side=tk.LEFT, padx=(10, 0))

    def _build_video_table(self):
        """Build the video table."""
        table_frame = ttk.Frame(self)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=10)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Selection buttons above table
        sel_frame = ttk.Frame(table_frame)
        sel_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

        ttk.Button(
            sel_frame,
            text="Select All",
            command=self._select_all
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            sel_frame,
            text="Deselect All",
            command=self._deselect_all
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            sel_frame,
            text="Invert Selection",
            command=self._invert_selection
        ).pack(side=tk.LEFT)

        # Selection count
        self.selection_label = ttk.Label(
            sel_frame,
            text="0 selected",
            foreground="gray"
        )
        self.selection_label.pack(side=tk.RIGHT)

        # Columns
        columns = ("index", "title", "duration", "uploader", "views", "date")

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="tree headings",
            selectmode="extended"
        )

        # Column headings and widths
        self.tree.heading("#0", text="")
        self.tree.heading("index", text="#")
        self.tree.heading("title", text="Title")
        self.tree.heading("duration", text="Duration")
        self.tree.heading("uploader", text="Channel")
        self.tree.heading("views", text="Views")
        self.tree.heading("date", text="Date")

        self.tree.column("#0", width=40, stretch=False)
        self.tree.column("index", width=40, anchor="center")
        self.tree.column("title", width=350, anchor="w")
        self.tree.column("duration", width=70, anchor="center")
        self.tree.column("uploader", width=150, anchor="w")
        self.tree.column("views", width=70, anchor="e")
        self.tree.column("date", width=90, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        # Bind events
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<space>", self._toggle_selected)

        # Progress bar
        self.progress = ttk.Progressbar(
            table_frame,
            mode="indeterminate",
            length=200
        )

    def _build_buttons(self):
        """Build action buttons."""
        btn_frame = ttk.Frame(self, padding=15)
        btn_frame.grid(row=3, column=0, sticky="ew")

        # Status
        self.status_label = ttk.Label(btn_frame, text="")
        self.status_label.pack(side=tk.LEFT)

        # Duration info
        self.duration_label = ttk.Label(
            btn_frame,
            text="",
            foreground="gray"
        )
        self.duration_label.pack(side=tk.LEFT, padx=(20, 0))

        # Buttons
        ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=(10, 0))

        self.add_btn = ttk.Button(
            btn_frame,
            text="Add Selected to Queue",
            command=self._add_selected,
            state="disabled"
        )
        self.add_btn.pack(side=tk.RIGHT)

    def _fetch_playlist(self):
        """Fetch playlist information."""
        self.title_label.config(text="Loading playlist...")
        self.info_label.config(text="Please wait...")

        # Show loading
        self.progress.grid(row=2, column=0, pady=20)
        self.progress.start(10)

        # Fetch async
        self.playlist_filter.get_playlist_info_async(
            self.url,
            on_complete=lambda result: self.after(0, lambda: self._on_playlist_loaded(result)),
            on_progress=lambda msg: self.after(0, lambda: self.status_label.config(text=msg))
        )

    def _on_playlist_loaded(self, result: PlaylistInfo):
        """Handle playlist loaded."""
        self.progress.stop()
        self.progress.grid_remove()

        self._playlist_info = result

        if result.error:
            self.title_label.config(text="Error loading playlist")
            self.info_label.config(text=result.error, foreground="red")
            return

        # Update header
        self.title_label.config(text=result.title or "Unknown Playlist")
        self.info_label.config(
            text=f"By: {result.uploader or 'Unknown'} | {result.video_count} videos | Total: {result.total_duration_str}",
            foreground="gray"
        )

        # Set end range default
        self.end_var.set(str(result.video_count))

        # Apply filters and populate
        self._apply_filters()

    def _apply_filters(self):
        """Apply filters and update table."""
        if not self._playlist_info:
            return

        videos = self._playlist_info.videos

        # Search filter
        search_query = self.search_var.get().strip()
        if search_query:
            videos = self.playlist_filter.search_by_title(videos, search_query)

        # Duration filter
        duration_filter = self.duration_var.get()
        if duration_filter == "< 5 min":
            videos = self.playlist_filter.filter_by_duration(videos, max_seconds=300)
        elif duration_filter == "< 10 min":
            videos = self.playlist_filter.filter_by_duration(videos, max_seconds=600)
        elif duration_filter == "< 30 min":
            videos = self.playlist_filter.filter_by_duration(videos, max_seconds=1800)
        elif duration_filter == "> 30 min":
            videos = self.playlist_filter.filter_by_duration(videos, min_seconds=1800)
        elif duration_filter == "> 1 hour":
            videos = self.playlist_filter.filter_by_duration(videos, min_seconds=3600)

        # Index range filter
        try:
            start = int(self.start_var.get()) if self.start_var.get() else 1
            end = int(self.end_var.get()) if self.end_var.get() else 0
            videos = self.playlist_filter.filter_by_index(videos, start, end)
        except ValueError:
            pass

        self._filtered_videos = videos
        self._populate_table()

    def _populate_table(self):
        """Populate the video table."""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)

        for video in self._filtered_videos:
            # Checkbox state
            checked = video.index in self._selected_indices
            checkbox = "[x]" if checked else "[ ]"

            # Availability indicator
            if not video.is_available:
                title = f"[UNAVAILABLE] {video.title}"
            else:
                title = video.title

            values = (
                video.index,
                title,
                video.duration_str or "-",
                video.uploader or "-",
                video.formatted_views,
                video.formatted_date,
            )

            self.tree.insert(
                "",
                tk.END,
                iid=str(video.index),
                text=checkbox,
                values=values,
                tags=("unavailable",) if not video.is_available else ()
            )

        # Style unavailable
        self.tree.tag_configure("unavailable", foreground="gray")

        # Update status
        self._update_selection_count()

    def _on_click(self, event):
        """Handle table click."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "tree":
            # Clicked on checkbox column
            item = self.tree.identify_row(event.y)
            if item:
                self._toggle_item(item)

    def _toggle_selected(self, event=None):
        """Toggle selection for currently selected items."""
        for item in self.tree.selection():
            self._toggle_item(item)

    def _toggle_item(self, item: str):
        """Toggle selection for an item."""
        try:
            index = int(item)
            video = next((v for v in self._filtered_videos if v.index == index), None)

            if video and video.is_available:
                if index in self._selected_indices:
                    self._selected_indices.discard(index)
                    self.tree.item(item, text="[ ]")
                else:
                    self._selected_indices.add(index)
                    self.tree.item(item, text="[x]")

                self._update_selection_count()
        except (ValueError, StopIteration):
            pass

    def _select_all(self):
        """Select all visible videos."""
        for video in self._filtered_videos:
            if video.is_available:
                self._selected_indices.add(video.index)

        self._populate_table()

    def _deselect_all(self):
        """Deselect all videos."""
        self._selected_indices.clear()
        self._populate_table()

    def _invert_selection(self):
        """Invert selection."""
        for video in self._filtered_videos:
            if video.is_available:
                if video.index in self._selected_indices:
                    self._selected_indices.discard(video.index)
                else:
                    self._selected_indices.add(video.index)

        self._populate_table()

    def _update_selection_count(self):
        """Update selection count display."""
        count = len(self._selected_indices)
        self.selection_label.config(text=f"{count} selected")

        # Calculate total duration of selected
        if self._playlist_info:
            total_duration = sum(
                v.duration for v in self._playlist_info.videos
                if v.index in self._selected_indices and v.duration
            )
            hours, remainder = divmod(total_duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                duration_str = f"{int(hours)}h {int(minutes)}m"
            else:
                duration_str = f"{int(minutes)}m {int(seconds)}s"
            self.duration_label.config(text=f"Selected duration: {duration_str}")

        # Enable/disable add button
        if count > 0:
            self.add_btn.config(state="normal")
        else:
            self.add_btn.config(state="disabled")

    def _add_selected(self):
        """Add selected videos to queue."""
        if not self._playlist_info:
            return

        # Get URLs of selected videos
        urls = []
        for video in self._playlist_info.videos:
            if video.index in self._selected_indices and video.is_available:
                urls.append(video.url)

        if urls and self.on_select:
            self.on_select(urls)

        self.destroy()

    def get_selected_urls(self) -> List[str]:
        """Get URLs of selected videos.

        Returns:
            List of video URLs
        """
        if not self._playlist_info:
            return []

        return [
            v.url for v in self._playlist_info.videos
            if v.index in self._selected_indices and v.is_available
        ]


def show_playlist_dialog(
    parent,
    url: str,
    on_select: Optional[Callable[[List[str]], None]] = None,
    playlist_filter: Optional[PlaylistFilter] = None
) -> PlaylistDialog:
    """Show the playlist selection dialog.

    Args:
        parent: Parent window
        url: YouTube playlist URL
        on_select: Callback when videos are selected
        playlist_filter: Optional PlaylistFilter instance

    Returns:
        The dialog instance
    """
    dialog = PlaylistDialog(
        parent,
        url=url,
        playlist_filter=playlist_filter,
        on_select=on_select
    )
    dialog.grab_set()
    return dialog
