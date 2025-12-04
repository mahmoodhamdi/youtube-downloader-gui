"""Theme management for YouTube Downloader.

Provides light/dark theme support with system theme detection.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
from dataclasses import dataclass
import sys


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


# Light theme
LIGHT_THEME = Theme(
    name="light",
    bg="#ffffff",
    fg="#1a1a1a",
    bg_secondary="#f5f5f5",
    fg_secondary="#666666",
    accent="#0078d4",
    accent_hover="#106ebe",
    accent_pressed="#005a9e",
    success="#107c10",
    warning="#ff8c00",
    error="#d13438",
    info="#0078d4",
    input_bg="#ffffff",
    input_fg="#1a1a1a",
    input_border="#d1d1d1",
    select_bg="#0078d4",
    select_fg="#ffffff",
    progress_bg="#e0e0e0",
    progress_fg="#0078d4",
    border="#d1d1d1",
    separator="#e0e0e0",
)

# Dark theme
DARK_THEME = Theme(
    name="dark",
    bg="#1e1e1e",
    fg="#ffffff",
    bg_secondary="#2d2d2d",
    fg_secondary="#a0a0a0",
    accent="#0078d4",
    accent_hover="#1a8cff",
    accent_pressed="#005a9e",
    success="#6ccb5f",
    warning="#ffb900",
    error="#f85149",
    info="#58a6ff",
    input_bg="#2d2d2d",
    input_fg="#ffffff",
    input_border="#3d3d3d",
    select_bg="#0078d4",
    select_fg="#ffffff",
    progress_bg="#3d3d3d",
    progress_fg="#0078d4",
    border="#3d3d3d",
    separator="#3d3d3d",
)


class ThemeManager:
    """Manages application themes and styling.

    Features:
    - Light/Dark/System theme support
    - Dynamic theme switching
    - ttk style configuration
    - System theme detection

    Usage:
        theme_manager = ThemeManager(root)
        theme_manager.set_theme("dark")
    """

    THEMES = {
        "light": LIGHT_THEME,
        "dark": DARK_THEME,
    }

    def __init__(self, root: tk.Tk):
        """Initialize theme manager.

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.style = ttk.Style()
        self._current_theme: Optional[Theme] = None
        self._callbacks: list = []

    def set_theme(self, theme_name: str):
        """Set the application theme.

        Args:
            theme_name: 'light', 'dark', or 'system'
        """
        if theme_name == "system":
            theme_name = self._detect_system_theme()

        if theme_name not in self.THEMES:
            theme_name = "light"

        theme = self.THEMES[theme_name]
        self._current_theme = theme

        # Apply theme
        self._apply_theme(theme)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(theme)
            except Exception:
                pass

    def _detect_system_theme(self) -> str:
        """Detect system dark/light mode.

        Returns:
            'dark' or 'light'
        """
        try:
            if sys.platform == "win32":
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if value else "dark"

            elif sys.platform == "darwin":
                import subprocess
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True, text=True
                )
                return "dark" if "Dark" in result.stdout else "light"

        except Exception:
            pass

        return "light"

    def _apply_theme(self, theme: Theme):
        """Apply theme to all widgets.

        Args:
            theme: Theme to apply
        """
        # Configure root window
        self.root.configure(bg=theme.bg)

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
            foreground=theme.success
        )

        style.configure("Warning.TLabel",
            foreground=theme.warning
        )

        style.configure("Error.TLabel",
            foreground=theme.error
        )

        style.configure("Info.TLabel",
            foreground=theme.info
        )

        # Button
        style.configure("TButton",
            background=theme.bg_secondary,
            foreground=theme.fg,
            padding=(10, 5),
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
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold")
        )

        style.map("Accent.TButton",
            background=[
                ("active", theme.accent_hover),
                ("pressed", theme.accent_pressed)
            ]
        )

        # Entry
        style.configure("TEntry",
            fieldbackground=theme.input_bg,
            foreground=theme.input_fg,
            insertcolor=theme.fg,
            padding=5
        )

        # Combobox
        style.configure("TCombobox",
            fieldbackground=theme.input_bg,
            foreground=theme.input_fg,
            arrowcolor=theme.fg,
            padding=5
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

        # Spinbox
        style.configure("TSpinbox",
            fieldbackground=theme.input_bg,
            foreground=theme.input_fg,
            arrowcolor=theme.fg,
            padding=5
        )

        # LabelFrame
        style.configure("TLabelframe",
            background=theme.bg,
            foreground=theme.fg
        )

        style.configure("TLabelframe.Label",
            background=theme.bg,
            foreground=theme.fg,
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
                ("selected", theme.accent)
            ],
            expand=[("selected", [1, 1, 1, 0])]
        )

        # Treeview
        style.configure("Treeview",
            background=theme.bg,
            foreground=theme.fg,
            fieldbackground=theme.bg,
            rowheight=30,
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

        # Configure treeview tag colors
        # These will be used in the queue widget

        # Progressbar
        style.configure("TProgressbar",
            background=theme.progress_fg,
            troughcolor=theme.progress_bg,
            thickness=20
        )

        style.configure("Success.Horizontal.TProgressbar",
            background=theme.success
        )

        style.configure("Error.Horizontal.TProgressbar",
            background=theme.error
        )

        # Scrollbar
        style.configure("TScrollbar",
            background=theme.bg_secondary,
            troughcolor=theme.bg,
            arrowcolor=theme.fg
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
            return getattr(self._current_theme, color_name, "#000000")
        return "#000000"

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
