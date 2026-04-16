"""Sprite animation and movement logic."""
import os
import random
import glob
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QPixmap
from state_manager import CharacterState

class Animator(QObject):
    """Handles sprite animation and movement."""

    # Signals
    sprite_changed = pyqtSignal(QPixmap)  # Emitted when sprite frame changes
    position_changed = pyqtSignal(int, int)  # Emitted when position changes (x, y)
    edge_reached = pyqtSignal()  # Emitted when screen edge is reached
    animation_sequence_complete = pyqtSignal()  # Emitted when animation sequence finishes

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

        # Animation sequence playback
        self.is_playing_sequence = False
        self.sequence_frames = []
        self.sequence_current_frame = 0
        self.sequence_completion_callback = None
        self.should_loop_waving = False  # Flag to control waving loop
        self.sequence_timer = QTimer()
        self.sequence_timer.timeout.connect(self._play_sequence_frame)

        # Load sprites
        self.sprites = {}
        self.climb_out_sequence = []
        self.fade_away_sequence = []
        self.waving_sequence = []
        self._load_sprites()

        # Animation timer
        self.animation_timer = QTimer()
        frame_interval_ms = 1000 // config.animation_fps
        self.animation_timer.setInterval(frame_interval_ms)
        self.animation_timer.timeout.connect(self._animate)

    def _load_sprite_sheet(self, sheet_path, frame_width, frame_height, num_frames, scale_to_size=None):
        """Load frames from a horizontal sprite sheet.

        Args:
            sheet_path: Path to sprite sheet image
            frame_width: Width of each frame in the sheet
            frame_height: Height of each frame in the sheet
            num_frames: Number of frames in the sheet
            scale_to_size: Optional size to scale frames to (width, height)

        Returns:
            List of QPixmap frames
        """
        frames = []

        if not os.path.exists(sheet_path):
            print(f"[ERROR] Sprite sheet not found: {sheet_path}")
            return frames

        sheet = QPixmap(sheet_path)
        if sheet.isNull():
            print(f"[ERROR] Failed to load sprite sheet: {sheet_path}")
            return frames

        # Extract each frame
        for i in range(num_frames):
            x = i * frame_width
            frame = sheet.copy(x, 0, frame_width, frame_height)

            # Scale frame if requested
            if scale_to_size:
                frame = frame.scaled(
                    scale_to_size[0],
                    scale_to_size[1],
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

            frames.append(frame)

        size_info = f" (scaled to {scale_to_size[0]}x{scale_to_size[1]})" if scale_to_size else ""
        print(f"[ANIMATOR] Loaded {len(frames)} frames from sprite sheet: {os.path.basename(sheet_path)}{size_info}")
        return frames

    def _load_sprites(self):
        """Load all sprite images and animation sequences."""
        # Load basic sprites
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

        # Load climb_out sequence
        # Get sprites directory by getting parent of any sprite path
        sprites_dir = os.path.dirname(self.config.get_sprite_path('idle.png'))
        climb_out_path = os.path.join(sprites_dir, 'climb_out', 'frame_*.png')
        climb_out_files = sorted(glob.glob(climb_out_path))
        for frame_file in climb_out_files:
            pixmap = QPixmap(frame_file)
            if not pixmap.isNull():
                self.climb_out_sequence.append(pixmap)
        print(f"[ANIMATOR] Loaded {len(self.climb_out_sequence)} climb_out frames")

        # Load fade_away sequence
        fade_away_path = os.path.join(sprites_dir, 'fade_away', 'frame_*.png')
        fade_away_files = sorted(glob.glob(fade_away_path))
        for frame_file in fade_away_files:
            pixmap = QPixmap(frame_file)
            if not pixmap.isNull():
                self.fade_away_sequence.append(pixmap)
        print(f"[ANIMATOR] Loaded {len(self.fade_away_sequence)} fade_away frames")

        # Load waving sequence from sprite sheet
        # Always divide into 8 horizontal frames regardless of image dimensions
        waving_sheet_path = os.path.join(sprites_dir, 'waving', 'waving_w.png')
        if os.path.exists(waving_sheet_path):
            # Load the sprite sheet to get its actual dimensions
            temp_sheet = QPixmap(waving_sheet_path)
            if not temp_sheet.isNull():
                sheet_width = temp_sheet.width()
                sheet_height = temp_sheet.height()
                frame_width = sheet_width // 8  # Always divide into 8 horizontal frames
                frame_height = sheet_height  # Use full height

                print(f"[ANIMATOR] Waving spritesheet: {sheet_width}x{sheet_height}, each frame: {frame_width}x{frame_height}")

                self.waving_sequence = self._load_sprite_sheet(
                    waving_sheet_path,
                    frame_width=frame_width,
                    frame_height=frame_height,
                    num_frames=8,
                    scale_to_size=(self.config.sprite_size, self.config.sprite_size)
                )
            else:
                print(f"[ERROR] Failed to load waving sprite sheet: {waving_sheet_path}")
        else:
            print(f"[WARNING] Waving sprite sheet not found: {waving_sheet_path}")

        # Create fallback sprite if loading failed
        if not self.sprites:
            print("[WARNING] No sprites loaded, using fallback")
            fallback = QPixmap(self.config.sprite_size, self.config.sprite_size)
            fallback.fill(Qt.blue)
            self.sprites['fallback'] = fallback

    def _get_random_spawn_x(self):
        """Generate random X position for spawn.

        Returns:
            Random X coordinate ensuring sprite is fully visible on screen
        """
        if not self.config.random_spawn_enabled:
            # If disabled, use edge-based positioning
            return 0 if self.direction > 0 else (self.screen_width - self.config.sprite_size)

        max_x = self.screen_width - self.config.sprite_size
        min_x = 0
        random_x = random.randint(min_x, max_x)

        print(f"[ANIMATOR] Random spawn at x={random_x}")
        return random_x

    def _play_animation_sequence(self, frames, fps=10, on_complete=None):
        """Play a sprite animation sequence.

        Args:
            frames: List of QPixmap frames to play
            fps: Frames per second for the sequence
            on_complete: Optional callback to call when sequence completes
        """
        if not frames:
            print("[ERROR] No frames to play")
            return

        self.sequence_frames = frames
        self.sequence_current_frame = 0
        self.sequence_completion_callback = on_complete
        self.is_playing_sequence = True

        # Set timer interval based on FPS
        interval_ms = 1000 // fps
        self.sequence_timer.setInterval(interval_ms)
        self.sequence_timer.start()

        print(f"[ANIMATOR] Starting sequence: {len(frames)} frames at {fps} FPS")

    def _play_sequence_frame(self):
        """Play next frame in the animation sequence."""
        if not self.is_playing_sequence or not self.sequence_frames:
            return

        # Emit current frame
        current_frame = self.sequence_frames[self.sequence_current_frame]
        self.sprite_changed.emit(current_frame)
        print(f"[ANIMATOR] Playing sequence frame {self.sequence_current_frame + 1}/{len(self.sequence_frames)}")

        # Move to next frame
        self.sequence_current_frame += 1

        # Check if sequence is complete
        if self.sequence_current_frame >= len(self.sequence_frames):
            # If looping waving animation, restart from frame 0
            if self.should_loop_waving:
                print("[ANIMATOR] Looping waving animation (restarting from frame 1)")
                self.sequence_current_frame = 0  # Reset to first frame
                # Continue playing, don't stop timer
            else:
                # Normal sequence completion
                self.sequence_timer.stop()
                self.is_playing_sequence = False
                print("[ANIMATOR] Sequence complete")

                # Call completion callback if provided
                if self.sequence_completion_callback:
                    self.sequence_completion_callback()
                    self.sequence_completion_callback = None

    def start_climb_out(self):
        """Start climb out animation sequence."""
        if self.climb_out_sequence:
            print("[ANIMATOR] Starting climb_out animation")
            self._play_animation_sequence(
                self.climb_out_sequence,
                fps=8,  # Slower so it's visible (was 12)
                on_complete=self._on_climb_out_complete
            )
        else:
            print("[ERROR] No climb_out sequence loaded")
            self._on_climb_out_complete()

    def _on_climb_out_complete(self):
        """Called when climb out sequence completes."""
        print("[ANIMATOR] Climb out complete - starting walking animation")
        # Start walking animation
        if not self.animation_timer.isActive():
            self.animation_timer.start()
            print("[ANIMATOR] Walking animation started")

    def start_fade_away(self):
        """Start fade away animation sequence."""
        if self.fade_away_sequence:
            print("[ANIMATOR] Starting fade_away animation")
            # Stop walking animation
            if self.animation_timer.isActive():
                self.animation_timer.stop()
            self._play_animation_sequence(
                self.fade_away_sequence,
                fps=6,  # Slower so it's visible (was 10)
                on_complete=self._on_fade_away_complete
            )
        else:
            print("[ERROR] No fade_away sequence loaded")
            self._on_fade_away_complete()

    def _on_fade_away_complete(self):
        """Called when fade away sequence completes."""
        print("[ANIMATOR] Fade away complete")
        self.animation_sequence_complete.emit()

    def start_waving(self):
        """Start waving animation sequence (loops until stopped)."""
        if self.waving_sequence:
            print("[ANIMATOR] Starting waving animation (action needed)")
            self.should_loop_waving = True  # Enable looping
            # Stop walking animation
            if self.animation_timer.isActive():
                self.animation_timer.stop()
            self._play_animation_sequence(
                self.waving_sequence,
                fps=8,  # 8 FPS for smooth waving
                on_complete=self._on_waving_loop  # Loop the animation
            )
        else:
            print("[ERROR] No waving sequence loaded")

    def _on_waving_loop(self):
        """Called when waving sequence completes - loop it."""
        # Keep looping waving animation until action is handled
        if self.should_loop_waving:
            print("[ANIMATOR] Looping waving animation (restarting from frame 0)")
            self._play_animation_sequence(
                self.waving_sequence,
                fps=8,
                on_complete=self._on_waving_loop
            )

    def stop_waving(self):
        """Stop waving animation and resume previous state."""
        self.should_loop_waving = False  # Disable looping
        if self.is_playing_sequence:
            self.sequence_timer.stop()
            self.is_playing_sequence = False
            print("[ANIMATOR] Waving stopped - resuming walking")
        # Resume walking animation
        if self.current_state in [CharacterState.WALKING_RIGHT, CharacterState.WALKING_LEFT]:
            if not self.animation_timer.isActive():
                self.animation_timer.start()

    def on_state_changed(self, new_state):
        """Handle state changes.

        Args:
            new_state: New CharacterState
        """
        # Clean up any in-progress animation sequence if interrupted
        if self.is_playing_sequence and new_state != CharacterState.HIDDEN:
            self.sequence_timer.stop()
            self.is_playing_sequence = False
            print("[ANIMATOR] Animation sequence interrupted")

        old_state = self.current_state
        self.current_state = new_state
        self.current_frame = 0

        if new_state in [CharacterState.WALKING_RIGHT, CharacterState.WALKING_LEFT]:
            # Only randomize spawn position if coming from HIDDEN state
            # When reversing direction (edge reached), keep current X position
            if old_state == CharacterState.HIDDEN:
                # First spawn - randomize position
                if new_state == CharacterState.WALKING_RIGHT:
                    self.direction = 1
                    self.x = self._get_random_spawn_x()  # Random spawn position
                else:
                    self.direction = -1
                    self.x = self._get_random_spawn_x()  # Random spawn position

                # Start climb out animation sequence
                self.start_climb_out()
            else:
                # Just reversing direction - keep current position
                if new_state == CharacterState.WALKING_RIGHT:
                    self.direction = 1
                else:
                    self.direction = -1

                # Start walking animation immediately when reversing
                if not self.animation_timer.isActive():
                    self.animation_timer.start()
                    print("[ANIMATOR] Animation started")

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
