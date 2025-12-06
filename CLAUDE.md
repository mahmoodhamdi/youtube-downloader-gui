# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Downloader Pro v2.0 is a Python-based GUI application for downloading YouTube videos and playlists using yt-dlp as the backend. It features a modular Tkinter-based interface with thread-safe queue management, concurrent downloads, and download history tracking.

## Commands

### Running the Application
```bash
python main.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

Key dependencies: `yt-dlp`, `pillow`, `requests`, `pyinstaller` (for building)

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run a single test file
python -m pytest tests/test_queue_manager.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Code Quality
```bash
black src/          # Format code
flake8 src/         # Lint
isort src/          # Sort imports
```

### Building Executable
```bash
pyinstaller --onefile --windowed main.py
```

## Architecture (v2.0)

The application follows a modular architecture with clear separation between core logic, UI, and configuration.

### Entry Point
- **main.py**: Application entry point, validates dependencies and launches `MainWindow`

### Core Modules (`src/core/`)
- **queue_manager.py**: Thread-safe `QueueManager` with `VideoItem` dataclass and `VideoStatus` enum. Uses `OrderedDict` with `RLock` and `Condition` for safe concurrent access
- **download_manager.py**: `DownloadManager` with `ThreadPoolExecutor` for concurrent downloads, pause/resume/stop controls, and retry logic with exponential backoff

### Configuration (`src/config/`)
- **config_manager.py**: Persistent settings stored in `~/.ytdownloader/config.json`
- **validators.py**: `URLValidator`, `PathValidator` for input validation
- **defaults.py**: Default configuration values

### UI Components (`src/ui/`)
- **main_window.py**: `MainWindow` class orchestrating all components with tabbed interface
- **tabs/**: `DownloadsTab`, `SettingsTab`, `HistoryTab`
- **widgets/**: Reusable components (`URLInput`, `ProgressWidget`, `QueueWidget`, `StatusBar`)
- **themes/**: `ThemeManager` for light/dark/system theme support

### Utilities (`src/utils/`)
- **logger.py**: Thread-safe `Logger` with file output
- **error_handler.py**: Centralized error handling
- **cache.py**: LRU-style caching utilities
- **file_utils.py**: File operations and filename sanitization

### Authentication (`src/auth/`)
- **auth_manager.py**: Cookie-based authentication for age-restricted/members-only content, browser cookie import
- **proxy_manager.py**: HTTP/HTTPS/SOCKS proxy support with connection testing

### Custom Exceptions (`src/exceptions/`)
- **errors.py**: `DownloadError`, `NetworkError`, `AuthenticationError`, `ExtractionError`

## Key Patterns

### Thread-Safe Queue Operations
```python
# QueueManager uses RLock + Condition for thread safety
with self._lock:
    self._queue[video.id] = video
    self._condition.notify_all()
```

### Callback-Based Communication
```python
# MainWindow connects callbacks between components
self.queue_manager.on_item_added = self._on_queue_item_added
self.download_manager.on_progress = self._on_download_progress
```

### GUI Thread Safety
```python
# Worker threads schedule GUI updates via root.after()
self.root.after(0, lambda: self.downloads_tab.update_progress(info))
```

### yt-dlp Integration
```python
ydl_opts = {
    'format': format_selector,
    'outtmpl': output_template,
    'progress_hooks': [lambda d: self._progress_hook(d, video_id)],
    'continuedl': True,  # Resume support
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
```

## Platform Notes

- Cross-platform (Windows, macOS, Linux)
- File explorer: `os.startfile` (Windows), `open` (macOS), `xdg-open` (Linux)
- Config stored in `~/.ytdownloader/` (cross-platform user home)
- Filename sanitization handles OS-specific invalid characters
