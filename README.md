# YouTube Downloader Pro 🎥

A comprehensive GUI application for downloading YouTube videos and playlists with advanced features including quality selection, subtitle support, batch processing, and background execution.

![Python](https://img.shields.io/badge/python-v3.13.1+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)

## Features ✨

- **Multi-URL Support**: Download single videos or entire playlists
- **Quality Selection**: Choose from various video qualities (best, 720p, 480p, 360p, audio-only)
- **Subtitle Download**: Automatic subtitle download with language selection
- **Batch Processing**: Queue multiple videos for sequential download
- **Background Execution**: Downloads run in background threads
- **Progress Monitoring**: Real-time progress bars and status updates
- **Save Path Selection**: Choose custom download directories
- **Error Handling**: Robust error handling with detailed logging
- **Configuration Persistence**: Saves your preferences between sessions
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Screenshots 📸

### Main Interface

```wireframe
┌─────────────────────────────────────────────────────────────────┐
│                     YouTube Downloader Pro                      │
├─────────────────────────────────────────────────────────────────┤
│ Video URLs                                                      │
│ URL: [https://youtube.com/watch?v=...]    [Add to Queue]       │
│ Multiple URLs (one per line):                                  │
│ ┌─────────────────────────────────────────┐                   │
│ │ https://youtube.com/watch?v=video1      │   [Add All]       │
│ │ https://youtube.com/playlist?list=...   │                   │
│ └─────────────────────────────────────────┘                   │
├─────────────────────────────────────────────────────────────────┤
│ Download Settings                                               │
│ Download Path: [/home/user/Downloads]          [Browse]        │
│ Quality: [best ▼]                    ☑ Download Subtitles     │
├─────────────────────────────────────────────────────────────────┤
│ Download Queue                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ID │ URL           │ Title         │ Duration │ Status      │ │
│ │ 1  │ youtube.co... │ Sample Video  │ 03:45    │ Queued     │ │
│ │ 2  │ youtube.co... │ Another Video │ 05:20    │ Downloading│ │
│ └─────────────────────────────────────────────────────────────┘ │
│         [Remove Selected] [Clear Queue] [Refresh Info]         │
├─────────────────────────────────────────────────────────────────┤
│ Download Progress                                               │
│ Current:  ████████████████████████████████████░░░░  85%        │
│ Overall:  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  35%        │
│ Downloading: Sample Video - Speed: 2.5 MB/s - ETA: 45s        │
├─────────────────────────────────────────────────────────────────┤
│            [Start Downloads] [Pause] [Stop]                    │
├─────────────────────────────────────────────────────────────────┤
│ Status Log                                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ [12:34:56] INFO: YouTube Downloader Pro initialized         │ │
│ │ [12:35:02] SUCCESS: Added 3 videos to queue                 │ │
│ │ [12:35:15] INFO: Starting download of 3 videos              │ │
│ │ [12:35:45] SUCCESS: Successfully downloaded: Sample Video   │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Installation 🚀

### Option 1: Run from Source

1. **Clone the repository**:

   ```bash
   git clone https://github.com/mahmoodhamdi/youtube-downloader-gui.git
   cd youtube-downloader-gui
   ```

2. **Create a virtual environment**:

   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
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

### Option 2: Use Pre-built Executable

1. Download the latest release from the [Releases](https://github.com/mahmoodhamdi/youtube-downloader-gui/releases) page
2. Extract the archive
3. Run the executable:
   - Windows: Double-click `YouTubeDownloader.exe`
   - macOS: Double-click `YouTubeDownloader.app`
   - Linux: Run `./YouTubeDownloader`

### Option 3: Build Your Own Executable

1. Follow steps 1-3 from "Run from Source"
2. Run the build script:

   ```bash
   python build.py
   ```

3. Find the executable in the `dist` folder

## Usage Guide 📖

### Basic Usage

1. **Add URLs**: Paste YouTube video or playlist URLs into the URL field
2. **Configure Settings**: Choose download path, quality, and subtitle options
3. **Build Queue**: Add multiple URLs to download in batch
4. **Start Download**: Click "Start Downloads" to begin processing

### Advanced Features

#### Quality Selection

- **best**: Highest available quality
- **720p/480p/360p**: Specific resolution limits
- **audio_only**: Extract audio only (MP3/M4A)
- **worst**: Lowest quality (for slow connections)

#### Subtitle Support

- Enable "Download Subtitles" checkbox
- Supports automatic and manual subtitles
- Multiple language support (configurable)

#### Playlist Handling

- Paste playlist URLs to download all videos
- Individual videos are extracted and queued
- Progress tracking for entire playlists

#### Queue Management

- Add/remove individual items
- Clear entire queue
- Refresh video information
- Status tracking for each video

## Configuration ⚙️

The application saves configuration in `downloader_config.json`:

```json
{
  "download_path": "/path/to/downloads",
  "quality": "best",
  "include_subtitles": false,
  "subtitle_langs": ["en"],
  "window_geometry": "900x700"
}
```

## Dependencies 📦

- `yt-dlp`: YouTube video extraction and downloading
- `tkinter`: GUI framework (included with Python)
- `pyinstaller`: Executable building (development only)

## Supported Sites 🌐

Thanks to `yt-dlp`, this application supports downloading from:

- YouTube (videos and playlists)
- YouTube Music
- Vimeo
- Dailymotion
- And [1000+ other sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

## Troubleshooting 🔧

### Common Issues

1. **"Module not found" errors**:
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Activate your virtual environment

2. **Download fails**:
   - Check internet connection
   - Verify URL is valid and accessible
   - Some videos may be region-restricted

3. **GUI not appearing**:
   - On Linux, install tkinter: `sudo apt-get install python3-tk`
   - Ensure you're not running in a headless environment

4. **Slow downloads**:
   - Choose lower quality settings
   - Check available bandwidth
   - Some servers may have rate limits

### Error Messages

- **"Invalid YouTube URL"**: Check URL format and try copying again
- **"Download path does not exist"**: Select a valid folder path  
- **"No videos in queue"**: Add URLs before starting downloads

## Development 💻

### Project Structure

```structure
youtube-downloader-gui/
├── core/
│   ├── config.py          # Configuration management
│   ├── logger.py         # Logging utilities
│   ├── downloader.py     # Download management and yt-dlp integration
├── ui/
│   ├── gui.py            # Tkinter GUI implementation
├── main.py               # Application entry point
├── requirements.txt       # Dependencies
├── build.py              # Build script
├── setup.py              # Package setup
├── .gitignore            # Git ignore rules
├── README.md             # This file
└── dist/                 # Built executables (created by build.py)
```

### Building Executables

The `build.py` script automates the build process:

```bash
python build.py
```

This will:

1. Clean previous builds
2. Install/upgrade PyInstaller
3. Create optimized executable
4. Generate installer (Windows)

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer ⚠️

This tool is for personal use only. Please respect copyright laws and YouTube's Terms of Service. The developers are not responsible for any misuse of this application.

## Support 💬

- **Issues**: [GitHub Issues](https://github.com/mahmoodhamdi/youtube-downloader-gui/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mahmoodhamdi/youtube-downloader-gui/discussions)
- **Email**: <hmdy7486@gmail.com>

## Acknowledgments 🙏

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The powerful backend for video downloading
- [PyInstaller](https://pyinstaller.org/) - For creating standalone executables
- The Python community for excellent documentation and support

---

***Made with ❤️ by Mahmood Hamdi***
