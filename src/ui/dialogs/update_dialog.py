"""Update dialog for yt-dlp updates.

Provides UI for checking and installing yt-dlp updates.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from src.core.update_manager import UpdateManager, UpdateInfo


class UpdateDialog(tk.Toplevel):
    """Dialog for managing yt-dlp updates.

    Features:
    - Display current and latest versions
    - Check for updates button
    - Update now button with progress
    - Status messages

    Usage:
        dialog = UpdateDialog(parent)
        dialog.grab_set()
        parent.wait_window(dialog)
    """

    def __init__(self, parent, update_manager: Optional[UpdateManager] = None):
        """Initialize update dialog.

        Args:
            parent: Parent window
            update_manager: Optional UpdateManager instance
        """
        super().__init__(parent)

        self.update_manager = update_manager or UpdateManager()
        self._update_info: Optional[UpdateInfo] = None

        self.title("yt-dlp Updates")
        self.geometry("450x300")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)

        self._build_ui()
        self._check_version()

    def _build_ui(self):
        """Build the dialog UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Header
        header_frame = ttk.Frame(self, padding=20)
        header_frame.grid(row=0, column=0, sticky="ew")

        ttk.Label(
            header_frame,
            text="yt-dlp Update Manager",
            font=("", 14, "bold")
        ).pack()

        ttk.Label(
            header_frame,
            text="Keep yt-dlp updated for best compatibility with YouTube",
            foreground="gray"
        ).pack(pady=(5, 0))

        # Version info frame
        version_frame = ttk.LabelFrame(self, text="Version Information", padding=15)
        version_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        version_frame.columnconfigure(1, weight=1)

        # Current version
        ttk.Label(version_frame, text="Current Version:").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=5
        )
        self.current_version_label = ttk.Label(
            version_frame,
            text="Checking...",
            font=("", 10, "bold")
        )
        self.current_version_label.grid(row=0, column=1, sticky="w", pady=5)

        # Latest version
        ttk.Label(version_frame, text="Latest Version:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=5
        )
        self.latest_version_label = ttk.Label(
            version_frame,
            text="Checking...",
            font=("", 10, "bold")
        )
        self.latest_version_label.grid(row=1, column=1, sticky="w", pady=5)

        # Status
        ttk.Label(version_frame, text="Status:").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=5
        )
        self.status_label = ttk.Label(
            version_frame,
            text="Checking for updates..."
        )
        self.status_label.grid(row=2, column=1, sticky="w", pady=5)

        # Progress bar (hidden initially)
        self.progress_bar = ttk.Progressbar(
            version_frame,
            mode="indeterminate",
            length=200
        )

        # Buttons
        btn_frame = ttk.Frame(self, padding=20)
        btn_frame.grid(row=3, column=0, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        self.check_btn = ttk.Button(
            btn_frame,
            text="Check for Updates",
            command=self._check_for_updates
        )
        self.check_btn.grid(row=0, column=0, padx=5)

        self.update_btn = ttk.Button(
            btn_frame,
            text="Update Now",
            command=self._do_update,
            state="disabled"
        )
        self.update_btn.grid(row=0, column=1, padx=5)

        ttk.Button(
            btn_frame,
            text="Close",
            command=self.destroy
        ).grid(row=0, column=2, padx=5)

    def _check_version(self):
        """Check current version on dialog open."""
        current = self.update_manager.get_current_version()
        self.current_version_label.config(text=current)

    def _check_for_updates(self):
        """Check for available updates."""
        self.check_btn.config(state="disabled")
        self.update_btn.config(state="disabled")
        self.status_label.config(text="Checking for updates...")
        self.latest_version_label.config(text="Checking...")

        # Show progress
        self.progress_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.progress_bar.start(10)

        # Run check in background
        self.after(100, self._do_check)

    def _do_check(self):
        """Perform the update check."""
        import threading

        def check_task():
            info = self.update_manager.check_for_updates()
            self.after(0, lambda: self._on_check_complete(info))

        thread = threading.Thread(target=check_task, daemon=True)
        thread.start()

    def _on_check_complete(self, info: UpdateInfo):
        """Handle check completion.

        Args:
            info: Update information
        """
        self._update_info = info
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

        self.current_version_label.config(text=info.current_version)
        self.latest_version_label.config(text=info.latest_version)

        self.check_btn.config(state="normal")

        if info.error:
            self.status_label.config(text=info.error, foreground="red")
            self.update_btn.config(state="disabled")
        elif info.update_available:
            self.status_label.config(
                text="Update available!",
                foreground="green"
            )
            self.update_btn.config(state="normal")
        else:
            self.status_label.config(
                text="You have the latest version",
                foreground="green"
            )
            self.update_btn.config(state="disabled")

    def _do_update(self):
        """Perform the update."""
        if not self._update_info or not self._update_info.update_available:
            return

        # Confirm update
        if not messagebox.askyesno(
            "Confirm Update",
            f"Update yt-dlp from {self._update_info.current_version} "
            f"to {self._update_info.latest_version}?",
            parent=self
        ):
            return

        self.check_btn.config(state="disabled")
        self.update_btn.config(state="disabled")
        self.status_label.config(text="Updating...")

        # Show progress
        self.progress_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.progress_bar.start(10)

        # Run update
        def on_complete(success: bool, message: str):
            self.after(0, lambda: self._on_update_complete(success, message))

        def on_progress(msg: str):
            self.after(0, lambda: self.status_label.config(text=msg))

        self.update_manager.update_ytdlp_async(
            on_complete=on_complete,
            on_progress=on_progress
        )

    def _on_update_complete(self, success: bool, message: str):
        """Handle update completion.

        Args:
            success: Whether update succeeded
            message: Status message
        """
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

        self.check_btn.config(state="normal")

        if success:
            self.status_label.config(text="Update successful!", foreground="green")
            new_version = self.update_manager.get_current_version()
            self.current_version_label.config(text=new_version)
            self.latest_version_label.config(text=new_version)
            self.update_btn.config(state="disabled")

            messagebox.showinfo(
                "Update Complete",
                message,
                parent=self
            )
        else:
            self.status_label.config(text="Update failed", foreground="red")
            self.update_btn.config(state="normal")

            messagebox.showerror(
                "Update Failed",
                message,
                parent=self
            )


def show_update_dialog(parent, update_manager: Optional[UpdateManager] = None):
    """Show the update dialog.

    Args:
        parent: Parent window
        update_manager: Optional UpdateManager instance

    Returns:
        The dialog instance
    """
    dialog = UpdateDialog(parent, update_manager)
    dialog.grab_set()
    return dialog
