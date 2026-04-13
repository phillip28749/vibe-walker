"""Configuration management for vibe-walker."""
import json
import os
from pathlib import Path

class Config:
    """Manages application configuration."""

    # Default configuration values
    DEFAULTS = {
        "poll_interval_ms": 1000,
        "idle_timeout_sec": 7,
        "animation_fps": 7,
        "movement_speed_px": 2,
        "sprite_size": 64,
        "window_bottom_offset": 50
    }

    def __init__(self, config_file="config.json"):
        """Initialize configuration.

        Args:
            config_file: Path to configuration JSON file
        """
        self.config_file = config_file
        self.config = self.DEFAULTS.copy()
        self.load()

    def load(self):
        """Load configuration from JSON file."""
        if not os.path.exists(self.config_file):
            print(f"[WARNING] Config file '{self.config_file}' not found, using defaults")
            return

        try:
            with open(self.config_file, 'r') as f:
                user_config = json.load(f)
                self.config.update(user_config)
            print(f"[OK] Loaded configuration from '{self.config_file}'")
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in '{self.config_file}': {e}")
            print("[WARNING] Using default configuration")
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            print("[WARNING] Using default configuration")

    def get(self, key, default=None):
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self.config.get(key, default)

    def __getitem__(self, key):
        """Allow dictionary-style access."""
        return self.config[key]

    def __contains__(self, key):
        """Check if key exists in configuration."""
        return key in self.config

    @property
    def poll_interval_ms(self):
        """Get process polling interval in milliseconds."""
        return self.config["poll_interval_ms"]

    @property
    def idle_timeout_sec(self):
        """Get idle timeout in seconds."""
        return self.config["idle_timeout_sec"]

    @property
    def animation_fps(self):
        """Get animation frames per second."""
        return self.config["animation_fps"]

    @property
    def movement_speed_px(self):
        """Get movement speed in pixels per frame."""
        return self.config["movement_speed_px"]

    @property
    def sprite_size(self):
        """Get sprite size in pixels."""
        return self.config["sprite_size"]

    @property
    def window_bottom_offset(self):
        """Get window bottom offset from screen edge."""
        return self.config["window_bottom_offset"]

    def get_sprite_path(self, sprite_name):
        """Get full path to sprite file.

        Args:
            sprite_name: Name of sprite file (e.g., 'idle.png')

        Returns:
            Full path to sprite file
        """
        # Get project root directory
        root_dir = Path(__file__).parent.parent
        return str(root_dir / "sprites" / sprite_name)
