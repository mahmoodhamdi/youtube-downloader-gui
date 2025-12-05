"""Theme management for YouTube Downloader.

Provides Dracula dark theme with eye-friendly colors.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Theme:
    """Theme color definitions."""
    name: str

    # Main colors
    bg: str
    fg: str
    bg_secondary: str
    fg_secondary: str

    # Accent colors
    accent: str
    accent_hover: str
    accent_pressed: str

    # Status colors
    success: str
    warning: str
    error: str
    info: str

    # Input colors
    input_bg: str
    input_fg: str
    input_border: str

    # Selection colors
    select_bg: str
    select_fg: str

    # Progress colors
    progress_bg: str
    progress_fg: str

    # Border and separator
    border: str
    separator: str


# Dracula Theme - Popular eye-friendly dark theme
# https://draculatheme.com/contribute
DRACULA_THEME = Theme(
    name="dracula",

    # Main colors
    bg="#282a36",              # Background
    fg="#f8f8f2",              # Foreground (white)
    bg_secondary="#44475a",    # Current Line / Selection background
    fg_secondary="#6272a4",    # Comment (muted purple-blue)

    # Accent colors - Purple (Dracula signature)
    accent="#bd93f9",          # Purple
    accent_hover="#caa9fa",    # Lighter purple on hover
    accent_pressed="#9d7cd4",  # Darker purple when pressed

    # Status colors
    success="#50fa7b",         # Green
    warning="#ffb86c",         # Orange
    error="#ff5555",           # Red
    info="#8be9fd",            # Cyan

    # Input colors
    input_bg="#21222c",        # Slightly darker than bg
    input_fg="#f8f8f2",        # White text
    input_border="#44475a",    # Current line color

    # Selection colors
    select_bg="#44475a",       # Current Line
    select_fg="#f8f8f2",       # White text

    # Progress colors
    progress_bg="#44475a",     # Current Line
    progress_fg="#bd93f9",     # Purple

    # Border and separator
    border="#44475a",          # Current Line
    separator="#44475a",       # Current Line
)


class ThemeManager:
    """Manages application themes and styling.

    Features:
    - Dracula dark theme
    - ttk style configuration
    - Consistent styling across all widgets

    Usage:
        theme_manager = ThemeManager(root)
        theme_manager.set_theme("dark")
    """

    THEMES = {
        "dark": DRACULA_THEME,
        "dracula": DRACULA_THEME,
        "system": DRACULA_THEME,
        "light": DRACULA_THEME,
    }

    def __init__(self, root: tk.Tk):
        """Initialize theme manager.

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.style = ttk.Style()

        # Use 'clam' theme as base - better support for custom colors on Windows
        try:
            self.style.theme_use('clam')
        except Exception:
            pass

        self._current_theme: Optional[Theme] = None
        self._callbacks: list = []

    def set_theme(self, theme_name: str = "dark"):
        """Set the application theme.

        Args:
            theme_name: Theme name (always uses Dracula theme)
        """
        theme = DRACULA_THEME
        self._current_theme = theme

        # Apply theme
        self._apply_theme(theme)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(theme)
            except Exception:
                pass

    def _apply_theme(self, theme: Theme):
        """Apply theme to all widgets.

        Args:
            theme: Theme to apply
        """
        # Configure root window
        self.root.configure(bg=theme.bg)

        # Configure root window options for native widgets (e.g., Combobox dropdown)
        self.root.option_add("*TCombobox*Listbox.background", theme.input_bg)
        self.root.option_add("*TCombobox*Listbox.foreground", theme.input_fg)
        self.root.option_add("*TCombobox*Listbox.selectBackground", theme.select_bg)
        self.root.option_add("*TCombobox*Listbox.selectForeground", theme.select_fg)

        # Configure ttk styles
        self._configure_ttk_styles(theme)

    def _configure_ttk_styles(self, theme: Theme):
        """Configure ttk widget styles.

        Args:
            theme: Theme to apply
        """
        style = self.style

        # General settings
        style.configure(".",
            background=theme.bg,
            foreground=theme.fg,
            fieldbackground=theme.input_bg,
            font=("Segoe UI", 10)
        )

        # Frame
        style.configure("TFrame",
            background=theme.bg
        )

        style.configure("Secondary.TFrame",
            background=theme.bg_secondary
        )

        style.configure("Card.TFrame",
            background=theme.bg_secondary,
            relief="flat"
        )

        # Label
        style.configure("TLabel",
            background=theme.bg,
            foreground=theme.fg
        )

        style.configure("Title.TLabel",
            font=("Segoe UI", 14, "bold"),
            foreground=theme.fg
        )

        style.configure("Subtitle.TLabel",
            font=("Segoe UI", 11),
            foreground=theme.fg_secondary
        )

        style.configure("Success.TLabel",
            foreground=theme.success,
            background=theme.bg
        )

        style.configure("Warning.TLabel",
            foreground=theme.warning,
            background=theme.bg
        )

        style.configure("Error.TLabel",
            foreground=theme.error,
            background=theme.bg
        )

        style.configure("Info.TLabel",
            foreground=theme.info,
            background=theme.bg
        )

        # Pink accent label (Dracula pink)
        style.configure("Pink.TLabel",
            foreground="#ff79c6",
            background=theme.bg
        )

        # Cyan accent label
        style.configure("Cyan.TLabel",
            foreground="#8be9fd",
            background=theme.bg
        )

        # Button
        style.configure("TButton",
            background=theme.bg_secondary,
            foreground=theme.fg,
            padding=(12, 6),
            font=("Segoe UI", 10)
        )

        style.map("TButton",
            background=[
                ("active", theme.accent_hover),
                ("pressed", theme.accent_pressed)
            ],
            foreground=[
                ("active", theme.fg)
            ]
        )

        style.configure("Accent.TButton",
            background=theme.accent,
            foreground=theme.bg,
            font=("Segoe UI", 10, "bold")
        )

        style.map("Accent.TButton",
            background=[
                ("active", theme.accent_hover),
                ("pressed", theme.accent_pressed)
            ]
        )

        # Pink button (Dracula pink)
        style.configure("Pink.TButton",
            background="#ff79c6",
            foreground=theme.bg,
            font=("Segoe UI", 10, "bold")
        )

        style.map("Pink.TButton",
            background=[
                ("active", "#ff92d0"),
                ("pressed", "#d160a2")
            ]
        )

        style.configure("Success.TButton",
            background=theme.success,
            foreground=theme.bg
        )

        style.configure("Danger.TButton",
            background=theme.error,
            foreground=theme.bg
        )

        # Entry
        style.configure("TEntry",
            fieldbackground=theme.input_bg,
            foreground=theme.input_fg,
            insertcolor=theme.fg,
            padding=8
        )

        style.map("TEntry",
            fieldbackground=[("focus", theme.bg_secondary)],
            bordercolor=[("focus", theme.accent)]
        )

        # Combobox
        style.configure("TCombobox",
            fieldbackground=theme.input_bg,
            foreground=theme.input_fg,
            arrowcolor=theme.fg,
            padding=8
        )

        style.map("TCombobox",
            fieldbackground=[("readonly", theme.input_bg)],
            selectbackground=[("readonly", theme.select_bg)],
            selectforeground=[("readonly", theme.select_fg)]
        )

        # Checkbutton
        style.configure("TCheckbutton",
            background=theme.bg,
            foreground=theme.fg
        )

        style.map("TCheckbutton",
            background=[("active", theme.bg)]
        )

        # Radiobutton
        style.configure("TRadiobutton",
            background=theme.bg,
            foreground=theme.fg
        )

        style.map("TRadiobutton",
            background=[("active", theme.bg)]
        )

        # Spinbox
        style.configure("TSpinbox",
            fieldbackground=theme.input_bg,
            foreground=theme.input_fg,
            arrowcolor=theme.fg,
            padding=8
        )

        # LabelFrame
        style.configure("TLabelframe",
            background=theme.bg,
            foreground=theme.fg
        )

        style.configure("TLabelframe.Label",
            background=theme.bg,
            foreground="#ff79c6",  # Dracula pink for labels
            font=("Segoe UI", 10, "bold")
        )

        # Notebook (Tabs)
        style.configure("TNotebook",
            background=theme.bg,
            tabmargins=[2, 5, 2, 0]
        )

        style.configure("TNotebook.Tab",
            background=theme.bg_secondary,
            foreground=theme.fg,
            padding=[15, 8],
            font=("Segoe UI", 10)
        )

        style.map("TNotebook.Tab",
            background=[
                ("selected", theme.bg),
                ("active", theme.bg)
            ],
            foreground=[
                ("selected", "#ff79c6")  # Dracula pink for selected tab
            ],
            expand=[("selected", [1, 1, 1, 0])]
        )

        # Treeview
        style.configure("Treeview",
            background=theme.bg,
            foreground=theme.fg,
            fieldbackground=theme.bg,
            rowheight=32,
            font=("Segoe UI", 10)
        )

        style.configure("Treeview.Heading",
            background=theme.bg_secondary,
            foreground=theme.fg,
            font=("Segoe UI", 10, "bold")
        )

        style.map("Treeview",
            background=[("selected", theme.select_bg)],
            foreground=[("selected", theme.select_fg)]
        )

        # Progressbar - Purple (Dracula accent)
        style.configure("TProgressbar",
            background=theme.progress_fg,
            troughcolor=theme.progress_bg,
            thickness=20
        )

        # Green progress for success
        style.configure("Success.Horizontal.TProgressbar",
            background=theme.success
        )

        # Red progress for error
        style.configure("Error.Horizontal.TProgressbar",
            background=theme.error
        )

        # Pink progress (Dracula pink)
        style.configure("Pink.Horizontal.TProgressbar",
            background="#ff79c6"
        )

        # Cyan progress
        style.configure("Cyan.Horizontal.TProgressbar",
            background="#8be9fd"
        )

        # Scrollbar
        style.configure("TScrollbar",
            background=theme.bg_secondary,
            troughcolor=theme.bg,
            arrowcolor=theme.fg
        )

        style.map("TScrollbar",
            background=[("active", theme.accent)]
        )

        # Separator
        style.configure("TSeparator",
            background=theme.separator
        )

        # Scale
        style.configure("TScale",
            background=theme.bg,
            troughcolor=theme.progress_bg
        )

        # Panedwindow
        style.configure("TPanedwindow",
            background=theme.bg
        )

        # Sizegrip
        style.configure("TSizegrip",
            background=theme.bg
        )

    @property
    def current_theme(self) -> Optional[Theme]:
        """Get current theme."""
        return self._current_theme

    def get_color(self, color_name: str) -> str:
        """Get a color from current theme.

        Args:
            color_name: Name of the color attribute

        Returns:
            Color hex code
        """
        if self._current_theme:
            return getattr(self._current_theme, color_name, "#f8f8f2")
        return "#f8f8f2"

    def add_callback(self, callback):
        """Add theme change callback.

        Args:
            callback: Function(theme) to call on theme change
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback):
        """Remove theme change callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)


# Export Dracula colors for use elsewhere
DRACULA_COLORS = {
    "background": "#282a36",
    "current_line": "#44475a",
    "foreground": "#f8f8f2",
    "comment": "#6272a4",
    "cyan": "#8be9fd",
    "green": "#50fa7b",
    "orange": "#ffb86c",
    "pink": "#ff79c6",
    "purple": "#bd93f9",
    "red": "#ff5555",
    "yellow": "#f1fa8c",
}
