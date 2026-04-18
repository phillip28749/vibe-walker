import pygame
from src.state_machine import State


class DragHandler:
    """Handles drag-and-drop physics for the character"""

    def __init__(self, sprite_size, baseline_y, drop_duration_ms=500):
        self.sprite_size = sprite_size
        self.baseline_y = baseline_y
        self.drop_duration_ms = drop_duration_ms

        self.is_dragging = False
        self.is_dropping = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.drop_start_y = 0
        self.drop_start_time = 0

    def handle_mouse_down(self, mouse_pos, window_pos):
        """Handle mouse button down event

        Args:
            mouse_pos: (x, y) mouse position in window coordinates
            window_pos: (x, y) window position on screen

        Returns:
            State.DRAGGED if drag started, None otherwise
        """
        # Always start drag when clicked (whole window is draggable)
        self.is_dragging = True
        # Store offset from mouse to window position
        self.drag_offset_x = mouse_pos[0]
        self.drag_offset_y = mouse_pos[1]
        return State.DRAGGED

    def handle_mouse_motion(self, mouse_pos, current_window_pos):
        """Handle mouse motion during drag

        Args:
            mouse_pos: (x, y) mouse position in window coordinates
            current_window_pos: (x, y) current window position on screen

        Returns:
            (dx, dy) delta to move window, or None if not dragging
        """
        if not self.is_dragging:
            return None

        # Calculate how much the mouse moved within the window
        dx = mouse_pos[0] - self.drag_offset_x
        dy = mouse_pos[1] - self.drag_offset_y

        # Update offset to current position for next frame
        self.drag_offset_x = mouse_pos[0]
        self.drag_offset_y = mouse_pos[1]

        return (dx, dy)

    def handle_mouse_up(self, sprite_y):
        """Handle mouse button up event

        Args:
            sprite_y: Current Y position of sprite

        Returns:
            State.DROPPING if should start drop, None otherwise
        """
        if not self.is_dragging:
            return None

        self.is_dragging = False

        if sprite_y != self.baseline_y:
            # Start drop animation
            self.is_dropping = True
            self.drop_start_y = sprite_y
            self.drop_start_time = pygame.time.get_ticks()
            return State.DROPPING

        return None

    def update_drop(self, current_time):
        """Update drop animation with gravity-like easing

        Returns:
            (y_position, is_complete) tuple
        """
        if not self.is_dropping:
            return (self.baseline_y, False)

        elapsed = current_time - self.drop_start_time
        progress = min(elapsed / self.drop_duration_ms, 1.0)

        # Ease-in-out (accelerate then decelerate) for smooth, natural drop
        if progress < 0.5:
            eased = 2 * progress * progress
        else:
            eased = 1 - pow(-2 * progress + 2, 2) / 2

        # Interpolate Y position
        current_y = self.drop_start_y + (self.baseline_y - self.drop_start_y) * eased

        if progress >= 1.0:
            self.is_dropping = False
            return (self.baseline_y, True)

        return (int(current_y), False)
