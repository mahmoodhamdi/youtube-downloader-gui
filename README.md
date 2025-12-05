# YouTube Downloader Pro v2.0

A modern, feature-rich GUI application for downloading YouTube videos and playlists with advanced queue management, batch processing, and a professional user interface.

![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)
![Version](https://img.shields.io/badge/version-2.0.0-orange.svg)
![Tests](https://img.shields.io/badge/tests-106%20passing-brightgreen.svg)

## What's New in v2.0

### Complete Architecture Rewrite
- **Modular Design**: Clean separation of concerns with dedicated modules for core logic, UI, configuration, and utilities
- **Thread-Safe Operations**: No more race conditions or UI freezing during downloads
- **Comprehensive Test Suite**: 106 passing tests covering all core functionality

### Core Features
- **Download Queue Manager**: Thread-safe queue with priority support, status tracking, and progress updates
- **Download Session Manager**: Resume interrupted downloads with automatic session persistence
- **Rate Limiter**: Prevent IP bans with configurable request throttling and adaptive rate limiting
- **Format Selector**: Advanced format selection with resolution, codec, and quality options

### Authentication & Network
- **Cookie-based Authentication**: Access age-restricted and members-only content
- **Browser Cookie Import**: Import cookies from Chrome, Firefox, Edge, Brave, Opera, and more
- **Proxy Support**: HTTP, HTTPS, SOCKS4, SOCKS5, and SOCKS5H proxy support
- **Proxy Testing**: Built-in proxy connection testing with latency measurement

### Post-Processing
- **FFmpeg Integration**: Format conversion, audio extraction, and video remuxing
- **Subtitle Embedding**: Embed subtitles directly into video files
- **Thumbnail Embedding**: Add thumbnails as cover art to media files
- **SponsorBlock Integration**: Automatically remove or mark sponsor segments

### UI/UX Improvements
- **System Tray Support**: Minimize to system tray with notifications
- **Format Selection Dialog**: Visual format picker with quality previews
- **Playlist Filter Dialog**: Filter playlist videos by index, title, or duration
- **Queue Search**: Search and filter items in the download queue
- **Statistics Tab**: View download statistics and usage metrics
- **Keyboard Shortcuts**: Quick access to common actions

## Features

### Download Capabilities
- **Multi-URL Support**: Download single videos, playlists, channels, and shorts
- **Quality Selection**: Choose from best, 4K, 1440p, 1080p, 720p, 480p, 360p, or audio-only
- **Concurrent Downloads**: Download multiple videos simultaneously (configurable 1-5)
- **Subtitle Download**: Automatic subtitle download with language selection
- **Batch Processing**: Queue multiple videos for sequential/parallel download
- **Download Resume**: Resume interrupted downloads automatically

### User Interface
- **Tabbed Interface**: Organized into Downloads, Settings, History, and Statistics tabs
- **Real-time Progress**: Individual and overall progress with speed and ETA
- **Queue Management**: Add, remove, reorder, search, and retry items in the queue
- **Status Logging**: Color-coded log messages with export functionality
- **Theme Support**: Light, Dark, and System theme detection

### Configuration Options
- **Download Settings**: Path, quality, format, filename template
- **Network Settings**: Concurrent downloads, retries, rate limit, proxy
- **Subtitle Settings**: Language selection, auto-generated, embedding
- **Appearance**: Light/Dark/System theme, window size, notifications
- **Advanced**: FFmpeg path, cookies, metadata embedding, SponsorBlock

## Installation

### Prerequisites
- Python 3.10 or higher
- FFmpeg (recommended for best quality)

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/mahmoodhamdi/youtube-downloader-gui.git
   cd youtube-downloader-gui
   ```

2. **Create virtual environment** (recommended):
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

### Installing FFmpeg

FFmpeg is required for merging video and audio streams and for post-processing features.

- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` or `sudo dnf install ffmpeg`

## Project Structure

```
youtube-downloader-gui/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Development dependencies
├── README.md                    # This file
├── CLAUDE.md                    # Development guidelines
├── DEVELOPMENT_PLAN.md          # Development roadmap
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                    # Core business logic
│   │   ├── __init__.py
│   │   ├── queue_manager.py     # Thread-safe queue management
│   │   ├── download_manager.py  # yt-dlp integration
│   │   ├── session_manager.py   # Download resume capability
│   │   ├── rate_limiter.py      # Request rate limiting
│   │   ├── format_selector.py   # Video format selection
│   │   ├── playlist_filter.py   # Playlist filtering
│   │   ├── update_manager.py    # Auto-update functionality
│   │   └── post_processor.py    # FFmpeg post-processing
│   │
│   ├── auth/                    # Authentication
│   │   ├── __init__.py
│   │   ├── auth_manager.py      # Cookie-based authentication
│   │   └── proxy_manager.py     # Proxy/VPN support
│   │
│   ├── config/                  # Configuration management
│   │   ├── __init__.py
│   │   ├── config_manager.py    # Settings persistence
│   │   ├── validators.py        # Input validation
│   │   └── defaults.py          # Default values
│   │
│   ├── ui/                      # User interface
│   │   ├── __init__.py
│   │   ├── main_window.py       # Main application window
│   │   ├── system_tray.py       # System tray integration
│   │   ├── keyboard_shortcuts.py # Keyboard shortcut handling
│   │   │
│   │   ├── tabs/                # Tab components
│   │   │   ├── downloads_tab.py # Downloads interface
│   │   │   ├── settings_tab.py  # Settings interface
│   │   │   ├── history_tab.py   # History interface
│   │   │   └── statistics_tab.py # Statistics interface
│   │   │
│   │   ├── widgets/             # Reusable widgets
│   │   │   ├── url_input.py     # URL input widget
│   │   │   ├── progress_widget.py
│   │   │   ├── queue_widget.py
│   │   │   ├── queue_search.py  # Queue search widget
│   │   │   └── status_bar.py
│   │   │
│   │   ├── themes/              # Theme management
│   │   │   └── theme_manager.py
│   │   │
│   │   └── dialogs/             # Dialog windows
│   │       ├── __init__.py
│   │       ├── format_dialog.py  # Format selection
│   │       ├── playlist_dialog.py # Playlist filtering
│   │       └── update_dialog.py  # Update notifications
│   │
│   ├── utils/                   # Utility modules
│   │   ├── __init__.py
│   │   ├── logger.py            # Logging system
│   │   ├── error_handler.py     # Error handling
│   │   ├── cache.py             # Caching utilities
│   │   └── file_utils.py        # File operations
│   │
│   └── exceptions/              # Custom exceptions
│       ├── __init__.py
│       └── errors.py
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Test fixtures
│   ├── test_queue_manager.py
│   ├── test_config.py
│   ├── test_format_selector.py
│   ├── test_playlist_filter.py
│   └── test_integration.py
│
└── plans/                       # Feature plans
    └── *.md
```

## Usage Guide

### Basic Usage

1. **Add URLs**:
   - Paste a single URL and click "Add to Queue"
   - Or use Ctrl+V to add from clipboard

2. **Configure Settings**:
   - Set download path
   - Choose quality preset
   - Enable/disable subtitles

3. **Manage Queue**:
   - Search items with the search bar
   - Reorder items with Move Up/Down
   - Remove unwanted items
   - Retry failed downloads

4. **Start Downloads**:
   - Click "Start Downloads" to begin
   - Use Pause/Resume/Stop as needed

### Advanced Features

#### Authentication for Private Videos
```python
# Import cookies from browser
auth_manager.import_cookies_from_browser("chrome")

# Or use a cookies file
auth_manager.import_cookies_file("/path/to/cookies.txt")
```

#### Proxy Configuration
```python
# Set up SOCKS5 proxy
proxy_manager.set_proxy("socks5", "127.0.0.1", 1080)

# Or with authentication
proxy_manager.set_proxy("http", "proxy.example.com", 8080,
                       username="user", password="pass")
```

#### Post-Processing Options
```python
options = PostProcessingOptions(
    embed_subtitles=True,
    embed_thumbnail=True,
    extract_audio=True,
    audio_format="mp3",
    audio_quality="320"
)
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Add URL dialog |
| `Ctrl+V` | Add from clipboard |
| `Ctrl+S` | Start downloads |
| `Ctrl+A` | Select all in queue |
| `Delete` | Remove selected |
| `Ctrl+F` | Focus search |

### Supported URL Formats

- `https://youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/playlist?list=PLAYLIST_ID`
- `https://youtube.com/channel/CHANNEL_ID`
- `https://youtube.com/@username`
- `https://youtube.com/shorts/SHORT_ID`

## Configuration

Configuration is stored in `~/.ytdownloader/config.json`:

```json
{
  "download_path": "~/Downloads",
  "quality": "best",
  "preferred_format": "mp4",
  "max_concurrent_downloads": 2,
  "retry_attempts": 3,
  "include_subtitles": false,
  "subtitle_language": "en",
  "theme": "system",
  "show_notifications": true,
  "rate_limit": {
    "requests_per_minute": 30,
    "cooldown_seconds": 5
  }
}
```

## Development

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Code Style
```bash
# Format code
black src/

# Check linting
flake8 src/
```

### Test Coverage
- 106 tests passing
- Core modules fully tested
- Integration tests for main workflows

## Dependencies

| Package | Purpose |
|---------|---------|
| `yt-dlp` | Video extraction and downloading |
| `tkinter` | GUI framework (included with Python) |
| `requests` | HTTP requests for proxy testing |

### Development Dependencies
| Package | Purpose |
|---------|---------|
| `pytest` | Testing framework |
| `pytest-cov` | Test coverage |
| `black` | Code formatting |
| `flake8` | Linting |

## Troubleshooting

### Common Issues

1. **"Module not found" errors**
   ```bash
   pip install -r requirements.txt
   ```

2. **GUI not appearing (Linux)**
   ```bash
   sudo apt-get install python3-tk
   ```

3. **Download fails with merge error**
   - Install FFmpeg and ensure it's in PATH

4. **Age-restricted videos**
   - Configure cookies file in Advanced Settings
   - Or import cookies from your browser

5. **Rate limited by YouTube**
   - Enable rate limiting in settings
   - Use a proxy or VPN

### Error Messages

| Error | Solution |
|-------|----------|
| Invalid URL | Check URL format |
| Network error | Check internet connection |
| Rate limited | Wait and retry, or use rate limiting |
| No video formats | Video may be unavailable |
| Authentication required | Configure cookies |

## Roadmap

- [x] Phase 1: Critical Fixes - Queue stability, thread safety
- [x] Phase 2: Performance & Stability - Session resume, rate limiting
- [x] Phase 3: New Features - Auth, proxy, post-processing
- [x] Phase 4: UI/UX - System tray, dialogs, shortcuts
- [x] Phase 5: Project Restructuring - Modular architecture
- [x] Phase 6: Testing - Comprehensive test suite

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `python -m pytest`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for personal use only. Please respect copyright laws and YouTube's Terms of Service. The developers are not responsible for any misuse of this application.

## Support

- **Issues**: [GitHub Issues](https://github.com/mahmoodhamdi/youtube-downloader-gui/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mahmoodhamdi/youtube-downloader-gui/discussions)
- **Email**: hmdy7486@gmail.com

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The powerful backend for video downloading
- [Python](https://python.org) - The programming language
- The open-source community

---

**Made with care by Mahmood Hamdi**
