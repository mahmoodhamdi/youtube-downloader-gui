# خطة تطوير YouTube Downloader Pro 🚀

## نظرة عامة

هذه الخطة الشاملة لتطوير المشروع ليكون جاهز للـ Production مع كل الفيتشرز المتوقعة من مستخدمي تطبيقات تحميل الفيديو الاحترافية.

---

## 📊 التقييم الحالي للمشروع

| المعيار | التقييم | الهدف |
|---------|---------|-------|
| الأركيتكتشر | 70/100 | 90/100 |
| معالجة الأخطاء | 50/100 | 95/100 |
| اكتمال الفيتشرز | 60/100 | 95/100 |
| الأمان | 65/100 | 90/100 |
| الأداء | 70/100 | 90/100 |
| UI/UX | 60/100 | 90/100 |
| **الإجمالي** | **65/100** | **92/100** |

---

## 🏗️ Phase 1: إصلاح المشاكل الحرجة (Critical Fixes)

### 1.1 إصلاح Race Conditions في الـ Threading

**المشكلة:** الـ Queue manipulation فيها race conditions بين الـ download threads والـ GUI thread.

**الحل:**
```python
# إنشاء Thread-Safe Queue Manager
class QueueManager:
    def __init__(self):
        self._queue = []
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

    def add(self, video):
        with self._lock:
            self._queue.append(video)
            self._condition.notify_all()

    def remove(self, video_id):
        with self._lock:
            self._queue = [v for v in self._queue if v['id'] != video_id]

    def get_next_queued(self):
        with self._lock:
            for video in self._queue:
                if video['status'] == 'Queued':
                    return video
            return None

    def reorder(self, video_id, new_index):
        with self._lock:
            video = next((v for v in self._queue if v['id'] == video_id), None)
            if video:
                self._queue.remove(video)
                self._queue.insert(new_index, video)
```

**ملفات التعديل:**
- `core/queue_manager.py` (جديد)
- `youtube_downloader.py` (تعديل)

---

### 1.2 تحسين Input Validation

**المشكلة:** لا يوجد validation كافي للـ user inputs.

**الحل:**
```python
class InputValidator:
    @staticmethod
    def validate_url(url: str) -> tuple[bool, str]:
        """Returns (is_valid, error_message)"""
        if not url or not url.strip():
            return False, "URL cannot be empty"

        # YouTube URL patterns
        patterns = [
            r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]{11}',
            r'^https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
            r'^https?://(?:www\.)?youtube\.com/channel/[\w-]+',
            r'^https?://(?:www\.)?youtube\.com/@[\w-]+',
            r'^https?://youtu\.be/[\w-]{11}',
        ]

        for pattern in patterns:
            if re.match(pattern, url.strip()):
                return True, ""

        return False, "Invalid YouTube URL format"

    @staticmethod
    def validate_path(path: str) -> tuple[bool, str]:
        if not os.path.exists(path):
            return False, "Path does not exist"
        if not os.access(path, os.W_OK):
            return False, "No write permission"
        return True, ""

    @staticmethod
    def validate_config(config: dict) -> dict:
        """Validate and sanitize configuration"""
        defaults = {
            "max_concurrent_downloads": (1, 10, 2),  # min, max, default
            "bandwidth_limit": (0, 100000, 0),
            "retry_attempts": (0, 10, 3),
        }

        for key, (min_val, max_val, default) in defaults.items():
            try:
                value = int(config.get(key, default))
                config[key] = max(min_val, min(max_val, value))
            except (ValueError, TypeError):
                config[key] = default

        return config
```

**ملفات التعديل:**
- `core/validators.py` (جديد)

---

### 1.3 تحسين Error Handling

**المشكلة:** استخدام `except: pass` و generic exception handling.

