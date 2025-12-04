# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Downloader Pro is a Python-based GUI application for downloading YouTube videos and playlists using yt-dlp as the backend. It features a Tkinter-based interface with multi-threaded downloads, queue management, and download history tracking.

## Commands

### Running the Application
```bash
python youtube_downloader.py
# or
python youtube_downloader1.py  # Enhanced version with tabbed interface
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

Key dependencies: `yt-dlp`, `pillow`, `requests`

## Architecture

### Main Files

- **youtube_downloader.py**: Original single-class implementation (~1200 lines) with basic download queue and progress tracking
- **youtube_downloader1.py**: Enhanced version (~1950 lines) with additional features:
  - Tabbed interface (Downloads, Settings, History)
  - Thread-safe state management classes
  - Video info caching (`VideoInfoCache`)
  - Download history persistence (`DownloadHistory`)
  - Retry mechanism with exponential backoff (`RetryManager`)

### Class Structure (youtube_downloader1.py)

- `YouTubeDownloaderGUI`: Main application class handling GUI and orchestrating downloads
- `ThreadSafeLogger`: Thread-safe logging wrapper
- `DownloadState`: Thread-safe download state management (start/stop/pause/resume)
- `VideoInfoCache`: LRU-style cache for video metadata
- `RetryManager`: Handles retry logic with exponential backoff
- `DownloadHistory`: Persists download history to JSON

### Threading Model

- Uses `ThreadPoolExecutor` for concurrent downloads
- Progress updates sent via `queue.Queue` to main thread
- GUI updates scheduled via `root.after()` for thread safety
- `threading.Lock` used for shared state protection

### Configuration

Config stored in `downloader_config.json`:
- Download path, quality settings
- Subtitle preferences
- Concurrent download limits
- Bandwidth limiting

## Key Patterns

### yt-dlp Integration
```python
ydl_opts = {
    'outtmpl': output_path,
    'format': format_selector,
    'progress_hooks': [progress_callback],
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
```

### Thread-safe GUI Updates
```python
# From worker thread
self.progress_queue.put(('status', video_id, 'Downloading'))

# In main thread (checked periodically)
def check_progress_queue(self):
    item = self.progress_queue.get_nowait()
    # Update GUI here
    self.root.after(100, self.check_progress_queue)
```

## Platform Notes

- Cross-platform (Windows, macOS, Linux)
- File explorer opening uses platform-specific commands: `explorer`, `open`, `xdg-open`
- Filename sanitization handles OS-specific invalid characters
