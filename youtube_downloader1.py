import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
import json
import sys
import re
import subprocess
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Event
import yt_dlp
from urllib.parse import urlparse, parse_qs
import requests
from PIL import Image, ImageTk
import io
import hashlib

class ThreadSafeLogger:
    """Thread-safe logger for the application"""
    def __init__(self, log_callback):
        self.log_callback = log_callback
        self.lock = Lock()
        
    def log(self, message, level="INFO"):
        with self.lock:
            self.log_callback(message, level)

class DownloadState:
    """Thread-safe download state management"""
    def __init__(self):
        self.lock = Lock()
        self.is_downloading = False
        self.should_stop = Event()
        self.pause_event = Event()
        self.pause_event.set()  # Initially not paused
        
    def start_download(self):
        with self.lock:
            self.is_downloading = True
            self.should_stop.clear()
            self.pause_event.set()
    
    def stop_download(self):
        with self.lock:
            self.is_downloading = False
            self.should_stop.set()
            self.pause_event.set()
    
    def pause_download(self):
        with self.lock:
            self.pause_event.clear()
    
    def resume_download(self):
        with self.lock:
            self.pause_event.set()
    
    def is_running(self):
        with self.lock:
            return self.is_downloading
    
    def should_continue(self):
        return not self.should_stop.is_set()
    
    def wait_if_paused(self):
        self.pause_event.wait()

class VideoInfoCache:
    """Cache for video metadata to avoid repeated API calls"""
    def __init__(self, max_size=1000):
        self.cache = {}
        self.max_size = max_size
        self.lock = Lock()
        
    def get(self, url):
        with self.lock:
            return self.cache.get(self._hash_url(url))
    
    def set(self, url, info):
        with self.lock:
            if len(self.cache) >= self.max_size:
                # Remove oldest entry
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
            self.cache[self._hash_url(url)] = info
    
    def _hash_url(self, url):
        return hashlib.md5(url.encode()).hexdigest()
    
    def clear(self):
        with self.lock:
            self.cache.clear()

class RetryManager:
    """Handle retry logic for failed operations"""
    def __init__(self, max_retries=3, base_delay=1):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise last_exception

class DownloadHistory:
    """Manage download history persistence"""
    def __init__(self, history_file="download_history.json"):
        self.history_file = history_file
        self.history = self.load_history()
        self.lock = Lock()
    
    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []
    
    def save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history[-1000:], f, indent=2, ensure_ascii=False)  # Keep last 1000
        except Exception:
            pass
    
    def add_download(self, video_info, status, file_path=None):
        with self.lock:
            entry = {
                'url': video_info['url'],
                'title': video_info['title'],
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'file_path': file_path,
                'duration': video_info.get('duration', 'Unknown')
            }
            self.history.append(entry)
            self.save_history()

class YouTubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader Pro Enhanced")
        self.root.geometry("1100x800")
        self.root.minsize(900, 700)
        
        # Initialize managers and state
        self.config_file = "downloader_config.json"
        self.download_state = DownloadState()
        self.video_cache = VideoInfoCache()
        self.retry_manager = RetryManager(max_retries=3, base_delay=2)
        self.download_history = DownloadHistory()
        
        # Thread management
        self.progress_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.download_futures = []
        
        # GUI state
        self.video_queue = []
        self.queue_lock = Lock()
        self.thumbnail_cache = {}
        
        # Load configuration
        self.config = self.load_config()
        
        # Setup logging
        self.thread_safe_logger = ThreadSafeLogger(self._log_message_internal)
        
        # Initialize GUI
        self.setup_gui()
        self.setup_styles()
        
        # Start progress monitoring
        self.root.after(100, self.check_progress_queue)
        
        # Setup periodic cleanup
        self.root.after(300000, self.periodic_cleanup)  # Every 5 minutes
    def refresh_queue_info(self):
        """Refresh video information for queued items"""
        if not self.video_queue:
            return
        
        self.log_message("Refreshing queue information...")
        
        def refresh_info():
            for i, video in enumerate(self.video_queue):
                if video['status'] == 'Queued':
                    updated_videos = self.extract_video_info(video['url'])
                    if updated_videos and len(updated_videos) > 0:
                        updated_video = updated_videos[0]  # Take first if multiple
                        video['title'] = updated_video['title']
                        video['duration'] = updated_video['duration']
                        
                        # Update treeview
                        self.root.after(0, lambda idx=i, v=video: self.update_queue_item(idx, v))
            
            self.root.after(0, lambda: self.log_message("Queue information refreshed"))
        
        threading.Thread(target=refresh_info, daemon=True).start()
     
    def load_config(self):
        """Load configuration with enhanced error handling"""
        default_config = {
            "download_path": str(Path.home() / "Downloads"),
            "quality": "best",
            "include_subtitles": False,
            "subtitle_langs": ["en"],
            "window_geometry": "1100x800",
            "max_concurrent_downloads": 2,
            "bandwidth_limit": 0,  # 0 means no limit
            "retry_attempts": 3,
            "auto_cleanup_completed": True,
            "check_disk_space": True,
            "min_disk_space_gb": 1.0
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge with defaults for missing keys
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
        except Exception as e:
            print(f"Error loading config: {e}")
        
        return default_config
    
    def save_config(self):
        """Save configuration with error handling"""
        try:
            self.config.update({
                "window_geometry": self.root.geometry(),
                "download_path": self.path_var.get(),
                "quality": self.quality_var.get(),
                "include_subtitles": self.subtitle_var.get(),
                "subtitle_langs": [lang.strip() for lang in self.subtitle_langs_var.get().split(',') if lang.strip()],
                "max_concurrent_downloads": self.concurrent_var.get(),
                "bandwidth_limit": self.bandwidth_var.get()
            })
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.thread_safe_logger.log(f"Error saving config: {e}", "ERROR")
    
    def check_disk_space(self, required_bytes=None):
        """Check available disk space"""
        try:
            download_path = self.path_var.get()
            if not os.path.exists(download_path):
                return False
            
            total, used, free = shutil.disk_usage(download_path)
            free_gb = free / (1024**3)
            
            min_space = self.config.get('min_disk_space_gb', 1.0)
            if required_bytes:
                required_gb = required_bytes / (1024**3)
                return free_gb > (min_space + required_gb)
            
            return free_gb > min_space
        except Exception:
            return True  # If we can't check, assume it's okay
    
    def setup_styles(self):
        """Setup enhanced custom styles"""
        style = ttk.Style()
        
        # Configure styles
        style.configure("Title.TLabel", font=("Arial", 14, "bold"))
        style.configure("Status.TLabel", font=("Arial", 9))
        style.configure("Success.TLabel", foreground="green", font=("Arial", 9, "bold"))
        style.configure("Error.TLabel", foreground="red", font=("Arial", 9, "bold"))
        style.configure("Warning.TLabel", foreground="orange", font=("Arial", 9, "bold"))
        
        # Progress bar styles
        style.configure("Success.Horizontal.TProgressbar", foreground="green", background="green")
        style.configure("Error.Horizontal.TProgressbar", foreground="red", background="red")
    
    def setup_gui(self):
        """Setup the enhanced GUI layout"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Main download tab
        self.main_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.main_frame, text="Downloads")
        
        # Settings tab
        self.settings_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.settings_frame, text="Settings")
        
        # History tab
        self.history_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.history_frame, text="History")
        
        # Setup each tab
        self.setup_main_tab()
        self.setup_settings_tab()
        self.setup_history_tab()
    
    def setup_main_tab(self):
        """Setup main download tab"""
        # Configure grid weights
        self.main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(self.main_frame, text="YouTube Downloader Pro Enhanced", style="Title.TLabel")
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # URL Input Section
        self.setup_url_section(self.main_frame, row=1)
        
        # Quick Settings Section
        self.setup_quick_settings_section(self.main_frame, row=2)
        
        # Queue Section with thumbnails
        self.setup_enhanced_queue_section(self.main_frame, row=3)
        
        # Progress Section
        self.setup_progress_section(self.main_frame, row=4)
        
        # Control Buttons
        self.setup_control_buttons(self.main_frame, row=5)
        
        # Status Section
        self.setup_status_section(self.main_frame, row=6)
        
        # Configure row weights
        self.main_frame.rowconfigure(3, weight=1)  # Queue section expands
        self.main_frame.rowconfigure(6, weight=1)  # Status section expands
    
    def setup_url_section(self, parent, row):
        """Setup enhanced URL input section"""
        url_frame = ttk.LabelFrame(parent, text="Video URLs", padding="10")
        url_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(1, weight=1)
        
        # Single URL input
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.url_entry.bind('<Return>', lambda e: self.add_to_queue())
        self.url_entry.bind('<Control-v>', self.on_paste)  # Handle paste events
        
        self.add_button = ttk.Button(url_frame, text="Add to Queue", command=self.add_to_queue)
        self.add_button.grid(row=0, column=2, padx=(5, 0))
        
        # Multi-URL text area
        ttk.Label(url_frame, text="Multiple URLs (one per line):").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=(10, 0), padx=(0, 5))
        
        # Frame for text area with scrollbar
        text_frame = ttk.Frame(url_frame)
        text_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0), padx=(0, 5))
        text_frame.columnconfigure(0, weight=1)
        
        self.multi_url_text = tk.Text(text_frame, height=4, width=50, wrap=tk.WORD)
        url_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.multi_url_text.yview)
        self.multi_url_text.configure(yscrollcommand=url_scrollbar.set)
        
        self.multi_url_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        url_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        multi_add_button = ttk.Button(url_frame, text="Add All", command=self.add_multiple_urls)
        multi_add_button.grid(row=1, column=2, sticky=(tk.N), pady=(10, 0), padx=(5, 0))
        
        # Status labels
        self.extracting_label = ttk.Label(url_frame, text="", style="Status.TLabel")
        self.extracting_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        self.url_count_label = ttk.Label(url_frame, text="Ready to add URLs", style="Status.TLabel")
        self.url_count_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(2, 0))
    
    def setup_quick_settings_section(self, parent, row):
        """Setup quick access settings"""
        settings_frame = ttk.LabelFrame(parent, text="Quick Settings", padding="10")
        settings_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        
        # Download path
        ttk.Label(settings_frame, text="Path:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.path_var = tk.StringVar(value=self.config["download_path"])
        path_entry = ttk.Entry(settings_frame, textvariable=self.path_var, state="readonly", width=40)
        path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        browse_button = ttk.Button(settings_frame, text="Browse", command=self.browse_download_path)
        browse_button.grid(row=0, column=2, padx=(5, 0))
        
        open_folder_button = ttk.Button(settings_frame, text="Open", command=self.open_download_folder)
        open_folder_button.grid(row=0, column=3, padx=(5, 0))
        
        # Quality and concurrent downloads
        settings_row2 = ttk.Frame(settings_frame)
        settings_row2.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Label(settings_row2, text="Quality:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.quality_var = tk.StringVar(value=self.config["quality"])
        quality_combo = ttk.Combobox(settings_row2, textvariable=self.quality_var, 
                                   values=["best", "worst", "1080p", "720p", "480p", "360p", "audio_only"], 
                                   state="readonly", width=12)
        quality_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(settings_row2, text="Concurrent:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.concurrent_var = tk.IntVar(value=self.config.get("max_concurrent_downloads", 2))
        concurrent_spin = ttk.Spinbox(settings_row2, from_=1, to=5, width=5, textvariable=self.concurrent_var)
        concurrent_spin.pack(side=tk.LEFT, padx=(0, 15))
        
        # Subtitles checkbox
        self.subtitle_var = tk.BooleanVar(value=self.config["include_subtitles"])
        subtitle_check = ttk.Checkbutton(settings_row2, text="Subtitles", variable=self.subtitle_var)
        subtitle_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Disk space indicator
        self.disk_space_label = ttk.Label(settings_row2, text="", style="Status.TLabel")
        self.disk_space_label.pack(side=tk.RIGHT)
        self.update_disk_space_info()
    
    def setup_enhanced_queue_section(self, parent, row):
        """Setup enhanced queue display with thumbnails"""
        queue_frame = ttk.LabelFrame(parent, text="Download Queue", padding="10")
        queue_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)
        
        # Create frame for treeview and scrollbars
        tree_frame = ttk.Frame(queue_frame)
        tree_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Treeview for queue with thumbnails
        columns = ("Thumbnail", "URL", "Title", "Duration", "Size", "Status", "Progress")
        self.queue_tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=8)
        
        # Configure columns
        self.queue_tree.heading("#0", text="ID")
        self.queue_tree.column("#0", width=50, minwidth=50)
        
        column_config = {
            "Thumbnail": (80, 80),
            "URL": (200, 150),
            "Title": (300, 200),
            "Duration": (80, 80),
            "Size": (80, 80),
            "Status": (100, 100),
            "Progress": (100, 100)
        }
        
        for col, (width, minwidth) in column_config.items():
            self.queue_tree.heading(col, text=col)
            self.queue_tree.column(col, width=width, minwidth=minwidth)
        
        self.queue_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.queue_tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.queue_tree.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.queue_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # Bind double-click to view details
        self.queue_tree.bind('<Double-1>', self.show_video_details)
        
        # Context menu
        self.create_context_menu()
        self.queue_tree.bind('<Button-3>', self.show_context_menu)
        
        # Queue control buttons
        queue_button_frame = ttk.Frame(queue_frame)
        queue_button_frame.grid(row=1, column=0, pady=(10, 0))
        
        self.remove_button = ttk.Button(queue_button_frame, text="Remove Selected", 
                                      command=self.remove_from_queue)
        self.remove_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_button = ttk.Button(queue_button_frame, text="Clear Queue", 
                                     command=self.clear_queue)
        self.clear_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.refresh_button = ttk.Button(queue_button_frame, text="Refresh Info", 
                                       command=self.refresh_queue_info)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.move_up_button = ttk.Button(queue_button_frame, text="↑ Move Up", 
                                        command=self.move_queue_item_up)
        self.move_up_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.move_down_button = ttk.Button(queue_button_frame, text="↓ Move Down", 
                                          command=self.move_queue_item_down)
        self.move_down_button.pack(side=tk.LEFT)
    
    def setup_progress_section(self, parent, row):
        """Setup enhanced progress display section"""
        progress_frame = ttk.LabelFrame(parent, text="Download Progress", padding="10")
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        
        # Current file progress
        ttk.Label(progress_frame, text="Current:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.current_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.current_progress.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.current_percent_label = ttk.Label(progress_frame, text="0%")
        self.current_percent_label.grid(row=0, column=2, padx=(5, 0))
        
        # Overall progress
        ttk.Label(progress_frame, text="Overall:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        
        self.overall_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.overall_progress.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(5, 0), padx=(0, 5))
        
        self.overall_percent_label = ttk.Label(progress_frame, text="0%")
        self.overall_percent_label.grid(row=1, column=2, pady=(5, 0), padx=(5, 0))
        
        # Download statistics
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))
        
        self.speed_label = ttk.Label(stats_frame, text="Speed: --", style="Status.TLabel")
        self.speed_label.pack(side=tk.LEFT)
        
        self.eta_label = ttk.Label(stats_frame, text="ETA: --", style="Status.TLabel")
        self.eta_label.pack(side=tk.LEFT, padx=(20, 0))
        
        self.downloaded_label = ttk.Label(stats_frame, text="Downloaded: 0 MB", style="Status.TLabel")
        self.downloaded_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Current file info
        self.current_file_label = ttk.Label(progress_frame, text="Ready to download...", style="Status.TLabel")
        self.current_file_label.grid(row=3, column=0, columnspan=3, pady=(5, 0), sticky=tk.W)
    
    def setup_control_buttons(self, parent, row):
        """Setup enhanced control buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="▶ Start Downloads", 
                                     command=self.start_downloads)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.pause_button = ttk.Button(button_frame, text="⏸ Pause", 
                                     command=self.pause_downloads, state="disabled")
        self.pause_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.resume_button = ttk.Button(button_frame, text="▶ Resume", 
                                      command=self.resume_downloads, state="disabled")
        self.resume_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="⏹ Stop", 
                                    command=self.stop_downloads, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Queue management buttons
        separator = ttk.Separator(button_frame, orient=tk.VERTICAL)
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 10))
        
        self.retry_failed_button = ttk.Button(button_frame, text="🔄 Retry Failed", 
                                            command=self.retry_failed_downloads)
        self.retry_failed_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.cleanup_button = ttk.Button(button_frame, text="🧹 Cleanup", 
                                       command=self.cleanup_completed)
        self.cleanup_button.pack(side=tk.LEFT)
    
    def setup_status_section(self, parent, row):
        """Setup enhanced status/log section"""
        status_frame = ttk.LabelFrame(parent, text="Status Log", padding="10")
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        # Log text area with enhanced formatting
        self.status_text = scrolledtext.ScrolledText(status_frame, height=8, wrap=tk.WORD,
                                                   font=("Consolas", 9))
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure tags for different log levels
        self.status_text.tag_configure("ERROR", foreground="red")
        self.status_text.tag_configure("SUCCESS", foreground="green")
        self.status_text.tag_configure("WARNING", foreground="orange")
        self.status_text.tag_configure("INFO", foreground="black")
        
        # Log controls
        log_controls = ttk.Frame(status_frame)
        log_controls.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_controls, text="Auto-scroll", variable=self.auto_scroll_var).pack(side=tk.LEFT)
        
        ttk.Button(log_controls, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(log_controls, text="Save Log", command=self.save_log).pack(side=tk.LEFT, padx=(5, 0))
        
        # Add initial message
        self.thread_safe_logger.log("YouTube Downloader Pro Enhanced initialized. Ready to download!")
    
    def setup_settings_tab(self):
        """Setup advanced settings tab"""
        # Configure grid
        self.settings_frame.columnconfigure(0, weight=1)
        
        # Advanced Download Settings
        adv_frame = ttk.LabelFrame(self.settings_frame, text="Advanced Download Settings", padding="10")
        adv_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        adv_frame.columnconfigure(1, weight=1)
        
        # Bandwidth limiting
        ttk.Label(adv_frame, text="Bandwidth Limit (KB/s):").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.bandwidth_var = tk.IntVar(value=self.config.get("bandwidth_limit", 0))
        bandwidth_spin = ttk.Spinbox(adv_frame, from_=0, to=10000, width=10, textvariable=self.bandwidth_var)
        bandwidth_spin.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        ttk.Label(adv_frame, text="(0 = unlimited)").grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        
        # Retry settings
        ttk.Label(adv_frame, text="Retry Attempts:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        self.retry_var = tk.IntVar(value=self.config.get("retry_attempts", 3))
        retry_spin = ttk.Spinbox(adv_frame, from_=0, to=10, width=10, textvariable=self.retry_var)
        retry_spin.grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        
        # Subtitle settings
        subtitle_frame = ttk.LabelFrame(self.settings_frame, text="Subtitle Settings", padding="10")
        subtitle_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        subtitle_frame.columnconfigure(1, weight=1)
        
        ttk.Label(subtitle_frame, text="Languages:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.subtitle_langs_var = tk.StringVar(value=",".join(self.config.get('subtitle_langs', ['en'])))
        subtitle_langs_entry = ttk.Entry(subtitle_frame, textvariable=self.subtitle_langs_var)
        subtitle_langs_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.auto_translate_var = tk.BooleanVar(value=self.config.get("auto_translate", False))
        ttk.Checkbutton(subtitle_frame, text="Auto-translate subtitles", 
                       variable=self.auto_translate_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # File Management
        file_frame = ttk.LabelFrame(self.settings_frame, text="File Management", padding="10")
        file_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        self.auto_cleanup_var = tk.BooleanVar(value=self.config.get("auto_cleanup_completed", True))
        ttk.Checkbutton(file_frame, text="Auto-cleanup completed downloads", 
                       variable=self.auto_cleanup_var).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        self.check_disk_var = tk.BooleanVar(value=self.config.get("check_disk_space", True))
        ttk.Checkbutton(file_frame, text="Check disk space before download", 
                       variable=self.check_disk_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(file_frame, text="Min. free space (GB):").grid(row=2, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        self.min_space_var = tk.DoubleVar(value=self.config.get("min_disk_space_gb", 1.0))
        min_space_spin = ttk.Spinbox(file_frame, from_=0.1, to=100.0, increment=0.1, 
                                   format="%.1f", width=10, textvariable=self.min_space_var)
        min_space_spin.grid(row=2, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        
        # Cache Management
        cache_frame = ttk.LabelFrame(self.settings_frame, text="Cache Management", padding="10")
        cache_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        cache_buttons = ttk.Frame(cache_frame)
        cache_buttons.pack(fill=tk.X)
        
        ttk.Button(cache_buttons, text="Clear Video Info Cache", 
                  command=self.clear_video_cache).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cache_buttons, text="Clear Thumbnails", 
                  command=self.clear_thumbnail_cache).pack(side=tk.LEFT, padx=(0, 5))
        
        self.cache_info_label = ttk.Label(cache_frame, text="", style="Status.TLabel")
        self.cache_info_label.pack(pady=(10, 0))
        self.update_cache_info()
        
        # Save settings button
        ttk.Button(self.settings_frame, text="Save Settings", 
                  command=self.save_config).grid(row=4, column=0, pady=(20, 0))
    
    def setup_history_tab(self):
        """Setup download history tab"""
        self.history_frame.columnconfigure(0, weight=1)
        self.history_frame.rowconfigure(0, weight=1)
        
        # History treeview
        history_columns = ("Timestamp", "Title", "Status", "File Path")
        self.history_tree = ttk.Treeview(self.history_frame, columns=history_columns, show="headings", height=15)
        
        for col in history_columns:
            self.history_tree.heading(col, text=col)
            if col == "Timestamp":
                self.history_tree.column(col, width=150, minwidth=150)
            elif col == "Title":
                self.history_tree.column(col, width=300, minwidth=200)
            elif col == "Status":
                self.history_tree.column(col, width=100, minwidth=100)
            else:  # File Path
                self.history_tree.column(col, width=250, minwidth=150)
        
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # History scrollbar
        history_scrollbar = ttk.Scrollbar(self.history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        history_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        # History controls
        history_controls = ttk.Frame(self.history_frame)
        history_controls.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(history_controls, text="Refresh", command=self.refresh_history).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(history_controls, text="Clear History", command=self.clear_history).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(history_controls, text="Export History", command=self.export_history).pack(side=tk.LEFT)
        
        # Load initial history
        self.refresh_history()
    
    def create_context_menu(self):
        """Create context menu for queue items"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Remove", command=self.remove_from_queue)
        self.context_menu.add_command(label="Move to Top", command=self.move_to_top)
        self.context_menu.add_command(label="Move to Bottom", command=self.move_to_bottom)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy URL", command=self.copy_selected_url)
        self.context_menu.add_command(label="Open in Browser", command=self.open_in_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Retry Download", command=self.retry_selected)
    
    def show_context_menu(self, event):
        """Show context menu"""
        item = self.queue_tree.identify_row(event.y)
        if item:
            self.queue_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def on_paste(self, event):
        """Handle paste events in URL entry"""
        # Get clipboard content
        try:
            clipboard_content = self.root.clipboard_get()
            urls = self.extract_urls_from_text(clipboard_content)
            if len(urls) > 1:
                # Multiple URLs found, ask user what to do
                result = messagebox.askyesnocancel("Multiple URLs", 
                    f"Found {len(urls)} URLs in clipboard. Add all to queue?")
                if result is True:  # Yes
                    self.multi_url_text.delete(1.0, tk.END)
                    self.multi_url_text.insert(1.0, '\n'.join(urls))
                    self.add_multiple_urls()
                    return "break"  # Prevent default paste
                elif result is False:  # No, just paste first URL
                    self.url_var.set(urls[0])
                    return "break"
                # Cancel - allow default paste
        except tk.TclError:
            pass  # No clipboard content
        
        return None  # Allow default paste
    
    def extract_urls_from_text(self, text):
        """Extract YouTube URLs from text"""
        youtube_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/playlist\?list=)[^\s]+'
        return re.findall(youtube_pattern, text)
    
    def _log_message_internal(self, message, level="INFO"):
        """Internal log message handler (called by thread-safe logger)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        # Insert with appropriate tag
        self.status_text.insert(tk.END, formatted_message, level)
        
        # Auto-scroll if enabled
        if self.auto_scroll_var.get():
            self.status_text.see(tk.END)
        
        # Limit log size
        if int(self.status_text.index('end').split('.')[0]) > 1000:
            self.status_text.delete(1.0, "100.0")
        
        # Also print to console for debugging
        print(formatted_message.strip())
    
    def validate_url(self, url):
        """Enhanced URL validation"""
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})|'
            r'(https?://)?(www\.)?youtube\.com/playlist\?list=([^&=%\?]+)|'
            r'(https?://)?(www\.)?youtube\.com/channel/([^&=%\?/]+)|'
            r'(https?://)?(www\.)?youtube\.com/c/([^&=%\?/]+)|'
            r'(https?://)?(www\.)?youtube\.com/@([^&=%\?/]+)'
        )
        return youtube_regex.match(url.strip()) is not None
    
    def extract_video_info(self, url):
        """Enhanced video info extraction with caching and error handling"""
        # Check cache first
        cached_info = self.video_cache.get(url)
        if cached_info:
            return cached_info
        
        def extract_info_with_retry():
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'ignoreerrors': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None
                
                if 'entries' in info:  # Playlist
                    playlist_title = info.get('title', 'Untitled Playlist')
                    videos = []
                    for i, entry in enumerate(info['entries']):
                        if entry and not self.download_state.should_stop.is_set():
                            try:
                                video_info = {
                                    'url': entry.get('webpage_url', url),
                                    'title': entry.get('title', 'Unknown Title'),
                                    'duration': self.format_duration(entry.get('duration', 0)),
                                    'filesize': entry.get('filesize') or entry.get('filesize_approx', 0),
                                    'thumbnail': entry.get('thumbnail'),
                                    'playlist_title': playlist_title,
                                    'playlist_index': entry.get('playlist_index', i + 1)
                                }
                                videos.append(video_info)
                                
                                # Update progress for large playlists
                                if len(videos) % 10 == 0:
                                    self.progress_queue.put(('extracting_progress', 
                                        f"Extracted {len(videos)} videos from playlist..."))
                                    
                            except Exception as e:
                                self.thread_safe_logger.log(f"Error processing playlist entry: {e}", "WARNING")
                                continue
                    return videos
                else:  # Single video
                    return [{
                        'url': url,
                        'title': info.get('title', 'Unknown Title'),
                        'duration': self.format_duration(info.get('duration', 0)),
                        'filesize': info.get('filesize') or info.get('filesize_approx', 0),
                        'thumbnail': info.get('thumbnail'),
                        'playlist_title': None,
                        'playlist_index': None
                    }]
        
        try:
            # Use retry manager for extraction
            videos = self.retry_manager.execute_with_retry(extract_info_with_retry)
            
            # Cache the result
            if videos:
                self.video_cache.set(url, videos)
            
            return videos
            
        except Exception as e:
            self.thread_safe_logger.log(f"Error extracting info for {url}: {str(e)}", "ERROR")
            return None
    
    def format_duration(self, seconds):
        """Format duration with better handling"""
        if not seconds or seconds <= 0:
            return "Unknown"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def format_filesize(self, size_bytes):
        """Format file size in human readable format"""
        if not size_bytes or size_bytes <= 0:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def load_thumbnail(self, url, size=(60, 45)):
        """Load thumbnail image with caching"""
        if not url or url in self.thumbnail_cache:
            return self.thumbnail_cache.get(url)
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content))
                image = image.resize(size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                self.thumbnail_cache[url] = photo
                return photo
        except Exception as e:
            self.thread_safe_logger.log(f"Error loading thumbnail: {e}", "WARNING")
        
        # Return placeholder if failed
        placeholder = self.create_placeholder_thumbnail(size)
        self.thumbnail_cache[url] = placeholder
        return placeholder
    
    def create_placeholder_thumbnail(self, size=(60, 45)):
        """Create placeholder thumbnail"""
        try:
            image = Image.new('RGB', size, color='lightgray')
            return ImageTk.PhotoImage(image)
        except Exception:
            return None
    
    def add_to_queue(self):
        """Enhanced add to queue with better feedback"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL")
            return
        
        if not self.validate_url(url):
            messagebox.showerror("Error", "Invalid YouTube URL")
            return
        
        # Check if URL already in queue
        with self.queue_lock:
            for video in self.video_queue:
                if video['url'] == url and video['status'] != 'Removed':
                    messagebox.showwarning("Warning", "URL already in queue")
                    return
        
        self.extracting_label.config(text="Extracting video info...")
        self.url_count_label.config(text="Please wait...")
        self.thread_safe_logger.log(f"Extracting info for: {url}")
        
        # Extract video info in background thread
        def extract_info():
            try:
                videos = self.extract_video_info(url)
                if videos:
                    self.root.after(0, lambda: self.add_videos_to_queue(videos))
                else:
                    self.root.after(0, lambda: self.thread_safe_logger.log("Failed to extract video information", "ERROR"))
            except Exception as e:
                self.root.after(0, lambda: self.thread_safe_logger.log(f"Extraction error: {e}", "ERROR"))
            finally:
                self.root.after(0, lambda: self.extracting_label.config(text=""))
                self.root.after(0, self.update_url_count)
        
        self.executor.submit(extract_info)
        self.url_var.set("")  # Clear the entry
    
    def add_multiple_urls(self):
        """Enhanced multiple URL addition"""
        urls_text = self.multi_url_text.get(1.0, tk.END).strip()
        if not urls_text:
            messagebox.showwarning("Warning", "Please enter URLs")
            return
        
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        valid_urls = []
        
        with self.queue_lock:
            existing_urls = {video['url'] for video in self.video_queue if video['status'] != 'Removed'}
        
        for url in urls:
            if self.validate_url(url):
                if url not in existing_urls:
                    valid_urls.append(url)
                else:
                    self.thread_safe_logger.log(f"Skipping duplicate URL: {url}", "WARNING")
            else:
                self.thread_safe_logger.log(f"Skipping invalid URL: {url}", "WARNING")
        
        if not valid_urls:
            messagebox.showwarning("Warning", "No new valid YouTube URLs found")
            return
        
        self.extracting_label.config(text=f"Extracting info for {len(valid_urls)} URLs...")
        self.thread_safe_logger.log(f"Processing {len(valid_urls)} URLs...")
        
        # Extract info for all URLs with progress updates
        def extract_all_info():
            all_videos = []
            for i, url in enumerate(valid_urls):
                if self.download_state.should_stop.is_set():
                    break
                    
                self.root.after(0, lambda i=i: self.extracting_label.config(
                    text=f"Processing URL {i+1}/{len(valid_urls)}..."))
                
                videos = self.extract_video_info(url)
                if videos:
                    all_videos.extend(videos)
            
            if all_videos:
                self.root.after(0, lambda: self.add_videos_to_queue(all_videos))
            
            self.root.after(0, lambda: self.extracting_label.config(text=""))
            self.root.after(0, self.update_url_count)
        
        self.executor.submit(extract_all_info)
        self.multi_url_text.delete(1.0, tk.END)  # Clear the text area
    
    def add_videos_to_queue(self, videos):
        """Enhanced video addition with thumbnails"""
        with self.queue_lock:
            for video in videos:
                video_id = len(self.video_queue)
                video_data = {
                    'id': video_id,
                    'url': video['url'],
                    'title': video['title'],
                    'duration': video['duration'],
                    'filesize': video.get('filesize', 0),
                    'thumbnail_url': video.get('thumbnail'),
                    'status': 'Queued',
                    'progress': 0,
                    'playlist_title': video.get('playlist_title'),
                    'playlist_index': video.get('playlist_index'),
                    'retry_count': 0,
                    'error_message': None
                }
                self.video_queue.append(video_data)
        
        # Add to treeview in main thread
        for video in videos:
            self.add_video_to_treeview(video, len(self.video_queue) - len(videos) + videos.index(video))
        
        self.thread_safe_logger.log(f"Added {len(videos)} video(s) to queue")
        self.update_overall_progress()
        self.update_url_count()
    
    def add_video_to_treeview(self, video, video_id):
        """Add video to treeview with thumbnail loading"""
        # Add item first with placeholder
        item_id = self.queue_tree.insert('', 'end', text=str(video_id), 
                                        values=("Loading...",
                                               video['url'][:50] + '...' if len(video['url']) > 50 else video['url'],
                                               video['title'][:40] + '...' if len(video['title']) > 40 else video['title'],
                                               video['duration'],
                                               self.format_filesize(video.get('filesize', 0)),
                                               'Queued',
                                               '0%'))
        
        # Load thumbnail asynchronously
        if video.get('thumbnail'):
            def load_thumb():
                thumbnail = self.load_thumbnail(video['thumbnail'])
                if thumbnail:
                    self.root.after(0, lambda: self.update_thumbnail_in_tree(item_id, thumbnail))
            
            self.executor.submit(load_thumb)
    
    def update_thumbnail_in_tree(self, item_id, thumbnail):
        """Update thumbnail in treeview item"""
        try:
            current_values = list(self.queue_tree.item(item_id, 'values'))
            current_values[0] = "📺"  # Use emoji as placeholder for actual thumbnail
            self.queue_tree.item(item_id, values=current_values)
            # Note: tkinter treeview doesn't support images directly in values
            # This is a simplified implementation
        except tk.TclError:
            pass  # Item might have been deleted
    
    def update_url_count(self):
        """Update URL count display"""
        with self.queue_lock:
            total = len([v for v in self.video_queue if v['status'] != 'Removed'])
            queued = len([v for v in self.video_queue if v['status'] == 'Queued'])
            
        self.url_count_label.config(text=f"Queue: {queued} waiting, {total} total")
    
    def update_disk_space_info(self):
        """Update disk space information"""
        try:
            download_path = self.path_var.get()
            if os.path.exists(download_path):
                total, used, free = shutil.disk_usage(download_path)
                free_gb = free / (1024**3)
                self.disk_space_label.config(text=f"Free space: {free_gb:.1f} GB")
            else:
                self.disk_space_label.config(text="Path not found")
        except Exception:
            self.disk_space_label.config(text="Unable to check space")
        
        # Schedule next update
        self.root.after(30000, self.update_disk_space_info)  # Every 30 seconds
    
    def start_downloads(self):
        """Enhanced download start with concurrent downloads"""
        with self.queue_lock:
            active_videos = [v for v in self.video_queue if v['status'] == 'Queued']
        
        if not active_videos:
            messagebox.showwarning("Warning", "No videos in queue to download")
            return
        
        if not os.path.exists(self.path_var.get()):
            messagebox.showerror("Error", "Download path does not exist")
            return
        
        if self.config.get('check_disk_space', True) and not self.check_disk_space():
            messagebox.showerror("Error", "Insufficient disk space for downloads")
            return
        
        # Update button states
        self.download_state.start_download()
        self.start_button.config(state="disabled")
        self.pause_button.config(state="normal")
        self.stop_button.config(state="normal")
        
        self.thread_safe_logger.log(f"Starting download of {len(active_videos)} video(s) with {self.concurrent_var.get()} concurrent downloads")
        
        # Start concurrent downloads
        max_workers = min(self.concurrent_var.get(), len(active_videos))
        
        def download_manager():
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit download tasks
                self.download_futures = []
                for video in active_videos:
                    if not self.download_state.should_continue():
                        break
                    future = executor.submit(self.download_single_video, video)
                    self.download_futures.append((future, video))
                
                # Wait for completion
                for future, video in as_completed([(f, v) for f, v in self.download_futures]):
                    try:
                        future.result()  # This will raise any exception that occurred
                    except Exception as e:
                        self.thread_safe_logger.log(f"Download failed for {video['title']}: {e}", "ERROR")
                        video['status'] = 'Error'
                        video['error_message'] = str(e)
                        self.progress_queue.put(('status', video['id'], 'Error'))
            
            # All downloads complete
            self.progress_queue.put(('download_complete',))
        
        self.executor.submit(download_manager)
    
    def download_single_video(self, video):
        """Download a single video with enhanced error handling"""
        if not self.download_state.should_continue():
            return
        
        try:
            # Wait if paused
            self.download_state.wait_if_paused()
            
            # Update status
            video['status'] = 'Downloading'
            self.progress_queue.put(('status', video['id'], 'Downloading'))
            self.progress_queue.put(('current_file', f"Downloading: {video['title']}"))
            
            # Configure output path
            output_path = self.get_output_path(video)
            
            # Check if file already exists
            if self.check_existing_file(output_path, video):
                return
            
            # Configure yt-dlp options with enhanced settings
            ydl_opts = self.get_ydl_options(video, output_path)
            
            # Download with retry mechanism
            def download_with_ydl():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video['url']])
            
            # Execute download with retries
            self.retry_manager.execute_with_retry(download_with_ydl)
            
            # Success
            video['status'] = 'Completed'
            self.progress_queue.put(('status', video['id'], 'Completed'))
            self.progress_queue.put(('log', f"✓ Successfully downloaded: {video['title']}", 'SUCCESS'))
            
            # Add to history
            self.download_history.add_download(video, 'Completed', output_path)
            
        except Exception as e:
            video['status'] = 'Error'
            video['error_message'] = str(e)
            video['retry_count'] = getattr(video, 'retry_count', 0) + 1
            self.progress_queue.put(('status', video['id'], 'Error'))
            self.progress_queue.put(('log', f"✗ Error downloading {video['title']}: {str(e)}", 'ERROR'))
            
            # Add to history
            self.download_history.add_download(video, 'Error')
    
    def get_output_path(self, video):
        """Get appropriate output path for video"""
        base_path = self.path_var.get()
        
        if video.get('playlist_title'):
            # Create playlist folder
            playlist_folder = self.sanitize_filename(video['playlist_title'])
            download_dir = os.path.join(base_path, playlist_folder)
            os.makedirs(download_dir, exist_ok=True)
            
            if video.get('playlist_index') is not None:
                return os.path.join(download_dir, f"{video['playlist_index']:03d} - %(title)s.%(ext)s")
            else:
                return os.path.join(download_dir, '%(title)s.%(ext)s')
        else:
            return os.path.join(base_path, '%(title)s.%(ext)s')
    
    def check_existing_file(self, output_template, video):
        """Check if file already exists and handle accordingly"""
        # This is a simplified check - yt-dlp handles this better internally
        return False
    
    def get_ydl_options(self, video, output_path):
        """Get comprehensive yt-dlp options"""
        ydl_opts = {
            'outtmpl': output_path,
            'format': self.get_format_selector(),
            'progress_hooks': [lambda d: self.progress_hook(d, video['id'])],
            'ignoreerrors': False,
            'no_warnings': False,
        }
        
        # Bandwidth limiting
        if self.bandwidth_var.get() > 0:
            ydl_opts['ratelimit'] = self.bandwidth_var.get() * 1024  # Convert KB/s to B/s
        
        # Subtitle options
        if self.subtitle_var.get():
            ydl_opts.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': self.config.get('subtitle_langs', ['en']),
            })
            
            if self.auto_translate_var.get():
                ydl_opts['subtitleslangs'].extend(['en-auto', 'auto'])
        
        # Retry options
        ydl_opts['retries'] = self.retry_var.get()
        ydl_opts['fragment_retries'] = self.retry_var.get()
        
        return ydl_opts
    
    def get_format_selector(self):
        """Enhanced format selector"""
        quality = self.quality_var.get()
        
        format_map = {
            'best': 'best[ext=mp4]/best',
            'worst': 'worst[ext=mp4]/worst',
            '1080p': 'best[height<=1080][ext=mp4]/best[height<=1080]',
            '720p': 'best[height<=720][ext=mp4]/best[height<=720]',
            '480p': 'best[height<=480][ext=mp4]/best[height<=480]',
            '360p': 'best[height<=360][ext=mp4]/best[height<=360]',
            'audio_only': 'bestaudio[ext=m4a]/bestaudio/best[acodec!=none]'
        }
        
        return format_map.get(quality, 'best[ext=mp4]/best')
    
    def sanitize_filename(self, name):
        """Enhanced filename sanitization"""
        # Remove invalid characters for filename
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Limit length
        if len(name) > 100:
            name = name[:97] + "..."
        
        return name.strip()
    
    def progress_hook(self, d, video_id):
        """Enhanced progress hook with better statistics"""
        if d['status'] == 'downloading':
            if 'total_bytes' in d or 'total_bytes_estimate' in d:
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                
                if total and total > 0:
                    percent = (downloaded / total) * 100
                    self.progress_queue.put(('progress', video_id, percent))
                    
                    # Update statistics
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)
                    
                    speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else "Unknown"
                    eta_str = self.format_time(eta) if eta else "Unknown"
                    downloaded_str = self.format_filesize(downloaded)
                    
                    self.progress_queue.put(('stats', {
                        'speed': speed_str,
                        'eta': eta_str,
                        'downloaded': downloaded_str
                    }))
                    
                    self.progress_queue.put(('current_file', 
                        f"Downloading: {percent:.1f}% - {speed_str} - ETA: {eta_str}"))
        
        elif d['status'] == 'finished':
            self.progress_queue.put(('progress', video_id, 100))
            filename = os.path.basename(d['filename'])
            self.progress_queue.put(('current_file', f"Finished: {filename}"))
    
    def format_time(self, seconds):
        """Format time duration in seconds to readable format"""
        if not seconds or seconds <= 0:
            return "Unknown"
        
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds//60)}m {int(seconds%60)}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def pause_downloads(self):
        """Pause downloads"""
        self.download_state.pause_download()
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="normal")
        self.thread_safe_logger.log("Downloads paused")
    
    def resume_downloads(self):
        """Resume downloads"""
        self.download_state.resume_download()
        self.pause_button.config(state="normal")
        self.resume_button.config(state="disabled")
        self.thread_safe_logger.log("Downloads resumed")
    
    def stop_downloads(self):
        """Enhanced stop with cleanup"""
        self.download_state.stop_download()
        self.thread_safe_logger.log("Stopping downloads...")
        
        # Cancel futures
        for future, _ in self.download_futures:
            future.cancel()
        
        # Reset UI
        self.reset_download_ui()
    
    def reset_download_ui(self):
        """Reset download UI to initial state"""
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.resume_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        
        # Reset progress
        self.current_progress['value'] = 0
        self.current_percent_label.config(text="0%")
        self.current_file_label.config(text="Ready to download...")
        
        # Reset stats
        self.speed_label.config(text="Speed: --")
        self.eta_label.config(text="ETA: --")
        self.downloaded_label.config(text="Downloaded: 0 MB")
    
    def check_progress_queue(self):
        """Enhanced progress queue checking"""
        try:
            while True:
                item = self.progress_queue.get_nowait()
                
                if item[0] == 'progress':
                    # Update progress for specific video
                    video_id, percent = item[1], item[2]
                    self.update_video_progress(video_id, percent)
                    
                    # Update current progress bar
                    self.current_progress['value'] = percent
                    self.current_percent_label.config(text=f"{percent:.1f}%")
                
                elif item[0] == 'status':
                    # Update video status
                    video_id, status = item[1], item[2]
                    self.update_video_status(video_id, status)
                    self.update_overall_progress()
                
                elif item[0] == 'current_file':
                    # Update current file label
                    self.current_file_label.config(text=item[1])
                
                elif item[0] == 'stats':
                    # Update download statistics
                    stats = item[1]
                    self.speed_label.config(text=f"Speed: {stats['speed']}")
                    self.eta_label.config(text=f"ETA: {stats['eta']}")
                    self.downloaded_label.config(text=f"Downloaded: {stats['downloaded']}")
                
                elif item[0] == 'log':
                    # Add log message
                    message, level = item[1], item[2] if len(item) > 2 else 'INFO'
                    self.thread_safe_logger.log(message, level)
                
                elif item[0] == 'extracting_progress':
                    # Update extraction progress
                    self.extracting_label.config(text=item[1])
                
                elif item[0] == 'download_complete':
                    # Downloads finished
                    self.download_complete()
                
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.check_progress_queue)
    
    def update_video_progress(self, video_id, percent):
        """Update progress for specific video in queue"""
        with self.queue_lock:
            for video in self.video_queue:
                if video['id'] == video_id:
                    video['progress'] = percent
                    break
        
        # Update treeview
        for item in self.queue_tree.get_children():
            if int(self.queue_tree.item(item, 'text')) == video_id:
                current_values = list(self.queue_tree.item(item, 'values'))
                current_values[6] = f"{percent:.1f}%"  # Progress column
                self.queue_tree.item(item, values=current_values)
                break
    
    def update_video_status(self, video_id, status):
        """Enhanced video status update"""
        with self.queue_lock:
            for video in self.video_queue:
                if video['id'] == video_id:
                    video['status'] = status
                    break
        
        # Update treeview with color coding
        for item in self.queue_tree.get_children():
            if int(self.queue_tree.item(item, 'text')) == video_id:
                current_values = list(self.queue_tree.item(item, 'values'))
                current_values[5] = status  # Status column
                self.queue_tree.item(item, values=current_values)
                
                # Apply color coding
                if status == 'Completed':
                    self.queue_tree.item(item, tags=('success',))
                elif status == 'Error':
                    self.queue_tree.item(item, tags=('error',))
                elif status == 'Downloading':
                    self.queue_tree.item(item, tags=('downloading',))
                
                break
        
        # Configure tags for color coding
        self.queue_tree.tag_configure('success', background='lightgreen')
        self.queue_tree.tag_configure('error', background='lightcoral')
        self.queue_tree.tag_configure('downloading', background='lightyellow')
    
    def update_overall_progress(self):
        """Enhanced overall progress calculation"""
        with self.queue_lock:
            active_videos = [v for v in self.video_queue if v['status'] != 'Removed']
        
        if not active_videos:
            self.overall_progress['value'] = 0
            self.overall_percent_label.config(text="0%")
            return
        
        # Calculate weighted progress based on file sizes when available
        total_progress = 0
        total_weight = 0
        
        for video in active_videos:
            if video['status'] == 'Completed':
                progress = 100
            elif video['status'] == 'Downloading':
                progress = video.get('progress', 0)
            else:
                progress = 0
            
            # Use file size as weight if available, otherwise equal weight
            weight = video.get('filesize', 1) or 1
            total_progress += progress * weight
            total_weight += weight
        
        if total_weight > 0:
            overall_percent = total_progress / total_weight
        else:
            overall_percent = 0
        
        self.overall_progress['value'] = overall_percent
        self.overall_percent_label.config(text=f"{overall_percent:.1f}%")
    
    def download_complete(self):
        """Enhanced download completion handling"""
        self.download_state.stop_download()
        self.reset_download_ui()
        
        with self.queue_lock:
            completed_count = len([v for v in self.video_queue if v['status'] == 'Completed'])
            error_count = len([v for v in self.video_queue if v['status'] == 'Error'])
        
        self.thread_safe_logger.log("All downloads completed!", "SUCCESS")
        
        # Show completion message
        if error_count > 0:
            message = f"Downloads completed!\n✓ Successful: {completed_count}\n✗ Failed: {error_count}"
            messagebox.showwarning("Downloads Complete", message)
        else:
            message = f"Successfully downloaded {completed_count} video(s)!"
            messagebox.showinfo("Downloads Complete", message)
        
        # Auto-cleanup if enabled
        if self.auto_cleanup_var.get():
            self.cleanup_completed()
        
        # Refresh history
        self.refresh_history()
    
    # Queue management methods
    def remove_from_queue(self):
        """Enhanced remove from queue"""
        selected_items = self.queue_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select items to remove")
            return
        
        # Get the IDs of selected items
        selected_ids = []
        for item in selected_items:
            item_id = int(self.queue_tree.item(item, 'text'))
            selected_ids.append(item_id)
        
        with self.queue_lock:
            # Mark as removed instead of deleting to maintain ID consistency
            for video in self.video_queue:
                if video['id'] in selected_ids:
                    video['status'] = 'Removed'
        
        # Remove from treeview
        for item in selected_items:
            self.queue_tree.delete(item)
        
        self.thread_safe_logger.log(f"Removed {len(selected_items)} item(s) from queue")
        self.update_overall_progress()
        self.update_url_count()
    
    def clear_queue(self):
        """Clear all items from queue"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the entire queue?"):
            with self.queue_lock:
                for video in self.video_queue:
                    video['status'] = 'Removed'
            
            # Clear treeview
            for item in self.queue_tree.get_children():
                self.queue_tree.delete(item)
            
            self.thread_safe_logger.log("Queue cleared")
            self.update_overall_progress()
            self.update_url_count()
    
    def retry_failed_downloads(self):
        """Retry all failed downloads"""
        with self.queue_lock:
            failed_videos = [v for v in self.video_queue if v['status'] == 'Error']
        
        if not failed_videos:
            messagebox.showinfo("Info", "No failed downloads to retry")
            return
        
        for video in failed_videos:
            video['status'] = 'Queued'
            video['progress'] = 0
            video['retry_count'] = getattr(video, 'retry_count', 0)
        
        # Update treeview
        for item in self.queue_tree.get_children():
            item_id = int(self.queue_tree.item(item, 'text'))
            with self.queue_lock:
                video = next((v for v in self.video_queue if v['id'] == item_id), None)
                if video and video['status'] == 'Queued':
                    self.update_video_status(item_id, 'Queued')
        
        self.thread_safe_logger.log(f"Reset {len(failed_videos)} failed download(s) for retry")
        self.update_overall_progress()
    
    def cleanup_completed(self):
        """Clean up completed downloads from queue"""
        with self.queue_lock:
            completed_videos = [v for v in self.video_queue if v['status'] == 'Completed']
        
        if not completed_videos:
            messagebox.showinfo("Info", "No completed downloads to clean up")
            return
        
        # Mark as removed
        for video in completed_videos:
            video['status'] = 'Removed'
        
        # Remove from treeview
        items_to_remove = []
        for item in self.queue_tree.get_children():
            item_id = int(self.queue_tree.item(item, 'text'))
            with self.queue_lock:
                video = next((v for v in self.video_queue if v['id'] == item_id), None)
                if video and video['status'] == 'Removed':
                    items_to_remove.append(item)
        
        for item in items_to_remove:
            self.queue_tree.delete(item)
        
        self.thread_safe_logger.log(f"Cleaned up {len(completed_videos)} completed download(s)")
        self.update_overall_progress()
        self.update_url_count()
    
    def move_queue_item_up(self):
        """Move selected queue item up"""
        selected = self.queue_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        prev_item = self.queue_tree.prev(item)
        
        if prev_item:
            self.queue_tree.move(item, '', self.queue_tree.index(prev_item))
    
    def move_queue_item_down(self):
        """Move selected queue item down"""
        selected = self.queue_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        next_item = self.queue_tree.next(item)
        
        if next_item:
            self.queue_tree.move(item, '', self.queue_tree.index(next_item) + 1)
    
    # Context menu actions
    def move_to_top(self):
        """Move selected item to top of queue"""
        selected = self.queue_tree.selection()
        if selected:
            self.queue_tree.move(selected[0], '', 0)
    
    def move_to_bottom(self):
        """Move selected item to bottom of queue"""
        selected = self.queue_tree.selection()
        if selected:
            self.queue_tree.move(selected[0], '', 'end')
    
    def copy_selected_url(self):
        """Copy selected video URL to clipboard"""
        selected = self.queue_tree.selection()
        if selected:
            item_id = int(self.queue_tree.item(selected[0], 'text'))
            with self.queue_lock:
                video = next((v for v in self.video_queue if v['id'] == item_id), None)
                if video:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(video['url'])
                    self.thread_safe_logger.log("URL copied to clipboard")
    
    def open_in_browser(self):
        """Open selected video URL in browser"""
        selected = self.queue_tree.selection()
        if selected:
            item_id = int(self.queue_tree.item(selected[0], 'text'))
            with self.queue_lock:
                video = next((v for v in self.video_queue if v['id'] == item_id), None)
                if video:
                    import webbrowser
                    webbrowser.open(video['url'])
    
    def retry_selected(self):
        """Retry selected failed downloads"""
        selected = self.queue_tree.selection()
        if not selected:
            return
        
        for item in selected:
            item_id = int(self.queue_tree.item(item, 'text'))
            with self.queue_lock:
                video = next((v for v in self.video_queue if v['id'] == item_id), None)
                if video and video['status'] == 'Error':
                    video['status'] = 'Queued'
                    video['progress'] = 0
                    self.update_video_status(item_id, 'Queued')
        
        self.update_overall_progress()
    
    def show_video_details(self, event):
        """Show detailed video information"""
        item = self.queue_tree.selection()[0] if self.queue_tree.selection() else None
        if not item:
            return
        
        item_id = int(self.queue_tree.item(item, 'text'))
        with self.queue_lock:
            video = next((v for v in self.video_queue if v['id'] == item_id), None)
        
        if not video:
            return
        
        # Create details window
        details_window = tk.Toplevel(self.root)
        details_window.title("Video Details")
        details_window.geometry("500x400")
        details_window.resizable(True, True)
        
        # Video information
        info_frame = ttk.LabelFrame(details_window, text="Video Information", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        details_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, height=15)
        details_text.pack(fill=tk.BOTH, expand=True)
        
        # Format details
        details = f"""Title: {video['title']}
URL: {video['url']}
Duration: {video['duration']}
File Size: {self.format_filesize(video.get('filesize', 0))}
Status: {video['status']}
Progress: {video.get('progress', 0):.1f}%
Retry Count: {video.get('retry_count', 0)}

"""
        
        if video.get('playlist_title'):
            details += f"Playlist: {video['playlist_title']}\n"
            details += f"Playlist Index: {video.get('playlist_index', 'Unknown')}\n\n"
        
        if video.get('error_message'):
            details += f"Error Message:\n{video['error_message']}\n"
        
        details_text.insert(tk.END, details)
        details_text.config(state=tk.DISABLED)
    
    # History management
    def refresh_history(self):
        """Refresh download history display"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Add history items
        for entry in reversed(self.download_history.history[-100:]):  # Show last 100
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            self.history_tree.insert('', 'end', values=(
                timestamp,
                entry['title'][:50] + '...' if len(entry['title']) > 50 else entry['title'],
                entry['status'],
                entry.get('file_path', 'N/A')[:50] + '...' if entry.get('file_path', '') and len(entry.get('file_path', '')) > 50 else entry.get('file_path', 'N/A')
            ))
    
    def clear_history(self):
        """Clear download history"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the download history?"):
            self.download_history.history.clear()
            self.download_history.save_history()
            self.refresh_history()
            self.thread_safe_logger.log("Download history cleared")
    
    def export_history(self):
        """Export download history to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export History"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.download_history.history, f, indent=2, ensure_ascii=False)
                self.thread_safe_logger.log(f"History exported to {filename}")
                messagebox.showinfo("Success", "History exported successfully!")
            except Exception as e:
                self.thread_safe_logger.log(f"Error exporting history: {e}", "ERROR")
                messagebox.showerror("Error", f"Failed to export history: {e}")
    
    # Utility methods
    def browse_download_path(self):
        """Browse for download directory with validation"""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            if os.access(path, os.W_OK):
                self.path_var.set(path)
                self.config["download_path"] = path
                self.save_config()
                self.thread_safe_logger.log(f"Download path changed to: {path}")
                self.update_disk_space_info()
            else:
                messagebox.showerror("Error", "Selected directory is not writable")
    
    def open_download_folder(self):
        """Open download folder in system explorer"""
        path = self.path_var.get()
        if os.path.exists(path):
            try:
                if sys.platform == "win32":
                    subprocess.run(["explorer", path])
                elif sys.platform == "darwin":
                    subprocess.run(["open", path])
                else:
                    subprocess.run(["xdg-open", path])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {e}")
        else:
            messagebox.showerror("Error", "Download path does not exist")
    
    def clear_video_cache(self):
        """Clear video info cache"""
        self.video_cache.clear()
        self.thread_safe_logger.log("Video info cache cleared")
        self.update_cache_info()
        messagebox.showinfo("Success", "Video info cache cleared!")
    
    def clear_thumbnail_cache(self):
        """Clear thumbnail cache"""
        self.thumbnail_cache.clear()
        self.thread_safe_logger.log("Thumbnail cache cleared")
        self.update_cache_info()
        messagebox.showinfo("Success", "Thumbnail cache cleared!")
    
    def update_cache_info(self):
        """Update cache information display"""
        video_cache_size = len(self.video_cache.cache)
        thumbnail_cache_size = len(self.thumbnail_cache)
        self.cache_info_label.config(
            text=f"Video cache: {video_cache_size} items, Thumbnail cache: {thumbnail_cache_size} items"
        )
    
    def clear_log(self):
        """Clear status log"""
        self.status_text.delete(1.0, tk.END)
        self.thread_safe_logger.log("Log cleared")
    
    def save_log(self):
        """Save log to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Log"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.status_text.get(1.0, tk.END))
                messagebox.showinfo("Success", "Log saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log: {e}")
    
    def periodic_cleanup(self):
        """Perform periodic cleanup tasks"""
        # Limit thumbnail cache size
        if len(self.thumbnail_cache) > 100:
            # Remove oldest thumbnails
            items_to_remove = list(self.thumbnail_cache.keys())[:-50]
            for key in items_to_remove:
                del self.thumbnail_cache[key]
        
        # Update cache info
        self.update_cache_info()
        
        # Schedule next cleanup
        self.root.after(300000, self.periodic_cleanup)  # Every 5 minutes
    
    def on_closing(self):
        """Enhanced application closing with cleanup"""
        # Save configuration
        self.save_config()
        
        # Stop any ongoing downloads
        if self.download_state.is_running():
            self.stop_downloads()
        
        # Shutdown executor
        self.executor.shutdown(wait=False)
        
        # Save history
        self.download_history.save_history()
        
        self.root.destroy()

def main():
    """Main application entry point with error handling"""
    try:
        root = tk.Tk()
        
        # Set window icon (if available)
        try:
            # You can add an icon file here
            # root.iconbitmap("icon.ico")
            pass
        except:
            pass
        
        app = YouTubeDownloaderGUI(root)
        
        # Handle window closing
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
        # Load saved window geometry
        if app.config.get("window_geometry"):
            try:
                root.geometry(app.config["window_geometry"])
            except:
                pass
        
        # Start the GUI
        root.mainloop()
        
    except Exception as e:
        # Show error dialog if GUI fails to start
        try:
            import tkinter.messagebox as mb
            mb.showerror("Startup Error", f"Failed to start application:\n{e}")
        except:
            print(f"Critical error: {e}")

if __name__ == "__main__":
    main()