# YouTube Downloader Pro v2.0 🎥

A modern, feature-rich GUI application for downloading YouTube videos and playlists with advanced queue management, batch processing, and a professional user interface.

![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)
![Version](https://img.shields.io/badge/version-2.0.0-orange.svg)

## What's New in v2.0 🚀

- **Completely Rewritten Architecture**: Modular, maintainable codebase
- **Thread-Safe Operations**: No more race conditions or freezing
- **Enhanced UI**: Modern tabbed interface with Downloads, Settings, and History tabs
- **Advanced Queue Management**: Drag & drop, reordering, retry failed downloads
- **Comprehensive Settings**: Full control over downloads, network, subtitles, and appearance
- **Download History**: Track all your downloads with search and filtering
- **Theme Support**: Light and Dark themes with system theme detection
- **Robust Error Handling**: User-friendly error messages and automatic retries

## Features ✨

### Core Features
- **Multi-URL Support**: Download single videos, playlists, channels, and shorts
- **Quality Selection**: Choose from best, 1080p, 720p, 480p, 360p, or audio-only
- **Concurrent Downloads**: Download multiple videos simultaneously (configurable 1-5)
- **Subtitle Download**: Automatic subtitle download with language selection
- **Batch Processing**: Queue multiple videos for sequential/parallel download

### User Interface
- **Tabbed Interface**: Organized into Downloads, Settings, and History tabs
- **Real-time Progress**: Individual and overall progress with speed and ETA
- **Queue Management**: Add, remove, reorder, retry items in the queue
- **Status Logging**: Color-coded log messages with export functionality
- **Keyboard Shortcuts**: Quick access to common actions

### Settings & Configuration
- **Download Settings**: Path, quality, format, filename template
- **Network Settings**: Concurrent downloads, retries, rate limit, proxy
- **Subtitle Settings**: Language selection, auto-generated, embedding
- **Appearance**: Light/Dark/System theme, window size, notifications
- **Advanced**: FFmpeg path, cookies, metadata embedding

### History & Tracking
- **Download History**: Complete record of all downloads
- **Search & Filter**: Find downloads by title, channel, date, or status
- **Quick Actions**: Re-download, open file/folder, copy URL
- **Export**: Export history to CSV or JSON

## Screenshots 📸

### Downloads Tab
```
┌─────────────────────────────────────────────────────────────────────┐
│  YouTube Downloader Pro v2.0          [─] [□] [×]                   │
├──────────────┬──────────────┬──────────────────────────────────────┤
│ ● Downloads  │   Settings   │   History                            │
├──────────────┴──────────────┴──────────────────────────────────────┤
│ ┌─ Add Video URL ─────────────────────────────────────────────────┐│
│ │ URL: [https://youtube.com/watch?v=...     ] [Add to Queue]     ││
│ │ ✓ Valid URL                                                     ││
│ └─────────────────────────────────────────────────────────────────┘│
│ ┌─ Quick Settings ────────────────────────────────────────────────┐│
│ │ Download Path: [C:\Downloads          ] [Browse] [Open]        ││
│ │ Quality: [best ▼]  Concurrent: [2]  ☑ Download Subtitles      ││
│ └─────────────────────────────────────────────────────────────────┘│
│ ┌─ Download Queue ────────────────────────────────────────────────┐│
│ │ Title              │ Duration │ Size    │ Status     │ Progress ││
│ │ Amazing Video      │ 10:25    │ 150 MB  │ Downloading│ 45.2%   ││
│ │ Tutorial Part 1    │ 25:30    │ 380 MB  │ Queued     │ 0.0%    ││
│ │ Music Video        │ 03:45    │ 45 MB   │ Completed  │ 100.0%  ││
│ │ [Remove Selected] [Clear Queue] [↑ Move Up] [↓ Move Down]      ││
│ └─────────────────────────────────────────────────────────────────┘│
│ ┌─ Current Download ──────────────────────────────────────────────┐│
│ │ Progress: ████████████████████░░░░░░░░░░░░░░░░░░░░  45.2%     ││
│ │ Amazing Video                                                   ││
│ │ Speed: 5.2 MB/s  │  ETA: 2m 15s  │  Downloaded: 67.5 MB       ││
│ └─────────────────────────────────────────────────────────────────┘│
│ ┌─ Overall Progress ──────────────────────────────────────────────┐│
│ │ Progress: ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  25.0%     ││
│ │ Active: 1  │  Queued: 2  │  Completed: 1                       ││
│ └─────────────────────────────────────────────────────────────────┘│
│  [▶ Start Downloads] [⏸ Pause] [▶ Resume] [⏹ Stop]               │
├───────────────────────────────────────────────────────────────────┤
│ ┌─ Status Log ────────────────────────────────────────────────────┐│
│ │ [14:25:30] [INFO] Added: Amazing Video                         ││
│ │ [14:25:32] [SUCCESS] Download started                          ││
│ │ [14:26:15] [SUCCESS] Completed: Music Video                    ││
│ └─────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────┘
```

## Installation 🚀

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

FFmpeg is required for merging video and audio streams and for some post-processing features.

- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` or `sudo dnf install ffmpeg`

## Project Structure 📁

```
youtube-downloader-gui/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
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
│   │   └── download_manager.py  # yt-dlp integration
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
│   │   │
│   │   ├── tabs/                # Tab components
│   │   │   ├── downloads_tab.py # Downloads interface
│   │   │   ├── settings_tab.py  # Settings interface
│   │   │   └── history_tab.py   # History interface
│   │   │
│   │   ├── widgets/             # Reusable widgets
│   │   │   ├── url_input.py     # URL input widget
│   │   │   ├── progress_widget.py
│   │   │   ├── queue_widget.py
│   │   │   └── status_bar.py
│   │   │
│   │   ├── themes/              # Theme management
│   │   │   └── theme_manager.py
│   │   │
│   │   └── dialogs/             # Dialog windows
│   │       └── __init__.py
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
│   └── __init__.py
│
└── resources/                   # Application resources
    └── __init__.py
```

## Usage Guide 📖

### Basic Usage

1. **Add URLs**:
   - Paste a single URL and click "Add to Queue"
   - Or use the batch input area for multiple URLs

2. **Configure Settings**:
   - Set download path
   - Choose quality preset
   - Enable/disable subtitles

3. **Manage Queue**:
   - Reorder items with Move Up/Down
   - Remove unwanted items
   - Retry failed downloads

4. **Start Downloads**:
   - Click "Start Downloads" to begin
   - Use Pause/Resume/Stop as needed

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Add URL dialog |
| `Ctrl+V` | Add from clipboard |
| `Ctrl+S` | Start downloads |
| `Ctrl+A` | Select all in queue |
| `Delete` | Remove selected |

### Supported URL Formats

- `https://youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/playlist?list=PLAYLIST_ID`
- `https://youtube.com/channel/CHANNEL_ID`
- `https://youtube.com/@username`
- `https://youtube.com/shorts/SHORT_ID`

## Configuration ⚙️

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
  "show_notifications": true
}
```

## Dependencies 📦

| Package | Purpose |
|---------|---------|
| `yt-dlp` | Video extraction and downloading |
| `tkinter` | GUI framework (included with Python) |

## Troubleshooting 🔧

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

### Error Messages

| Error | Solution |
|-------|----------|
| Invalid URL | Check URL format |
| Network error | Check internet connection |
| Rate limited | Wait and retry later |
| No video formats | Video may be unavailable |

## Development 💻

### Running Tests
```bash
python -m pytest tests/
```

### Code Style
```bash
# Format code
black src/

# Check linting
flake8 src/
```

### Building Executable
```bash
python build.py
```

## Roadmap 🗺️

- [x] Phase 1: Core Infrastructure
- [x] Phase 2: UI Components
- [ ] Phase 3: Advanced Download Features
- [ ] Phase 4: Testing & Documentation
- [ ] Phase 5: Performance Optimization
- [ ] Phase 6: Release Preparation

## Contributing 🤝

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `python -m pytest`
5. Submit a pull request

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer ⚠️

This tool is for personal use only. Please respect copyright laws and YouTube's Terms of Service. The developers are not responsible for any misuse of this application.

## Support 💬

- **Issues**: [GitHub Issues](https://github.com/mahmoodhamdi/youtube-downloader-gui/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mahmoodhamdi/youtube-downloader-gui/discussions)
- **Email**: hmdy7486@gmail.com

## Acknowledgments 🙏

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The powerful backend for video downloading
- [Python](https://python.org) - The programming language
- The open-source community

---

**Made with ❤️ by Mahmood Hamdi**
