"""URL input widget for YouTube Downloader.

Provides single and batch URL input with validation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Optional
import threading


class URLInputWidget(ttk.Frame):
    """Widget for URL input with validation.

    Features:
    - Single URL input with Enter key support
    - Multi-URL input for batch processing
    - Real-time URL validation
    - Paste detection for multiple URLs
    - Loading indicator during extraction

    Usage:
        url_input = URLInputWidget(parent)
        url_input.on_urls_submitted = callback_function
        url_input.pack(fill=tk.X)
    """

    def __init__(self, parent, **kwargs):
        """Initialize URL input widget.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        # Callbacks
        self.on_urls_submitted: Optional[Callable[[List[str]], None]] = None
        self.on_validation_changed: Optional[Callable[[bool], None]] = None

        # State
        self._is_loading = False

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the widget UI."""
        self.columnconfigure(1, weight=1)

        # Single URL section
        single_frame = ttk.LabelFrame(self, text="Add Video URL", padding=10)
        single_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        single_frame.columnconfigure(1, weight=1)

        ttk.Label(single_frame, text="URL:").grid(row=0, column=0, sticky="w", padx=(0, 5))

        self.url_var = tk.StringVar()
        self.url_var.trace_add("write", self._on_url_changed)

        self.url_entry = ttk.Entry(single_frame, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        self.url_entry.bind("<Return>", self._on_add_single)
        self.url_entry.bind("<Control-v>", self._on_paste)

        self.add_button = ttk.Button(
            single_frame,
            text="Add to Queue",
            command=self._on_add_single,
            style="Accent.TButton"
        )
        self.add_button.grid(row=0, column=2)

        # Validation label
        self.validation_label = ttk.Label(single_frame, text="", style="Info.TLabel")
        self.validation_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))

        # Multi URL section
        multi_frame = ttk.LabelFrame(self, text="Batch Add (Multiple URLs)", padding=10)
        multi_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        multi_frame.columnconfigure(0, weight=1)

        ttk.Label(
            multi_frame,
            text="Enter multiple URLs (one per line):",
            style="Subtitle.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Text area with scrollbar
        text_frame = ttk.Frame(multi_frame)
        text_frame.grid(row=1, column=0, sticky="ew")
        text_frame.columnconfigure(0, weight=1)

        self.multi_text = tk.Text(
            text_frame,
            height=4,
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        self.multi_text.grid(row=0, column=0, sticky="ew")

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.multi_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.multi_text.configure(yscrollcommand=scrollbar.set)

        # Multi URL buttons
        btn_frame = ttk.Frame(multi_frame)
        btn_frame.grid(row=2, column=0, sticky="e", pady=(10, 0))

        self.clear_btn = ttk.Button(
            btn_frame,
            text="Clear",
            command=self._clear_multi
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.add_all_btn = ttk.Button(
            btn_frame,
            text="Add All to Queue",
            command=self._on_add_multiple,
            style="Accent.TButton"
        )
        self.add_all_btn.pack(side=tk.LEFT)

        # Loading indicator
        self.loading_label = ttk.Label(self, text="", style="Info.TLabel")
        self.loading_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _on_url_changed(self, *args):
        """Handle URL entry change for validation."""
        url = self.url_var.get().strip()

        if not url:
            self.validation_label.configure(text="", style="Info.TLabel")
            return

        # Simple validation check
        if self._is_valid_url(url):
            self.validation_label.configure(text="✓ Valid URL", style="Success.TLabel")
        else:
            self.validation_label.configure(text="✗ Invalid URL format", style="Error.TLabel")

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL looks like a valid YouTube URL.

        Args:
            url: URL to validate

        Returns:
            True if valid
        """
        import re
        patterns = [
            r'youtube\.com/watch',
            r'youtu\.be/',
            r'youtube\.com/playlist',
            r'youtube\.com/channel',
            r'youtube\.com/@',
            r'youtube\.com/shorts',
        ]

        url_lower = url.lower()
        return any(re.search(p, url_lower) for p in patterns)

    def _on_paste(self, event):
        """Handle paste event to detect multiple URLs."""
        try:
            clipboard = self.clipboard_get()
            urls = self._extract_urls(clipboard)

            if len(urls) > 1:
                # Multiple URLs detected
                result = messagebox.askyesnocancel(
                    "Multiple URLs Detected",
                    f"Found {len(urls)} URLs in clipboard.\n\n"
                    "Yes - Add all to batch area\n"
                    "No - Paste first URL only\n"
                    "Cancel - Cancel paste"
                )

                if result is True:  # Yes
                    self.multi_text.delete("1.0", tk.END)
                    self.multi_text.insert("1.0", "\n".join(urls))
                    return "break"
                elif result is False:  # No
                    self.url_var.set(urls[0])
                    return "break"
                else:  # Cancel
                    return "break"

        except tk.TclError:
            pass

        return None

    def _extract_urls(self, text: str) -> List[str]:
        """Extract YouTube URLs from text.

        Args:
            text: Text to search

        Returns:
            List of found URLs
        """
        import re
        pattern = r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s<>"\']*'
        urls = re.findall(pattern, text)
        return list(dict.fromkeys(urls))  # Remove duplicates, preserve order

    def _on_add_single(self, event=None):
        """Handle add single URL."""
        url = self.url_var.get().strip()

        if not url:
            messagebox.showwarning("Warning", "Please enter a URL")
            return

        if not self._is_valid_url(url):
            messagebox.showerror("Error", "Please enter a valid YouTube URL")
            return

        if self.on_urls_submitted:
            self.on_urls_submitted([url])

        self.url_var.set("")

    def _on_add_multiple(self):
        """Handle add multiple URLs."""
        text = self.multi_text.get("1.0", tk.END).strip()

        if not text:
            messagebox.showwarning("Warning", "Please enter URLs")
            return

        # Parse URLs
        lines = text.split("\n")
        urls = []
        invalid = []

        for line in lines:
            url = line.strip()
            if not url:
                continue

            if self._is_valid_url(url):
                urls.append(url)
            else:
                invalid.append(url)

        if invalid:
            messagebox.showwarning(
                "Invalid URLs",
                f"Skipping {len(invalid)} invalid URL(s):\n\n" +
                "\n".join(invalid[:5]) +
                ("\n..." if len(invalid) > 5 else "")
            )

        if urls and self.on_urls_submitted:
            self.on_urls_submitted(urls)
            self._clear_multi()

    def _clear_multi(self):
        """Clear multi-URL text area."""
        self.multi_text.delete("1.0", tk.END)

    def set_loading(self, loading: bool, message: str = ""):
        """Set loading state.

        Args:
            loading: Whether loading is in progress
            message: Loading message to display
        """
        self._is_loading = loading

        if loading:
            self.loading_label.configure(text=f"⏳ {message}")
            self.add_button.configure(state="disabled")
            self.add_all_btn.configure(state="disabled")
        else:
            self.loading_label.configure(text="")
            self.add_button.configure(state="normal")
            self.add_all_btn.configure(state="normal")

    def clear(self):
        """Clear all inputs."""
        self.url_var.set("")
        self._clear_multi()
        self.validation_label.configure(text="")

    def focus_entry(self):
        """Focus the URL entry field."""
        self.url_entry.focus_set()