**الحل:**
```python
# Custom Exception Classes
class DownloaderException(Exception):
    """Base exception for downloader"""
    pass

class URLValidationError(DownloaderException):
    """Invalid URL format"""
    pass

class NetworkError(DownloaderException):
    """Network-related errors"""
    pass

class DiskSpaceError(DownloaderException):
    """Insufficient disk space"""
    pass

class AuthenticationError(DownloaderException):
    """Authentication required"""
    pass

class RateLimitError(DownloaderException):
    """Rate limited by server"""
    pass

# Error Handler
class ErrorHandler:
    ERROR_MESSAGES = {
        URLValidationError: "Invalid URL. Please check the URL format.",
        NetworkError: "Network error. Check your internet connection.",
        DiskSpaceError: "Not enough disk space. Free up space and try again.",
        AuthenticationError: "This video requires login. Please add cookies.",
        RateLimitError: "Too many requests. Please wait before trying again.",
    }

    @classmethod
    def handle(cls, error: Exception, logger=None) -> str:
        """Handle exception and return user-friendly message"""
        for error_type, message in cls.ERROR_MESSAGES.items():
            if isinstance(error, error_type):
                if logger:
                    logger.log(f"{error_type.__name__}: {str(error)}", "ERROR")
                return message

        # Unknown error
        if logger:
            logger.log(f"Unexpected error: {str(error)}", "ERROR")
        return f"An unexpected error occurred: {str(error)}"
```

**ملفات التعديل:**
- `core/exceptions.py` (جديد)
- `core/error_handler.py` (جديد)

---

### 1.4 إصلاح Filename Sanitization لـ Windows

**المشكلة:** الـ sanitization الحالي لا يتعامل مع كل الـ Windows reserved characters.

**الحل:**
```python
class FilenameSanitizer:
    # Windows reserved characters
    INVALID_CHARS = '<>:"/\\|?*'
    # Windows reserved names
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }

    @classmethod
    def sanitize(cls, filename: str, max_length: int = 200) -> str:
        """Sanitize filename for all operating systems"""
        if not filename:
            return "untitled"

        # Remove invalid characters
        for char in cls.INVALID_CHARS:
            filename = filename.replace(char, '_')

        # Remove control characters
        filename = ''.join(c for c in filename if ord(c) >= 32)

        # Handle reserved names (Windows)
        name_without_ext = filename.rsplit('.', 1)[0].upper()
        if name_without_ext in cls.RESERVED_NAMES:
            filename = f"_{filename}"

        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')

        # Truncate if too long
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            max_name_length = max_length - len(ext)
            filename = name[:max_name_length] + ext

        return filename or "untitled"
```

---

## 🔧 Phase 2: تحسين الأداء والاستقرار

### 2.1 نظام Download Resume

**الهدف:** استئناف التحميل من حيث توقف في حالة فشل الاتصال.

```python
class DownloadSession:
    """Track download progress for resume capability"""

    def __init__(self, session_file: str = "download_sessions.json"):
        self.session_file = session_file
        self.sessions = self._load_sessions()

    def _load_sessions(self) -> dict:
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_session(self, video_id: str, data: dict):
        """Save download progress"""
        self.sessions[video_id] = {
            'url': data['url'],
            'output_path': data['output_path'],
            'downloaded_bytes': data.get('downloaded_bytes', 0),
            'total_bytes': data.get('total_bytes', 0),
            'temp_file': data.get('temp_file'),
            'timestamp': datetime.now().isoformat()
        }
        self._save_to_file()

    def get_session(self, video_id: str) -> dict | None:
        return self.sessions.get(video_id)

    def remove_session(self, video_id: str):
        if video_id in self.sessions:
            del self.sessions[video_id]
            self._save_to_file()

    def _save_to_file(self):
        with open(self.session_file, 'w') as f:
            json.dump(self.sessions, f, indent=2)
```

**yt-dlp options للـ Resume:**
```python
ydl_opts = {
    'continuedl': True,
    'nopart': False,  # Use .part files
    'retries': 10,
    'fragment_retries': 10,
    'skip_unavailable_fragments': True,
}
```

---

### 2.2 نظام Rate Limiting

**الهدف:** تجنب الـ IP ban من YouTube.

```python
class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.request_times = []
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Wait if we're exceeding rate limit"""
        with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.request_times = [t for t in self.request_times if now - t < 60]

            if len(self.request_times) >= self.requests_per_minute:
                # Calculate wait time
                oldest_request = min(self.request_times)
                wait_time = 60 - (now - oldest_request)
                if wait_time > 0:
                    time.sleep(wait_time)

            self.request_times.append(time.time())

    def add_delay_between_downloads(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """Add random delay to avoid detection"""
        import random
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
```

---

### 2.3 Memory Management

**الهدف:** إدارة الذاكرة بشكل أفضل لتجنب Memory Leaks.

