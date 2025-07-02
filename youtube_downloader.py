import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
import json
import sys
from pathlib import Path
import yt_dlp
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime

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
        self.current_download_thread = None
        self.progress_queue = queue.Queue()
        
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
            "window_geometry": "900x700"
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
        
        # Queue Section
        self.setup_queue_section(main_frame, row=3)
        
        # Progress Section
        self.setup_progress_section(main_frame, row=4)
        
        # Control Buttons
        self.setup_control_buttons(main_frame, row=5)
        
        # Status Section
        self.setup_status_section(main_frame, row=6)
        
        # Configure row weights
        main_frame.rowconfigure(3, weight=1)  # Queue section expands
        main_frame.rowconfigure(6, weight=1)  # Status section expands
    
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
    
    def setup_queue_section(self, parent, row):
        """Setup queue display section"""
        queue_frame = ttk.LabelFrame(parent, text="Download Queue", padding="10")
        queue_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)
        
        # Treeview for queue
        columns = ("URL", "Title", "Duration", "Status")
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, show="tree headings", height=8)
        
        # Configure columns
        self.queue_tree.heading("#0", text="ID")
        self.queue_tree.column("#0", width=50, minwidth=50)
        
        for col in columns:
            self.queue_tree.heading(col, text=col)
            if col == "URL":
                self.queue_tree.column(col, width=300, minwidth=200)
            elif col == "Title":
                self.queue_tree.column(col, width=250, minwidth=150)
            elif col == "Duration":
                self.queue_tree.column(col, width=80, minwidth=80)
            else:  # Status
                self.queue_tree.column(col, width=100, minwidth=100)
        
        self.queue_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
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
        self.refresh_button.pack(side=tk.LEFT)
    
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
        self.stop_button.pack(side=tk.LEFT)
    
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
        
        self.status_text.insert(tk.END, formatted_message)
        self.status_text.see(tk.END)
        
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
    
    def validate_url(self, url):
        """Validate YouTube URL"""
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})|'
            r'(https?://)?(www\.)?youtube\.com/playlist\?list=([^&=%\?]+)'
        )
        return youtube_regex.match(url) is not None
    
    def extract_video_info(self, url):
        """Extract video information using yt-dlp"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:  # Playlist
                    videos = []
                    for entry in info['entries']:
                        if entry:  # Some entries might be None
                            videos.append({
                                'url': entry.get('webpage_url', url),
                                'title': entry.get('title', 'Unknown Title'),
                                'duration': self.format_duration(entry.get('duration', 0)),
                                'is_playlist': True
                            })
                    return videos
                else:  # Single video
                    return [{
                        'url': url,
                        'title': info.get('title', 'Unknown Title'),
                        'duration': self.format_duration(info.get('duration', 0)),
                        'is_playlist': False
                    }]
        except Exception as e:
            self.log_message(f"Error extracting info for {url}: {str(e)}", "ERROR")
            return None
    
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
        
        self.log_message(f"Extracting info for: {url}")
        
        # Extract video info in background thread
        def extract_info():
            videos = self.extract_video_info(url)
            if videos:
                self.root.after(0, lambda: self.add_videos_to_queue(videos))
            else:
                self.root.after(0, lambda: self.log_message("Failed to extract video information", "ERROR"))
        
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
                'is_playlist': video.get('is_playlist', False)
            })
            
            # Add to treeview
            self.queue_tree.insert('', 'end', text=str(video_id), 
                                 values=(video['url'][:50] + '...' if len(video['url']) > 50 else video['url'],
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
                    video['url'][:50] + '...' if len(video['url']) > 50 else video['url'],
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
    
    def start_downloads(self):
        """Start downloading queued videos"""
        active_videos = [v for v in self.video_queue if v['status'] == 'Queued']
        
        if not active_videos:
            messagebox.showwarning("Warning", "No videos in queue to download")
            return
        
        if not os.path.exists(self.path_var.get()):
            messagebox.showerror("Error", "Download path does not exist")
            return
        
        self.is_downloading = True
        self.start_button.config(state="disabled")
        self.pause_button.config(state="normal")
        self.stop_button.config(state="normal")
        
        self.log_message(f"Starting download of {len(active_videos)} video(s)")
        
        # Start download thread
        self.current_download_thread = threading.Thread(target=self.download_worker, daemon=True)
        self.current_download_thread.start()
    
    def pause_downloads(self):
        """Pause downloads (placeholder - yt-dlp doesn't support pause)"""
        messagebox.showinfo("Info", "Pause functionality is not available with yt-dlp. Use Stop to cancel downloads.")
    
    def stop_downloads(self):
        """Stop all downloads"""
        self.is_downloading = False
        self.log_message("Stopping downloads...")
        
        # Reset buttons
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        
        # Reset progress
        self.current_progress['value'] = 0
        self.current_percent_label.config(text="0%")
        self.current_file_label.config(text="Downloads stopped")
    
    def download_worker(self):
        """Background worker for downloading videos"""
        active_videos = [v for v in self.video_queue if v['status'] == 'Queued']
        
        for i, video in enumerate(active_videos):
            if not self.is_downloading:
                break
            
            try:
                # Update status
                video['status'] = 'Downloading'
                self.progress_queue.put(('status', video['id'], 'Downloading'))
                self.progress_queue.put(('current_file', f"Downloading: {video['title']}"))
                
                # Configure yt-dlp options
                ydl_opts = {
                    'outtmpl': os.path.join(self.path_var.get(), '%(title)s.%(ext)s'),
                    'format': self.get_format_selector(),
                    'progress_hooks': [lambda d: self.progress_hook(d, video['id'])],
                }
                
                # Add subtitle options if enabled
                if self.subtitle_var.get():
                    ydl_opts.update({
                        'writesubtitles': True,
                        'writeautomaticsub': True,
                        'subtitleslangs': self.config.get('subtitle_langs', ['en']),
                    })
                
                # Download the video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video['url']])
                
                # Update status to completed
                video['status'] = 'Completed'
                self.progress_queue.put(('status', video['id'], 'Completed'))
                self.progress_queue.put(('log', f"Successfully downloaded: {video['title']}", 'SUCCESS'))
                
            except Exception as e:
                video['status'] = 'Error'
                self.progress_queue.put(('status', video['id'], 'Error'))
                self.progress_queue.put(('log', f"Error downloading {video['title']}: {str(e)}", 'ERROR'))
        
        # Download completed
        self.progress_queue.put(('download_complete',))
    
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
            self.progress_queue.put(('current_file', f"Finished downloading: {d['filename']}"))
    
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
        # Save configuration
        self.save_config()
        
        # Stop any ongoing downloads
        if self.is_downloading:
            self.stop_downloads()
        
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