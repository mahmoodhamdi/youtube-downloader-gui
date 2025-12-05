"""Queue search and filter widget for YouTube Downloader.

Provides search and filter functionality for the download queue.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, List
from enum import Enum

from src.ui.styled_widgets import StyledEntry, DRACULA


class QueueFilterStatus(Enum):
    """Filter options for queue status."""
    ALL = "all"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class QueueSearchWidget(ttk.Frame):
    """Widget for searching and filtering the download queue.

    Features:
    - Text search by title
    - Filter by status
    - Sort options
    - Clear filters button
    - Real-time filtering

    Usage:
        search = QueueSearchWidget(parent)
        search.on_filter_changed = callback
        search.pack(fill=tk.X)
    """

    def __init__(self, parent, **kwargs):
        """Initialize search widget.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        # Callbacks
        self.on_filter_changed: Optional[Callable[[str, str, str], None]] = None

        # State
        self._search_after_id = None

        self._build_ui()

    def _build_ui(self):
        """Build the widget UI."""
        self.columnconfigure(1, weight=1)

        # Search entry
        ttk.Label(self, text="Search:").grid(row=0, column=0, padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)

        self.search_entry = StyledEntry(self, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        # Placeholder text
        self.search_entry.insert(0, "Search by title...")
        self.search_entry.config(fg=DRACULA["selection"])  # Gray-ish placeholder color
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)

        # Status filter
        ttk.Label(self, text="Status:").grid(row=0, column=2, padx=(0, 5))

        self.status_var = tk.StringVar(value="all")
        status_combo = ttk.Combobox(
            self,
            textvariable=self.status_var,
            values=[
                "All",
                "Queued",
                "Downloading",
                "Completed",
                "Failed",
                "Paused"
            ],
            state="readonly",
            width=12
        )
        status_combo.grid(row=0, column=3, padx=(0, 10))
        status_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # Sort options
        ttk.Label(self, text="Sort:").grid(row=0, column=4, padx=(0, 5))

        self.sort_var = tk.StringVar(value="added")
        sort_combo = ttk.Combobox(
            self,
            textvariable=self.sort_var,
            values=[
                "Date Added",
                "Title A-Z",
                "Title Z-A",
                "Duration",
                "Size"
            ],
            state="readonly",
            width=12
        )
        sort_combo.grid(row=0, column=5, padx=(0, 10))
        sort_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # Clear button
        self.clear_btn = ttk.Button(
            self,
            text="Clear",
            command=self._clear_filters,
            width=6
        )
        self.clear_btn.grid(row=0, column=6)

        # Results count label
        self.results_label = ttk.Label(
            self,
            text="",
            foreground="gray"
        )
        self.results_label.grid(row=0, column=7, padx=(10, 0))

    def _on_search_focus_in(self, event):
        """Handle search entry focus in."""
        if self.search_entry.get() == "Search by title...":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg=DRACULA["fg"])

    def _on_search_focus_out(self, event):
        """Handle search entry focus out."""
        if not self.search_entry.get():
            self.search_entry.insert(0, "Search by title...")
            self.search_entry.config(fg=DRACULA["selection"])

    def _on_search_changed(self, *args):
        """Handle search text change with debounce."""
        # Cancel previous scheduled call
        if self._search_after_id:
            self.after_cancel(self._search_after_id)

        # Schedule new call after 300ms delay
        self._search_after_id = self.after(300, self._trigger_filter_change)

    def _on_filter_changed(self, event=None):
        """Handle filter change."""
        self._trigger_filter_change()

    def _trigger_filter_change(self):
        """Trigger filter change callback."""
        if self.on_filter_changed:
            search_text = self.get_search_text()
            status = self.get_status_filter()
            sort = self.get_sort_option()
            self.on_filter_changed(search_text, status, sort)

    def _clear_filters(self):
        """Clear all filters."""
        self.search_var.set("")
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, "Search by title...")
        self.search_entry.config(fg=DRACULA["selection"])

        self.status_var.set("All")
        self.sort_var.set("Date Added")

        self._trigger_filter_change()

    def get_search_text(self) -> str:
        """Get current search text.

        Returns:
            Search text or empty string
        """
        text = self.search_var.get()
        if text == "Search by title...":
            return ""
        return text.strip()

    def get_status_filter(self) -> str:
        """Get current status filter.

        Returns:
            Status filter value
        """
        status = self.status_var.get().lower()
        return status if status != "all" else ""

    def get_sort_option(self) -> str:
        """Get current sort option.

        Returns:
            Sort option value
        """
        sort_map = {
            "Date Added": "added",
            "Title A-Z": "title_asc",
            "Title Z-A": "title_desc",
            "Duration": "duration",
            "Size": "size"
        }
        return sort_map.get(self.sort_var.get(), "added")

    def update_results_count(self, shown: int, total: int):
        """Update results count display.

        Args:
            shown: Number of items shown after filter
            total: Total number of items
        """
        if shown == total:
            self.results_label.config(text=f"{total} items")
        else:
            self.results_label.config(text=f"{shown} of {total} items")

    def focus_search(self):
        """Focus the search entry."""
        self.search_entry.focus_set()
        if self.search_entry.get() == "Search by title...":
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg=DRACULA["fg"])


class QueueFilter:
    """Filter logic for queue items.

    Usage:
        filter = QueueFilter()
        filtered = filter.apply(items, search="video", status="queued")
    """

    @staticmethod
    def filter_by_search(items: List, search_text: str) -> List:
        """Filter items by search text.

        Args:
            items: List of items with 'title' attribute
            search_text: Search text

        Returns:
            Filtered list
        """
        if not search_text:
            return items

        search_lower = search_text.lower()
        return [
            item for item in items
            if hasattr(item, 'title') and search_lower in item.title.lower()
        ]

    @staticmethod
    def filter_by_status(items: List, status: str) -> List:
        """Filter items by status.

        Args:
            items: List of items with 'status' attribute
            status: Status to filter by

        Returns:
            Filtered list
        """
        if not status:
            return items

        status_lower = status.lower()
        return [
            item for item in items
            if hasattr(item, 'status') and item.status.name.lower() == status_lower
        ]

    @staticmethod
    def sort_items(items: List, sort_by: str) -> List:
        """Sort items by specified criteria.

        Args:
            items: List of items
            sort_by: Sort criteria

        Returns:
            Sorted list
        """
        if sort_by == "title_asc":
            return sorted(items, key=lambda x: getattr(x, 'title', '').lower())
        elif sort_by == "title_desc":
            return sorted(items, key=lambda x: getattr(x, 'title', '').lower(), reverse=True)
        elif sort_by == "duration":
            return sorted(items, key=lambda x: getattr(x, 'duration', 0) or 0, reverse=True)
        elif sort_by == "size":
            return sorted(items, key=lambda x: getattr(x, 'filesize', 0) or 0, reverse=True)
        else:  # "added" - default, maintain original order
            return items

    @classmethod
    def apply(
        cls,
        items: List,
        search_text: str = "",
        status: str = "",
        sort_by: str = "added"
    ) -> List:
        """Apply all filters and sorting.

        Args:
            items: List of items to filter
            search_text: Search text filter
            status: Status filter
            sort_by: Sort criteria

        Returns:
            Filtered and sorted list
        """
        result = items

        # Apply filters
        result = cls.filter_by_search(result, search_text)
        result = cls.filter_by_status(result, status)

        # Apply sorting
        result = cls.sort_items(result, sort_by)

        return result