```python
class CacheManager:
    """Centralized cache management with LRU eviction"""

    def __init__(self, max_size: int = 100, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key: str):
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]
            return None

    def set(self, key: str, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # Remove oldest item
                    self.cache.popitem(last=False)
            self.cache[key] = value

    def clear(self):
        with self.lock:
            self.cache.clear()

    def get_memory_usage(self) -> int:
        """Estimate memory usage in bytes"""
        import sys
        total = 0
        with self.lock:
            for value in self.cache.values():
                total += sys.getsizeof(value)
        return total
```

---

## 🌟 Phase 3: الفيتشرز الجديدة المهمة

### 3.1 نظام Authentication (Cookies Support)

**الهدف:** دعم تحميل الفيديوهات اللي محتاجة login.

```python
class AuthManager:
    """Manage authentication for YouTube"""

    def __init__(self, cookies_dir: str = "cookies"):
        self.cookies_dir = cookies_dir
        os.makedirs(cookies_dir, exist_ok=True)

    def import_cookies_from_browser(self, browser: str = "chrome") -> bool:
        """Import cookies from browser"""
        try:
            # yt-dlp can extract cookies from browsers
            return True
        except Exception as e:
            return False

    def import_cookies_file(self, file_path: str) -> bool:
        """Import cookies from Netscape format file"""
        if not os.path.exists(file_path):
            return False

        dest_path = os.path.join(self.cookies_dir, "cookies.txt")
        shutil.copy(file_path, dest_path)
        return True

    def get_ydl_opts(self) -> dict:
        """Get yt-dlp options for authentication"""
        cookies_file = os.path.join(self.cookies_dir, "cookies.txt")
        opts = {}

        if os.path.exists(cookies_file):
            opts['cookiefile'] = cookies_file
        else:
            # Try to extract from browser
            opts['cookiesfrombrowser'] = ('chrome',)

        return opts
```

**الـ UI:**
```
┌─────────────────────────────────────────────┐
│ Authentication Settings                      │
├─────────────────────────────────────────────┤
│ ○ No authentication                         │
│ ○ Import from browser: [Chrome ▼]           │
│ ○ Import cookies file: [Browse...]          │
│                                             │
│ Status: ✓ Authenticated                     │
└─────────────────────────────────────────────┘
```

---

### 3.2 نظام Proxy Support

**الهدف:** دعم استخدام Proxy/VPN.

```python
class ProxyManager:
    """Manage proxy connections"""

    PROXY_TYPES = ['http', 'https', 'socks4', 'socks5']

    def __init__(self):
        self.current_proxy = None
        self.proxy_list = []

    def set_proxy(self, proxy_type: str, host: str, port: int,
                  username: str = None, password: str = None):
        """Set proxy configuration"""
        if proxy_type not in self.PROXY_TYPES:
            raise ValueError(f"Invalid proxy type. Use: {self.PROXY_TYPES}")

        if username and password:
            proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
        else:
            proxy_url = f"{proxy_type}://{host}:{port}"

        self.current_proxy = proxy_url

    def test_proxy(self) -> tuple[bool, str]:
        """Test if proxy is working"""
        if not self.current_proxy:
            return False, "No proxy configured"

        try:
            proxies = {'http': self.current_proxy, 'https': self.current_proxy}
            response = requests.get('https://www.youtube.com',
                                   proxies=proxies, timeout=10)
            return response.status_code == 200, "Proxy working"
        except Exception as e:
            return False, str(e)

    def get_ydl_opts(self) -> dict:
        """Get yt-dlp options for proxy"""
        if self.current_proxy:
            return {'proxy': self.current_proxy}
        return {}
```

**الـ UI:**
```
┌─────────────────────────────────────────────┐
│ Proxy Settings                              │
├─────────────────────────────────────────────┤
│ ☑ Enable Proxy                              │
│                                             │
│ Type: [SOCKS5 ▼]                           │
│ Host: [proxy.example.com     ]              │
│ Port: [1080]                                │
│ Username: [optional          ]              │
│ Password: [••••••••          ]              │
│                                             │
│ [Test Connection]  Status: ✓ Connected      │
└─────────────────────────────────────────────┘
```

---

### 3.3 نظام Auto-Update لـ yt-dlp

**الهدف:** تحديث yt-dlp تلقائياً عند تغيير YouTube API.

