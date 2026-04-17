import pygame
from state_machine import State


class DragHandler:
    """Handles drag-and-drop physics for the character"""

    def __init__(self, sprite_size, baseline_y, drop_duration_ms=500):
        self.sprite_size = sprite_size
        self.baseline_y = baseline_y
        self.drop_duration_ms = drop_duration_ms

        self.is_dragging = False
        self.is_dropping = False
        self.drag_offset = (0, 0)

        self.drop_start_y = 0
        self.drop_start_time = 0

    def handle_mouse_down(self, mouse_pos, sprite_rect):
        """Handle mouse button down event

        Returns:
            State.DRAGGED if drag started, None otherwise
        """
        if sprite_rect.collidepoint(mouse_pos):
            self.is_dragging = True
            self.drag_offset = (
                sprite_rect.x - mouse_pos[0],
                sprite_rect.y - mouse_pos[1]
            )
            return State.DRAGGED
        return None

    def handle_mouse_motion(self, mouse_pos):
        """Handle mouse motion during drag

        Returns:
            (x, y) new sprite position if dragging, None otherwise
        """
        if not self.is_dragging:
            return None

        new_x = mouse_pos[0] + self.drag_offset[0]
        new_y = mouse_pos[1] + self.drag_offset[1]
        return (new_x, new_y)

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
        """Update drop animation

        Returns:
            (y_position, is_complete) tuple
        """
        if not self.is_dropping:
            return (self.baseline_y, False)

        elapsed = current_time - self.drop_start_time
        progress = min(elapsed / self.drop_duration_ms, 1.0)

        # Linear interpolation (smooth drop)
        current_y = self.drop_start_y + (self.baseline_y - self.drop_start_y) * progress

        if progress >= 1.0:
            self.is_dropping = False
            return (self.baseline_y, True)

        return (int(current_y), False)
