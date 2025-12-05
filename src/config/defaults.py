"""Default configuration values for YouTube Downloader."""

from pathlib import Path


# Application metadata
APP_NAME = "YouTube Downloader Pro"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Mahmood Hamdi"

# Default paths
DEFAULT_DOWNLOAD_PATH = str(Path.home() / "Downloads")
DEFAULT_CONFIG_FILE = "downloader_config.json"
DEFAULT_HISTORY_FILE = "download_history.json"
DEFAULT_LOG_DIR = "logs"

# Quality options
QUALITY_OPTIONS = [
    ("Best Quality", "best"),
    ("2160p (4K)", "2160p"),
    ("1440p (2K)", "1440p"),
    ("1080p (Full HD)", "1080p"),
    ("720p (HD)", "720p"),
    ("480p", "480p"),
    ("360p", "360p"),
    ("Audio Only", "audio_only"),
    ("Worst Quality", "worst"),
]

# Subtitle language options
SUBTITLE_LANGUAGES = [
    ("English", "en"),
    ("Arabic", "ar"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Russian", "ru"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Chinese", "zh"),
    ("Hindi", "hi"),
]

# Theme options (dark mode only for eye comfort)
THEME_OPTIONS = [
    ("Dark Mode", "dark"),
]

# Download limits
MAX_CONCURRENT_DOWNLOADS = 5
MIN_CONCURRENT_DOWNLOADS = 1
DEFAULT_CONCURRENT_DOWNLOADS = 2

MAX_RETRY_ATTEMPTS = 10
MIN_RETRY_ATTEMPTS = 0
DEFAULT_RETRY_ATTEMPTS = 3

MAX_BANDWIDTH_LIMIT = 100000  # KB/s
MIN_BANDWIDTH_LIMIT = 0  # 0 = unlimited
DEFAULT_BANDWIDTH_LIMIT = 0

# Timeouts
DEFAULT_SOCKET_TIMEOUT = 30
DEFAULT_RETRY_DELAY = 5

# UI defaults
DEFAULT_WINDOW_WIDTH = 1100
DEFAULT_WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 700

# Cache settings
MAX_THUMBNAIL_CACHE_SIZE = 100
MAX_VIDEO_INFO_CACHE_SIZE = 500
THUMBNAIL_CACHE_TTL = 3600  # 1 hour
VIDEO_INFO_CACHE_TTL = 7200  # 2 hours

# File settings
MAX_FILENAME_LENGTH = 200
MIN_DISK_SPACE_GB = 1.0

# Rate limiting
DEFAULT_RATE_LIMIT_DELAY = 1.0  # seconds between requests

# Update settings
DEFAULT_AUTO_CHECK_UPDATES = True