```python
class UpdateManager:
    """Manage yt-dlp updates"""

    def __init__(self):
        self.current_version = self._get_current_version()

    def _get_current_version(self) -> str:
        try:
            return yt_dlp.version.__version__
        except:
            return "unknown"

    def check_for_updates(self) -> tuple[bool, str]:
        """Check if update is available"""
        try:
            response = requests.get(
                "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
                timeout=10
            )
            latest_version = response.json()['tag_name']

            if latest_version != self.current_version:
                return True, latest_version
            return False, self.current_version
        except Exception as e:
            return False, str(e)

    def update_ytdlp(self, progress_callback=None) -> bool:
        """Update yt-dlp to latest version"""
        try:
            import subprocess

            if progress_callback:
                progress_callback("Updating yt-dlp...")

            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Reload yt-dlp module
                import importlib
                importlib.reload(yt_dlp)
                self.current_version = self._get_current_version()
                return True

            return False
        except Exception as e:
            return False

    def schedule_auto_update(self, check_interval_hours: int = 24):
        """Schedule periodic update checks"""
        pass  # Implement with threading.Timer
```

---

### 3.4 Format Selection Preview

**الهدف:** السماح للمستخدم باختيار الـ format بدقة.

```python
class FormatSelector:
    """Preview and select video formats"""

    def get_available_formats(self, url: str) -> list[dict]:
        """Get all available formats for a video"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            formats = []
            for f in info.get('formats', []):
                formats.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'resolution': f.get('resolution', 'audio only'),
                    'fps': f.get('fps'),
                    'vcodec': f.get('vcodec'),
                    'acodec': f.get('acodec'),
                    'filesize': f.get('filesize') or f.get('filesize_approx'),
                    'tbr': f.get('tbr'),  # Total bitrate
                    'format_note': f.get('format_note', ''),
                })

            return formats

    def format_for_display(self, format_info: dict) -> str:
        """Format info for display in UI"""
        resolution = format_info.get('resolution', 'N/A')
        ext = format_info.get('ext', 'N/A')
        size = self._format_size(format_info.get('filesize', 0))
        note = format_info.get('format_note', '')

        return f"{resolution} | {ext} | {size} | {note}"

    def _format_size(self, size_bytes: int) -> str:
        if not size_bytes:
            return "Unknown"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
```

**الـ UI:**
```
┌──────────────────────────────────────────────────────────────┐
│ Select Format for: "Video Title Here"                        │
├──────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Format          │ Size    │ Codec      │ Note            │ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ ○ 1080p60 mp4   │ 450 MB  │ h264+aac   │ Premium         │ │
│ │ ● 1080p mp4     │ 320 MB  │ h264+aac   │                 │ │
│ │ ○ 720p mp4      │ 180 MB  │ h264+aac   │                 │ │
│ │ ○ 480p mp4      │ 95 MB   │ h264+aac   │                 │ │
│ │ ○ 360p mp4      │ 45 MB   │ h264+aac   │                 │ │
│ │ ○ Audio only    │ 12 MB   │ m4a        │ 128kbps         │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Cancel]                              [Download Selected]    │
└──────────────────────────────────────────────────────────────┘
```

---

### 3.5 Post-Processing Options

**الهدف:** دعم تحويل الصيغ وإضافة metadata بعد التحميل.

```python
class PostProcessor:
    """Handle post-processing of downloaded files"""

    def __init__(self, ffmpeg_path: str = None):
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg()

    def _find_ffmpeg(self) -> str | None:
        """Find ffmpeg in system PATH"""
        import shutil
        return shutil.which('ffmpeg')

    def get_ydl_postprocessors(self, options: dict) -> list:
        """Get yt-dlp postprocessor configuration"""
        postprocessors = []

        # Embed subtitles
        if options.get('embed_subtitles'):
            postprocessors.append({
                'key': 'FFmpegEmbedSubtitle',
            })

        # Embed thumbnail
        if options.get('embed_thumbnail'):
            postprocessors.append({
                'key': 'EmbedThumbnail',
            })

        # Convert format
        if options.get('convert_to'):
            postprocessors.append({
                'key': 'FFmpegVideoConvertor',
                'preferedformat': options['convert_to'],  # mp4, mkv, webm
            })

        # Extract audio
        if options.get('extract_audio'):
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': options.get('audio_format', 'mp3'),
                'preferredquality': options.get('audio_quality', '192'),
            })

        # Add metadata
        if options.get('add_metadata'):
            postprocessors.append({
                'key': 'FFmpegMetadata',
            })

        return postprocessors
```

