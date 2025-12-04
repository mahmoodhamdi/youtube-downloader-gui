"""Queue display widget for YouTube Downloader.

Displays the download queue with status and controls.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Optional, Dict
import webbrowser

from src.core.queue_manager import VideoItem, VideoStatus


class QueueWidget(ttk.Frame):
    """Widget displaying the download queue.

    Features:
    - Treeview with video information
    - Status color coding
    - Context menu for actions
    - Drag and drop reordering
    - Selection management

    Usage:
        queue = QueueWidget(parent)
        queue.on_remove = remove_callback
        queue.add_item(video_item)
        queue.pack(fill=tk.BOTH, expand=True)
    """

    # Column definitions: (id, header, width, stretch)
    COLUMNS = [
        ("title", "Title", 300, True),
        ("duration", "Duration", 80, False),
        ("size", "Size", 80, False),
        ("status", "Status", 100, False),
        ("progress", "Progress", 80, False),
    ]

    def __init__(self, parent, **kwargs):
        """Initialize queue widget.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        # Callbacks
        self.on_remove: Optional[Callable[[List[str]], None]] = None
        self.on_clear: Optional[Callable[[], None]] = None
        self.on_retry: Optional[Callable[[List[str]], None]] = None
        self.on_move_up: Optional[Callable[[str], None]] = None
        self.on_move_down: Optional[Callable[[str], None]] = None

        # Item mapping
        self._items: Dict[str, str] = {}  # video_id -> tree_item_id

        self._build_ui()
        self._create_context_menu()

    def _build_ui(self):
        """Build the widget UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Create treeview frame
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=0, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Create treeview
        columns = [col[0] for col in self.COLUMNS]
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        # Configure columns
        for col_id, header, width, stretch in self.COLUMNS:
            self.tree.heading(col_id, text=header, anchor="w")
            self.tree.column(col_id, width=width, stretch=stretch, anchor="w")

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=v_scroll.set)

        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=h_scroll.set)

        # Configure tags for status colors
        self.tree.tag_configure("queued", background="#f0f0f0")
        self.tree.tag_configure("downloading", background="#fff3cd")
        self.tree.tag_configure("completed", background="#d4edda")
        self.tree.tag_configure("error", background="#f8d7da")
        self.tree.tag_configure("paused", background="#e2e3e5")

        # Bind events
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Delete>", self._on_delete_key)

        # Button frame
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        self.remove_btn = ttk.Button(
            btn_frame,
            text="Remove Selected",
            command=self._on_remove_selected
        )
        self.remove_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.clear_btn = ttk.Button(
            btn_frame,
            text="Clear Queue",
            command=self._on_clear_queue
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        self.move_up_btn = ttk.Button(
            btn_frame,
            text="↑ Move Up",
            command=self._on_move_up
        )
        self.move_up_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.move_down_btn = ttk.Button(
            btn_frame,
            text="↓ Move Down",
            command=self._on_move_down
        )
        self.move_down_btn.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        self.retry_btn = ttk.Button(
            btn_frame,
            text="Retry Failed",
            command=self._on_retry_failed
        )
        self.retry_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.clear_completed_btn = ttk.Button(
            btn_frame,
            text="Clear Completed",
            command=self._on_clear_completed
        )
        self.clear_completed_btn.pack(side=tk.LEFT)

        # Queue count label
        self.count_label = ttk.Label(btn_frame, text="0 items")
        self.count_label.pack(side=tk.RIGHT)

    def _create_context_menu(self):
        """Create right-click context menu."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Remove", command=self._on_remove_selected)
        self.context_menu.add_command(label="Retry", command=self._on_retry_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Move to Top", command=self._on_move_to_top)
        self.context_menu.add_command(label="Move to Bottom", command=self._on_move_to_bottom)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy URL", command=self._on_copy_url)
        self.context_menu.add_command(label="Open in Browser", command=self._on_open_browser)

    def _show_context_menu(self, event):
        """Show context menu."""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def add_item(self, video: VideoItem):
        """Add a video to the queue display.

        Args:
            video: VideoItem to add
        """
        # Format values
        values = (
            self._truncate(video.title, 50),
            video.format_duration(),
            video.format_filesize(),
            video.status.name.title(),
            f"{video.progress:.1f}%"
        )

        # Determine tag based on status
        tag = self._get_status_tag(video.status)

        # Insert item
        item_id = self.tree.insert("", "end", values=values, tags=(tag,))
        self._items[video.id] = item_id

        self._update_count()

    def update_item(self, video: VideoItem):
        """Update a video in the queue display.

        Args:
            video: VideoItem to update
        """
        item_id = self._items.get(video.id)
        if not item_id:
            return

        # Check if item still exists
        if not self.tree.exists(item_id):
            return

        # Update values
        values = (
            self._truncate(video.title, 50),
            video.format_duration(),
            video.format_filesize(),
            video.status.name.title(),
            f"{video.progress:.1f}%"
        )

        tag = self._get_status_tag(video.status)

        self.tree.item(item_id, values=values, tags=(tag,))

    def remove_item(self, video_id: str):
        """Remove a video from the queue display.

        Args:
            video_id: ID of video to remove
        """
        item_id = self._items.pop(video_id, None)
        if item_id and self.tree.exists(item_id):
            self.tree.delete(item_id)

        self._update_count()

    def clear(self):
        """Clear all items from the display."""
        for item_id in self._items.values():
            if self.tree.exists(item_id):
                self.tree.delete(item_id)

        self._items.clear()
        self._update_count()

    def get_selected_ids(self) -> List[str]:
        """Get IDs of selected videos.

        Returns:
            List of video IDs
        """
        selected_items = self.tree.selection()
        video_ids = []

        for video_id, item_id in self._items.items():
            if item_id in selected_items:
                video_ids.append(video_id)

        return video_ids

    def _get_status_tag(self, status: VideoStatus) -> str:
        """Get tag name for status.

        Args:
            status: Video status

        Returns:
            Tag name
        """
        mapping = {
            VideoStatus.QUEUED: "queued",
            VideoStatus.WAITING: "queued",
            VideoStatus.EXTRACTING: "downloading",
            VideoStatus.DOWNLOADING: "downloading",
            VideoStatus.POST_PROCESSING: "downloading",
            VideoStatus.COMPLETED: "completed",
            VideoStatus.ERROR: "error",
            VideoStatus.PAUSED: "paused",
            VideoStatus.CANCELLED: "error",
        }
        return mapping.get(status, "queued")

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text with ellipsis.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def _update_count(self):
        """Update item count label."""
        count = len(self._items)
        self.count_label.configure(text=f"{count} item{'s' if count != 1 else ''}")

    # Event handlers
    def _on_remove_selected(self):
        """Handle remove selected."""
        ids = self.get_selected_ids()
        if ids and self.on_remove:
            self.on_remove(ids)

    def _on_clear_queue(self):
        """Handle clear queue."""
        if messagebox.askyesno("Confirm", "Clear all items from queue?"):
            if self.on_clear:
                self.on_clear()

    def _on_retry_failed(self):
        """Handle retry all failed."""
        if self.on_retry:
            self.on_retry([])  # Empty list means retry all

    def _on_retry_selected(self):
        """Handle retry selected."""
        ids = self.get_selected_ids()
        if ids and self.on_retry:
            self.on_retry(ids)

    def _on_clear_completed(self):
        """Handle clear completed."""
        # Find completed items
        completed_ids = []
        for video_id, item_id in list(self._items.items()):
            if self.tree.exists(item_id):
                values = self.tree.item(item_id, "values")
                if values and values[3] == "Completed":
                    completed_ids.append(video_id)

        if completed_ids and self.on_remove:
            self.on_remove(completed_ids)

    def _on_move_up(self):
        """Handle move up."""
        ids = self.get_selected_ids()
        if ids and len(ids) == 1 and self.on_move_up:
            self.on_move_up(ids[0])

    def _on_move_down(self):
        """Handle move down."""
        ids = self.get_selected_ids()
        if ids and len(ids) == 1 and self.on_move_down:
            self.on_move_down(ids[0])

    def _on_move_to_top(self):
        """Handle move to top."""
        ids = self.get_selected_ids()
        if ids and len(ids) == 1:
            # Move in tree
            item_id = self._items.get(ids[0])
            if item_id:
                self.tree.move(item_id, "", 0)

    def _on_move_to_bottom(self):
        """Handle move to bottom."""
        ids = self.get_selected_ids()
        if ids and len(ids) == 1:
            # Move in tree
            item_id = self._items.get(ids[0])
            if item_id:
                self.tree.move(item_id, "", "end")

    def _on_copy_url(self):
        """Handle copy URL to clipboard."""
        # This needs to be connected to the actual video data
        pass

    def _on_open_browser(self):
        """Handle open in browser."""
        # This needs to be connected to the actual video data
        pass

    def _on_double_click(self, event):
        """Handle double click."""
        # Could show video details
        pass

    def _on_delete_key(self, event):
        """Handle delete key press."""
        self._on_remove_selected()
