import tkinter as tk
from ui.gui import YouTubeDownloaderGUI

def main() -> None:
    """Main entry point for the YouTube Downloader application."""
    root = tk.Tk()
    app = YouTubeDownloaderGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    if app.config.get("window_geometry"):
        try:
            root.geometry(app.config.get("window_geometry"))
        except:
            pass
    root.mainloop()

if __name__ == "__main__":
    main()