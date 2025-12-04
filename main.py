#!/usr/bin/env python3
"""YouTube Downloader GUI - Main Entry Point.

A modern YouTube video downloader with queue management,
batch processing, and a user-friendly interface.

Usage:
    python main.py

Or as a module:
    python -m youtube_downloader
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []

    try:
        import tkinter
    except ImportError:
        missing.append("tkinter")

    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")

    if missing:
        print("Missing required dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print("\nInstall with: pip install -r requirements.txt")
        sys.exit(1)


def main():
    """Main entry point."""
    # Check dependencies
    check_dependencies()

    # Import and run application
    from src.ui.main_window import MainWindow

    try:
        app = MainWindow()
        app.run()
    except Exception as e:
        import traceback
        print(f"Error starting application: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
