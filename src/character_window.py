"""Transparent overlay window for character display."""
from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter
from state_manager import CharacterState

class CharacterWindow(QWidget):
    """Transparent overlay window that displays the character."""

    def __init__(self, config):
        """Initialize character window.

        Args:
            config: Configuration object
        """
        super().__init__()
        self.config = config
        self.current_sprite = None
        self._init_window()

    def _init_window(self):
        """Initialize window properties."""
        # Set window flags for transparent overlay
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |  # Always on top
            Qt.FramelessWindowHint |   # No window frame
            Qt.Tool |                  # Tool window (doesn't appear in taskbar)
            Qt.WindowTransparentForInput  # Click-through enabled
        )

        # Enable transparency
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Set fixed size
        size = self.config.sprite_size
        self.setFixedSize(size, size)

        # Start hidden
        self.hide()

        print(f"[WINDOW] Initialized {size}x{size} transparent window")

    def on_state_changed(self, new_state):
        """Handle state changes.

        Args:
            new_state: New CharacterState
        """
        if new_state == CharacterState.HIDDEN:
            self.hide()
            print("[WINDOW] Window hidden")
        else:
            self.show()
            print("[WINDOW] Window shown")

    def update_sprite(self, pixmap):
        """Update the displayed sprite.

        Args:
            pixmap: QPixmap to display
        """
        if pixmap and not pixmap.isNull():
            self.current_sprite = pixmap
            self.update()  # Trigger repaint
            print(f"[WINDOW] Sprite updated: {pixmap.width()}x{pixmap.height()}")

    def update_position(self, x, y):
        """Update window position.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.move(int(x), int(y))

    def paintEvent(self, event):
        """Custom paint event for transparency."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.current_sprite and not self.current_sprite.isNull():
            painter.drawPixmap(0, 0, self.current_sprite)

        painter.end()
