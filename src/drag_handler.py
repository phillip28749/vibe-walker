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

        # Bouncing physics
        self.drop_x = 0
        self.drop_y = 0
        self.velocity_x = 0
        self.velocity_y = 0
        self.gravity = 0.8  # Gravity acceleration per frame
        self.bounce_coefficient = 0.65  # Energy retained after bounce
        self.friction = 0.98  # Horizontal friction (air resistance)
        self.last_update_time = 0

        # Track mouse velocity for throw physics
        self.mouse_history = []  # List of (x, y, time) tuples
        self.max_history_len = 5  # Track last 5 positions

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

    def update_mouse_position(self, x, y):
        """Track mouse position for velocity calculation

        Args:
            x, y: Current mouse position in screen coordinates
        """
        current_time = pygame.time.get_ticks()
        self.mouse_history.append((x, y, current_time))

        # Keep only recent history
        if len(self.mouse_history) > self.max_history_len:
            self.mouse_history.pop(0)

    def calculate_throw_velocity(self):
        """Calculate throw velocity from mouse movement history

        Returns:
            (velocity_x, velocity_y) tuple
        """
        if len(self.mouse_history) < 2:
            return (0, 0)

        # Use last few positions to calculate velocity
        start_pos = self.mouse_history[0]
        end_pos = self.mouse_history[-1]

        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        dt = max(end_pos[2] - start_pos[2], 1)  # Avoid division by zero

        # Calculate velocity (pixels per frame, assuming ~60fps)
        velocity_x = (dx / dt) * 16.67  # Convert to per-frame velocity
        velocity_y = (dy / dt) * 16.67

        # Clamp maximum throw velocity
        max_velocity = 30
        velocity_x = max(-max_velocity, min(max_velocity, velocity_x))
        velocity_y = max(-max_velocity, min(max_velocity, velocity_y))

        return (velocity_x, velocity_y)

    def handle_mouse_up(self, sprite_x, sprite_y):
        """Handle mouse button up event

        Args:
            sprite_x: Current X position of sprite
            sprite_y: Current Y position of sprite

        Returns:
            State.DROPPING if should start drop, None otherwise
        """
        if not self.is_dragging:
            return None

        self.is_dragging = False

        if sprite_y != self.baseline_y:
            # Calculate throw velocity from mouse movement
            vel_x, vel_y = self.calculate_throw_velocity()

            # Start drop animation with bouncing physics
            self.is_dropping = True
            self.drop_start_y = sprite_y
            self.drop_start_time = pygame.time.get_ticks()
            self.last_update_time = self.drop_start_time
            self.drop_x = float(sprite_x)
            self.drop_y = float(sprite_y)
            self.velocity_x = vel_x
            self.velocity_y = vel_y

            # Clear mouse history
            self.mouse_history.clear()

            return State.DROPPING

        # Clear mouse history even if not dropping
        self.mouse_history.clear()
        return None

    def update_drop(self, current_time, screen_width, window_size):
        """Update drop animation with bouncing ball physics

        Args:
            current_time: Current time in milliseconds
            screen_width: Width of the screen for edge detection
            window_size: Size of the window sprite

        Returns:
            (x_position, y_position, is_complete) tuple
        """
        if not self.is_dropping:
            return (int(self.drop_x), self.baseline_y, False)

        # Calculate time delta (in case frame rate varies)
        dt = min(current_time - self.last_update_time, 50)  # Cap at 50ms to avoid huge jumps
        self.last_update_time = current_time

        # Apply gravity to vertical velocity
        self.velocity_y += self.gravity * (dt / 16.67)  # Normalize to ~60fps

        # Apply friction to horizontal velocity (air resistance)
        self.velocity_x *= self.friction

        # Update positions
        self.drop_x += self.velocity_x
        self.drop_y += self.velocity_y

        # Check screen edge collisions for horizontal bounce
        if self.drop_x <= 0:
            self.drop_x = 0
            self.velocity_x = -self.velocity_x * 0.5  # Bounce off left edge with energy loss
        elif self.drop_x >= screen_width - window_size:
            self.drop_x = screen_width - window_size
            self.velocity_x = -self.velocity_x * 0.5  # Bounce off right edge with energy loss

        # Check if hit the ground
        if self.drop_y >= self.baseline_y:
            self.drop_y = self.baseline_y

            # Bounce if velocity is significant
            if abs(self.velocity_y) > 0.5:
                self.velocity_y = -self.velocity_y * self.bounce_coefficient
                # Reduce horizontal velocity on ground bounce
                self.velocity_x *= 0.9
            else:
                # Bounce too small, stop dropping if horizontal velocity also low
                if abs(self.velocity_x) < 0.3:
                    self.is_dropping = False
                    return (int(self.drop_x), self.baseline_y, True)
                else:
                    # Keep sliding horizontally
                    self.velocity_y = 0

        return (int(self.drop_x), int(self.drop_y), False)
