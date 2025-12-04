"""History tab for YouTube Downloader.

Displays download history with search and management features.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable, List, Dict
from datetime import datetime, timedelta
import os
import json
from dataclasses import dataclass, asdict
from enum import Enum


class HistoryFilter(Enum):
    """Filter options for history."""
    ALL = "All"
    TODAY = "Today"
    WEEK = "This Week"
    MONTH = "This Month"
    COMPLETED = "Completed"
    FAILED = "Failed"


@dataclass
class HistoryEntry:
    """Represents a download history entry."""
    id: str
    url: str
    title: str
    uploader: str
    duration: int  # seconds
    filesize: int  # bytes
    filepath: str
    quality: str
    status: str  # completed, failed
    error_message: str
    download_date: str  # ISO format
    thumbnail_url: str

    def format_duration(self) -> str:
        """Format duration as HH:MM:SS."""
        if self.duration <= 0:
            return "--:--"

        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def format_filesize(self) -> str:
        """Format filesize in human readable format."""
        if self.filesize <= 0:
            return "--"

        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.filesize < 1024:
                return f"{self.filesize:.1f} {unit}"
            self.filesize /= 1024

        return f"{self.filesize:.1f} TB"

    def format_date(self) -> str:
        """Format download date."""
        try:
            dt = datetime.fromisoformat(self.download_date)
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return self.download_date


class HistoryManager:
    """Manages download history persistence."""

    def __init__(self, history_file: str):
        """Initialize history manager.

        Args:
            history_file: Path to history JSON file
        """
        self.history_file = history_file
        self._history: List[HistoryEntry] = []
        self._load()

    def _load(self):
        """Load history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._history = [
                        HistoryEntry(**entry) for entry in data
                    ]
            except Exception:
                self._history = []

    def _save(self):
        """Save history to file."""
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                data = [asdict(entry) for entry in self._history]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def add(self, entry: HistoryEntry):
        """Add entry to history."""
        self._history.insert(0, entry)
        self._save()

    def remove(self, entry_id: str):
        """Remove entry from history."""
        self._history = [e for e in self._history if e.id != entry_id]
        self._save()

    def clear(self):
        """Clear all history."""
        self._history.clear()
        self._save()

    def get_all(self) -> List[HistoryEntry]:
        """Get all history entries."""
        return self._history.copy()

    def search(self, query: str) -> List[HistoryEntry]:
        """Search history by title or uploader."""
        query_lower = query.lower()
        return [
            e for e in self._history
            if query_lower in e.title.lower() or query_lower in e.uploader.lower()
        ]

    def filter_by_date(self, days: int) -> List[HistoryEntry]:
        """Filter history by date range."""
        cutoff = datetime.now() - timedelta(days=days)
        return [
            e for e in self._history
            if datetime.fromisoformat(e.download_date) >= cutoff
        ]

    def filter_by_status(self, status: str) -> List[HistoryEntry]:
        """Filter history by status."""
        return [e for e in self._history if e.status == status]


