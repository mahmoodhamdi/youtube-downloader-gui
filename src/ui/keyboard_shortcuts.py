"""Keyboard shortcuts manager for YouTube Downloader.

Provides centralized keyboard shortcut handling.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum


class ShortcutCategory(Enum):
    """Categories for keyboard shortcuts."""
    GENERAL = "General"
    DOWNLOADS = "Downloads"
    QUEUE = "Queue"
    NAVIGATION = "Navigation"
    PLAYBACK = "Playback"


@dataclass
class Shortcut:
    """Represents a keyboard shortcut.

    Attributes:
        key: Key combination (e.g., "<Control-s>")
        display_key: Human-readable key (e.g., "Ctrl+S")
        description: What the shortcut does
        category: Shortcut category
        callback: Function to call when triggered
        enabled: Whether shortcut is enabled
    """
    key: str
    display_key: str
    description: str
    category: ShortcutCategory
    callback: Optional[Callable] = None
    enabled: bool = True


class KeyboardShortcuts:
    """Manager for keyboard shortcuts.

    Features:
    - Register and unregister shortcuts
    - Category-based organization
    - Enable/disable individual shortcuts
    - Show shortcuts help dialog
    - Conflict detection

    Usage:
        shortcuts = KeyboardShortcuts(root)
        shortcuts.register("ctrl_s", "<Control-s>", "Ctrl+S", "Start downloads",
                          ShortcutCategory.DOWNLOADS, start_callback)
        shortcuts.bind_all()
    """

    # Default shortcuts configuration
    DEFAULT_SHORTCUTS = {
        # General
        "new_url": ("<Control-n>", "Ctrl+N", "Add new URL", ShortcutCategory.GENERAL),
        "paste_url": ("<Control-v>", "Ctrl+V", "Paste URL from clipboard", ShortcutCategory.GENERAL),
        "settings": ("<Control-comma>", "Ctrl+,", "Open settings", ShortcutCategory.GENERAL),
        "help": ("<F1>", "F1", "Show help", ShortcutCategory.GENERAL),
        "quit": ("<Control-q>", "Ctrl+Q", "Quit application", ShortcutCategory.GENERAL),
        "shortcuts_help": ("<Control-slash>", "Ctrl+/", "Show keyboard shortcuts", ShortcutCategory.GENERAL),

        # Downloads
        "start_downloads": ("<Control-Return>", "Ctrl+Enter", "Start downloads", ShortcutCategory.DOWNLOADS),
        "pause_downloads": ("<Control-p>", "Ctrl+P", "Pause downloads", ShortcutCategory.DOWNLOADS),
        "resume_downloads": ("<Control-r>", "Ctrl+R", "Resume downloads", ShortcutCategory.DOWNLOADS),
        "stop_downloads": ("<Control-period>", "Ctrl+.", "Stop all downloads", ShortcutCategory.DOWNLOADS),

        # Queue
        "select_all": ("<Control-a>", "Ctrl+A", "Select all in queue", ShortcutCategory.QUEUE),
        "delete_selected": ("<Delete>", "Delete", "Remove selected items", ShortcutCategory.QUEUE),
        "clear_queue": ("<Control-Shift-Delete>", "Ctrl+Shift+Del", "Clear entire queue", ShortcutCategory.QUEUE),
        "move_up": ("<Control-Up>", "Ctrl+Up", "Move selected up", ShortcutCategory.QUEUE),
        "move_down": ("<Control-Down>", "Ctrl+Down", "Move selected down", ShortcutCategory.QUEUE),
        "retry_failed": ("<Control-Shift-r>", "Ctrl+Shift+R", "Retry failed downloads", ShortcutCategory.QUEUE),

        # Navigation
        "tab_downloads": ("<Control-Key-1>", "Ctrl+1", "Go to Downloads tab", ShortcutCategory.NAVIGATION),
        "tab_settings": ("<Control-Key-2>", "Ctrl+2", "Go to Settings tab", ShortcutCategory.NAVIGATION),
        "tab_history": ("<Control-Key-3>", "Ctrl+3", "Go to History tab", ShortcutCategory.NAVIGATION),
        "tab_statistics": ("<Control-Key-4>", "Ctrl+4", "Go to Statistics tab", ShortcutCategory.NAVIGATION),
        "focus_search": ("<Control-f>", "Ctrl+F", "Focus search field", ShortcutCategory.NAVIGATION),
        "focus_url": ("<Control-l>", "Ctrl+L", "Focus URL input", ShortcutCategory.NAVIGATION),
    }

    def __init__(self, root: tk.Tk):
        """Initialize keyboard shortcuts manager.

        Args:
            root: Root Tk window
        """
        self.root = root
        self.shortcuts: Dict[str, Shortcut] = {}
        self._bound_keys: List[str] = []

    def register(
        self,
        name: str,
        key: str,
        display_key: str,
        description: str,
        category: ShortcutCategory,
        callback: Optional[Callable] = None,
        enabled: bool = True
    ):
        """Register a keyboard shortcut.

        Args:
            name: Unique identifier for the shortcut
            key: Tkinter key binding (e.g., "<Control-s>")
            display_key: Human-readable key combo
            description: What the shortcut does
            category: Shortcut category
            callback: Function to call
            enabled: Whether enabled
        """
        self.shortcuts[name] = Shortcut(
            key=key,
            display_key=display_key,
            description=description,
            category=category,
            callback=callback,
            enabled=enabled
        )

    def register_defaults(self):
        """Register all default shortcuts without callbacks."""
        for name, (key, display, desc, category) in self.DEFAULT_SHORTCUTS.items():
            self.register(name, key, display, desc, category)

    def set_callback(self, name: str, callback: Callable):
        """Set callback for a registered shortcut.

        Args:
            name: Shortcut identifier
            callback: Function to call
        """
        if name in self.shortcuts:
            self.shortcuts[name].callback = callback

    def enable(self, name: str):
        """Enable a shortcut.

        Args:
            name: Shortcut identifier
        """
        if name in self.shortcuts:
            self.shortcuts[name].enabled = True

    def disable(self, name: str):
        """Disable a shortcut.

        Args:
            name: Shortcut identifier
        """
        if name in self.shortcuts:
            self.shortcuts[name].enabled = False

    def bind_all(self):
        """Bind all registered shortcuts to the root window."""
        for name, shortcut in self.shortcuts.items():
            if shortcut.callback and shortcut.enabled:
                self._bind_shortcut(name, shortcut)

    def _bind_shortcut(self, name: str, shortcut: Shortcut):
        """Bind a single shortcut.

        Args:
            name: Shortcut identifier
            shortcut: Shortcut object
        """
        def handler(event, s=shortcut):
            if s.enabled and s.callback:
                try:
                    s.callback()
                except Exception as e:
                    print(f"Shortcut error ({name}): {e}")
                return "break"

        try:
            self.root.bind_all(shortcut.key, handler)
            self._bound_keys.append(shortcut.key)
        except tk.TclError as e:
            print(f"Failed to bind {shortcut.key}: {e}")

    def unbind_all(self):
        """Unbind all shortcuts."""
        for key in self._bound_keys:
            try:
                self.root.unbind_all(key)
            except tk.TclError:
                pass
        self._bound_keys.clear()

    def get_shortcuts_by_category(self) -> Dict[ShortcutCategory, List[Shortcut]]:
        """Get shortcuts organized by category.

        Returns:
            Dictionary mapping categories to shortcut lists
        """
        by_category: Dict[ShortcutCategory, List[Shortcut]] = {}

        for shortcut in self.shortcuts.values():
            if shortcut.category not in by_category:
                by_category[shortcut.category] = []
            by_category[shortcut.category].append(shortcut)

        return by_category

    def show_help_dialog(self, parent=None):
        """Show keyboard shortcuts help dialog.

        Args:
            parent: Parent window (defaults to root)
        """
        dialog = ShortcutsHelpDialog(parent or self.root, self)
        dialog.grab_set()


class ShortcutsHelpDialog(tk.Toplevel):
    """Dialog showing all keyboard shortcuts.

    Displays shortcuts organized by category in a scrollable list.
    """

    def __init__(self, parent, shortcuts_manager: KeyboardShortcuts):
        """Initialize help dialog.

        Args:
            parent: Parent window
            shortcuts_manager: KeyboardShortcuts instance
        """
        super().__init__(parent)

        self.shortcuts_manager = shortcuts_manager

        self.title("Keyboard Shortcuts")
        self.geometry("500x450")
        self.resizable(True, True)

        self.transient(parent)

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Main frame with scrollbar
        main_frame = ttk.Frame(self, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Canvas for scrolling
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)

        content_frame = ttk.Frame(canvas)
        content_frame.columnconfigure(1, weight=1)

        content_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Populate shortcuts by category
        by_category = self.shortcuts_manager.get_shortcuts_by_category()
        row = 0

        # Order categories
        category_order = [
            ShortcutCategory.GENERAL,
            ShortcutCategory.DOWNLOADS,
            ShortcutCategory.QUEUE,
            ShortcutCategory.NAVIGATION,
        ]

        for category in category_order:
            if category not in by_category:
                continue

            shortcuts = by_category[category]

            # Category header
            header = ttk.Label(
                content_frame,
                text=category.value,
                font=("", 11, "bold")
            )
            header.grid(row=row, column=0, columnspan=2, sticky="w", pady=(15, 5))
            row += 1

            # Separator
            sep = ttk.Separator(content_frame, orient=tk.HORIZONTAL)
            sep.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 5))
            row += 1

            # Shortcuts
            for shortcut in shortcuts:
                # Key
                key_label = ttk.Label(
                    content_frame,
                    text=shortcut.display_key,
                    font=("Consolas", 10),
                    width=20
                )
                key_label.grid(row=row, column=0, sticky="w", padx=(10, 10), pady=2)

                # Description
                desc_label = ttk.Label(
                    content_frame,
                    text=shortcut.description,
                    foreground="gray" if not shortcut.enabled else None
                )
                desc_label.grid(row=row, column=1, sticky="w", pady=2)

                row += 1

        # Close button
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        ttk.Button(
            btn_frame,
            text="Close",
            command=self.destroy
        ).pack(side=tk.RIGHT)


class ShortcutsIntegration:
    """Helper class to integrate shortcuts with MainWindow.

    Usage:
        integration = ShortcutsIntegration(main_window)
        integration.setup()
    """

    def __init__(self, main_window):
        """Initialize integration.

        Args:
            main_window: MainWindow instance
        """
        self.main_window = main_window
        self.shortcuts: Optional[KeyboardShortcuts] = None

    def setup(self):
        """Set up keyboard shortcuts for the main window."""
        if not hasattr(self.main_window, 'root'):
            return

        self.shortcuts = KeyboardShortcuts(self.main_window.root)
        self.shortcuts.register_defaults()

        # Set up callbacks
        self._setup_general_callbacks()
        self._setup_download_callbacks()
        self._setup_queue_callbacks()
        self._setup_navigation_callbacks()

        # Bind all
        self.shortcuts.bind_all()

    def _setup_general_callbacks(self):
        """Set up general shortcuts."""
        # Focus URL input
        if hasattr(self.main_window, 'downloads_tab'):
            self.shortcuts.set_callback(
                "new_url",
                lambda: self._focus_url_input()
            )
            self.shortcuts.set_callback(
                "focus_url",
                lambda: self._focus_url_input()
            )

        # Paste URL
        self.shortcuts.set_callback(
            "paste_url",
            lambda: self._paste_url()
        )

        # Show shortcuts help
        self.shortcuts.set_callback(
            "shortcuts_help",
            lambda: self.shortcuts.show_help_dialog(self.main_window.root)
        )

        # Quit
        self.shortcuts.set_callback(
            "quit",
            lambda: self._quit_app()
        )

    def _setup_download_callbacks(self):
        """Set up download control shortcuts."""
        if hasattr(self.main_window, '_start_downloads'):
            self.shortcuts.set_callback(
                "start_downloads",
                self.main_window._start_downloads
            )

        if hasattr(self.main_window, '_pause_downloads'):
            self.shortcuts.set_callback(
                "pause_downloads",
                self.main_window._pause_downloads
            )

        if hasattr(self.main_window, '_resume_downloads'):
            self.shortcuts.set_callback(
                "resume_downloads",
                self.main_window._resume_downloads
            )

        if hasattr(self.main_window, '_stop_downloads'):
            self.shortcuts.set_callback(
                "stop_downloads",
                self.main_window._stop_downloads
            )

    def _setup_queue_callbacks(self):
        """Set up queue management shortcuts."""
        if hasattr(self.main_window, 'downloads_tab'):
            tab = self.main_window.downloads_tab

            if hasattr(tab, 'queue_widget'):
                self.shortcuts.set_callback(
                    "select_all",
                    lambda: tab.queue_widget.select_all()
                )

                self.shortcuts.set_callback(
                    "delete_selected",
                    lambda: tab.queue_widget.remove_selected()
                )

                self.shortcuts.set_callback(
                    "clear_queue",
                    lambda: self._clear_queue()
                )

    def _setup_navigation_callbacks(self):
        """Set up navigation shortcuts."""
        if hasattr(self.main_window, 'notebook'):
            notebook = self.main_window.notebook

            self.shortcuts.set_callback(
                "tab_downloads",
                lambda: notebook.select(0)
            )
            self.shortcuts.set_callback(
                "tab_settings",
                lambda: notebook.select(1)
            )
            self.shortcuts.set_callback(
                "tab_history",
                lambda: notebook.select(2)
            )
            self.shortcuts.set_callback(
                "tab_statistics",
                lambda: self._select_tab_safe(notebook, 3)
            )

        # Focus search
        self.shortcuts.set_callback(
            "focus_search",
            lambda: self._focus_search()
        )

    def _focus_url_input(self):
        """Focus the URL input field."""
        if hasattr(self.main_window, 'downloads_tab'):
            tab = self.main_window.downloads_tab
            if hasattr(tab, 'url_input'):
                tab.url_input.focus_entry()

    def _paste_url(self):
        """Paste URL from clipboard."""
        try:
            clipboard = self.main_window.root.clipboard_get()
            if hasattr(self.main_window, 'downloads_tab'):
                tab = self.main_window.downloads_tab
                if hasattr(tab, 'url_input'):
                    tab.url_input.url_var.set(clipboard)
                    tab.url_input.focus_entry()
        except tk.TclError:
            pass

    def _clear_queue(self):
        """Clear queue with confirmation."""
        if messagebox.askyesno("Clear Queue", "Clear all items from the queue?"):
            if hasattr(self.main_window, 'downloads_tab'):
                tab = self.main_window.downloads_tab
                if hasattr(tab, '_handle_clear'):
                    tab._handle_clear()

    def _focus_search(self):
        """Focus the search field if available."""
        if hasattr(self.main_window, 'downloads_tab'):
            tab = self.main_window.downloads_tab
            if hasattr(tab, 'search_widget'):
                tab.search_widget.focus_search()

    def _select_tab_safe(self, notebook, index):
        """Select tab if it exists."""
        try:
            if index < notebook.index("end"):
                notebook.select(index)
        except tk.TclError:
            pass

    def _quit_app(self):
        """Quit application with confirmation."""
        if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
            self.main_window.root.quit()

    def cleanup(self):
        """Clean up shortcuts."""
        if self.shortcuts:
            self.shortcuts.unbind_all()