**الـ UI:**
```
┌─────────────────────────────────────────────┐
│ Post-Processing Options                     │
├─────────────────────────────────────────────┤
│ ☑ Embed subtitles into video               │
│ ☑ Embed thumbnail as cover art             │
│ ☐ Add metadata (title, description, etc.)  │
│                                             │
│ Convert to format: [Keep Original ▼]        │
│   Options: MP4, MKV, WebM, AVI             │
│                                             │
│ ── Audio Extraction ──                      │
│ ☐ Extract audio only                       │
│   Format: [MP3 ▼]  Quality: [192 kbps ▼]   │
└─────────────────────────────────────────────┘
```

---

### 3.6 Advanced Playlist Filtering

**الهدف:** تحميل فيديوهات محددة من Playlist بناءً على معايير.

```python
class PlaylistFilter:
    """Filter playlist videos by criteria"""

    def __init__(self):
        self.filters = {}

    def set_index_range(self, start: int = None, end: int = None):
        """Filter by video index in playlist"""
        self.filters['playlist_items'] = f"{start or 1}:{end or ''}"

    def set_date_range(self, after: str = None, before: str = None):
        """Filter by upload date (YYYYMMDD format)"""
        if after:
            self.filters['dateafter'] = after
        if before:
            self.filters['datebefore'] = before

    def set_duration_range(self, min_seconds: int = None, max_seconds: int = None):
        """Filter by video duration"""
        conditions = []
        if min_seconds:
            conditions.append(f"duration>={min_seconds}")
        if max_seconds:
            conditions.append(f"duration<={max_seconds}")

        if conditions:
            self.filters['match_filter'] = ' & '.join(conditions)

    def set_view_count_range(self, min_views: int = None):
        """Filter by view count"""
        if min_views:
            current = self.filters.get('match_filter', '')
            new_filter = f"view_count>={min_views}"
            if current:
                self.filters['match_filter'] = f"{current} & {new_filter}"
            else:
                self.filters['match_filter'] = new_filter

    def get_ydl_opts(self) -> dict:
        return self.filters.copy()
```

**الـ UI:**
```
┌─────────────────────────────────────────────┐
│ Playlist Filter Options                     │
├─────────────────────────────────────────────┤
│ Video Range: [1] to [50] (leave empty = all)│
│                                             │
│ Upload Date:                                │
│   After:  [2024-01-01]                     │
│   Before: [         ]                       │
│                                             │
│ Duration:                                   │
│   Min: [0] minutes  Max: [60] minutes      │
│                                             │
│ Minimum Views: [1000]                       │
│                                             │
│ [Preview Matching Videos: 23 found]         │
└─────────────────────────────────────────────┘
```

---

## 🎨 Phase 4: تحسينات الـ UI/UX

### 4.1 Dark Mode Support

```python
class ThemeManager:
    """Manage application themes"""

    THEMES = {
        'light': {
            'bg': '#ffffff',
            'fg': '#000000',
            'accent': '#0078d4',
            'success': '#107c10',
            'error': '#d13438',
            'warning': '#ff8c00',
        },
        'dark': {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'accent': '#0078d4',
            'success': '#6ccb5f',
            'error': '#f85149',
            'warning': '#d29922',
        },
        'system': None,  # Follow system preference
    }

    def __init__(self, root):
        self.root = root
        self.current_theme = 'light'

    def apply_theme(self, theme_name: str):
        if theme_name not in self.THEMES:
            return

        self.current_theme = theme_name
        theme = self.THEMES[theme_name]

        if theme is None:
            theme = self._get_system_theme()

        # Apply to ttk styles
        style = ttk.Style()
        style.configure('.', background=theme['bg'], foreground=theme['fg'])
        style.configure('TLabel', background=theme['bg'], foreground=theme['fg'])
        style.configure('TButton', background=theme['accent'])
        # ... more style configurations

    def _get_system_theme(self) -> dict:
        """Detect system dark/light mode"""
        # Platform-specific implementation
        import darkdetect
        if darkdetect.isDark():
            return self.THEMES['dark']
        return self.THEMES['light']
```

---

### 4.2 Keyboard Shortcuts

