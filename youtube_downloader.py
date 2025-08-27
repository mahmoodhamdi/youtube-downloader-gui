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
import math
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from PIL import Image, ImageTk
import requests
from io import BytesIO

import yt_dlp

class YouTubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader Pro")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Configuration
        self.config_file = "downloader_config.json"
        self.download_queue = queue.Queue()
        self.video_queue = []
        self.is_downloading = False
        self.is_paused = False
        self.current_download_threads = []
        self.progress_queue = queue.Queue()
        self.thread_lock = threading.Lock()
        self.download_history = []
        self.thumbnail_cache = {}
        
        # Load saved configuration
        self.config = self.load_config()
        
        # Initialize GUI
        self.setup_gui()
        self.setup_styles()
        
        # Start progress monitoring
        self.root.after(100, self.check_progress_queue)
        
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            "download_path": str(Path.home() / "Downloads"),
            "quality": "best",
            "include_subtitles": False,
            "subtitle_langs": ["en"],
            "window_geometry": "900x700",
            "max_retries": 3,
            "retry_delay": 5,
            "max_concurrent_downloads": 1,
            "bandwidth_limit": 0,
            "download_history": [],
            "schedule_downloads": False,
            "schedule_time": "00:00",
            "auto_clear_completed": False,
            "thumbnail_size": 100
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
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
        """Save configuration to file"""
        try:
            self.config["window_geometry"] = self.root.geometry()
            self.config["download_path"] = self.path_var.get()
            self.config["quality"] = self.quality_var.get()
            self.config["include_subtitles"] = self.subtitle_var.get()
            self.config["subtitle_langs"] = [lang.strip() for lang in self.subtitle_langs_var.get().split(',') if lang.strip()]
            self.config["max_retries"] = int(self.retries_var.get())
            self.config["retry_delay"] = int(self.retry_delay_var.get())
            self.config["max_concurrent_downloads"] = int(self.concurrent_downloads_var.get())
            self.config["bandwidth_limit"] = int(self.bandwidth_limit_var.get())
            self.config["schedule_downloads"] = self.schedule_var.get()
            self.config["schedule_time"] = self.schedule_time_var.get()
            self.config["auto_clear_completed"] = self.auto_clear_var.get()
            self.config["thumbnail_size"] = int(self.thumbnail_size_var.get())
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def setup_styles(self):
        """Setup custom styles for the application"""
        style = ttk.Style()
        
        # Configure styles
        style.configure("Title.TLabel", font=("Arial", 12, "bold"))
        style.configure("Status.TLabel", font=("Arial", 9))
        style.configure("Success.TLabel", foreground="green")
        style.configure("Error.TLabel", foreground="red")
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))
    
    def setup_gui(self):
        """Setup the main GUI layout"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="YouTube Downloader Pro", style="Title.TLabel")
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # URL Input Section
        self.setup_url_section(main_frame, row=1)
        
        # Settings Section
        self.setup_settings_section(main_frame, row=2)
        
        # Advanced Settings Section
        self.setup_advanced_settings_section(main_frame, row=3)
        
        # Queue Section
        self.setup_queue_section(main_frame, row=4)
        
        # Progress Section
        self.setup_progress_section(main_frame, row=5)
        
        # Control Buttons
        self.setup_control_buttons(main_frame, row=6)
        
        # Status Section
        self.setup_status_section(main_frame, row=7)
        
        # Configure row weights
        main_frame.rowconfigure(4, weight=1)  # Queue section expands
        main_frame.rowconfigure(7, weight=1)  # Status section expands
    
    def setup_url_section(self, parent, row):
        """Setup URL input section"""
        url_frame = ttk.LabelFrame(parent, text="Video URLs", padding="10")
        url_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(1, weight=1)
        
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.url_entry.bind('<Return>', lambda e: self.add_to_queue())
        
        self.add_button = ttk.Button(url_frame, text="Add to Queue", command=self.add_to_queue)
        self.add_button.grid(row=0, column=2, padx=(5, 0))
        
        # Multi-URL text area
        ttk.Label(url_frame, text="Multiple URLs (one per line):").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=(10, 0), padx=(0, 5))
        
        self.multi_url_text = tk.Text(url_frame, height=4, width=50)
        self.multi_url_text.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0), padx=(0, 5))
        
        multi_add_button = ttk.Button(url_frame, text="Add All", command=self.add_multiple_urls)
        multi_add_button.grid(row=1, column=2, sticky=(tk.N), pady=(10, 0), padx=(5, 0))
        
        # Extracting progress label
        self.extracting_label = ttk.Label(url_frame, text="", style="Status.TLabel")
        self.extracting_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
    
    def setup_settings_section(self, parent, row):
        """Setup settings section"""
        settings_frame = ttk.LabelFrame(parent, text="Download Settings", padding="10")
        settings_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        
        # Download path
        ttk.Label(settings_frame, text="Download Path:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.path_var = tk.StringVar(value=self.config["download_path"])
        path_entry = ttk.Entry(settings_frame, textvariable=self.path_var, state="readonly")
        path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        browse_button = ttk.Button(settings_frame, text="Browse", command=self.browse_download_path)
        browse_button.grid(row=0, column=2, padx=(5, 0))
        
        open_folder_button = ttk.Button(settings_frame, text="Open Folder", command=self.open_download_folder)
        open_folder_button.grid(row=0, column=3, padx=(5, 0))
        
        # Quality selection
        ttk.Label(settings_frame, text="Quality:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        
        self.quality_var = tk.StringVar(value=self.config["quality"])
        quality_combo = ttk.Combobox(settings_frame, textvariable=self.quality_var, 
                                   values=["best", "worst", "720p", "480p", "360p", "audio_only"], 
                                   state="readonly", width=15)
        quality_combo.grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        
        # Subtitle options
        self.subtitle_var = tk.BooleanVar(value=self.config["include_subtitles"])
        subtitle_check = ttk.Checkbutton(settings_frame, text="Download Subtitles", 
                                       variable=self.subtitle_var)
        subtitle_check.grid(row=1, column=2, pady=(10, 0), padx=(5, 0))
        
        # Subtitle languages
        ttk.Label(settings_frame, text="Subtitle Languages:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        self.subtitle_langs_var = tk.StringVar(value=",".join(self.config.get('subtitle_langs', ['en'])))
        subtitle_langs_entry = ttk.Entry(settings_frame, textvariable=self.subtitle_langs_var, width=20)
        subtitle_langs_entry.grid(row=2, column=1, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        
        # Auto translate subtitles
        self.translate_subs_var = tk.BooleanVar(value=False)
        translate_check = ttk.Checkbutton(settings_frame, text="Auto Translate to English", 
                                        variable=self.translate_subs_var)
        translate_check.grid(row=2, column=2, pady=(5, 0), padx=(5, 0))
    
    def setup_advanced_settings_section(self, parent, row):
        """Setup advanced settings section"""
        advanced_frame = ttk.LabelFrame(parent, text="Advanced Settings", padding="10")
        advanced_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        advanced_frame.columnconfigure(1, weight=1)
        
        # Retry settings
        ttk.Label(advanced_frame, text="Max Retries:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.retries_var = tk.StringVar(value=str(self.config["max_retries"]))
        retries_spin = ttk.Spinbox(advanced_frame, from_=0, to=10, textvariable=self.retries_var, width=5)
        retries_spin.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        
        ttk.Label(advanced_frame, text="Retry Delay (s):").grid(row=0, column=2, sticky=tk.W, padx=(20, 5))
        self.retry_delay_var = tk.StringVar(value=str(self.config["retry_delay"]))
        retry_delay_spin = ttk.Spinbox(advanced_frame, from_=1, to=60, textvariable=self.retry_delay_var, width=5)
        retry_delay_spin.grid(row=0, column=3, sticky=tk.W, padx=(0, 5))
        
        # Concurrent downloads
        ttk.Label(advanced_frame, text="Concurrent Downloads:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        self.concurrent_downloads_var = tk.StringVar(value=str(self.config["max_concurrent_downloads"]))
        concurrent_spin = ttk.Spinbox(advanced_frame, from_=1, to=5, textvariable=self.concurrent_downloads_var, width=5)
        concurrent_spin.grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        
        # Bandwidth limit
        ttk.Label(advanced_frame, text="Bandwidth Limit (KB/s):").grid(row=1, column=2, sticky=tk.W, pady=(10, 0), padx=(20, 5))
        self.bandwidth_limit_var = tk.StringVar(value=str(self.config["bandwidth_limit"]))
        bandwidth_spin = ttk.Spinbox(advanced_frame, from_=0, to=10000, textvariable=self.bandwidth_limit_var, width=8)
        bandwidth_spin.grid(row=1, column=3, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        
        # Schedule downloads
        self.schedule_var = tk.BooleanVar(value=self.config["schedule_downloads"])
        schedule_check = ttk.Checkbutton(advanced_frame, text="Schedule Downloads", 
                                       variable=self.schedule_var, command=self.toggle_schedule)
        schedule_check.grid(row=2, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        
        self.schedule_time_var = tk.StringVar(value=self.config["schedule_time"])
        schedule_time_entry = ttk.Entry(advanced_frame, textvariable=self.schedule_time_var, width=8, state="disabled")
        schedule_time_entry.grid(row=2, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        self.schedule_time_entry = schedule_time_entry
        
        # Auto clear completed
        self.auto_clear_var = tk.BooleanVar(value=self.config["auto_clear_completed"])
        auto_clear_check = ttk.Checkbutton(advanced_frame, text="Auto Clear Completed", 
                                         variable=self.auto_clear_var)
        auto_clear_check.grid(row=2, column=2, pady=(10, 0), padx=(20, 5))
        
        # Thumbnail size
        ttk.Label(advanced_frame, text="Thumbnail Size:").grid(row=3, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        self.thumbnail_size_var = tk.StringVar(value=str(self.config["thumbnail_size"]))
        thumbnail_spin = ttk.Spinbox(advanced_frame, from_=50, to=200, textvariable=self.thumbnail_size_var, width=5)
        thumbnail_spin.grid(row=3, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 5))
    
    def toggle_schedule(self):
        """Enable/disable schedule time entry based on checkbox"""
        if self.schedule_var.get():
            self.schedule_time_entry.config(state="normal")
        else:
            self.schedule_time_entry.config(state="disabled")
    
    def setup_queue_section(self, parent, row):
        """Setup queue display section"""
        queue_frame = ttk.LabelFrame(parent, text="Download Queue", padding="10")
        queue_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)
        
        # Treeview for queue
        columns = ("Thumbnail", "Title", "Duration", "Status")
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, show="tree headings", height=8)
        
        # Configure columns
        self.queue_tree.heading("#0", text="ID")
        self.queue_tree.column("#0", width=50, minwidth=50)
        
        for col in columns:
            self.queue_tree.heading(col, text=col)
            if col == "Thumbnail":
                self.queue_tree.column(col, width=self.config["thumbnail_size"], minwidth=50)
            elif col == "Title":
                self.queue_tree.column(col, width=250, minwidth=150)
            elif col == "Duration":
                self.queue_tree.column(col, width=80, minwidth=80)
            else:  # Status
                self.queue_tree.column(col, width=100, minwidth=100)
        
        self.queue_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Enable drag and drop for reordering
        self.queue_tree.bind("<ButtonPress-1>", self.on_treeview_drag_start)
        self.queue_tree.bind("<B1-Motion>", self.on_treeview_drag_motion)
        self.queue_tree.bind("<ButtonRelease-1>", self.on_treeview_drag_end)
        
        # Scrollbar for treeview
        queue_scrollbar = ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        queue_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.queue_tree.configure(yscrollcommand=queue_scrollbar.set)
        
        # Queue control buttons
        queue_button_frame = ttk.Frame(queue_frame)
        queue_button_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        self.remove_button = ttk.Button(queue_button_frame, text="Remove Selected", 
                                      command=self.remove_from_queue)
        self.remove_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_button = ttk.Button(queue_button_frame, text="Clear Queue", 
                                     command=self.clear_queue)
        self.clear_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.refresh_button = ttk.Button(queue_button_frame, text="Refresh Info", 
                                       command=self.refresh_queue_info)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_completed_button = ttk.Button(queue_button_frame, text="Clear Completed", 
                                               command=self.clear_completed)
        self.clear_completed_button.pack(side=tk.LEFT)
    
    def on_treeview_drag_start(self, event):
        """Handle treeview drag start"""
        item = self.queue_tree.identify_row(event.y)
        if item:
            self.drag_data = {"item": item, "index": self.queue_tree.index(item)}
    
    def on_treeview_drag_motion(self, event):
        """Handle treeview drag motion"""
        pass  # Visual feedback can be added here
    
    def on_treeview_drag_end(self, event):
        """Handle treeview drag end - reorder items"""
        if hasattr(self, 'drag_data'):
            item = self.queue_tree.identify_row(event.y)
            if item and item != self.drag_data["item"]:
                new_index = self.queue_tree.index(item)
                
                # Reorder video queue
                with self.thread_lock:
                    video_id = int(self.queue_tree.item(self.drag_data["item"], 'text'))
                    video = next((v for v in self.video_queue if v['id'] == video_id), None)
                    
                    if video:
                        self.video_queue.remove(video)
                        if new_index < len(self.video_queue):
                            self.video_queue.insert(new_index, video)
                        else:
                            self.video_queue.append(video)
                
                # Reorder treeview
                self.refresh_queue_display()
            
            del self.drag_data
    
    def refresh_queue_display(self):
        """Refresh the entire queue display"""
        # Clear treeview
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        # Repopulate with current video queue
        for video in self.video_queue:
            if video['status'] != 'Removed':
                self.queue_tree.insert('', 'end', text=str(video['id']), 
                                     values=(video.get('thumbnail', ''),
                                            video['title'][:40] + '...' if len(video['title']) > 40 else video['title'],
                                            video['duration'],
                                            video['status']))
    
    def setup_progress_section(self, parent, row):
        """Setup progress display section"""
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
        
        # Current file info
        self.current_file_label = ttk.Label(progress_frame, text="Ready to download...", style="Status.TLabel")
        self.current_file_label.grid(row=2, column=0, columnspan=3, pady=(5, 0), sticky=tk.W)
        
        # Active downloads count
        self.active_downloads_label = ttk.Label(progress_frame, text="Active downloads: 0", style="Status.TLabel")
        self.active_downloads_label.grid(row=3, column=0, columnspan=3, pady=(5, 0), sticky=tk.W)
    
    def setup_control_buttons(self, parent, row):
        """Setup control buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="Start Downloads", 
                                     command=self.start_downloads, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.pause_button = ttk.Button(button_frame, text="Pause", 
                                     command=self.pause_downloads, state="disabled")
        self.pause_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="Stop", 
                                    command=self.stop_downloads, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.schedule_button = ttk.Button(button_frame, text="Schedule", 
                                        command=self.schedule_downloads, state="normal")
        self.schedule_button.pack(side=tk.LEFT, padx=(5, 0))
    
    def setup_status_section(self, parent, row):
        """Setup status/log section"""
        status_frame = ttk.LabelFrame(parent, text="Status Log", padding="10")
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=8, wrap=tk.WORD)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add initial message
        self.log_message("YouTube Downloader Pro initialized. Ready to download videos!")
    
    def log_message(self, message, level="INFO"):
        """Add message to status log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        # Thread-safe logging
        def update_log():
            self.status_text.insert(tk.END, formatted_message)
            self.status_text.see(tk.END)
        
        self.root.after(0, update_log)
        
        # Also print to console for debugging
        print(formatted_message.strip())
    
    def browse_download_path(self):
        """Browse for download directory"""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)
            self.config["download_path"] = path
            self.save_config()
            self.log_message(f"Download path changed to: {path}")
    
    def open_download_folder(self):
        """Open the download folder in the system's file explorer"""
        path = self.path_var.get()
        if os.path.exists(path):
            if sys.platform == "win32":
                subprocess.run(["explorer", path])
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            messagebox.showerror("Error", "Download path does not exist")
    
    def validate_url(self, url):
        """Validate YouTube URL"""
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})|'
            r'(https?://)?(www\.)?youtube\.com/playlist\?list=([^&=%\?]+)'
        )
        return youtube_regex.match(url) is not None
    
    def extract_video_info(self, url):
        """Extract video information using yt-dlp with error handling"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'socket_timeout': 30,
                    'extractor_args': {'youtube': {'skip': ['dash', 'hls']}},
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    if 'entries' in info:  # Playlist
                        playlist_title = info.get('title', 'Untitled Playlist')
                        videos = []
                        for entry in info['entries']:
                            if entry:  # Some entries might be None
                                # Get thumbnail
                                thumbnail_url = entry.get('thumbnail')
                                thumbnail = self.get_video_thumbnail(thumbnail_url) if thumbnail_url else ''
                                
                                videos.append({
                                    'url': entry.get('webpage_url', url),
                                    'title': entry.get('title', 'Unknown Title'),
                                    'duration': self.format_duration(entry.get('duration', 0)),
                                    'playlist_title': playlist_title,
                                    'playlist_index': entry.get('playlist_index', 0),
                                    'thumbnail': thumbnail
                                })
                        return videos
                    else:  # Single video
                        # Get thumbnail
                        thumbnail_url = info.get('thumbnail')
                        thumbnail = self.get_video_thumbnail(thumbnail_url) if thumbnail_url else ''
                        
                        return [{
                            'url': url,
                            'title': info.get('title', 'Unknown Title'),
                            'duration': self.format_duration(info.get('duration', 0)),
                            'playlist_title': None,
                            'playlist_index': None,
                            'thumbnail': thumbnail
                        }]
            
            except Exception as e:
                if attempt < max_retries - 1:
                    self.log_message(f"Attempt {attempt + 1} failed for {url}. Retrying in {retry_delay} seconds...", "WARNING")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    self.log_message(f"Error extracting info for {url}: {str(e)}", "ERROR")
                    return None
    
    def get_video_thumbnail(self, thumbnail_url):
        """Download and resize video thumbnail"""
        if not thumbnail_url:
            return ""
        
        # Check cache first
        if thumbnail_url in self.thumbnail_cache:
            return self.thumbnail_cache[thumbnail_url]
        
        try:
            response = requests.get(thumbnail_url, timeout=10)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                thumbnail_size = self.config.get("thumbnail_size", 100)
                image.thumbnail((thumbnail_size, thumbnail_size), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage for tkinter
                photo = ImageTk.PhotoImage(image)
                
                # Store in cache
                self.thumbnail_cache[thumbnail_url] = photo
                return photo
        except Exception as e:
            self.log_message(f"Error loading thumbnail: {str(e)}", "WARNING")
        
        return ""
    
    def format_duration(self, seconds):
        """Format duration in seconds to MM:SS or HH:MM:SS"""
        if not seconds:
            return "Unknown"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def add_to_queue(self):
        """Add URL to download queue"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL")
            return
        
        if not self.validate_url(url):
            messagebox.showerror("Error", "Invalid YouTube URL")
            return
        
        self.extracting_label.config(text="Extracting video info...")
        self.log_message(f"Extracting info for: {url}")
        
        # Extract video info in background thread
        def extract_info():
            videos = self.extract_video_info(url)
            if videos:
                self.root.after(0, lambda: self.add_videos_to_queue(videos))
            else:
                self.root.after(0, lambda: self.log_message("Failed to extract video information", "ERROR"))
            self.root.after(0, lambda: self.extracting_label.config(text=""))
        
        threading.Thread(target=extract_info, daemon=True).start()
        self.url_var.set("")  # Clear the entry
    
    def add_multiple_urls(self):
        """Add multiple URLs from text area"""
        urls_text = self.multi_url_text.get(1.0, tk.END).strip()
        if not urls_text:
            messagebox.showwarning("Warning", "Please enter URLs")
            return
        
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        valid_urls = []
        
        for url in urls:
            if self.validate_url(url):
                valid_urls.append(url)
            else:
                self.log_message(f"Skipping invalid URL: {url}", "WARNING")
        
        if not valid_urls:
            messagebox.showerror("Error", "No valid YouTube URLs found")
            return
        
        self.extracting_label.config(text="Extracting info for multiple URLs...")
        self.log_message(f"Processing {len(valid_urls)} URLs...")
        
        # Extract info for all URLs
        def extract_all_info():
            all_videos = []
            for url in valid_urls:
                videos = self.extract_video_info(url)
                if videos:
                    all_videos.extend(videos)
            
            if all_videos:
                self.root.after(0, lambda: self.add_videos_to_queue(all_videos))
            self.root.after(0, lambda: self.extracting_label.config(text=""))
        
        threading.Thread(target=extract_all_info, daemon=True).start()
        self.multi_url_text.delete(1.0, tk.END)  # Clear the text area
    
    def add_videos_to_queue(self, videos):
        """Add videos to the queue display"""
        for video in videos:
            video_id = len(self.video_queue)
            self.video_queue.append({
                'id': video_id,
                'url': video['url'],
                'title': video['title'],
                'duration': video['duration'],
                'status': 'Queued',
                'playlist_title': video.get('playlist_title'),
                'playlist_index': video.get('playlist_index'),
                'thumbnail': video.get('thumbnail', ''),
                'retry_count': 0
            })
            
            # Add to treeview
            self.queue_tree.insert('', 'end', text=str(video_id), 
                                 values=(video.get('thumbnail', ''),
                                        video['title'][:40] + '...' if len(video['title']) > 40 else video['title'],
                                        video['duration'],
                                        'Queued'))
        
        self.log_message(f"Added {len(videos)} video(s) to queue")
        self.update_overall_progress()
    
    def remove_from_queue(self):
        """Remove selected items from queue"""
        selected_items = self.queue_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select items to remove")
            return
        
        # Get the IDs of selected items
        selected_ids = []
        for item in selected_items:
            item_id = int(self.queue_tree.item(item, 'text'))
            selected_ids.append(item_id)
        
        # Remove from video_queue (mark as removed)
        for video in self.video_queue:
            if video['id'] in selected_ids:
                video['status'] = 'Removed'
        
        # Remove from treeview
        for item in selected_items:
            self.queue_tree.delete(item)
        
        self.log_message(f"Removed {len(selected_items)} item(s) from queue")
        self.update_overall_progress()
    
    def clear_queue(self):
        """Clear all items from queue"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the entire queue?"):
            self.video_queue.clear()
            for item in self.queue_tree.get_children():
                self.queue_tree.delete(item)
            self.log_message("Queue cleared")
            self.update_overall_progress()
    
    def clear_completed(self):
        """Clear completed items from queue"""
        # Remove completed videos from video_queue
        self.video_queue = [v for v in self.video_queue if v['status'] != 'Completed']
        
        # Refresh treeview
        self.refresh_queue_display()
        self.log_message("Completed items cleared from queue")
        self.update_overall_progress()
    
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
    
    def update_queue_item(self, index, video):
        """Update a specific queue item in the treeview"""
        for item in self.queue_tree.get_children():
            if int(self.queue_tree.item(item, 'text')) == video['id']:
                self.queue_tree.item(item, values=(
                    video.get('thumbnail', ''),
                    video['title'][:40] + '...' if len(video['title']) > 40 else video['title'],
                    video['duration'],
                    video['status']
                ))
                break
    
    def update_overall_progress(self):
        """Update overall progress bar"""
        if not self.video_queue:
            self.overall_progress['value'] = 0
            self.overall_percent_label.config(text="0%")
            return
        
        active_videos = [v for v in self.video_queue if v['status'] != 'Removed']
        if not active_videos:
            self.overall_progress['value'] = 0
            self.overall_percent_label.config(text="0%")
            return
        
        completed = len([v for v in active_videos if v['status'] == 'Completed'])
        total = len(active_videos)
        
        progress_percent = (completed / total) * 100 if total > 0 else 0
        self.overall_progress['value'] = progress_percent
        self.overall_percent_label.config(text=f"{progress_percent:.1f}%")
    
    def check_disk_space(self, required_bytes=100*1024*1024):  # Default 100MB
        """Check if there's enough disk space for downloads"""
        try:
            download_path = self.path_var.get()
            stat = os.statvfs(download_path)
            free_space = stat.f_frsize * stat.f_bavail  # Bytes available
            return free_space >= required_bytes
        except Exception as e:
            self.log_message(f"Error checking disk space: {str(e)}", "ERROR")
            return False
    
    def check_write_permission(self):
        """Check if we have write permission to the download directory"""
        try:
            test_file = os.path.join(self.path_var.get(), 'write_test.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True
        except Exception as e:
            self.log_message(f"No write permission to download directory: {str(e)}", "ERROR")
            return False
    
    def start_downloads(self):
        """Start downloading queued videos"""
        active_videos = [v for v in self.video_queue if v['status'] == 'Queued']
        
        if not active_videos:
            messagebox.showwarning("Warning", "No videos in queue to download")
            return
        
        if not os.path.exists(self.path_var.get()):
            messagebox.showerror("Error", "Download path does not exist")
            return
        
        if not self.check_write_permission():
            messagebox.showerror("Error", "No write permission to download directory")
            return
        
        if not self.check_disk_space():
            messagebox.showwarning("Warning", "Low disk space in download directory")
        
        self.is_downloading = True
        self.is_paused = False
        self.start_button.config(state="disabled")
        self.pause_button.config(state="normal")
        self.stop_button.config(state="normal")
        self.schedule_button.config(state="disabled")
        
        self.log_message(f"Starting download of {len(active_videos)} video(s)")
        
        # Start download threads based on concurrent download setting
        max_concurrent = int(self.concurrent_downloads_var.get())
        active_videos = active_videos[:max_concurrent]  # Only start with max concurrent
        
        for video in active_videos:
            thread = threading.Thread(target=self.download_worker, args=(video,), daemon=True)
            thread.start()
            self.current_download_threads.append(thread)
        
        self.update_active_downloads_count()
    
    def pause_downloads(self):
        """Pause downloads"""
        if self.is_paused:
            self.is_paused = False
            self.pause_button.config(text="Pause")
            self.log_message("Downloads resumed")
            
            # Resume any queued videos
            active_videos = [v for v in self.video_queue if v['status'] == 'Queued']
            max_concurrent = int(self.concurrent_downloads_var.get())
            current_active = len([v for v in self.video_queue if v['status'] == 'Downloading'])
            
            # Start new threads if we have capacity
            if current_active < max_concurrent and active_videos:
                videos_to_start = active_videos[:max_concurrent - current_active]
                for video in videos_to_start:
                    thread = threading.Thread(target=self.download_worker, args=(video,), daemon=True)
                    thread.start()
                    self.current_download_threads.append(thread)
        else:
            self.is_paused = True
            self.pause_button.config(text="Resume")
            self.log_message("Downloads paused")
    
    def stop_downloads(self):
        """Stop all downloads"""
        self.is_downloading = False
        self.is_paused = False
        self.log_message("Stopping downloads...")
        
        # Reset buttons
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.schedule_button.config(state="normal")
        
        # Reset progress
        self.current_progress['value'] = 0
        self.current_percent_label.config(text="0%")
        self.current_file_label.config(text="Downloads stopped")
        self.update_active_downloads_count()
    
    def schedule_downloads(self):
        """Schedule downloads for a later time"""
        if not self.schedule_var.get():
            messagebox.showwarning("Warning", "Please enable schedule downloads first")
            return
        
        try:
            schedule_time = datetime.strptime(self.schedule_time_var.get(), "%H:%M")
            now = datetime.now()
            scheduled_dt = datetime(now.year, now.month, now.day, schedule_time.hour, schedule_time.minute)
            
            # If the scheduled time is already past today, schedule for tomorrow
            if scheduled_dt < now:
                scheduled_dt += timedelta(days=1)
            
            delay_seconds = (scheduled_dt - now).total_seconds()
            
            self.log_message(f"Downloads scheduled for {scheduled_dt.strftime('%Y-%m-%d %H:%M')}")
            self.start_button.config(state="disabled")
            self.schedule_button.config(state="disabled")
            
            # Schedule the download
            self.root.after(int(delay_seconds * 1000), self.start_downloads)
            
        except ValueError:
            messagebox.showerror("Error", "Invalid time format. Please use HH:MM")
    
    def sanitize_filename(self, name):
        """Sanitize filename by removing invalid characters"""
        return re.sub(r'[^\w\-_\. ]', '_', name)
    
    def download_worker(self, video):
        """Background worker for downloading videos"""
        max_retries = int(self.retries_var.get())
        retry_delay = int(self.retry_delay_var.get())
        
        while video['retry_count'] <= max_retries and self.is_downloading:
            if self.is_paused:
                time.sleep(1)  # Check every second if still paused
                continue
            
            try:
                # Update status
                with self.thread_lock:
                    video['status'] = 'Downloading'
                self.progress_queue.put(('status', video['id'], 'Downloading'))
                self.progress_queue.put(('current_file', f"Downloading: {video['title']}"))
                
                # Configure output template based on playlist
                if video.get('playlist_title'):
                    playlist_folder = self.sanitize_filename(video['playlist_title'])
                    download_dir = os.path.join(self.path_var.get(), playlist_folder)
                    os.makedirs(download_dir, exist_ok=True)
                    if video.get('playlist_index') is not None:
                        outtmpl = os.path.join(download_dir, f"{video['playlist_index']:03d} - %(title)s.%(ext)s")
                    else:
                        outtmpl = os.path.join(download_dir, '%(title)s.%(ext)s')
                else:
                    outtmpl = os.path.join(self.path_var.get(), '%(title)s.%(ext)s')
                
                # Configure yt-dlp options
                ydl_opts = {
                    'outtmpl': outtmpl,
                    'format': self.get_format_selector(),
                    'progress_hooks': [lambda d: self.progress_hook(d, video['id'])],
                    'retries': max_retries,
                    'fragment_retries': max_retries,
                    'file_access_retries': max_retries,
                    'continuedl': True,  # Enable resuming interrupted downloads
                }
                
                # Add bandwidth limit if set
                bandwidth_limit = int(self.bandwidth_limit_var.get())
                if bandwidth_limit > 0:
                    ydl_opts['ratelimit'] = bandwidth_limit * 1024  # Convert KB/s to bytes/s
                
                # Add subtitle options if enabled
                if self.subtitle_var.get():
                    ydl_opts.update({
                        'writesubtitles': True,
                        'writeautomaticsub': True,
                        'subtitleslangs': self.config.get('subtitle_langs', ['en']),
                    })
                    
                    # Add subtitle translation if enabled
                    if self.translate_subs_var.get():
                        ydl_opts['subtitlesformat'] = 'srt'
                        ydl_opts['convert-subs'] = 'srt'
                
                # Download the video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video['url']])
                
                # Update status to completed
                with self.thread_lock:
                    video['status'] = 'Completed'
                
                # Add to download history
                self.download_history.append({
                    'url': video['url'],
                    'title': video['title'],
                    'date': datetime.now().isoformat(),
                    'path': self.path_var.get()
                })
                
                self.progress_queue.put(('status', video['id'], 'Completed'))
                self.progress_queue.put(('log', f"Successfully downloaded: {video['title']}", 'SUCCESS'))
                
                # Check if we should auto-clear completed downloads
                if self.auto_clear_var.get():
                    self.root.after(0, self.clear_completed)
                
                break  # Exit retry loop on success
                
            except Exception as e:
                video['retry_count'] += 1
                
                if video['retry_count'] <= max_retries:
                    self.progress_queue.put(('log', f"Retry {video['retry_count']}/{max_retries} for {video['title']} in {retry_delay}s", 'WARNING'))
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    with self.thread_lock:
                        video['status'] = 'Error'
                    self.progress_queue.put(('status', video['id'], 'Error'))
                    self.progress_queue.put(('log', f"Error downloading {video['title']}: {str(e)}", 'ERROR'))
                    break
        
        # Start next download if there are more queued videos
        if self.is_downloading and not self.is_paused:
            self.start_next_download()
        
        # Update active downloads count
        self.update_active_downloads_count()
    
    def start_next_download(self):
        """Start the next queued download if there's capacity"""
        with self.thread_lock:
            active_downloads = len([v for v in self.video_queue if v['status'] == 'Downloading'])
            max_concurrent = int(self.concurrent_downloads_var.get())
            
            if active_downloads < max_concurrent:
                queued_videos = [v for v in self.video_queue if v['status'] == 'Queued']
                if queued_videos:
                    next_video = queued_videos[0]
                    thread = threading.Thread(target=self.download_worker, args=(next_video,), daemon=True)
                    thread.start()
                    self.current_download_threads.append(thread)
    
    def update_active_downloads_count(self):
        """Update the active downloads count label"""
        with self.thread_lock:
            active_count = len([v for v in self.video_queue if v['status'] == 'Downloading'])
        
        def update_label():
            self.active_downloads_label.config(text=f"Active downloads: {active_count}")
        
        self.root.after(0, update_label)
    
    def get_format_selector(self):
        """Get format selector based on quality setting"""
        quality = self.quality_var.get()
        
        format_map = {
            'best': 'best[ext=mp4]/best',
            'worst': 'worst[ext=mp4]/worst',
            '720p': 'best[height<=720][ext=mp4]/best[height<=720]',
            '480p': 'best[height<=480][ext=mp4]/best[height<=480]',
            '360p': 'best[height<=360][ext=mp4]/best[height<=360]',
            'audio_only': 'bestaudio[ext=m4a]/bestaudio'
        }
        
        return format_map.get(quality, 'best[ext=mp4]/best')
    
    def progress_hook(self, d, video_id):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            if 'total_bytes' in d or 'total_bytes_estimate' in d:
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                
                if total and total > 0:
                    percent = (downloaded / total) * 100
                    self.progress_queue.put(('progress', percent))
                    
                    # Update speed and ETA info
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)
                    
                    speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else "Unknown"
                    eta_str = f"{eta}s" if eta else "Unknown"
                    
                    self.progress_queue.put(('current_file', 
                        f"Downloading: {percent:.1f}% - Speed: {speed_str} - ETA: {eta_str}"))
        
        elif d['status'] == 'finished':
            self.progress_queue.put(('progress', 100))
            self.progress_queue.put(('current_file', f"Finished downloading: {os.path.basename(d['filename'])}"))
    
    def check_progress_queue(self):
        """Check for progress updates from download thread"""
        try:
            while True:
                item = self.progress_queue.get_nowait()
                
                if item[0] == 'progress':
                    # Update current progress bar
                    self.current_progress['value'] = item[1]
                    self.current_percent_label.config(text=f"{item[1]:.1f}%")
                
                elif item[0] == 'status':
                    # Update video status in queue
                    video_id, status = item[1], item[2]
                    self.update_video_status(video_id, status)
                    self.update_overall_progress()
                
                elif item[0] == 'current_file':
                    # Update current file label
                    self.current_file_label.config(text=item[1])
                
                elif item[0] == 'log':
                    # Add log message
                    message, level = item[1], item[2] if len(item) > 2 else 'INFO'
                    self.log_message(message, level)
                
                elif item[0] == 'download_complete':
                    # Downloads finished
                    self.download_complete()
                
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.check_progress_queue)
    
    def update_video_status(self, video_id, status):
        """Update video status in treeview"""
        for item in self.queue_tree.get_children():
            if int(self.queue_tree.item(item, 'text')) == video_id:
                current_values = list(self.queue_tree.item(item, 'values'))
                current_values[3] = status  # Status is the 4th column (index 3)
                self.queue_tree.item(item, values=current_values)
                break
    
    def download_complete(self):
        """Handle download completion"""
        self.is_downloading = False
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.schedule_button.config(state="normal")
        
        self.current_progress['value'] = 0
        self.current_percent_label.config(text="0%")
        self.current_file_label.config(text="All downloads completed!")
        
        self.log_message("All downloads completed!", "SUCCESS")
        
        # Show completion message
        completed_count = len([v for v in self.video_queue if v['status'] == 'Completed'])
        messagebox.showinfo("Downloads Complete", 
                          f"Successfully downloaded {completed_count} video(s)!")
    
    def on_closing(self):
        """Handle application closing"""
        # Save configuration and download history
        self.config["download_history"] = self.download_history[-100:]  # Keep last 100 entries
        self.save_config()
        
        # Stop any ongoing downloads
        if self.is_downloading:
            self.stop_downloads()
        
        # Clean up threads
        for thread in self.current_download_threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
        
        self.root.destroy()

def main():
    """Main application entry point"""
    root = tk.Tk()
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

if __name__ == "__main__":
    main()