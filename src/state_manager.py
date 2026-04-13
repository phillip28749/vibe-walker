"""State machine for managing character behavior."""
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

class CharacterState(Enum):
    """Character behavior states."""
    HIDDEN = "hidden"
    WALKING_RIGHT = "walking_right"
    WALKING_LEFT = "walking_left"
    IDLE = "idle"

class StateManager(QObject):
    """Manages character state transitions."""

    # Signals emitted on state changes
    state_changed = pyqtSignal(CharacterState)  # Emitted when state changes
    fade_away_triggered = pyqtSignal()  # Emitted when fade away animation should start

    def __init__(self, config):
        """Initialize state manager.

        Args:
            config: Configuration object
        """
        super().__init__()
        self.config = config
        self.current_state = CharacterState.HIDDEN
        self.claude_running = False

        # Setup idle timer (30 second countdown)
        self.idle_timer = QTimer()
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self._on_idle_timeout)

    def get_state(self):
        """Get current state."""
        return self.current_state

    def on_claude_started(self):
        """Handle Claude Code started event."""
        print("[STATE] Claude Code started")
        self.claude_running = True

        # Stop idle timer if running
        if self.idle_timer.isActive():
            self.idle_timer.stop()

        # Transition from HIDDEN or IDLE to WALKING_RIGHT
        if self.current_state in [CharacterState.HIDDEN, CharacterState.IDLE]:
            self._set_state(CharacterState.WALKING_RIGHT)

    def on_claude_stopped(self):
        """Handle Claude Code stopped event."""
        print("[STATE] Claude Code stopped")
        self.claude_running = False

        # Transition from WALKING_* to IDLE
        if self.current_state in [CharacterState.WALKING_RIGHT, CharacterState.WALKING_LEFT]:
            self._set_state(CharacterState.IDLE)
            # Start 30-second countdown
            timeout_ms = self.config.idle_timeout_sec * 1000
            self.idle_timer.start(timeout_ms)
            print(f"[STATE] Starting {self.config.idle_timeout_sec}s idle timer")

    def reverse_direction(self):
        """Reverse walking direction when edge is reached."""
        if self.current_state == CharacterState.WALKING_RIGHT:
            self._set_state(CharacterState.WALKING_LEFT)
        elif self.current_state == CharacterState.WALKING_LEFT:
            self._set_state(CharacterState.WALKING_RIGHT)

    def _on_idle_timeout(self):
        """Handle idle timer timeout."""
        print("[STATE] Idle timeout - triggering fade away")
        if self.current_state == CharacterState.IDLE and not self.claude_running:
            # Trigger fade away animation instead of immediate hide
            self.fade_away_triggered.emit()

    def on_fade_away_complete(self):
        """Called when fade away animation finishes."""
        print("[STATE] Fade away complete - transitioning to HIDDEN")
        if self.current_state == CharacterState.IDLE:
            self._set_state(CharacterState.HIDDEN)

    def _set_state(self, new_state):
        """Set new state and emit signal if changed.

        Args:
            new_state: New CharacterState
        """
        if new_state != self.current_state:
            old_state = self.current_state
            self.current_state = new_state
            print(f"[STATE] Transition: {old_state.value} -> {new_state.value}")
            self.state_changed.emit(new_state)

    def is_visible(self):
        """Check if character should be visible."""
        return self.current_state != CharacterState.HIDDEN

    def is_walking(self):
        """Check if character is walking."""
        return self.current_state in [CharacterState.WALKING_RIGHT, CharacterState.WALKING_LEFT]

    def is_idle(self):
        """Check if character is idle."""
        return self.current_state == CharacterState.IDLE
