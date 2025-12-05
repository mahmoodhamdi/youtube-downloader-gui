"""Styled widgets with Dracula theme colors.

Provides pre-styled tk widgets with dark theme colors
since ttk widgets don't always respect theme settings.
"""

import tkinter as tk
from tkinter import ttk

# Dracula theme colors
DRACULA = {
    "bg": "#282a36",
    "fg": "#f8f8f2",
    "input_bg": "#21222c",
    "selection": "#44475a",
    "cursor": "#f8f8f2",
    "border": "#44475a",
    "accent": "#bd93f9",
    "purple": "#bd93f9",
    "pink": "#ff79c6",
    "cyan": "#8be9fd",
    "green": "#50fa7b",
    "orange": "#ffb86c",
    "red": "#ff5555",
    "yellow": "#f1fa8c",
}


class StyledEntry(tk.Entry):
    """Dark themed Entry widget."""

    def __init__(self, parent, **kwargs):
        # Default styling
        defaults = {
            "bg": DRACULA["input_bg"],
            "fg": DRACULA["fg"],
            "insertbackground": DRACULA["cursor"],
            "selectbackground": DRACULA["selection"],
            "selectforeground": DRACULA["fg"],
            "relief": "flat",
            "font": ("Segoe UI", 10),
            "highlightthickness": 1,
            "highlightcolor": DRACULA["accent"],
            "highlightbackground": DRACULA["border"],
        }

        # Merge with provided kwargs
        defaults.update(kwargs)
        super().__init__(parent, **defaults)


class StyledText(tk.Text):
    """Dark themed Text widget."""

    def __init__(self, parent, **kwargs):
        # Default styling
        defaults = {
            "bg": DRACULA["input_bg"],
            "fg": DRACULA["fg"],
            "insertbackground": DRACULA["cursor"],
            "selectbackground": DRACULA["selection"],
            "selectforeground": DRACULA["fg"],
            "relief": "flat",
            "font": ("Consolas", 10),
            "highlightthickness": 1,
            "highlightcolor": DRACULA["accent"],
            "highlightbackground": DRACULA["border"],
        }

        # Merge with provided kwargs
        defaults.update(kwargs)
        super().__init__(parent, **defaults)


class StyledListbox(tk.Listbox):
    """Dark themed Listbox widget."""

    def __init__(self, parent, **kwargs):
        defaults = {
            "bg": DRACULA["input_bg"],
            "fg": DRACULA["fg"],
            "selectbackground": DRACULA["selection"],
            "selectforeground": DRACULA["fg"],
            "relief": "flat",
            "font": ("Segoe UI", 10),
            "highlightthickness": 1,
            "highlightcolor": DRACULA["accent"],
            "highlightbackground": DRACULA["border"],
            "activestyle": "none",
        }

        defaults.update(kwargs)
        super().__init__(parent, **defaults)


class StyledSpinbox(tk.Spinbox):
    """Dark themed Spinbox widget."""

    def __init__(self, parent, **kwargs):
        defaults = {
            "bg": DRACULA["input_bg"],
            "fg": DRACULA["fg"],
            "insertbackground": DRACULA["cursor"],
            "selectbackground": DRACULA["selection"],
            "selectforeground": DRACULA["fg"],
            "relief": "flat",
            "font": ("Segoe UI", 10),
            "highlightthickness": 1,
            "highlightcolor": DRACULA["accent"],
            "highlightbackground": DRACULA["border"],
            "buttonbackground": DRACULA["border"],
        }

        defaults.update(kwargs)
        super().__init__(parent, **defaults)


def apply_dark_style_to_entry(entry_widget):
    """Apply dark styling to an existing tk.Entry or ttk.Entry widget.

    Args:
        entry_widget: The entry widget to style
    """
    if isinstance(entry_widget, tk.Entry) and not isinstance(entry_widget, ttk.Entry):
        entry_widget.configure(
            bg=DRACULA["input_bg"],
            fg=DRACULA["fg"],
            insertbackground=DRACULA["cursor"],
            selectbackground=DRACULA["selection"],
            selectforeground=DRACULA["fg"],
            relief="flat",
            highlightthickness=1,
            highlightcolor=DRACULA["accent"],
            highlightbackground=DRACULA["border"],
        )


def apply_dark_style_to_text(text_widget):
    """Apply dark styling to an existing tk.Text widget.

    Args:
        text_widget: The text widget to style
    """
    text_widget.configure(
        bg=DRACULA["input_bg"],
        fg=DRACULA["fg"],
        insertbackground=DRACULA["cursor"],
        selectbackground=DRACULA["selection"],
        selectforeground=DRACULA["fg"],
        relief="flat",
        highlightthickness=1,
        highlightcolor=DRACULA["accent"],
        highlightbackground=DRACULA["border"],
    )


def get_colors():
    """Get the Dracula color palette.

    Returns:
        dict: Color palette dictionary
    """
    return DRACULA.copy()