class HistoryTab(ttk.Frame):
    """History display tab.

    Features:
    - Searchable history list
    - Filter by date/status
    - Re-download option
    - Open file/folder
    - Export history
    - Clear history

    Usage:
        tab = HistoryTab(notebook, history_manager)
        tab.on_redownload = callback
    """

    COLUMNS = [
        ("title", "Title", 250, True),
        ("uploader", "Channel", 150, False),
        ("duration", "Duration", 80, False),
        ("size", "Size", 80, False),
        ("quality", "Quality", 80, False),
        ("status", "Status", 80, False),
        ("date", "Date", 120, False),
    ]

    def __init__(self, parent, config_manager, **kwargs):
        """Initialize history tab.

        Args:
            parent: Parent widget
            config_manager: Configuration manager instance
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self.config = config_manager

        # Get history file path from config or use default
        data_dir = self.config.get("data_directory", os.path.expanduser("~/.ytdownloader"))
        history_file = os.path.join(data_dir, "history.json")
        self.history_manager = HistoryManager(history_file)

        # Callbacks
        self.on_redownload: Optional[Callable[[str], None]] = None

        # Item mapping
        self._items: Dict[str, str] = {}  # entry_id -> tree_item_id

        self._build_ui()
        self._create_context_menu()
        self._load_history()

    def _build_ui(self):
        """Build the tab UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Search and filter section
        self._build_search_section()

        # History list
        self._build_history_list()

        # Action buttons
        self._build_action_buttons()

    def _build_search_section(self):
        """Build search and filter section."""
        search_frame = ttk.Frame(self)
        search_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        search_frame.columnconfigure(1, weight=1)

        # Search entry
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)

        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 20))

        # Filter dropdown
        ttk.Label(search_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))

        self.filter_var = tk.StringVar(value=HistoryFilter.ALL.value)
        filter_combo = ttk.Combobox(
            search_frame,
            textvariable=self.filter_var,
            values=[f.value for f in HistoryFilter],
            state="readonly",
            width=15
        )
        filter_combo.pack(side=tk.LEFT)
        filter_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # Stats label
        self.stats_label = ttk.Label(search_frame, text="0 items")
        self.stats_label.pack(side=tk.RIGHT)

    def _build_history_list(self):
        """Build history treeview."""
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
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
            self.tree.heading(col_id, text=header, anchor="w",
                            command=lambda c=col_id: self._sort_by_column(c))
            self.tree.column(col_id, width=width, stretch=stretch, anchor="w")

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=v_scroll.set)

        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=h_scroll.set)

        # Configure tags
        self.tree.tag_configure("completed", background="#d4edda")
        self.tree.tag_configure("failed", background="#f8d7da")

        # Bind events
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Delete>", self._on_delete_key)

    def _build_action_buttons(self):
        """Build action button section."""
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Open file button
        self.open_btn = ttk.Button(
            btn_frame,
            text="Open File",
            command=self._open_selected_file
        )
        self.open_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Open folder button
        self.folder_btn = ttk.Button(
            btn_frame,
            text="Open Folder",
            command=self._open_selected_folder
        )
        self.folder_btn.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Redownload button
        self.redownload_btn = ttk.Button(
            btn_frame,
            text="Re-download",
            command=self._redownload_selected
        )
        self.redownload_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Delete button
        self.delete_btn = ttk.Button(
            btn_frame,
            text="Delete from History",
            command=self._delete_selected
        )
        self.delete_btn.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Export button
        ttk.Button(
            btn_frame,
            text="Export History",
            command=self._export_history
        ).pack(side=tk.LEFT, padx=(0, 5))

        # Clear button
        ttk.Button(
            btn_frame,
            text="Clear History",
            command=self._clear_history
        ).pack(side=tk.LEFT)

    def _create_context_menu(self):
        """Create right-click context menu."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Open File", command=self._open_selected_file)
        self.context_menu.add_command(label="Open Folder", command=self._open_selected_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Re-download", command=self._redownload_selected)
        self.context_menu.add_command(label="Copy URL", command=self._copy_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete from History", command=self._delete_selected)

    def _show_context_menu(self, event):
        """Show context menu."""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _load_history(self):
        """Load and display history."""
        self._refresh_display(self.history_manager.get_all())

    def _refresh_display(self, entries: List[HistoryEntry]):
        """Refresh display with entries."""
        # Clear current items
        for item_id in self._items.values():
            if self.tree.exists(item_id):
                self.tree.delete(item_id)
        self._items.clear()

        # Add entries
        for entry in entries:
            values = (
                self._truncate(entry.title, 40),
                self._truncate(entry.uploader, 20),
                entry.format_duration(),
                entry.format_filesize(),
                entry.quality,
                entry.status.title(),
                entry.format_date(),
            )

            tag = "completed" if entry.status == "completed" else "failed"
            item_id = self.tree.insert("", "end", values=values, tags=(tag,))
            self._items[entry.id] = item_id

        # Update stats
        self._update_stats(len(entries))

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def _update_stats(self, count: int):
        """Update stats label."""
        self.stats_label.configure(text=f"{count} item{'s' if count != 1 else ''}")

    def _on_search_changed(self, *args):
        """Handle search text change."""
        query = self.search_var.get()
        if query:
            entries = self.history_manager.search(query)
        else:
            entries = self._get_filtered_entries()
        self._refresh_display(entries)

    def _on_filter_changed(self, event=None):
        """Handle filter change."""
        entries = self._get_filtered_entries()

        # Apply search if active
        query = self.search_var.get()
        if query:
            query_lower = query.lower()
            entries = [
                e for e in entries
                if query_lower in e.title.lower() or query_lower in e.uploader.lower()
            ]

        self._refresh_display(entries)

    def _get_filtered_entries(self) -> List[HistoryEntry]:
        """Get entries based on current filter."""
        filter_value = self.filter_var.get()

        if filter_value == HistoryFilter.ALL.value:
            return self.history_manager.get_all()
        elif filter_value == HistoryFilter.TODAY.value:
            return self.history_manager.filter_by_date(1)
        elif filter_value == HistoryFilter.WEEK.value:
            return self.history_manager.filter_by_date(7)
        elif filter_value == HistoryFilter.MONTH.value:
            return self.history_manager.filter_by_date(30)
        elif filter_value == HistoryFilter.COMPLETED.value:
            return self.history_manager.filter_by_status("completed")
        elif filter_value == HistoryFilter.FAILED.value:
            return self.history_manager.filter_by_status("failed")

        return self.history_manager.get_all()

    def _sort_by_column(self, column: str):
        """Sort treeview by column."""
        # Get all items
        items = [(self.tree.set(item, column), item) for item in self.tree.get_children("")]

        # Sort items
        items.sort(key=lambda t: t[0])

        # Rearrange items in sorted positions
        for index, (_, item) in enumerate(items):
            self.tree.move(item, "", index)

    def _get_selected_entries(self) -> List[HistoryEntry]:
        """Get selected history entries."""
        selected_items = self.tree.selection()
        entries = []

        all_entries = self.history_manager.get_all()
        entry_map = {e.id: e for e in all_entries}

        for entry_id, item_id in self._items.items():
            if item_id in selected_items and entry_id in entry_map:
                entries.append(entry_map[entry_id])

        return entries

    def _open_selected_file(self):
        """Open selected file."""
        entries = self._get_selected_entries()
        if not entries:
            return

        filepath = entries[0].filepath
        if os.path.exists(filepath):
            import subprocess
            import sys

            if sys.platform == "win32":
                os.startfile(filepath)
            elif sys.platform == "darwin":
                subprocess.run(["open", filepath])
            else:
                subprocess.run(["xdg-open", filepath])
        else:
            messagebox.showerror("Error", "File not found")

    def _open_selected_folder(self):
        """Open folder containing selected file."""
        entries = self._get_selected_entries()
        if not entries:
            return

        folder = os.path.dirname(entries[0].filepath)
        if os.path.exists(folder):
            import subprocess
            import sys

            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        else:
            messagebox.showerror("Error", "Folder not found")

    def _redownload_selected(self):
        """Re-download selected items."""
        entries = self._get_selected_entries()
        if entries and self.on_redownload:
            for entry in entries:
                self.on_redownload(entry.url)

    def _copy_url(self):
        """Copy URL to clipboard."""
        entries = self._get_selected_entries()
        if entries:
            self.clipboard_clear()
            self.clipboard_append(entries[0].url)

    def _delete_selected(self):
        """Delete selected entries from history."""
        entries = self._get_selected_entries()
        if not entries:
            return

        if messagebox.askyesno(
            "Confirm Delete",
            f"Remove {len(entries)} item(s) from history?\n\n"
            "Note: This does not delete the downloaded files."
        ):
            for entry in entries:
                self.history_manager.remove(entry.id)
                item_id = self._items.pop(entry.id, None)
                if item_id and self.tree.exists(item_id):
                    self.tree.delete(item_id)

            self._update_stats(len(self._items))

    def _export_history(self):
        """Export history to CSV."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ],
            title="Export History"
        )

        if not filepath:
            return

        try:
            entries = self.history_manager.get_all()

            if filepath.endswith(".json"):
                with open(filepath, 'w', encoding='utf-8') as f:
                    data = [asdict(e) for e in entries]
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                # CSV export
                import csv
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Title", "URL", "Channel", "Duration", "Size",
                        "Quality", "Status", "Date", "File Path"
                    ])
                    for entry in entries:
                        writer.writerow([
                            entry.title,
                            entry.url,
                            entry.uploader,
                            entry.format_duration(),
                            entry.format_filesize(),
                            entry.quality,
                            entry.status,
                            entry.format_date(),
                            entry.filepath
                        ])

            messagebox.showinfo("Export", f"History exported to {filepath}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")

    def _clear_history(self):
        """Clear all history."""
        if messagebox.askyesno(
            "Clear History",
            "Clear all download history?\n\n"
            "Note: This does not delete downloaded files."
        ):
            self.history_manager.clear()
            self._load_history()

    def _on_double_click(self, event):
        """Handle double click to open file."""
        self._open_selected_file()

    def _on_delete_key(self, event):
        """Handle delete key press."""
        self._delete_selected()

    # Public methods

    def add_entry(self, entry: HistoryEntry):
        """Add new entry to history.

        Args:
            entry: History entry to add
        """
        self.history_manager.add(entry)
        self._on_filter_changed()  # Refresh display

    def refresh(self):
        """Refresh the history display."""
        self._on_filter_changed()
