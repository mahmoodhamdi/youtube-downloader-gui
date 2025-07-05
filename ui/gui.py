import os
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import subprocess
import sys
import re
from typing import List, Dict, Any
from core.config import Config
from core.logger import Logger
from core.downloader import DownloadManager

class YouTubeDownloaderGUI:
    """GUI for the YouTube Downloader application."""
    
    def __init__(self, root: tk.Tk):
        """
        Initialize the GUI with a Tkinter root window.

        Args:
            root (tk.Tk): Tkinter root window.
        """
        self.root = root
        self.root.title("YouTube Downloader Pro")
        self.root.minsize(800, 600)
        
        self.config = Config("downloader_config.json")
        self.status_text = scrolledtext.ScrolledText(self.root, height=8, wrap=tk.WORD)  # Temporary, set in setup_gui
        self.logger = Logger(self.status_text)
        self.download_manager = DownloadManager(self.config, self.logger)
        self.video_queue: List[Dict[str, Any]] = []  # GUI display queue
        
        self.setup_gui()
        self.setup_styles()
        self.root.after(100, self.check_progress_queue)
        self.logger.log(message="YouTube Downloader Pro initialized. Ready to download videos!")  # Fixed: Added 'message='

    def setup_styles(self) -> None:
        """Setup custom styles for the application."""
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Arial", 12, "bold"))
        style.configure("Status.TLabel", font=("Arial", 9))
        style.configure("Success.TLabel", foreground="green")
        style.configure("Error.TLabel", foreground="red")

    def setup_gui(self) -> None:
        """Setup the main GUI layout."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        ttk.Label(main_frame, text="YouTube Downloader Pro", style="Title.TLabel").grid(row=0, column=0, columnspan=3, pady=(0, 20))
        self.setup_url_section(main_frame, 1)
        self.setup_settings_section(main_frame, 2)
        self.setup_queue_section(main_frame, 3)
        self.setup_progress_section(main_frame, 4)
        self.setup_control_buttons(main_frame, 5)
        self.setup_status_section(main_frame, 6)
        
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(6, weight=1)

    def setup_url_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup URL input section."""
        url_frame = ttk.LabelFrame(parent, text="Video URLs", padding="10")
        url_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(1, weight=1)
        
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.url_entry.bind('<Return>', lambda e: self.add_to_queue())
        ttk.Button(url_frame, text="Add to Queue", command=self.add_to_queue).grid(row=0, column=2, padx=(5, 0))
        
        ttk.Label(url_frame, text="Multiple URLs (one per line):").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=(10, 0), padx=(0, 5))
        self.multi_url_text = tk.Text(url_frame, height=4, width=50)
        self.multi_url_text.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0), padx=(0, 5))
        ttk.Button(url_frame, text="Add All", command=self.add_multiple_urls).grid(row=1, column=2, sticky=tk.N, pady=(10, 0), padx=(5, 0))
        
        self.extracting_label = ttk.Label(url_frame, text="", style="Status.TLabel")
        self.extracting_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

    def setup_settings_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup download settings section."""
        settings_frame = ttk.LabelFrame(parent, text="Download Settings", padding="10")
        settings_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        
        ttk.Label(settings_frame, text="Download Path:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.path_var = tk.StringVar(value=self.config.get("download_path"))
        ttk.Entry(settings_frame, textvariable=self.path_var, state="readonly").grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(settings_frame, text="Browse", command=self.browse_download_path).grid(row=0, column=2, padx=(5, 0))
        ttk.Button(settings_frame, text="Open Folder", command=self.open_download_folder).grid(row=0, column=3, padx=(5, 0))
        
        ttk.Label(settings_frame, text="Quality:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        self.quality_var = tk.StringVar(value=self.config.get("quality"))
        ttk.Combobox(settings_frame, textvariable=self.quality_var, values=["best", "worst", "720p", "480p", "360p", "audio_only"], 
                     state="readonly", width=15).grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        
        self.subtitle_var = tk.BooleanVar(value=self.config.get("include_subtitles"))
        ttk.Checkbutton(settings_frame, text="Download Subtitles", variable=self.subtitle_var).grid(row=1, column=2, pady=(10, 0), padx=(5, 0))
        
        ttk.Label(settings_frame, text="Subtitle Languages:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        self.subtitle_langs_var = tk.StringVar(value=",".join(self.config.get('subtitle_langs', ['en'])))
        ttk.Entry(settings_frame, textvariable=self.subtitle_langs_var, width=20).grid(row=2, column=1, sticky=tk.W, pady=(5, 0), padx=(0, 5))

    def setup_queue_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup download queue display section."""
        queue_frame = ttk.LabelFrame(parent, text="Download Queue", padding="10")
        queue_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)
        
        columns = ("URL", "Title", "Duration", "Status")
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, show="tree headings", height=8)
        self.queue_tree.heading("#0", text="ID")
        self.queue_tree.column("#0", width=50, minwidth=50)
        for col in columns:
            self.queue_tree.heading(col, text=col)
            self.queue_tree.column(col, width=300 if col == "URL" else 250 if col == "Title" else 80 if col == "Duration" else 100, minwidth=100)
        self.queue_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview).grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.queue_tree.configure(yscrollcommand=lambda f, l: None)  # Placeholder to avoid warnings
        
        queue_button_frame = ttk.Frame(queue_frame)
        queue_button_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(queue_button_frame, text="Remove Selected", command=self.remove_from_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_button_frame, text="Clear Queue", command=self.clear_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_button_frame, text="Refresh Info", command=self.refresh_queue_info).pack(side=tk.LEFT)

    def setup_progress_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup download progress display section."""
        progress_frame = ttk.LabelFrame(parent, text="Download Progress", padding="10")
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        
        ttk.Label(progress_frame, text="Current:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.current_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.current_progress.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.current_percent_label = ttk.Label(progress_frame, text="0%")
        self.current_percent_label.grid(row=0, column=2, padx=(5, 0))
        
        ttk.Label(progress_frame, text="Overall:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        self.overall_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.overall_progress.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(5, 0), padx=(0, 5))
        self.overall_percent_label = ttk.Label(progress_frame, text="0%")
        self.overall_percent_label.grid(row=1, column=2, pady=(5, 0), padx=(5, 0))
        
        self.current_file_label = ttk.Label(progress_frame, text="Ready to download...", style="Status.TLabel")
        self.current_file_label.grid(row=2, column=0, columnspan=3, pady=(5, 0), sticky=tk.W)

    def setup_control_buttons(self, parent: ttk.Frame, row: int) -> None:
        """Setup control buttons for starting/stopping downloads."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="Start Downloads", command=self.start_downloads, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        self.pause_button = ttk.Button(button_frame, text="Pause", command=self.pause_downloads, state="disabled")
        self.pause_button.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_downloads, state="disabled")
        self.stop_button.pack(side=tk.LEFT)

    def setup_status_section(self, parent: ttk.Frame, row: int) -> None:
        """Setup status log section."""
        status_frame = ttk.LabelFrame(parent, text="Status Log", padding="10")
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=8, wrap=tk.WORD)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def browse_download_path(self) -> None:
        """Browse and set the download directory."""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)
            self.config.set("download_path", path)
            self.config.save_config()
            self.logger.log(message=f"Download path changed to: {path}")

    def open_download_folder(self) -> None:
        """Open the download folder in the system file explorer."""
        path = self.path_var.get()
        if os.path.exists(path):
            subprocess.run(["explorer" if sys.platform == "win32" else "open" if sys.platform == "darwin" else "xdg-open", path])
        else:
            messagebox.showerror("Error", "Download path does not exist")

    def validate_url(self, url: str) -> bool:
        """
        Validate if a URL is a valid YouTube URL.

        Args:
            url (str): URL to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})|'
            r'(https?://)?(www\.)?youtube\.com/playlist\?list=([^&=%\?]+)'
        )
        return bool(youtube_regex.match(url))

    def add_to_queue(self) -> None:
        """Add a single URL to the download queue."""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL")
            return
        if not self.validate_url(url):
            messagebox.showerror("Error", "Invalid YouTube URL")
            return
        self.extracting_label.config(text="Extracting video info...")
        self.logger.log(message=f"Extracting info for: {url}")
        threading.Thread(target=lambda: self._add_url(url), daemon=True).start()
        self.url_var.set("")

    def add_multiple_urls(self) -> None:
        """Add multiple URLs from the text area to the queue."""
        urls_text = self.multi_url_text.get(1.0, tk.END).strip()
        if not urls_text:
            messagebox.showwarning("Warning", "Please enter URLs")
            return
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        valid_urls = [url for url in urls if self.validate_url(url) or self.logger.log(message=f"Skipping invalid URL: {url}", level="WARNING")]
        if not valid_urls:
            messagebox.showerror("Error", "No valid YouTube URLs found")
            return
        self.extracting_label.config(text="Extracting info for multiple URLs...")
        self.logger.log(message=f"Processing {len(valid_urls)} URLs...")
        threading.Thread(target=lambda: [self._add_url(url) for url in valid_urls], daemon=True).start()
        self.multi_url_text.delete(1.0, tk.END)

    def _add_url(self, url: str) -> None:
        """Helper to add URL in background thread."""
        self.download_manager.add_to_queue(url)
        self.root.after(0, lambda: self.extracting_label.config(text=""))

    def remove_from_queue(self) -> None:
        """Remove selected items from the queue."""
        selected_items = self.queue_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select items to remove")
            return
        selected_ids = [int(self.queue_tree.item(item, 'text')) for item in selected_items]
        for video in self.video_queue:
            if video['id'] in selected_ids:
                video['status'] = 'Removed'
        for item in selected_items:
            self.queue_tree.delete(item)
        self.logger.log(message=f"Removed {len(selected_items)} item(s) from queue")
        self.update_overall_progress()

    def clear_queue(self) -> None:
        """Clear all items from the queue."""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the entire queue?"):
            self.video_queue.clear()
            for item in self.queue_tree.get_children():
                self.queue_tree.delete(item)
            self.logger.log(message="Queue cleared")
            self.update_overall_progress()

    def refresh_queue_info(self) -> None:
        """Refresh video information for queued items."""
        if not self.video_queue:
            return
        self.logger.log(message="Refreshing queue information...")
        for video in self.video_queue:
            if video['status'] == 'Queued':
                self.download_manager.add_to_queue(video['url'])  # Re-add to refresh info
        self.logger.log(message="Queue information refreshed")

    def start_downloads(self) -> None:
        """Start downloading queued videos."""
        active_videos = [v for v in self.video_queue if v['status'] == 'Queued']
        if not active_videos:
            messagebox.showwarning("Warning", "No videos in queue to download")
            return
        self.config.set("download_path", self.path_var.get())
        self.config.set("quality", self.quality_var.get())
        self.config.set("include_subtitles", self.subtitle_var.get())
        self.config.set("subtitle_langs", [lang.strip() for lang in self.subtitle_langs_var.get().split(',') if lang.strip()])
        self.config.save_config()
        self.start_button.config(state="disabled")
        self.pause_button.config(state="normal")
        self.stop_button.config(state="normal")
        self.download_manager.start_downloads()

    def pause_downloads(self) -> None:
        """Placeholder for pause functionality."""
        messagebox.showinfo("Info", "Pause functionality is not available with yt-dlp. Use Stop to cancel downloads.")

    def stop_downloads(self) -> None:
        """Stop all downloads."""
        self.download_manager.stop_downloads()
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.current_progress['value'] = 0
        self.current_percent_label.config(text="0%")
        self.current_file_label.config(text="Downloads stopped")

    def check_progress_queue(self) -> None:
        """Check for progress updates from the download manager."""
        try:
            while True:
                item = self.download_manager.progress_queue.get_nowait()
            
                if item[0] == 'video_added':
                    self.video_queue.append(item[1])
                    self.queue_tree.insert('', 'end', text=str(item[1]['id']), values=(
                        item[1]['url'][:50] + '...' if len(item[1]['url']) > 50 else item[1]['url'],
                        item[1]['title'][:40] + '...' if len(item[1]['title']) > 40 else item[1]['title'],
                        item[1]['duration'],
                        'Queued'
                    ))
                elif item[0] == 'progress':
                    self.current_progress['value'] = item[1]
                    self.current_percent_label.config(text=f"{item[1]:.1f}%")
                elif item[0] == 'status':
                    self.update_video_status(item[1], item[2])
                    self.update_overall_progress()
                elif item[0] == 'current_file':
                    self.current_file_label.config(text=item[1])
                elif item[0] == 'log':
                    self.logger.log(message=item[1], level=item[2] if len(item) > 2 else 'INFO')
                elif item[0] == 'download_complete':
                    self.download_complete()
        except queue.Empty:
            pass
        self.root.after(100, self.check_progress_queue)

    def update_video_status(self, video_id: int, status: str) -> None:
        """
        Update video status in the treeview.

        Args:
            video_id (int): ID of the video.
            status (str): New status to set.
        """
        for item in self.queue_tree.get_children():
            if int(self.queue_tree.item(item, 'text')) == video_id:
                current_values = list(self.queue_tree.item(item, 'values'))
                current_values[3] = status
                self.queue_tree.item(item, values=current_values)
                break

    def update_overall_progress(self) -> None:
        """Update the overall progress bar."""
        active_videos = [v for v in self.video_queue if v['status'] != 'Removed']
        if not active_videos:
            self.overall_progress['value'] = 0
            self.overall_percent_label.config(text="0%")
            return
        completed = len([v for v in active_videos if v['status'] == 'Completed'])
        progress_percent = (completed / len(active_videos)) * 100 if active_videos else 0
        self.overall_progress['value'] = progress_percent
        self.overall_percent_label.config(text=f"{progress_percent:.1f}%")

    def download_complete(self) -> None:
        """Handle download completion."""
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.current_progress['value'] = 0
        self.current_percent_label.config(text="0%")
        self.current_file_label.config(text="All downloads completed!")
        completed_count = len([v for v in self.video_queue if v['status'] == 'Completed'])
        messagebox.showinfo("Downloads Complete", f"Successfully downloaded {completed_count} video(s)!")

    def on_closing(self) -> None:
        """Handle application closing."""
        self.config.set("window_geometry", self.root.geometry())
        self.config.save_config()
        if self.download_manager.is_downloading:
            self.stop_downloads()
        self.root.destroy()