```python
class ShortcutManager:
    """Manage keyboard shortcuts"""

    DEFAULT_SHORTCUTS = {
        '<Control-s>': 'start_downloads',
        '<Control-p>': 'pause_downloads',
        '<Control-Shift-s>': 'stop_downloads',
        '<Control-v>': 'paste_url',
        '<Control-a>': 'select_all_queue',
        '<Delete>': 'remove_selected',
        '<Control-o>': 'open_download_folder',
        '<Control-q>': 'quit_application',
        '<F5>': 'refresh_queue',
        '<Control-f>': 'focus_search',
    }

    def __init__(self, root, callbacks: dict):
        self.root = root
        self.callbacks = callbacks
        self.shortcuts = self.DEFAULT_SHORTCUTS.copy()

    def bind_all(self):
        """Bind all shortcuts"""
        for shortcut, action in self.shortcuts.items():
            if action in self.callbacks:
                self.root.bind(shortcut, lambda e, a=action: self.callbacks[a]())

    def show_shortcuts_dialog(self):
        """Show dialog with all shortcuts"""
        # Create dialog showing all shortcuts
        pass
```

---

### 4.3 System Tray Support

```python
class SystemTray:
    """System tray integration"""

    def __init__(self, root, icon_path: str = None):
        self.root = root
        self.icon_path = icon_path
        self.tray_icon = None

    def setup(self):
        """Setup system tray icon"""
        try:
            from pystray import Icon, Menu, MenuItem
            from PIL import Image

            # Create menu
            menu = Menu(
                MenuItem('Show', self.show_window),
                MenuItem('Start Downloads', self.start_downloads),
                MenuItem('Pause', self.pause_downloads),
                Menu.SEPARATOR,
                MenuItem('Quit', self.quit_app),
            )

            # Create icon
            image = Image.open(self.icon_path) if self.icon_path else self._create_default_icon()
            self.tray_icon = Icon("YouTube Downloader", image, menu=menu)

            # Start in separate thread
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

        except ImportError:
            pass  # pystray not installed

    def minimize_to_tray(self):
        """Minimize window to system tray"""
        self.root.withdraw()

    def show_window(self):
        """Show window from tray"""
        self.root.deiconify()
        self.root.lift()

    def show_notification(self, title: str, message: str):
        """Show system notification"""
        if self.tray_icon:
            self.tray_icon.notify(title, message)
```

---

### 4.4 Search and Filter in Queue

```python
class QueueSearch:
    """Search and filter functionality for queue"""

    def __init__(self, queue_tree, video_queue):
        self.queue_tree = queue_tree
        self.video_queue = video_queue
        self.original_items = []

    def search(self, query: str):
        """Filter queue by search query"""
        query = query.lower().strip()

        if not query:
            self.show_all()
            return

        # Hide non-matching items
        for item in self.queue_tree.get_children():
            values = self.queue_tree.item(item, 'values')
            title = values[2].lower() if len(values) > 2 else ''
            url = values[1].lower() if len(values) > 1 else ''

            if query in title or query in url:
                # Show item
                pass
            else:
                # Hide item (detach but keep reference)
                self.queue_tree.detach(item)

    def show_all(self):
        """Show all items"""
        # Reattach all items
        pass

    def filter_by_status(self, status: str):
        """Filter by download status"""
        pass
```

---

### 4.5 Download Statistics Dashboard

```python
class StatisticsManager:
    """Track and display download statistics"""

    def __init__(self, stats_file: str = "download_stats.json"):
        self.stats_file = stats_file
        self.stats = self._load_stats()

    def _load_stats(self) -> dict:
        default = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_bytes_downloaded': 0,
            'total_time_seconds': 0,
            'daily_stats': {},  # date -> stats
            'by_quality': {},   # quality -> count
        }
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    return {**default, **json.load(f)}
        except:
            pass
        return default

    def record_download(self, video_info: dict, success: bool,
                       bytes_downloaded: int, duration_seconds: float):
        """Record a download for statistics"""
        today = datetime.now().strftime('%Y-%m-%d')

        self.stats['total_downloads'] += 1
        if success:
            self.stats['successful_downloads'] += 1
        else:
            self.stats['failed_downloads'] += 1

        self.stats['total_bytes_downloaded'] += bytes_downloaded
        self.stats['total_time_seconds'] += duration_seconds

        # Daily stats
        if today not in self.stats['daily_stats']:
            self.stats['daily_stats'][today] = {'count': 0, 'bytes': 0}
        self.stats['daily_stats'][today]['count'] += 1
        self.stats['daily_stats'][today]['bytes'] += bytes_downloaded

        self._save_stats()

    def get_summary(self) -> dict:
        """Get summary statistics"""
        return {
            'total': self.stats['total_downloads'],
            'success_rate': (self.stats['successful_downloads'] /
                           max(1, self.stats['total_downloads'])) * 100,
            'total_size': self._format_size(self.stats['total_bytes_downloaded']),
            'avg_speed': self._calculate_avg_speed(),
        }
```

