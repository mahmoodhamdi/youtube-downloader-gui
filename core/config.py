import json
from pathlib import Path
from typing import Any, Dict

class Config:
    """Handles loading and saving of configuration settings."""
    
    def __init__(self, config_file: str):
        """
        Initialize the Config object with a file path.

        Args:
            config_file (str): Path to the configuration file.
        """
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or return default values if file doesn't exist.

        Returns:
            Dict[str, Any]: Configuration dictionary.
        """
        default_config = {
            "download_path": str(Path.home() / "Downloads"),
            "quality": "best",
            "include_subtitles": False,
            "subtitle_langs": ["en"],
            "window_geometry": "900x700"
        }
        
        try:
            if Path(self.config_file).exists():
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

    def save_config(self) -> None:
        """Save the current configuration to the file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key (str): Configuration key to retrieve.
            default (Any, optional): Default value if key not found.

        Returns:
            Any: Value associated with the key or default.
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key (str): Configuration key to set.
            value (Any): Value to associate with the key.
        """
        self.config[key] = value