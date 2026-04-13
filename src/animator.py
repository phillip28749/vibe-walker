"""Sprite animation and movement logic."""
import os
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QPixmap
from state_manager import CharacterState

class Animator(QObject):
    """Handles sprite animation and movement."""

    # Signals
    sprite_changed = pyqtSignal(QPixmap)  # Emitted when sprite frame changes
    position_changed = pyqtSignal(int, int)  # Emitted when position changes (x, y)
    edge_reached = pyqtSignal()  # Emitted when screen edge is reached

    def __init__(self, config, screen_width, screen_height):
        """Initialize animator.

        Args:
            config: Configuration object
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        super().__init__()
        self.config = config
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Current position
        self.x = 0
        self.y = screen_height - config.window_bottom_offset - config.sprite_size

        # Animation state
        self.current_state = CharacterState.HIDDEN
        self.current_frame = 0
        self.direction = 1  # 1 for right, -1 for left

        # Load sprites
        self.sprites = {}
        self._load_sprites()

        # Animation timer
        self.animation_timer = QTimer()
        frame_interval_ms = 1000 // config.animation_fps
        self.animation_timer.setInterval(frame_interval_ms)
        self.animation_timer.timeout.connect(self._animate)

    def _load_sprites(self):
        """Load all sprite images."""
        sprite_files = {
            'idle': 'idle.png',
            'walk_right_1': 'walk_right_1.png',
            'walk_right_2': 'walk_right_2.png',
            'walk_left_1': 'walk_left_1.png',
            'walk_left_2': 'walk_left_2.png'
        }

        for key, filename in sprite_files.items():
            path = self.config.get_sprite_path(filename)
            if os.path.exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    self.sprites[key] = pixmap
                    print(f"[ANIMATOR] Loaded sprite: {filename}")
                else:
                    print(f"[ERROR] Failed to load sprite: {filename}")
            else:
                print(f"[ERROR] Sprite file not found: {path}")

        # Create fallback sprite if loading failed
        if not self.sprites:
            print("[WARNING] No sprites loaded, using fallback")
            fallback = QPixmap(self.config.sprite_size, self.config.sprite_size)
            fallback.fill(Qt.blue)
            self.sprites['fallback'] = fallback

    def on_state_changed(self, new_state):
        """Handle state changes.

        Args:
            new_state: New CharacterState
        """
        self.current_state = new_state
        self.current_frame = 0

        if new_state in [CharacterState.WALKING_RIGHT, CharacterState.WALKING_LEFT]:
            # Start animation
            if not self.animation_timer.isActive():
                self.animation_timer.start()
                print("[ANIMATOR] Animation started")

            # Reset position if coming from HIDDEN
            if new_state == CharacterState.WALKING_RIGHT:
                self.direction = 1
                self.x = 0  # Start from left
            else:
                self.direction = -1
                self.x = self.screen_width - self.config.sprite_size  # Start from right

            self._update_sprite()
            self._update_position()

        elif new_state == CharacterState.IDLE:
            # Stop animation, show idle sprite
            self.animation_timer.stop()
            print("[ANIMATOR] Animation stopped (idle)")
            self._update_sprite()

        elif new_state == CharacterState.HIDDEN:
            # Stop everything
            self.animation_timer.stop()
            print("[ANIMATOR] Animation stopped (hidden)")

    def _animate(self):
        """Called on each animation frame."""
        if self.current_state == CharacterState.HIDDEN:
            return

        # Update animation frame
        self.current_frame = (self.current_frame + 1) % 2

        # Update sprite
        self._update_sprite()

        # Update position if walking
        if self.current_state in [CharacterState.WALKING_RIGHT, CharacterState.WALKING_LEFT]:
            self._update_position()
            self._check_edges()

    def _update_sprite(self):
        """Update the current sprite based on state and frame."""
        sprite = None

        if self.current_state == CharacterState.IDLE:
            sprite = self.sprites.get('idle')
        elif self.current_state == CharacterState.WALKING_RIGHT:
            frame_num = self.current_frame + 1
            sprite = self.sprites.get(f'walk_right_{frame_num}')
        elif self.current_state == CharacterState.WALKING_LEFT:
            frame_num = self.current_frame + 1
            sprite = self.sprites.get(f'walk_left_{frame_num}')

        # Fallback if sprite not found
        if sprite is None:
            sprite = self.sprites.get('fallback')
            if sprite is None:
                return

        self.sprite_changed.emit(sprite)

    def _update_position(self):
        """Update character position."""
        # Move horizontally
        self.x += self.config.movement_speed_px * self.direction

        # Emit position change
        self.position_changed.emit(self.x, self.y)

    def _check_edges(self):
        """Check if character reached screen edge."""
        sprite_width = self.config.sprite_size

        # Check right edge
        if self.direction > 0 and self.x >= (self.screen_width - sprite_width):
            self.x = self.screen_width - sprite_width
            print("[ANIMATOR] Reached right edge")
            self.edge_reached.emit()

        # Check left edge
        elif self.direction < 0 and self.x <= 0:
            self.x = 0
            print("[ANIMATOR] Reached left edge")
            self.edge_reached.emit()

    def get_current_position(self):
        """Get current position.

        Returns:
            Tuple of (x, y)
        """
        return (self.x, self.y)

    def get_current_sprite(self):
        """Get current sprite.

        Returns:
            QPixmap of current sprite
        """
        if self.current_state == CharacterState.IDLE:
            return self.sprites.get('idle')
        elif self.current_state == CharacterState.WALKING_RIGHT:
            frame_num = self.current_frame + 1
            return self.sprites.get(f'walk_right_{frame_num}')
        elif self.current_state == CharacterState.WALKING_LEFT:
            frame_num = self.current_frame + 1
            return self.sprites.get(f'walk_left_{frame_num}')
        return None
