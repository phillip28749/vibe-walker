"""Configuration dialog for vibe-walker startup settings."""

import os
from pathlib import Path
from PIL import Image

from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QLineEdit, QPushButton, QWidget, QDialogButtonBox, QSlider
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage


class ConfigDialog(QDialog):
    """Startup configuration dialog for vibe-walker settings."""

    # Tooltips for each setting
    TOOLTIPS = {
        'sprite_size': 'Size of the character sprite in pixels',
        'reactive_mode_enabled': 'Show/hide minion based on Claude activity',
        'behavior_mode': 'Claude mode: responds to activity | Pet mode: random walking',
        'random_spawn_enabled': 'Randomize spawn position (if disabled, spawns centered)',
        'walk_freely': 'Allow walking freely across all monitors (if disabled, stays on current monitor)',
        'window_bottom_offset': 'Distance from bottom of screen to window edge',
        'baseline_y_offset': 'Vertical offset for character baseline position',
        'animation_fps': 'Frames per second for sprite animations',
        'drag_transition_fps': 'Frames per second for drag-to-idle and idle-to-drag transitions',
        'idle_to_walking_fps': 'Frames per second for idle-to-walking and walk-to-idle transitions',
        'pygame_fps': 'Frames per second for game loop rendering',
        'movement_speed_px': 'Movement speed in pixels per frame',
        'drop_duration_ms': 'Duration of drop animation in milliseconds',
        'dragged_animation_enabled': 'Use animated sprite when being dragged',
        'poll_interval_ms': 'How often to check for system activity (milliseconds)',
        'idle_timeout_sec': 'Seconds of inactivity before hiding character',
        'trace_poll_interval_ms': 'How often to poll trace file for events',
        'action_detection_mode': 'Method for detecting Claude actions: hybrid, timing, or trace',
        'timing_threshold_sec': 'Time threshold for action detection (seconds)',
        'debug_action_detection': 'Print debug info for action detection',
        'trace_file_path': 'Path to trace events file (relative or absolute)',
        'permission_timeout_sec': 'Timeout for permission dialogs (seconds)',
        'action_timeout_sec': 'Timeout for other actions (seconds)',
    }

    # Valid ranges for numeric settings
    RANGES = {
        'sprite_size': (32, 256),
        'window_bottom_offset': (0, 200),
        'baseline_y_offset': (0, 200),
        'animation_fps': (1, 60),
        'drag_transition_fps': (1, 60),
        'idle_to_walking_fps': (1, 60),
        'pygame_fps': (30, 120),
        'movement_speed_px': (1, 10),
        'drop_duration_ms': (100, 2000),
        'poll_interval_ms': (100, 5000),
        'idle_timeout_sec': (1, 30),
        'trace_poll_interval_ms': (100, 2000),
        'timing_threshold_sec': (0.1, 10.0),
        'permission_timeout_sec': (10, 300),
        'action_timeout_sec': (5, 120),
    }

    def __init__(self, config, parent=None):
        """Initialize configuration dialog.

        Args:
            config: Config object to read from and write to
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.config = config
        self.widgets = {}  # Store widget references by config key
        self.preview_label = None  # Will hold the sprite preview label

        self._setup_ui()
        self._load_values_from_config()
        self._update_preview()  # Initial preview render

    def _setup_ui(self):
        """Setup dialog UI components."""
        self.setWindowTitle("Vibe Walker - Configuration")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        # Main layout
        layout = QVBoxLayout()

        # Create tabs
        self.tab_widget = self._create_tabs()
        layout.addWidget(self.tab_widget)

        # Buttons
        buttons = self._create_buttons()
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _create_tabs(self):
        """Create tabbed interface for settings."""
        tabs = QTabWidget()

        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_monitoring_tab(), "Monitoring")

        return tabs

    def _create_general_tab(self):
        """Create general settings tab."""
        widget = QWidget()
        layout = QFormLayout()
        layout.setSpacing(10)

        # Preview section
        preview_container = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(0, 0, 0, 10)

        preview_title = QLabel("Sprite Preview:")
        preview_title.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        preview_layout.addWidget(preview_title)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "background-color: #f0f0f0; "
            "border: 2px solid #ccc; "
            "border-radius: 5px; "
            "padding: 10px; "
            "min-height: 150px;"
        )
        preview_layout.addWidget(self.preview_label)

        preview_container.setLayout(preview_layout)
        layout.addRow("", preview_container)

        # sprite_size - slider with value label
        slider_container = QWidget()
        slider_layout = QHBoxLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)

        sprite_size_slider = QSlider(Qt.Horizontal)
        sprite_size_slider.setRange(*self.RANGES['sprite_size'])
        sprite_size_slider.setToolTip(self.TOOLTIPS['sprite_size'])
        sprite_size_slider.valueChanged.connect(self._update_preview)
        slider_layout.addWidget(sprite_size_slider)

        sprite_size_label = QLabel("64 px")
        sprite_size_label.setMinimumWidth(60)
        sprite_size_label.setStyleSheet("font-weight: bold;")
        slider_layout.addWidget(sprite_size_label)

        slider_container.setLayout(slider_layout)
        layout.addRow("Sprite Size:", slider_container)

        self.widgets['sprite_size'] = sprite_size_slider
        self.sprite_size_label = sprite_size_label  # Store label reference for updates

        # Update label when slider changes
        sprite_size_slider.valueChanged.connect(
            lambda value: sprite_size_label.setText(f"{value} px")
        )

        # behavior_mode
        behavior_mode = QComboBox()
        behavior_mode.addItems(['claude', 'pet'])
        behavior_mode.setToolTip(self.TOOLTIPS['behavior_mode'])
        layout.addRow("Behavior Mode:", behavior_mode)
        self.widgets['behavior_mode'] = behavior_mode

        # drag_transition_fps
        drag_transition_fps = QSpinBox()
        drag_transition_fps.setRange(*self.RANGES['drag_transition_fps'])
        drag_transition_fps.setToolTip(self.TOOLTIPS['drag_transition_fps'])
        layout.addRow("Drag Transition FPS:", drag_transition_fps)
        self.widgets['drag_transition_fps'] = drag_transition_fps

        # idle_to_walking_fps
        idle_to_walking_fps = QSpinBox()
        idle_to_walking_fps.setRange(*self.RANGES['idle_to_walking_fps'])
        idle_to_walking_fps.setToolTip(self.TOOLTIPS['idle_to_walking_fps'])
        layout.addRow("Idle-to-Walking FPS:", idle_to_walking_fps)
        self.widgets['idle_to_walking_fps'] = idle_to_walking_fps

        # random_spawn_enabled
        random_spawn = QCheckBox()
        random_spawn.setToolTip(self.TOOLTIPS['random_spawn_enabled'])
        layout.addRow("Random Spawn Position:", random_spawn)
        self.widgets['random_spawn_enabled'] = random_spawn

        # walk_freely
        walk_freely = QCheckBox()
        walk_freely.setToolTip(self.TOOLTIPS['walk_freely'])
        layout.addRow("Walk Freely:", walk_freely)
        self.widgets['walk_freely'] = walk_freely

        widget.setLayout(layout)
        return widget

    def _create_monitoring_tab(self):
        """Create activity monitoring settings tab."""
        widget = QWidget()
        layout = QFormLayout()
        layout.setSpacing(10)

        # idle_timeout_sec
        idle_timeout = QSpinBox()
        idle_timeout.setRange(*self.RANGES['idle_timeout_sec'])
        idle_timeout.setSuffix(" sec")
        idle_timeout.setToolTip(self.TOOLTIPS['idle_timeout_sec'])
        layout.addRow("Idle Timeout:", idle_timeout)
        self.widgets['idle_timeout_sec'] = idle_timeout

        widget.setLayout(layout)
        return widget

    def _create_buttons(self):
        """Create dialog buttons."""
        button_box = QDialogButtonBox()

        # Custom buttons
        defaults_btn = button_box.addButton("Use Defaults", QDialogButtonBox.ResetRole)
        defaults_btn.clicked.connect(self._reset_to_defaults)

        cancel_btn = button_box.addButton(QDialogButtonBox.Cancel)
        cancel_btn.clicked.connect(self.reject)

        save_btn = button_box.addButton("Save && Start", QDialogButtonBox.AcceptRole)
        save_btn.clicked.connect(self._on_save_clicked)

        return button_box

    def _load_values_from_config(self):
        """Load current config values into widgets."""
        for key, widget in self.widgets.items():
            value = self.config.get(key, self.config.DEFAULTS.get(key))

            if isinstance(widget, QCheckBox):
                widget.setChecked(value)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox, QSlider)):
                widget.setValue(value)
            elif isinstance(widget, QComboBox):
                index = widget.findText(str(value))
                if index >= 0:
                    widget.setCurrentIndex(index)
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))

    def _save_values_to_config(self):
        """Save widget values to config object."""
        for key, widget in self.widgets.items():
            if isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox, QSlider)):
                value = widget.value()
            elif isinstance(widget, QComboBox):
                value = widget.currentText()
            elif isinstance(widget, QLineEdit):
                value = widget.text()

            self.config.config[key] = value

    def _reset_to_defaults(self):
        """Reset all fields to default values."""
        for key, widget in self.widgets.items():
            value = self.config.DEFAULTS.get(key)

            if value is None:
                continue

            if isinstance(widget, QCheckBox):
                widget.setChecked(value)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox, QSlider)):
                widget.setValue(value)
            elif isinstance(widget, QComboBox):
                index = widget.findText(str(value))
                if index >= 0:
                    widget.setCurrentIndex(index)
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))

        # Update preview after resetting
        self._update_preview()

    def _update_preview(self):
        """Update the sprite preview with current sprite size."""
        if self.preview_label is None:
            return

        # Get current sprite size
        sprite_size_widget = self.widgets.get('sprite_size')
        if sprite_size_widget is None:
            sprite_size = self.config.sprite_size
        else:
            sprite_size = sprite_size_widget.value()

        # Get path to idle sprite
        project_root = Path(__file__).parent.parent
        sprite_path = project_root / "sprites" / "idle.png"

        if not sprite_path.exists():
            # Show placeholder if sprite not found
            self.preview_label.setText(f"Preview not available\n(sprite not found)")
            return

        try:
            # Load and scale sprite using PIL
            img = Image.open(sprite_path)
            img = img.resize((sprite_size, sprite_size), Image.Resampling.LANCZOS)

            # Convert PIL image to QPixmap
            img_rgba = img.convert("RGBA")
            data = img_rgba.tobytes("raw", "RGBA")
            qimage = QImage(data, img_rgba.width, img_rgba.height, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimage)

            # Display in label
            self.preview_label.setPixmap(pixmap)

            # Add size info below preview
            size_text = f"{sprite_size}x{sprite_size} px"
            self.preview_label.setToolTip(f"Current size: {size_text}")

        except Exception as e:
            self.preview_label.setText(f"Preview error:\n{str(e)}")

    def get_preview_screen_position(self):
        """Get the global screen position of the preview label center.

        Returns:
            tuple: (x, y) coordinates on screen where mob should spawn
        """
        if self.preview_label is None:
            return None

        # Get preview label's global position
        label_rect = self.preview_label.rect()
        center_point = label_rect.center()
        global_pos = self.preview_label.mapToGlobal(center_point)

        print(f"[CONFIG] Preview label rect: {label_rect}")
        print(f"[CONFIG] Preview center (local): {center_point}")
        print(f"[CONFIG] Preview center (global): ({global_pos.x()}, {global_pos.y()})")

        return (global_pos.x(), global_pos.y())

    def _on_save_clicked(self):
        """Handle save button click."""
        self._save_values_to_config()
        self.config.save()  # Persist to config.json
        self.accept()
