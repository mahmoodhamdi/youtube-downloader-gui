"""System tray integration for YouTube Downloader.

Provides system tray icon with menu and notifications.
"""

import threading
import sys
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class TrayCallbacks:
    """Callbacks for tray menu actions."""
    on_show: Optional[Callable[[], None]] = None
    on_hide: Optional[Callable[[], None]] = None
    on_start_downloads: Optional[Callable[[], None]] = None
    on_pause_downloads: Optional[Callable[[], None]] = None
    on_stop_downloads: Optional[Callable[[], None]] = None
    on_quit: Optional[Callable[[], None]] = None


class SystemTray:
    """System tray icon manager.

    Features:
    - Tray icon with context menu
    - Show/hide main window
    - Quick download controls
    - Desktop notifications
    - Download progress in tooltip

    Usage:
        tray = SystemTray(callbacks)
        tray.start()
        tray.update_tooltip("Downloading: 50%")
        tray.show_notification("Download Complete", "video.mp4")
        tray.stop()

    Note:
        Requires pystray and pillow packages for full functionality.
        Falls back gracefully if packages are not available.
    """

    def __init__(self, callbacks: Optional[TrayCallbacks] = None):
        """Initialize system tray.

        Args:
            callbacks: Callbacks for menu actions
        """
        self.callbacks = callbacks or TrayCallbacks()
        self._icon = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self._is_available = self._check_availability()

        # State
        self._is_downloading = False
        self._is_paused = False
        self._progress = 0.0

    def _check_availability(self) -> bool:
        """Check if system tray is available.

        Returns:
            True if pystray and PIL are available
        """
        try:
            import pystray
            from PIL import Image
            return True
        except ImportError:
            return False

    @property
    def is_available(self) -> bool:
        """Check if system tray functionality is available."""
        return self._is_available

    def _create_icon_image(self, size: int = 64):
        """Create a simple icon image.

        Args:
            size: Icon size in pixels

        Returns:
            PIL Image object
        """
        from PIL import Image, ImageDraw

        # Create a simple download icon
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Background circle (red/orange for YouTube theme)
        padding = 4
        draw.ellipse(
            [padding, padding, size - padding, size - padding],
            fill=(255, 0, 0, 255)
        )

        # White arrow pointing down
        arrow_margin = size // 4
        arrow_width = size // 6
        center_x = size // 2
        center_y = size // 2

        # Arrow body (rectangle)
        draw.rectangle(
            [
                center_x - arrow_width // 2,
                arrow_margin,
                center_x + arrow_width // 2,
                center_y + arrow_margin // 2
            ],
            fill=(255, 255, 255, 255)
        )

        # Arrow head (triangle)
        draw.polygon(
            [
                (arrow_margin, center_y),
                (size - arrow_margin, center_y),
                (center_x, size - arrow_margin)
            ],
            fill=(255, 255, 255, 255)
        )

        return image

    def _create_menu(self):
        """Create the tray menu.

        Returns:
            pystray Menu object
        """
        import pystray

        def show_window(icon, item):
            if self.callbacks.on_show:
                self.callbacks.on_show()

        def hide_window(icon, item):
            if self.callbacks.on_hide:
                self.callbacks.on_hide()

        def start_downloads(icon, item):
            if self.callbacks.on_start_downloads:
                self.callbacks.on_start_downloads()

        def pause_downloads(icon, item):
            if self.callbacks.on_pause_downloads:
                self.callbacks.on_pause_downloads()

        def stop_downloads(icon, item):
            if self.callbacks.on_stop_downloads:
                self.callbacks.on_stop_downloads()

        def quit_app(icon, item):
            self.stop()
            if self.callbacks.on_quit:
                self.callbacks.on_quit()

        return pystray.Menu(
            pystray.MenuItem("Show Window", show_window, default=True),
            pystray.MenuItem("Hide Window", hide_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Start Downloads",
                start_downloads,
                enabled=lambda item: not self._is_downloading
            ),
            pystray.MenuItem(
                "Pause Downloads",
                pause_downloads,
                enabled=lambda item: self._is_downloading and not self._is_paused
            ),
            pystray.MenuItem(
                "Stop Downloads",
                stop_downloads,
                enabled=lambda item: self._is_downloading
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", quit_app),
        )

    def start(self):
        """Start the system tray icon."""
        if not self._is_available:
            return

        if self._is_running:
            return

        import pystray

        try:
            image = self._create_icon_image()
            menu = self._create_menu()

            self._icon = pystray.Icon(
                name="YouTube Downloader",
                icon=image,
                title="YouTube Downloader Pro",
                menu=menu
            )

            # Run in separate thread
            self._thread = threading.Thread(
                target=self._icon.run,
                daemon=True
            )
            self._thread.start()
            self._is_running = True

        except Exception as e:
            print(f"Failed to start system tray: {e}")
            self._is_running = False

    def stop(self):
        """Stop the system tray icon."""
        if self._icon and self._is_running:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._is_running = False

    def update_tooltip(self, text: str):
        """Update the tray icon tooltip.

        Args:
            text: New tooltip text
        """
        if self._icon and self._is_running:
            try:
                self._icon.title = text
            except Exception:
                pass

    def update_state(self, is_downloading: bool, is_paused: bool = False, progress: float = 0.0):
        """Update download state for menu and tooltip.

        Args:
            is_downloading: Whether downloads are active
            is_paused: Whether downloads are paused
            progress: Overall progress (0.0 - 100.0)
        """
        self._is_downloading = is_downloading
        self._is_paused = is_paused
        self._progress = progress

        # Update tooltip
        if is_downloading:
            if is_paused:
                tooltip = f"YouTube Downloader - Paused ({progress:.1f}%)"
            else:
                tooltip = f"YouTube Downloader - Downloading {progress:.1f}%"
        else:
            tooltip = "YouTube Downloader Pro"

        self.update_tooltip(tooltip)

        # Update menu (force refresh)
        if self._icon:
            try:
                self._icon.update_menu()
            except Exception:
                pass

    def show_notification(self, title: str, message: str):
        """Show a desktop notification.

        Args:
            title: Notification title
            message: Notification message
        """
        if not self._icon or not self._is_running:
            return

        try:
            self._icon.notify(message, title)
        except Exception:
            # Notifications may not be supported on all platforms
            pass

    def remove_notification(self):
        """Remove any active notification."""
        if self._icon and self._is_running:
            try:
                self._icon.remove_notification()
            except Exception:
                pass


class SystemTrayManager:
    """Manager for system tray integration with the main application.

    Handles the connection between tray and main window.

    Usage:
        manager = SystemTrayManager(main_window, config)
        manager.setup()
    """

    def __init__(self, main_window, config_manager):
        """Initialize tray manager.

        Args:
            main_window: Main application window
            config_manager: Configuration manager
        """
        self.main_window = main_window
        self.config = config_manager
        self.tray: Optional[SystemTray] = None

    def setup(self):
        """Set up system tray if enabled in config."""
        if not self.config.get("minimize_to_tray", False):
            return

        callbacks = TrayCallbacks(
            on_show=self._show_window,
            on_hide=self._hide_window,
            on_start_downloads=self._start_downloads,
            on_pause_downloads=self._pause_downloads,
            on_stop_downloads=self._stop_downloads,
            on_quit=self._quit_app
        )

        self.tray = SystemTray(callbacks)

        if self.tray.is_available:
            self.tray.start()

    def _show_window(self):
        """Show the main window."""
        if hasattr(self.main_window, 'root'):
            self.main_window.root.deiconify()
            self.main_window.root.lift()
            self.main_window.root.focus_force()

    def _hide_window(self):
        """Hide the main window to tray."""
        if hasattr(self.main_window, 'root'):
            self.main_window.root.withdraw()

    def _start_downloads(self):
        """Start downloads from tray."""
        if hasattr(self.main_window, '_start_downloads'):
            self.main_window._start_downloads()

    def _pause_downloads(self):
        """Pause downloads from tray."""
        if hasattr(self.main_window, '_pause_downloads'):
            self.main_window._pause_downloads()

    def _stop_downloads(self):
        """Stop downloads from tray."""
        if hasattr(self.main_window, '_stop_downloads'):
            self.main_window._stop_downloads()

    def _quit_app(self):
        """Quit the application."""
        if hasattr(self.main_window, 'root'):
            self.main_window.root.quit()

    def update_progress(self, progress: float, is_downloading: bool, is_paused: bool = False):
        """Update tray with download progress.

        Args:
            progress: Overall progress percentage
            is_downloading: Whether downloading
            is_paused: Whether paused
        """
        if self.tray:
            self.tray.update_state(is_downloading, is_paused, progress)

    def notify(self, title: str, message: str):
        """Show notification if enabled.

        Args:
            title: Notification title
            message: Notification message
        """
        if self.tray and self.config.get("show_notifications", True):
            self.tray.show_notification(title, message)

    def cleanup(self):
        """Clean up tray resources."""
        if self.tray:
            self.tray.stop()