**الـ UI:**
```
┌──────────────────────────────────────────────────────────────┐
│ Download Statistics                                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Total Downloads: 1,234        Success Rate: 98.5%          │
│  Total Downloaded: 45.6 GB     Average Speed: 5.2 MB/s      │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │     Downloads This Week                                │ │
│  │  50 ┤                                     ▓▓           │ │
│  │  40 ┤                          ▓▓        ▓▓▓▓          │ │
│  │  30 ┤              ▓▓         ▓▓▓▓       ▓▓▓▓          │ │
│  │  20 ┤    ▓▓       ▓▓▓▓       ▓▓▓▓▓▓     ▓▓▓▓▓▓        │ │
│  │  10 ┤   ▓▓▓▓     ▓▓▓▓▓▓     ▓▓▓▓▓▓▓▓   ▓▓▓▓▓▓▓▓       │ │
│  │   0 └───Mon───Tue───Wed───Thu───Fri───Sat───Sun────    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Most Downloaded Quality: 1080p (45%)                       │
│  Peak Download Time: 8:00 PM - 10:00 PM                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 Phase 5: إعادة هيكلة المشروع

### 5.1 هيكل المشروع الجديد

```
youtube-downloader-gui/
├── main.py                     # Entry point
├── requirements.txt
├── setup.py
├── pyproject.toml
├── CLAUDE.md
├── README.md
├── LICENSE
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                   # Business Logic
│   │   ├── __init__.py
│   │   ├── downloader.py       # Main download logic
│   │   ├── queue_manager.py    # Queue management
│   │   ├── format_selector.py  # Format selection
│   │   ├── post_processor.py   # Post-processing
│   │   ├── rate_limiter.py     # Rate limiting
│   │   ├── session_manager.py  # Download sessions
│   │   └── statistics.py       # Statistics tracking
│   │
│   ├── auth/                   # Authentication
│   │   ├── __init__.py
│   │   ├── auth_manager.py     # Cookie management
│   │   └── proxy_manager.py    # Proxy support
│   │
│   ├── config/                 # Configuration
│   │   ├── __init__.py
│   │   ├── config_manager.py   # Config handling
│   │   ├── validators.py       # Input validation
│   │   └── defaults.py         # Default values
│   │
│   ├── ui/                     # User Interface
│   │   ├── __init__.py
│   │   ├── main_window.py      # Main window
│   │   ├── tabs/
│   │   │   ├── __init__.py
│   │   │   ├── downloads_tab.py
│   │   │   ├── settings_tab.py
│   │   │   ├── history_tab.py
│   │   │   └── statistics_tab.py
│   │   ├── dialogs/
│   │   │   ├── __init__.py
│   │   │   ├── format_dialog.py
│   │   │   ├── filter_dialog.py
│   │   │   └── settings_dialog.py
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── progress_widget.py
│   │   │   ├── queue_widget.py
│   │   │   └── status_bar.py
│   │   ├── themes/
│   │   │   ├── __init__.py
│   │   │   ├── theme_manager.py
│   │   │   ├── light.py
│   │   │   └── dark.py
│   │   └── shortcuts.py        # Keyboard shortcuts
│   │
│   ├── utils/                  # Utilities
│   │   ├── __init__.py
│   │   ├── logger.py           # Logging
│   │   ├── cache.py            # Caching
│   │   ├── file_utils.py       # File operations
│   │   └── network_utils.py    # Network utilities
│   │
│   └── exceptions/             # Custom Exceptions
│       ├── __init__.py
│       └── errors.py
│
├── tests/                      # Unit Tests
│   ├── __init__.py
│   ├── test_downloader.py
│   ├── test_queue.py
│   ├── test_validators.py
│   └── test_config.py
│
├── resources/                  # Assets
│   ├── icons/
│   │   ├── app_icon.ico
│   │   ├── app_icon.png
│   │   └── tray_icon.png
│   ├── themes/
│   └── translations/
│       ├── en.json
│       └── ar.json
│
└── docs/                       # Documentation
    ├── user_guide.md
    ├── developer_guide.md
    └── api_reference.md
