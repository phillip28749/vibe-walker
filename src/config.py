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
        "sprite_size": 69,
        "window_bottom_offset": 50,
        "trace_file_path": "trace/query_events.jsonl",
        "trace_poll_interval_ms": 500,
        "random_spawn_enabled": True,
        "reactive_mode_enabled": True,
        "baseline_y_offset": 50,
        "drop_duration_ms": 500,
        "pygame_fps": 60,
        "action_detection_mode": "hybrid",
        "timing_threshold_sec": 2.0,
        "debug_action_detection": False,
        "permission_timeout_sec": 60,  # Timeout for permission dialogs
        "action_timeout_sec": 30,      # Timeout for other actions
        "behavior_mode": "claude",     # Behavior mode: "claude" or "pet"
        "dragged_animation_enabled": False  # Use animated sprite when dragged
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

    def save(self):
        """Save current configuration to JSON file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"[OK] Saved configuration to '{self.config_file}'")
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")

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

    @property
    def trace_file_path(self):
        """Get trace event output file path.

        Resolves relative paths relative to the project root directory.
        """
        path = self.config["trace_file_path"]
        path_obj = Path(path)

        # If it's already absolute, return as-is
        if path_obj.is_absolute():
            return str(path_obj)

        # Otherwise, resolve relative to project root
        root_dir = Path(__file__).parent.parent
        return str(root_dir / path)

    @property
    def trace_poll_interval_ms(self):
        """Get trace polling interval in milliseconds."""
        return self.config["trace_poll_interval_ms"]

    @property
    def random_spawn_enabled(self):
        """Get whether random spawn position is enabled."""
        return self.config.get("random_spawn_enabled", True)

    @property
    def reactive_mode_enabled(self):
        """Get whether reactive mode is enabled."""
        return self.config.get("reactive_mode_enabled", True)

    @reactive_mode_enabled.setter
    def reactive_mode_enabled(self, value):
        """Set whether reactive mode is enabled."""
        self.config["reactive_mode_enabled"] = value

    @property
    def baseline_y_offset(self):
        """Get baseline Y offset in pixels."""
        return self.config.get("baseline_y_offset", 50)

    @property
    def drop_duration_ms(self):
        """Get drop animation duration in milliseconds."""
        return self.config.get("drop_duration_ms", 500)

    @property
    def pygame_fps(self):
        """Get Pygame rendering loop frame rate."""
        return self.config.get("pygame_fps", 60)

    @property
    def dragged_animation_enabled(self):
        """Get whether dragged sprite animation is enabled."""
        return self.config.get("dragged_animation_enabled", True)

    @property
    def behavior_mode(self):
        """Get current behavior mode ('claude' or 'pet')."""
        return self.config.get("behavior_mode", "claude")

    @behavior_mode.setter
    def behavior_mode(self, value):
        """Set behavior mode."""
        if value not in ["claude", "pet"]:
            raise ValueError(f"Invalid behavior mode: {value}")
        self.config["behavior_mode"] = value

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
