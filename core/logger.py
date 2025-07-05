from datetime import datetime
from tkinter import scrolledtext
from typing import Optional

class Logger:
    """Handles logging messages to the GUI and optionally to a file."""
    
    def __init__(self, status_text: scrolledtext.ScrolledText, log_file: Optional[str] = None):
        """
        Initialize the Logger with a GUI text widget and optional file path.

        Args:
            status_text (scrolledtext.ScrolledText): GUI widget for log display.
            log_file (Optional[str]): Path to log file, if logging to file is desired.
        """
        self.status_text = status_text
        self.log_file = log_file

    def log(self, message: str, level: str = "INFO") -> None:
        """
        Log a message to the GUI and optionally to a file.

        Args:
            message (str): Message to log.
            level (str): Log level (e.g., INFO, ERROR, WARNING, SUCCESS). Defaults to "INFO".
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        self.status_text.insert('end', formatted_message)
        self.status_text.see('end')
        
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(formatted_message)
            except Exception as e:
                self.status_text.insert('end', f"[{timestamp}] ERROR: Failed to write to log file: {e}\n")
                self.status_text.see('end')
        
        print(formatted_message.strip())