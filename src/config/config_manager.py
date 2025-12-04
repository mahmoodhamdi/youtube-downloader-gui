"""Configuration management for YouTube Downloader.

This module provides centralized configuration management with:
- JSON-based persistence
- Validation on load/save
- Default value handling
- Thread-safe access
"""

import os
import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict

from .validators import ConfigValidator


@dataclass
class AppConfig:
    """Application configuration with default values.

    This dataclass defines all configurable options for the application.
    """
    # Download settings
    download_path: str = field(default_factory=lambda: str(Path.home() / "Downloads"))
    quality: str = "best"
    max_concurrent_downloads: int = 2
    bandwidth_limit: int = 0  # KB/s, 0 = unlimited

    # Retry settings
    retry_attempts: int = 3
    retry_delay: int = 5  # seconds

    # Subtitle settings
    include_subtitles: bool = False
    subtitle_langs: list = field(default_factory=lambda: ["en"])
    auto_translate_subtitles: bool = False

    # Post-processing
    embed_subtitles: bool = False
    embed_thumbnail: bool = False
    add_metadata: bool = True

    # UI settings
    window_geometry: str = "1100x800"
    theme: str = "system"  # light, dark, system
    auto_scroll_log: bool = True

    # Queue settings
    auto_clear_completed: bool = False
    confirm_clear_queue: bool = True

    # System settings
    check_disk_space: bool = True
    min_disk_space_gb: float = 1.0
    check_updates: bool = True

    # Authentication
    cookies_file: str = ""
    proxy: str = ""

    # Advanced
    rate_limit_delay: float = 1.0  # seconds between requests
    socket_timeout: int = 30

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'AppConfig':
        """Create from dictionary."""
        # Filter only valid keys
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


class ConfigManager:
    """Manages application configuration with persistence.

    Features:
    - Thread-safe access
    - Automatic validation
    - JSON persistence
    - Default value handling
    - Change notifications

    Usage:
        config = ConfigManager("config.json")
        config.load()
        download_path = config.get("download_path")
        config.set("quality", "1080p")
        config.save()
    """

    def __init__(
        self,
        config_file: str = "downloader_config.json",
        auto_save: bool = True
    ):
        """Initialize configuration manager.

        Args:
            config_file: Path to configuration file
            auto_save: Automatically save on changes
        """
        self.config_file = config_file
        self.auto_save = auto_save

        self._config = AppConfig()
        self._lock = threading.RLock()
        self._dirty = False

        # Change callbacks
        self._callbacks: list = []

    def load(self) -> bool:
        """Load configuration from file.

        Returns:
            True if loaded successfully
        """
        with self._lock:
            try:
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Validate configuration
                    result = ConfigValidator.validate_config(data)
                    if result.is_valid:
                        self._config = AppConfig.from_dict(result.sanitized_value)
                    else:
                        # Use sanitized values even with errors
                        self._config = AppConfig.from_dict(result.sanitized_value)

                    self._dirty = False
                    return True
                else:
                    # Create default config
                    self._config = AppConfig()
                    self.save()
                    return True

            except Exception as e:
                print(f"Error loading config: {e}")
                self._config = AppConfig()
                return False

    def save(self) -> bool:
        """Save configuration to file.

        Returns:
            True if saved successfully
        """
        with self._lock:
            try:
                data = self._config.to_dict()

                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                self._dirty = False
                return True

            except Exception as e:
                print(f"Error saving config: {e}")
                return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        with self._lock:
            return getattr(self._config, key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value.

        Args:
            key: Configuration key
            value: New value

        Returns:
            True if set successfully
        """
        with self._lock:
            if not hasattr(self._config, key):
                return False

            # Validate single value
            result = ConfigValidator.validate_single(key, value)
            if not result.is_valid:
                return False

            old_value = getattr(self._config, key)
            setattr(self._config, key, value)
            self._dirty = True

            # Notify callbacks
            self._notify_change(key, old_value, value)

            # Auto-save if enabled
            if self.auto_save:
                self.save()

            return True

    def update(self, updates: Dict[str, Any]) -> bool:
        """Update multiple configuration values.

        Args:
            updates: Dictionary of key-value pairs

        Returns:
            True if all updates successful
        """
        with self._lock:
            changes = []

            for key, value in updates.items():
                if hasattr(self._config, key):
                    old_value = getattr(self._config, key)
                    setattr(self._config, key, value)
                    changes.append((key, old_value, value))

            if changes:
                self._dirty = True

                # Notify callbacks
                for key, old_value, new_value in changes:
                    self._notify_change(key, old_value, new_value)

                # Auto-save if enabled
                if self.auto_save:
                    self.save()

            return True

    def reset(self, key: Optional[str] = None):
        """Reset configuration to defaults.

        Args:
            key: Specific key to reset (None = reset all)
        """
        with self._lock:
            if key:
                default_config = AppConfig()
                if hasattr(default_config, key):
                    default_value = getattr(default_config, key)
                    self.set(key, default_value)
            else:
                self._config = AppConfig()
                self._dirty = True

                if self.auto_save:
                    self.save()

    def get_all(self) -> dict:
        """Get all configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        with self._lock:
            return self._config.to_dict()

    def is_dirty(self) -> bool:
        """Check if there are unsaved changes.

        Returns:
            True if there are unsaved changes
        """
        with self._lock:
            return self._dirty

    def add_change_callback(self, callback):
        """Add a callback for configuration changes.

        Args:
            callback: Function(key, old_value, new_value)
        """
        with self._lock:
            self._callbacks.append(callback)

    def remove_change_callback(self, callback):
        """Remove a change callback.

        Args:
            callback: Callback to remove
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _notify_change(self, key: str, old_value: Any, new_value: Any):
        """Notify callbacks of a change."""
        for callback in self._callbacks:
            try:
                callback(key, old_value, new_value)
            except Exception:
                pass

    def export_config(self, filepath: str) -> bool:
        """Export configuration to a file.

        Args:
            filepath: Export file path

        Returns:
            True if exported successfully
        """
        try:
            data = self.get_all()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def import_config(self, filepath: str) -> bool:
        """Import configuration from a file.

        Args:
            filepath: Import file path

        Returns:
            True if imported successfully
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate imported config
            result = ConfigValidator.validate_config(data)
            if result.sanitized_value:
                self._config = AppConfig.from_dict(result.sanitized_value)
                self._dirty = True

                if self.auto_save:
                    self.save()

                return True

            return False
        except Exception:
            return False

    # Property shortcuts for common settings
    @property
    def download_path(self) -> str:
        return self.get("download_path")

    @download_path.setter
    def download_path(self, value: str):
        self.set("download_path", value)

    @property
    def quality(self) -> str:
        return self.get("quality")

    @quality.setter
    def quality(self, value: str):
        self.set("quality", value)

    @property
    def max_concurrent(self) -> int:
        return self.get("max_concurrent_downloads")

    @max_concurrent.setter
    def max_concurrent(self, value: int):
        self.set("max_concurrent_downloads", value)

    @property
    def theme(self) -> str:
        return self.get("theme")

    @theme.setter
    def theme(self, value: str):
        self.set("theme", value)