```

---

### 5.2 Dependency Injection Pattern

```python
# src/core/container.py
class Container:
    """Dependency injection container"""

    def __init__(self):
        self._services = {}
        self._singletons = {}

    def register(self, interface, implementation, singleton=False):
        self._services[interface] = (implementation, singleton)

    def resolve(self, interface):
        if interface not in self._services:
            raise ValueError(f"Service {interface} not registered")

        implementation, singleton = self._services[interface]

        if singleton:
            if interface not in self._singletons:
                self._singletons[interface] = implementation()
            return self._singletons[interface]

        return implementation()

# Usage
container = Container()
container.register(IDownloader, YouTubeDownloader, singleton=True)
container.register(IQueueManager, QueueManager, singleton=True)
container.register(IConfigManager, ConfigManager, singleton=True)
```

---

## 🧪 Phase 6: Testing & Quality Assurance

### 6.1 Unit Tests

```python
# tests/test_validators.py
import pytest
from src.config.validators import InputValidator

class TestInputValidator:
    def test_valid_youtube_url(self):
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
        ]
        for url in valid_urls:
            is_valid, error = InputValidator.validate_url(url)
            assert is_valid, f"URL should be valid: {url}"

    def test_invalid_youtube_url(self):
        invalid_urls = [
            "",
            "not a url",
            "https://vimeo.com/123456",
            "https://www.youtube.com/",
        ]
        for url in invalid_urls:
            is_valid, error = InputValidator.validate_url(url)
            assert not is_valid, f"URL should be invalid: {url}"

# tests/test_downloader.py
import pytest
from unittest.mock import Mock, patch
from src.core.downloader import YouTubeDownloader

class TestYouTubeDownloader:
    @pytest.fixture
    def downloader(self):
        return YouTubeDownloader()

    @patch('yt_dlp.YoutubeDL')
    def test_extract_video_info(self, mock_ydl, downloader):
        mock_ydl.return_value.__enter__.return_value.extract_info.return_value = {
            'title': 'Test Video',
            'duration': 180,
        }

        info = downloader.extract_video_info("https://youtube.com/watch?v=test")
        assert info['title'] == 'Test Video'
```

---

### 6.2 Integration Tests

```python
# tests/integration/test_full_download.py
import pytest
import tempfile
import os

class TestFullDownload:
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.integration
    @pytest.mark.slow
    def test_download_short_video(self, temp_dir):
        """Test downloading a short public domain video"""
        # Use a short creative commons video for testing
        test_url = "https://www.youtube.com/watch?v=BaW_jenozKc"  # Short test video

        downloader = YouTubeDownloader()
        result = downloader.download(test_url, temp_dir)

        assert result['success']
        assert os.path.exists(result['file_path'])
```

---

## 📋 ملخص المراحل والجدول الزمني

| المرحلة | الوصف | الأولوية |
|---------|-------|----------|
| **Phase 1** | إصلاح المشاكل الحرجة | 🔴 Critical |
| **Phase 2** | تحسين الأداء والاستقرار | 🟠 High |
| **Phase 3** | الفيتشرز الجديدة المهمة | 🟡 Medium |
| **Phase 4** | تحسينات الـ UI/UX | 🟢 Normal |
| **Phase 5** | إعادة هيكلة المشروع | 🔵 Low |
| **Phase 6** | Testing & QA | 🟣 Ongoing |

---

## 📝 الخطوات التالية

1. **ابدأ بـ Phase 1** - إصلاح المشاكل الحرجة أولاً
2. **اعمل Tests** لكل جزء بتصلحه
3. **Document** كل تغيير
4. **Review** الكود قبل الـ merge

---

## 🎯 الهدف النهائي

تطبيق احترافي لتحميل الفيديوهات يتميز بـ:
- ✅ استقرار عالي (99.9% uptime)
- ✅ سهولة الاستخدام
- ✅ كل الفيتشرز اللي المستخدم محتاجها
- ✅ أداء ممتاز
- ✅ كود نظيف وقابل للصيانة
- ✅ توثيق شامل
- ✅ تغطية اختبارات عالية
