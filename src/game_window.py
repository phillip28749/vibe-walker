import os
import sys
import ctypes
from ctypes import wintypes
import pygame
import random
from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer
from src.sprite_manager import CharacterSprite
from src.state_machine import State
from src.drag_handler import DragHandler
from src.activity_bridge import CLAUDE_STARTED, CLAUDE_STOPPED, SHOW_MINION, HIDE_MINION, ACTION_NEEDED, ACTION_HANDLED


class GameWindow(QMainWindow):
    """PyQt5 window with embedded Pygame surface"""

    def __init__(self, config, state_machine, spawn_from=None):
        super().__init__()
        self.config = config
        self.state_machine = state_machine
        self.spawn_from = spawn_from  # Optional (x, y) position to spawn from
        self.last_topmost_enforce_ms = 0
        self.topmost_enforce_interval_ms = 500
        self.window_bounds_update_interval_ms = 2000
        self.last_window_bounds_update_ms = -self.window_bounds_update_interval_ms
        self.window_platforms = []
        self.window_union_bounds = None
        self.platform_baseline_tolerance_px = 30
        self.last_virtual_bounds = self._get_virtual_screen_bounds()

        print("[GAME] Initializing game window...")

        # Setup window
        self._setup_window()
        print("[GAME] Window setup complete")

        # Embed Pygame
        self._setup_pygame()
        print("[GAME] Pygame initialized")

        # Initialize game objects
        self._init_game_objects()
        print("[GAME] Game objects initialized")

        # Start game loop
        self._start_game_loop()
        print("[GAME] Game loop started")

    @staticmethod
    def _frame_divider(game_fps, anim_fps):
        """Return a safe integer frame divider for animation updates."""
        return max(1, game_fps // max(1, anim_fps))

    def _setup_window(self):
        """Configure PyQt5 window properties"""
        # Frameless, transparent, always-on-top
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        # Transparency disabled - embedded pygame + Qt transparency is problematic on Windows

        # Set window size slightly larger than sprite to prevent edge clipping
        # Padding ensures transparency mask works correctly
        size = self.config.sprite_size
        self.setFixedSize(size, size)

        # Create container widget for Pygame
        self.embed = QWidget(self)
        self.embed.setGeometry(0, 0, size, size)
        self.setCentralWidget(self.embed)

        # Store size for pygame setup
        self.window_size = size

        # Position at baseline
        self._position_at_baseline()

    def _position_at_baseline(self):
        """Position window at baseline or spawn position with optional random X"""
        screen = QApplication.primaryScreen().geometry()

        size = self.window_size

        # If spawn position provided, start there and drop straight down
        if self.spawn_from is not None:
            spawn_x, spawn_y = self.spawn_from
            # Center the window on the spawn point
            x = spawn_x - size // 2
            y = spawn_y - size // 2
            baseline_y = self._get_taskbar_baseline_for_point(x + size // 2, y + size // 2)
            self.move(x, y)
            self.window_x = x
            # Baseline should be directly below spawn position
            self.baseline_y = baseline_y
            self.initial_window_x = x
            print(f"[GAME] Spawning at preview position ({x}, {y}), will drop to ({x}, {baseline_y})")
        else:
            # Normal baseline positioning with optional random X
            if self.config.random_spawn_enabled:
                baseline_x = random.randint(0, screen.width() - size)
            else:
                baseline_x = (screen.width() - size) // 2

            baseline_y = self._get_taskbar_baseline_for_point(baseline_x + size // 2, screen.center().y())

            self.move(baseline_x, baseline_y)
            self.window_x = baseline_x
            self.baseline_y = baseline_y
            self.initial_window_x = baseline_x

    def _setup_pygame(self):
        """Initialize Pygame surface embedded in Qt widget"""
        # Tell SDL to use our Qt widget
        os.environ['SDL_WINDOWID'] = str(int(self.embed.winId()))
        os.environ['SDL_VIDEODRIVER'] = 'windib' if sys.platform == 'win32' else 'x11'

        # Initialize Pygame
        pygame.init()
        pygame.display.init()

        # Create display surface - match window size
        size = self.window_size
        self.pygame_screen = pygame.display.set_mode((size, size), pygame.NOFRAME)
        self.render_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        self.clock = pygame.time.Clock()

    def _init_game_objects(self):
        """Initialize sprite, drag handler, etc."""
        # Create sprite
        self.sprite = CharacterSprite(
            sprite_size=self.config.sprite_size,
            use_dragged_animation=self.config.dragged_animation_enabled
        )
        self.sprite_group = pygame.sprite.Group(self.sprite)

        # Create drag handler
        self.drag_handler = DragHandler(
            sprite_size=self.config.sprite_size,
            baseline_y=self.baseline_y,  # Window's baseline Y position on screen
            drop_duration_ms=self.config.drop_duration_ms
        )

        # Walking state
        self.walk_direction = 1  # 1 = right, -1 = left
        self.walk_frame_counter = 0
        self.walk_frame_update_rate = self._frame_divider(self.config.pygame_fps, self.config.animation_fps)

        # Dragged animation state
        self.dragged_frame_counter = 0
        self.dragged_frame_update_rate = self._frame_divider(self.config.pygame_fps, self.config.animation_fps)

        # Waving animation state
        self.waving_frame_counter = 0
        self.waving_frame_update_rate = self._frame_divider(self.config.pygame_fps, self.config.animation_fps)

        # Appearing animation state
        self.appearing_frame_counter = 0
        self.appearing_frame_update_rate = self._frame_divider(self.config.pygame_fps, self.config.animation_fps)

        # Drag-to-idle transition animation state
        self.drag_to_idle_frame_counter = 0
        self.drag_to_idle_frame_update_rate = self._frame_divider(self.config.pygame_fps, self.config.drag_transition_fps)

        # Idle-to-walking transition animation state
        self.idle_to_walking_frame_counter = 0
        self.idle_to_walking_frame_update_rate = self._frame_divider(self.config.pygame_fps, self.config.idle_to_walking_fps)

        # Walk-to-idle transition animation state (reuse idle-to-walking speed)
        self.walk_to_idle_frame_counter = 0
        self.walk_to_idle_frame_update_rate = self.idle_to_walking_frame_update_rate

        # Idle-to-drag transition animation state
        self.idle_to_drag_frame_counter = 0
        self.idle_to_drag_frame_update_rate = self.drag_to_idle_frame_update_rate

        # Track window position on screen for walking
        self.window_x = self.initial_window_x

        # Position sprite centered in window
        self.sprite.rect.x = (self.window_size - self.config.sprite_size) // 2
        self.sprite.rect.y = (self.window_size - self.config.sprite_size) // 2

        # Track last sprite image to avoid unnecessary mask updates
        self.last_sprite_image = None

        # Connect state machine signals
        self.state_machine.state_changed.connect(self.on_state_changed)

        # Track activity-driven mode state
        self.claude_active = False
        self.pending_actions_count = 0  # Count of pending actions requiring user input
        self.state_before_waving = None  # Store state to return to after waving

        # Behavior mode tracking
        self.behavior_mode = self.config.behavior_mode
        print(f"[GAME] Behavior mode: {self.behavior_mode}")

        # Pet mode state
        self.pet_mode_timer = None
        self.pet_mode_state_duration = 0
        self.pet_mode_state_elapsed = 0
        self.pet_mode_target_state = State.IDLE

        # Window walking state tracking
        self.walking_on_window = False  # True if currently on a window surface
        self.walking_on_window_hwnd = None  # HWND of the window we're walking on
        self.drop_support_window_hwnd = None  # Window surface retained during bouncing drop
        self.current_walking_baseline = self.baseline_y  # Current baseline (taskbar or window top)
        # Start pet mode if configured
        if self.behavior_mode == "pet":
            self._start_pet_mode()

    def _start_game_loop(self):
        """Start Pygame update loop via QTimer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        frame_time = int(1000 / self.config.pygame_fps)
        self.timer.start(frame_time)

    def update_game(self):
        """Main Pygame update loop (called every frame)"""
        try:
            self._maybe_enforce_topmost()
            self._refresh_active_window_bounds()
            self._recover_if_display_layout_changed()

            # Process events
            for event in pygame.event.get():
                self._handle_event(event)

            # Update sprite based on state
            self._update_sprite()

            # Update drag position if dragging
            self._update_drag()

            # Update drag/drop physics
            self._update_physics()

            # Render to an alpha surface so transparency comes from the sprite,
            # not from a reserved background color.
            self.render_surface.fill((0, 0, 0, 0))
            self.sprite_group.draw(self.render_surface)
            self._blit_render_surface_to_display()

            # Only update mask if sprite image changed
            if self.sprite.image != self.last_sprite_image:
                self._update_transparency_mask()
                self.last_sprite_image = self.sprite.image

            pygame.display.flip()

            # Maintain framerate
            self.clock.tick(self.config.pygame_fps)
        except pygame.error as exc:
            if self.timer.isActive():
                self.timer.stop()
            print(f"[GAME] Stopping frame update after pygame shutdown: {exc}")

    def _blit_render_surface_to_display(self):
        """Draw visible sprite pixels without blending them against a mask color."""
        display_surface = self.render_surface.copy()
        try:
            alpha = pygame.surfarray.pixels_alpha(display_surface)
            alpha[alpha > 0] = 255
            del alpha
        except (ValueError, TypeError, pygame.error):
            # Some pygame/numpy combinations cannot expose the alpha view without copying.
            # Falling back to the original surface keeps rendering responsive.
            pass

        self.pygame_screen.fill((0, 0, 0))
        self.pygame_screen.blit(display_surface, (0, 0))

    def _recover_if_display_layout_changed(self):
        """Re-anchor the mob when monitor layout changes or when it drifts off-screen."""
        if self.state_machine.current_state in [State.DRAGGED, State.DROPPING]:
            return

        current_virtual_bounds = self._get_virtual_screen_bounds()
        layout_changed = current_virtual_bounds != self.last_virtual_bounds

        x = self.x()
        y = self.y()
        is_offscreen = self._is_window_offscreen(x, y, current_virtual_bounds)

        if not layout_changed and not is_offscreen:
            return

        if layout_changed:
            print("[GAME] Display layout changed - re-anchoring minion")
            self.last_virtual_bounds = current_virtual_bounds

        target_x, target_y = self._recover_visible_position(x, y, current_virtual_bounds)
        self.move(target_x, target_y)
        self.window_x = target_x
        self.baseline_y = target_y
        self.drag_handler.baseline_y = target_y

    def _is_window_offscreen(self, x, y, bounds):
        """Return True when the window is fully outside the virtual desktop bounds."""
        left, top, right, bottom = bounds
        return (
            x + self.window_size <= left or
            x >= right or
            y + self.window_size <= top or
            y >= bottom
        )

    def _recover_visible_position(self, x, y, virtual_bounds):
        """Compute a safe visible position on the nearest monitor baseline."""
        clamped_x, _ = self._clamp_position_to_bounds(x, y, virtual_bounds, clamp_top=False)
        monitor_center_x = clamped_x + self.window_size // 2
        monitor_center_y = y + self.window_size // 2
        baseline_y = self._get_taskbar_baseline_for_point(monitor_center_x, monitor_center_y)
        return clamped_x, baseline_y

    def _handle_event(self, event):
        """Handle Pygame events"""
        if event.type == CLAUDE_STARTED:
            print("[GAME] Received CLAUDE_STARTED event")
            self.claude_active = True
            if self.behavior_mode == "vibe":  # Only respond in vibe mode
                if self.state_machine.current_state in [State.IDLE, State.WALKING]:
                    self.state_machine.transition_to(State.WALKING)

        elif event.type == CLAUDE_STOPPED:
            print("[GAME] Received CLAUDE_STOPPED event")
            self.claude_active = False
            if self.behavior_mode == "vibe":  # Only respond in vibe mode
                if self.state_machine.current_state == State.WALKING:
                    self.state_machine.transition_to(State.IDLE)

        elif event.type == SHOW_MINION:
            # Show with appearing animation
            self.sprite.reset_appearing_animation()
            self.state_machine.transition_to(State.APPEARING)
            self.show()

        elif event.type == HIDE_MINION:
            self.state_machine.transition_to(State.HIDDEN)
            self.hide()

        elif event.type == ACTION_NEEDED:
            self.pending_actions_count += 1
            print(f"[GAME] Received ACTION_NEEDED event (pending: {self.pending_actions_count})")

            # Start waving if not already waving
            current_state = self.state_machine.current_state
            if current_state not in [State.WAVING, State.HIDDEN, State.APPEARING]:
                self.state_before_waving = current_state
                self.state_machine.transition_to(State.WAVING)
                print("[GAME] Started waving animation")

        elif event.type == ACTION_HANDLED:
            self.pending_actions_count = max(0, self.pending_actions_count - 1)
            print(f"[GAME] Received ACTION_HANDLED event (pending: {self.pending_actions_count})")

            # Only stop waving when ALL actions are handled
            if self.pending_actions_count == 0 and self.state_machine.current_state == State.WAVING:
                print("[GAME] All actions handled - stopping waving")
                if self.state_before_waving:
                    self.state_machine.transition_to(self.state_before_waving)
                    self.state_before_waving = None
                elif self.claude_active:
                    self.state_machine.transition_to(State.WALKING)
                else:
                    self.state_machine.transition_to(State.IDLE)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click - drag
                # Store where in the window they clicked
                self.drag_start_offset_x = event.pos[0]
                self.drag_start_offset_y = event.pos[1]
                self.state_machine.transition_to(State.DRAGGED)

        elif event.type == pygame.MOUSEMOTION:
            # Mouse motion events handled in _update_drag() for smoother tracking
            pass

        elif event.type == pygame.MOUSEBUTTONUP:
            if self.state_machine.current_state == State.DRAGGED:
                # Check if we need to drop (if above baseline or has horizontal velocity)
                current_x = self.x()
                current_y = self.y()
                landing_baseline = self._get_landing_baseline(current_x, current_y)
                self.baseline_y = landing_baseline
                self.drag_handler.baseline_y = landing_baseline

                # Calculate throw velocity
                vel_x, vel_y = self.drag_handler.calculate_throw_velocity()

                # Drop if above baseline or has significant throw velocity
                if current_y < landing_baseline or abs(vel_x) > 1 or abs(vel_y) > 1:
                    self._start_dropping_from(current_x, current_y, vel_x, vel_y)
                else:
                    # Already at baseline with no throw velocity
                    self.move(current_x, landing_baseline)
                    self._update_window_walking_state(current_x, landing_baseline)
                    self.drag_handler.mouse_history.clear()
                    if self.claude_active:
                        self.state_machine.transition_to(State.WALKING)
                    else:
                        self.state_machine.transition_to(State.IDLE)

    def _update_sprite(self):
        """Update sprite animation based on state"""
        state = self.state_machine.current_state

        # A new state should interrupt the opposite transition so release can
        # immediately play drag-to-idle instead of waiting for idle-to-drag.
        if state == State.IDLE and self.sprite.playing_idle_to_drag:
            self.sprite.playing_idle_to_drag = False
            self.sprite.idle_to_drag_frame = 0

        if state == State.DRAGGED and self.sprite.playing_drag_to_idle:
            self.sprite.playing_drag_to_idle = False
            self.drag_to_idle_frame_counter = 0
            self.sprite.drag_to_idle_frame = 0

        if state == State.IDLE and self.sprite.playing_idle_to_walking:
            self.sprite.playing_idle_to_walking = False
            self.idle_to_walking_frame_counter = 0
            self.sprite.idle_to_walking_frame = 0

        if state == State.WALKING and self.sprite.playing_walk_to_idle:
            self.sprite.playing_walk_to_idle = False
            self.walk_to_idle_frame_counter = 0
            self.sprite.walk_to_idle_frame = 0

        # Handle drag-to-idle transition animation
        if self.sprite.playing_drag_to_idle:
            self.drag_to_idle_frame_counter += 1
            if self.drag_to_idle_frame_counter >= self.drag_to_idle_frame_update_rate:
                self.drag_to_idle_frame_counter = 0
                self.sprite.update_drag_to_idle_frame()
            # Refresh image for the current transition frame.
            self.sprite.update_state(state)
            # Don't process other state updates while transition is playing
            return

        # Handle idle-to-walking transition animation
        if self.sprite.playing_idle_to_walking:
            self.idle_to_walking_frame_counter += 1
            if self.idle_to_walking_frame_counter >= self.idle_to_walking_frame_update_rate:
                self.idle_to_walking_frame_counter = 0
                self.sprite.update_idle_to_walking_frame()
            # Refresh image for the current transition frame.
            self.sprite.update_state(state)
            # Don't process other state updates while transition is playing
            return

        # Handle walk-to-idle transition animation
        if self.sprite.playing_walk_to_idle:
            self.walk_to_idle_frame_counter += 1
            if self.walk_to_idle_frame_counter >= self.walk_to_idle_frame_update_rate:
                self.walk_to_idle_frame_counter = 0
                self.sprite.update_walk_to_idle_frame()
            # Refresh image for the current transition frame.
            self.sprite.update_state(state)
            # Don't process other state updates while transition is playing
            return

        # Handle idle-to-drag transition animation
        if self.sprite.playing_idle_to_drag:
            self.idle_to_drag_frame_counter += 1
            if self.idle_to_drag_frame_counter >= self.idle_to_drag_frame_update_rate:
                self.idle_to_drag_frame_counter = 0
                self.sprite.update_idle_to_drag_frame()
            # Refresh image for the current transition frame.
            self.sprite.update_state(state)
            # Don't process other state updates while transition is playing
            return

        if state == State.APPEARING:
            # Update appearing animation
            self.appearing_frame_counter += 1
            if self.appearing_frame_counter >= self.appearing_frame_update_rate:
                self.appearing_frame_counter = 0
                is_complete = self.sprite.update_appearing_frame()
                if is_complete:
                    # Appearing animation complete, transition to idle
                    if self.claude_active:
                        self.state_machine.transition_to(State.WALKING)
                    else:
                        self.state_machine.transition_to(State.IDLE)

        elif state == State.DRAGGED or state == State.DROPPING:
            # Update dragged animation
            self.dragged_frame_counter += 1
            if self.dragged_frame_counter >= self.dragged_frame_update_rate:
                self.dragged_frame_counter = 0
                self.sprite.update_dragged_frame()

        elif state == State.WAVING:
            # Update waving animation
            self.waving_frame_counter += 1
            if self.waving_frame_counter >= self.waving_frame_update_rate:
                self.waving_frame_counter = 0
                self.sprite.update_waving_frame()

        elif state == State.WALKING:
            # Update walk frame
            self.walk_frame_counter += 1
            if self.walk_frame_counter >= self.walk_frame_update_rate:
                self.walk_frame_counter = 0
                self.sprite.update_walk_frame()

            # If the mob is meant to walk on a window but that support moved away,
            # switch into a real drop from the current position instead of snapping
            # straight to the taskbar baseline.
            if self.walking_on_window:
                current_window_surface = self._get_current_window_surface(self.window_x, self.baseline_y)
                if current_window_surface is None:
                    self._start_dropping_from(
                        int(self.window_x),
                        int(self.y()),
                        self.walk_direction * max(1.0, float(self.config.movement_speed_px * (self.config.sprite_size / 69.0))),
                        0
                    )
                    return

            # Move window position on screen (not the sprite within the window)
            # Scale movement speed with sprite size (base size = 69px)
            self.config.scale_factor = self.config.sprite_size / 69.0
            scaled_speed = self.config.movement_speed_px * self.config.scale_factor
            next_x = self.window_x + self.walk_direction * scaled_speed

            baseline_y, min_x, max_x = self._get_walk_lane(self.window_x, self.baseline_y)

            # When walking on a window top, stepping past an edge should drop.
            if self.walking_on_window and self._should_drop_from_window_edge(self.window_x, next_x, min_x, max_x):
                edge_x = min(max(next_x, min_x), max_x)
                self.window_x = edge_x
                self.move(int(self.window_x), baseline_y)
                self._start_dropping_from(
                    int(self.window_x),
                    baseline_y,
                    self.walk_direction * max(1.0, float(scaled_speed)),
                    0
                )
                return

            # Check for collision with windows while walking
            if self.config.window_collision_enabled:
                margin = self.config.collision_safe_margin
                if not self._is_position_valid_for_walking(self.window_x, next_x, baseline_y, margin):
                    # Collision detected - reverse direction instead of moving forward
                    self.walk_direction = -self.walk_direction
                    self.sprite.set_walk_direction(self.walk_direction)
                else:
                    # No collision - update position
                    self.window_x = next_x
            else:
                # Collision detection disabled, always move forward
                self.window_x = next_x

            # Check current lane edges (side-by-side windows share a lane)
            if self.window_x <= min_x:
                self.walk_direction = 1
                self.sprite.set_walk_direction(1)
                self.window_x = min_x
            elif self.window_x >= max_x:
                self.walk_direction = -1
                self.sprite.set_walk_direction(-1)
                self.window_x = max_x

            self.baseline_y = baseline_y
            self.drag_handler.baseline_y = baseline_y

            # Update window position (sprite stays centered in window)
            self.move(int(self.window_x), baseline_y)

        # Update sprite image
        self.sprite.update_state(state)

    def _update_drag(self):
        """Update window position during drag (every frame for smooth tracking)"""
        if self.state_machine.current_state == State.DRAGGED:
            # Get current global mouse position
            from PyQt5.QtGui import QCursor
            global_pos = QCursor.pos()

            # Calculate where window should be (mouse - offset from where they clicked)
            screen_x = global_pos.x() - self.drag_start_offset_x
            screen_y = global_pos.y() - self.drag_start_offset_y
            screen_x, screen_y = self._clamp_position_to_bounds(
                screen_x,
                screen_y,
                self._get_virtual_screen_bounds(),
                clamp_top=False
            )

            # Track mouse position for throw velocity calculation
            self.drag_handler.update_mouse_position(global_pos.x(), global_pos.y())

            # Update window position
            self.move(screen_x, screen_y)
            self.window_x = screen_x

    def _update_physics(self):
        """Update drop physics if dropping"""
        if self.state_machine.current_state == State.DROPPING:
            current_time = pygame.time.get_ticks()
            bounds = self._get_virtual_screen_bounds()
            left = bounds[0]
            movement_width = max(self.window_size, bounds[2] - bounds[0])

            self.baseline_y = self._get_landing_baseline(self.drag_handler.drop_x, self.drag_handler.drop_y)
            self.drag_handler.baseline_y = self.baseline_y

            # Drag physics is zero-based; map global position into union-local space.
            self.drag_handler.drop_x -= left
            x_local, y, is_complete = self.drag_handler.update_drop(
                current_time,
                movement_width,
                self.window_size
            )
            self.drag_handler.drop_x += left

            x = x_local + left
            x, y = self._clamp_position_to_bounds(x, y, bounds, clamp_top=False)

            # Update window position (both X and Y)
            self.move(x, y)
            self.window_x = x

            if is_complete:
                # Drop complete, return to baseline
                self.move(self.window_x, self.baseline_y)
                self._update_window_walking_state(self.window_x, self.baseline_y)
                self.drop_support_window_hwnd = None

                # Transition to idle or walking based on Claude state
                if self.claude_active:
                    self.state_machine.transition_to(State.WALKING)
                else:
                    self.state_machine.transition_to(State.IDLE)

    def _start_dropping_from(self, x, y, vel_x=0, vel_y=0):
        """Start drop animation with current position and velocity."""
        current_time = pygame.time.get_ticks()
        self.drag_handler.is_dropping = True
        self.drag_handler.drop_start_y = y
        self.drag_handler.drop_start_time = current_time
        self.drag_handler.last_update_time = current_time
        self.drag_handler.drop_x = float(x)
        self.drag_handler.drop_y = float(y)
        self.drag_handler.velocity_x = vel_x
        self.drag_handler.velocity_y = vel_y
        self.drag_handler.mouse_history.clear()

        # Preserve current platform during bounce so same-height frames do not
        # immediately switch to taskbar baseline while still inside window lane.
        self.drop_support_window_hwnd = self.walking_on_window_hwnd

        # During free-fall we are no longer attached to any walking surface.
        self.walking_on_window = False
        self.walking_on_window_hwnd = None

        self.state_machine.transition_to(State.DROPPING)

    def _get_virtual_screen_bounds(self):
        """Return virtual desktop bounds (all monitors)."""
        if sys.platform == 'win32':
            user32 = ctypes.windll.user32
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79
            left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            return (left, top, left + width, top + height)

        screen = QApplication.primaryScreen().geometry()
        return (0, 0, screen.width(), screen.height())

    def _get_taskbar_baseline_for_point(self, x, y):
        """Return baseline aligned with the monitor work area (taskbar-adjusted)."""
        work_area = self._get_monitor_work_area_for_point(x, y)
        return work_area[3] - self.window_size

    def _get_monitor_work_area_for_point(self, x, y):
        """Get monitor work area for a point, using Win32 APIs on Windows."""
        if sys.platform != 'win32':
            bounds = self._get_virtual_screen_bounds()
            return bounds

        try:
            MONITOR_DEFAULTTONEAREST = 2

            class _MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD),
                ]

            pt = wintypes.POINT(int(x), int(y))
            monitor = ctypes.windll.user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
            if not monitor:
                return self._get_virtual_screen_bounds()

            monitor_info = _MONITORINFO()
            monitor_info.cbSize = ctypes.sizeof(_MONITORINFO)
            ok = ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info))
            if not ok:
                return self._get_virtual_screen_bounds()

            work = monitor_info.rcWork
            return (work.left, work.top, work.right, work.bottom)
        except Exception:
            return self._get_virtual_screen_bounds()

    def _get_walk_lane(self, x, current_baseline):
        """Get walking lane baseline and horizontal limits for current position."""
        if self.config.walk_on_windows_enabled:
            current_window = self._get_current_window_surface(x, current_baseline)
            if current_window is not None:
                left, top, right, _ = current_window["bounds"]
                baseline = top - self.window_size
                min_x = left
                max_x = max(left, right - self.window_size)
                self.walking_on_window = True
                self.walking_on_window_hwnd = current_window.get("hwnd")
                self.current_walking_baseline = baseline
                return baseline, min_x, max_x

        baseline = self._get_taskbar_baseline_for_point(x, current_baseline)
        self.walking_on_window = False
        self.walking_on_window_hwnd = None
        self.current_walking_baseline = baseline

        # If walk_freely is disabled, restrict to current monitor only
        if not self.config.walk_freely:
            bounds = self._get_monitor_work_area_for_point(x, current_baseline)
        else:
            # Walk across the full virtual screen
            bounds = self._get_virtual_screen_bounds()

        return baseline, bounds[0], max(bounds[0], bounds[2] - self.window_size)

    def _should_drop_from_window_edge(self, current_x, next_x, min_x, max_x):
        """Return True only when crossing a window edge from inside to outside."""
        current_inside = min_x <= current_x <= max_x
        next_inside = min_x <= next_x <= max_x
        return current_inside and not next_inside

    def _get_window_platform_by_hwnd(self, hwnd):
        """Return cached window platform dict for hwnd, or None."""
        if hwnd is None:
            return None
        for window in self.window_platforms:
            if window.get("hwnd") == hwnd:
                return window
        return None

    def _get_win32gui_module(self):
        """Return win32gui module when available on Windows, else None."""
        if sys.platform != 'win32':
            return None
        try:
            import win32gui  # type: ignore[import-not-found]
            return win32gui
        except Exception:
            return None

    def _resolve_top_level_hwnd(self, window_handle, win32gui):
        """Resolve a point-hit window handle to its top-level/root owner."""
        if not window_handle:
            return 0

        get_ancestor = getattr(win32gui, "GetAncestor", None)
        if get_ancestor:
            try:
                return get_ancestor(window_handle, 2)  # GA_ROOT
            except Exception:
                pass

        get_parent = getattr(win32gui, "GetParent", None)
        if get_parent:
            try:
                current = window_handle
                while True:
                    parent = get_parent(current)
                    if not parent:
                        return current
                    current = parent
            except Exception:
                return window_handle

        return window_handle

    def _point_hits_window(self, target_hwnd, x, y, win32gui):
        """Return True when the top-level window at point belongs to target_hwnd."""
        try:
            point_hwnd = win32gui.WindowFromPoint((int(x), int(y)))
            if not point_hwnd:
                return False

            own_hwnd = int(self.winId()) if self.winId() else 0
            if own_hwnd and point_hwnd == own_hwnd:
                return False

            if point_hwnd == target_hwnd:
                return True

            return self._resolve_top_level_hwnd(point_hwnd, win32gui) == target_hwnd
        except Exception:
            return False

    def _visible_overlap_on_row(self, window, x, probe_y):
        """Estimate visible overlap width between mob and a window on one row."""
        left, top, right, bottom = window["bounds"]
        mob_left = int(x)
        mob_right = int(x + self.window_size)
        overlap_left = max(mob_left, left)
        overlap_right = min(mob_right, right)
        geometric_overlap = max(0, overlap_right - overlap_left)
        if geometric_overlap <= 0:
            return 0

        # Synthetic/manual platforms (e.g., unit tests or pre-refresh state)
        # have no visibility metadata; use geometric overlap for stability.
        if not window.get("visibility_checked", False):
            return geometric_overlap

        win32gui = self._get_win32gui_module()
        target_hwnd = window.get("hwnd")
        if win32gui is None or target_hwnd is None:
            return geometric_overlap

        if probe_y < top or probe_y >= bottom:
            return 0

        step = max(2, min(12, self.window_size // 6 if self.window_size else 6))
        visible_hits = 0
        samples = 0
        sample_x = overlap_left

        while sample_x < overlap_right:
            samples += 1
            if self._point_hits_window(target_hwnd, sample_x, probe_y, win32gui):
                visible_hits += 1
            sample_x += step

        # Always include the right edge as a sample.
        edge_x = overlap_right - 1
        if edge_x >= overlap_left:
            samples += 1
            if self._point_hits_window(target_hwnd, edge_x, probe_y, win32gui):
                visible_hits += 1

        if samples <= 0 or visible_hits <= 0:
            return 0

        return int((geometric_overlap * visible_hits) / samples)

    def _horizontal_support_overlap(self, x, window):
        """Return horizontal overlap (in px) between mob window and a platform."""
        left, top, right, bottom = window["bounds"]
        height = max(1, bottom - top)
        probe_y = top + min(height - 1, max(1, min(6, height // 4)))
        return self._visible_overlap_on_row(window, x, probe_y)

    def _get_current_window_surface(self, x, current_baseline):
        """Return the window currently acting as the walking surface, if any."""
        if not self.window_platforms:
            return None

        # Treat any visible overlap as support so edge landings keep the window surface.
        min_support_overlap = 1

        # Prefer previously tracked window when still valid.
        if self.walking_on_window and self.walking_on_window_hwnd is not None:
            for window in self.window_platforms:
                if window.get("hwnd") == self.walking_on_window_hwnd:
                    _, top, _, _ = window["bounds"]
                    baseline = top - self.window_size
                    overlap = self._horizontal_support_overlap(x, window)
                    # Keep the tracked surface while any support overlap exists.
                    if overlap > 0 and abs(baseline - current_baseline) <= self.platform_baseline_tolerance_px:
                        return window
                    break

        # Acquire a supporting window under current position/baseline.
        best_window = None
        best_distance = float("inf")
        for window in self.window_platforms:
            _, top, _, _ = window["bounds"]
            overlap = self._horizontal_support_overlap(x, window)
            if overlap < min_support_overlap:
                continue

            baseline = top - self.window_size
            distance = abs(baseline - current_baseline)
            if distance <= self.platform_baseline_tolerance_px and distance < best_distance:
                best_distance = distance
                best_window = window

        return best_window

    def _update_window_walking_state(self, x, baseline_y):
        """Update walking surface tracking after snapping to a baseline."""
        window = None
        if self.config.walk_on_windows_enabled:
            window = self._get_current_window_surface(x, baseline_y)

        if window is None:
            self.walking_on_window = False
            self.walking_on_window_hwnd = None
            self.current_walking_baseline = baseline_y
            return

        self.walking_on_window = True
        self.walking_on_window_hwnd = window.get("hwnd")
        self.current_walking_baseline = baseline_y

    def _get_landing_baseline(self, x, current_y):
        """Choose the nearest landing surface below current position.

        Prefers window tops (when enabled) and falls back to monitor taskbar
        baseline when no valid window platform is below the mob.
        """
        taskbar_baseline = self._get_taskbar_baseline_for_point(x, current_y)

        if not self.config.walk_on_windows_enabled or not self.window_platforms:
            return taskbar_baseline

        # Treat any visible overlap as support so edge landings keep the window surface.
        min_support_overlap = 1

        def _inner_x_bounds(bounds):
            left, _, right, _ = bounds
            return left, max(left, right - self.window_size)

        # While dropping/bouncing, keep the tracked support window as long as x
        # stays inside its inner lane. Once x leaves the lane, allow fall-through.
        if self.drop_support_window_hwnd is not None:
            tracked_window = self._get_window_platform_by_hwnd(self.drop_support_window_hwnd)
            if tracked_window is not None:
                tracked_bounds = tracked_window["bounds"]
                tracked_min_x, tracked_max_x = _inner_x_bounds(tracked_bounds)
                tracked_baseline = tracked_bounds[1] - self.window_size
                tracked_overlap = self._horizontal_support_overlap(x, tracked_window)
                if tracked_min_x <= x <= tracked_max_x and tracked_overlap > 0:
                    return min(taskbar_baseline, tracked_baseline)

            # Tracked window disappeared or x left its inner lane.
            self.drop_support_window_hwnd = None

        candidates = [taskbar_baseline]

        for window in self.window_platforms:
            _, top, _, _ = window["bounds"]
            window_bounds = window["bounds"]
            overlap = self._horizontal_support_overlap(x, window)
            if overlap < min_support_overlap:
                continue

            window_top_baseline = top - self.window_size
            inner_min_x, inner_max_x = _inner_x_bounds(window_bounds)
            in_inner_lane = inner_min_x <= x <= inner_max_x

            # Land only on surfaces strictly below current_y so stepping off
            # a window edge enters a real fall instead of sticking in place.
            if window_top_baseline > current_y:
                candidates.append(window_top_baseline)
                continue

            # When already at platform height during a bounce, keep support only
            # while inside the platform's inner lane.
            if in_inner_lane and abs(window_top_baseline - current_y) <= 1:
                candidates.append(window_top_baseline)
                if self.state_machine.current_state == State.DROPPING:
                    self.drop_support_window_hwnd = window.get("hwnd")

        return min(candidates)

    def _clamp_position_to_bounds(self, x, y, bounds, clamp_top=True):
        """Clamp window position to bounds while optionally allowing movement above top edge."""
        min_x = bounds[0]
        max_x = max(bounds[0], bounds[2] - self.window_size)
        min_y = bounds[1] if clamp_top else -10_000_000
        max_y = max(bounds[1], bounds[3] - self.window_size)
        clamped_x = max(min_x, min(max_x, int(x)))
        clamped_y = max(min_y, min(max_y, int(y)))
        return clamped_x, clamped_y

    def _get_window_z_order_index(self, hwnd):
        """Get z-order index for a window (0 = topmost, higher = further back)."""
        try:
            user32 = ctypes.windll.user32
            z_index = 0
            top_hwnd = user32.GetTopWindow(0)

            while top_hwnd:
                if top_hwnd == hwnd:
                    return z_index
                top_hwnd = user32.GetWindow(top_hwnd, 2)  # GW_HWNDNEXT = 2
                z_index += 1

            return 1000  # Not found, assign high value
        except Exception:
            return 1000

    def _is_position_valid_for_walking(self, current_x, next_x, baseline_y, margin=2):
        """Check if moving from current_x to next_x at baseline_y collides with any window.

        Mob walks on desktop and collides when trying to walk through an application window.
        Only checks collision if the window's height spans the walking level.
        Returns True if safe to move, False if collision detected.
        """
        if not self.window_platforms:
            return True

        for window in self.window_platforms:
            window_left, window_top, window_right, window_bottom = window["bounds"]

            # Check if window's vertical span overlaps with mob's walking height
            sprite_top = baseline_y
            sprite_bottom = baseline_y + self.config.sprite_size

            # No vertical overlap - window doesn't block at this height
            if sprite_bottom < window_top or sprite_top > window_bottom:
                continue

            # Measure overlap on the sprite midline using visible screen coverage.
            probe_y = int(min(window_bottom - 1, max(window_top, baseline_y + self.config.sprite_size // 2)))
            current_overlap = self._visible_overlap_on_row(window, current_x, probe_y)
            next_overlap = self._visible_overlap_on_row(window, next_x, probe_y)

            currently_overlaps = current_overlap > margin
            next_overlaps = next_overlap > margin

            # Collision when entering or exiting a window
            if currently_overlaps != next_overlaps:
                # Moving from inside to outside or vice versa - collision!
                return False

        return True

    def _refresh_active_window_bounds(self, force=False):
        """Refresh visible top-level windows used as movement platforms."""
        if sys.platform != 'win32':
            self.window_platforms = []
            self.window_union_bounds = None
            return

        now_ms = pygame.time.get_ticks()
        if not force and now_ms - self.last_window_bounds_update_ms < self.window_bounds_update_interval_ms:
            return

        self.last_window_bounds_update_ms = now_ms

        try:
            import win32gui  # type: ignore[import-not-found]

            own_hwnd = int(self.winId())
            platforms = []

            # Exclude shell/desktop infrastructure windows that otherwise act as
            # a full-screen invisible blocker for horizontal movement.
            ignored_classes = {
                "progman",
                "workerw",
                "shell_traywnd",
                "shell_secondarytraywnd",
            }

            def enum_handler(hwnd, _):
                if hwnd == own_hwnd:
                    return True
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                if win32gui.IsIconic(hwnd):
                    return True

                try:
                    class_name = win32gui.GetClassName(hwnd).lower()
                    if class_name in ignored_classes:
                        return True
                except Exception:
                    pass

                # Skip tool/owned/cloaked windows. These are typically utility
                # surfaces (or hidden app internals), not interactive blockers.
                try:
                    user32 = ctypes.windll.user32
                    GWL_EXSTYLE = -20
                    GW_OWNER = 4
                    WS_EX_TOOLWINDOW = 0x00000080
                    DWMWA_CLOAKED = 14

                    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    if ex_style & WS_EX_TOOLWINDOW:
                        return True

                    owner = user32.GetWindow(hwnd, GW_OWNER)
                    if owner:
                        return True

                    cloaked = wintypes.DWORD(0)
                    result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
                        hwnd,
                        DWMWA_CLOAKED,
                        ctypes.byref(cloaked),
                        ctypes.sizeof(cloaked)
                    )
                    if result == 0 and cloaked.value != 0:
                        return True
                except Exception:
                    pass

                bounds = self._get_window_bounds_win32(hwnd, win32gui)
                if bounds is None:
                    return True

                left, top, right, bottom = bounds
                if right - left < self.window_size or bottom - top < self.window_size:
                    return True

                if self._is_window_fully_occluded(hwnd, bounds, win32gui):
                    return True

                z_index = self._get_window_z_order_index(hwnd)
                platforms.append({
                    "bounds": bounds,
                    "hwnd": hwnd,
                    "z_index": z_index,
                    "visibility_checked": True
                })
                return True

            win32gui.EnumWindows(enum_handler, None)

            if not platforms:
                self.window_platforms = []
                self.window_union_bounds = None
                return

            self.window_platforms = sorted(platforms, key=lambda w: w["z_index"])

            min_left = min(w["bounds"][0] for w in self.window_platforms)
            min_top = min(w["bounds"][1] for w in self.window_platforms)
            max_right = max(w["bounds"][2] for w in self.window_platforms)
            max_bottom = max(w["bounds"][3] for w in self.window_platforms)
            self.window_union_bounds = (min_left, min_top, max_right, max_bottom)
        except Exception as exc:
            print(f"[GAME] Could not refresh window bounds: {exc}")

    def _get_window_bounds_win32(self, hwnd, win32gui):
        """Get window bounds, preferring DWM extended frame bounds."""
        try:
            rect = wintypes.RECT()
            DWMWA_EXTENDED_FRAME_BOUNDS = 9
            result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
                hwnd,
                DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(rect),
                ctypes.sizeof(rect)
            )
            if result == 0 and rect.right > rect.left and rect.bottom > rect.top:
                return (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            pass

        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            if right > left and bottom > top:
                return (left, top, right, bottom)
        except Exception:
            return None

        return None

    def _is_window_fully_occluded(self, hwnd, bounds, win32gui):
        """Return True when sampled points inside a window are all covered."""
        try:
            left, top, right, bottom = bounds
            width = right - left
            height = bottom - top
            if width <= 2 or height <= 2:
                return False

            # Probe interior points to avoid edge artifacts from rounded corners,
            # drop-shadows, and frame margins.
            probe_ratios = (0.20, 0.35, 0.50, 0.65, 0.80)
            x_offsets = [max(1, min(width - 2, int(width * ratio))) for ratio in probe_ratios]
            y_offsets = [max(1, min(height - 2, int(height * ratio))) for ratio in probe_ratios]

            probe_points = set()
            for x_offset in x_offsets:
                x = left + min(width - 2, max(1, x_offset))
                for y_offset in y_offsets:
                    y = top + min(height - 2, max(1, y_offset))
                    probe_points.add((int(x), int(y)))

            visible_hit_count = 0
            sampled_count = 0
            min_visible_hits = 2
            own_hwnd = int(self.winId()) if self.winId() else 0

            for x, y in probe_points:
                point_hwnd = win32gui.WindowFromPoint((x, y))
                if not point_hwnd:
                    continue

                if own_hwnd and point_hwnd == own_hwnd:
                    continue

                sampled_count += 1

                root_hwnd = self._resolve_top_level_hwnd(point_hwnd, win32gui)
                if root_hwnd == hwnd or point_hwnd == hwnd:
                    visible_hit_count += 1
                    if visible_hit_count >= min_visible_hits:
                        return False

            if sampled_count == 0:
                return False

            return True
        except Exception:
            return False

    def _update_transparency_mask(self):
        """Update window mask from rendered sprite alpha."""
        import numpy as np
        from PyQt5.QtCore import QRect
        from PyQt5.QtGui import QRegion

        try:
            # Get rendered alpha data from the offscreen surface.
            alpha_data = pygame.surfarray.array_alpha(self.render_surface)
        except (ValueError, TypeError, pygame.error):
            return

        # array_alpha is shaped as (width, height), so transpose it to y/x coordinates.
        is_visible = alpha_data.T > 24

        region = QRegion()
        for y, row in enumerate(is_visible):
            visible_columns = np.flatnonzero(row)
            if visible_columns.size == 0:
                continue

            run_start = int(visible_columns[0])
            run_end = run_start

            for x in visible_columns[1:]:
                x = int(x)
                if x == run_end + 1:
                    run_end = x
                    continue

                region = region.united(QRegion(QRect(run_start, y, run_end - run_start + 1, 1)))
                run_start = run_end = x

            region = region.united(QRegion(QRect(run_start, y, run_end - run_start + 1, 1)))

        # Apply region as mask
        self.setMask(region)

    def on_state_changed(self, new_state):
        """Handle state changes"""
        print(f"[GAME] State changed to: {new_state}")
        if new_state == State.HIDDEN:
            print("[GAME] Hiding window")
            self.hide()
        else:
            print("[GAME] Showing window")
            self.show()
            self._ensure_on_top()

    def showEvent(self, event):
        """Re-assert topmost when the window is shown."""
        super().showEvent(event)
        self._ensure_on_top()

    def _maybe_enforce_topmost(self):
        """Periodically enforce always-on-top to recover from z-order loss."""
        if not self.isVisible() or self.state_machine.current_state == State.HIDDEN:
            return

        current_time = pygame.time.get_ticks()
        if current_time - self.last_topmost_enforce_ms >= self.topmost_enforce_interval_ms:
            self._ensure_on_top()
            self.last_topmost_enforce_ms = current_time

    def _ensure_on_top(self):
        """Keep window above other windows using Qt and a Win32 fallback."""
        self.raise_()

        # Reassert with Win32 to prevent other regular windows from covering the minion.
        if sys.platform == 'win32':
            try:
                hwnd = int(self.winId())
                HWND_TOPMOST = -1
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOACTIVATE = 0x0010
                SWP_SHOWWINDOW = 0x0040

                ctypes.windll.user32.SetWindowPos(
                    hwnd,
                    HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
                )
            except Exception as exc:
                print(f"[GAME] Failed to enforce topmost via Win32: {exc}")

    def mousePressEvent(self, event):
        """Handle mouse press events at Qt level (works with mask, bypasses pygame transparency)"""
        from PyQt5.QtCore import Qt as QtCore

        if event.button() == QtCore.RightButton:
            # Right-click detected - show context menu
            print(f"[GAME] Qt right-click detected at: {event.pos()}")
            self._show_context_menu()
            event.accept()
        else:
            # Pass other events to parent (for drag handling via pygame)
            super().mousePressEvent(event)

    def _show_context_menu(self):
        """Show right-click context menu for behavior mode selection"""
        from PyQt5.QtWidgets import QMenu, QAction
        from PyQt5.QtCore import QPoint

        print("[GAME] Creating context menu...")

        # Get window position
        window_pos = self.pos()
        print(f"[GAME] Window position: {window_pos.x()}, {window_pos.y()}")

        # Calculate menu position above the sprite (centered horizontally, above vertically)
        menu_x = window_pos.x() + self.window_size // 2
        menu_y = window_pos.y() - 80  # 80 pixels above the sprite
        menu_pos = QPoint(menu_x, menu_y)
        print(f"[GAME] Menu will appear at: {menu_x}, {menu_y}")

        # Create menu with self as parent for proper window hierarchy
        menu = QMenu(self)

        # Ensure menu appears on top with proper window flags
        menu.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)

        # Add stylesheet to make menu visible with proper background
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #999999;
                padding: 5px;
                border-radius: 3px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 5px 25px 5px 25px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QMenu::item:checked {
                font-weight: bold;
            }
            QMenu::separator {
                height: 1px;
                background-color: #cccccc;
                margin: 5px 10px;
            }
        """)
        print("[GAME] Menu stylesheet applied")

        # Pet mode option
        pet_action = QAction("Pet mode (random walking)", menu)
        pet_action.setCheckable(True)
        pet_action.setChecked(self.behavior_mode == "pet")
        pet_action.triggered.connect(lambda: self.set_behavior_mode("pet"))
        menu.addAction(pet_action)

        # Vibe mode option
        claude_action = QAction("Vibe mode (activity-driven)", menu)
        claude_action.setCheckable(True)
        claude_action.setChecked(self.behavior_mode == "vibe")
        claude_action.triggered.connect(lambda: self.set_behavior_mode("vibe"))
        menu.addAction(claude_action)

        menu.addSeparator()

        # Remove option
        remove_action = QAction("Remove minion", menu)
        remove_action.triggered.connect(self.remove_instance)
        menu.addAction(remove_action)

        # Show menu using popup above the sprite
        print("[GAME] Showing menu above sprite...")
        menu.popup(menu_pos)
        menu.raise_()  # Ensure menu appears on top
        menu.activateWindow()  # Give menu focus
        print("[GAME] Menu popup called")

    def set_behavior_mode(self, mode):
        """Switch behavior mode between pet and vibe."""
        print(f"[GAME] Switching to {mode} mode")
        self.behavior_mode = mode
        self.config.behavior_mode = mode
        self.config.save()

        if mode == "pet":
            self._start_pet_mode()
        else:  # vibe mode
            self._stop_pet_mode()
            # Return to appropriate state based on current activity state
            if self.state_machine.current_state in [State.IDLE, State.WALKING]:
                if self.claude_active:
                    self.state_machine.transition_to(State.WALKING)
                else:
                    self.state_machine.transition_to(State.IDLE)

    def _start_pet_mode(self):
        """Start pet mode with random walking/idle behavior"""
        print("[GAME] Starting pet mode")
        if self.pet_mode_timer:
            self.pet_mode_timer.stop()

        self.pet_mode_timer = QTimer()
        self.pet_mode_timer.timeout.connect(self._update_pet_mode)
        self.pet_mode_timer.start(100)  # 10Hz update
        self._choose_next_pet_state()

    def _stop_pet_mode(self):
        """Stop pet mode timer"""
        print("[GAME] Stopping pet mode")
        if self.pet_mode_timer:
            self.pet_mode_timer.stop()
            self.pet_mode_timer = None

    def _choose_next_pet_state(self):
        """Randomly choose next state and duration"""
        import random

        # 60% walking, 40% idle
        if random.random() < 0.6:
            self.pet_mode_target_state = State.WALKING
            self.walk_direction = random.choice([-1, 1])
            self.sprite.set_walk_direction(self.walk_direction)
            self.pet_mode_state_duration = random.uniform(2.0, 8.0)  # Walk 2-8 seconds
        else:
            self.pet_mode_target_state = State.IDLE
            self.pet_mode_state_duration = random.uniform(1.0, 5.0)  # Idle 1-5 seconds

        self.pet_mode_state_elapsed = 0
        self.state_machine.transition_to(self.pet_mode_target_state)
        print(f"[PET MODE] Switching to {self.pet_mode_target_state.name} for {self.pet_mode_state_duration:.1f}s")

    def _update_pet_mode(self):
        """Update pet mode state machine (called every 100ms)"""
        if self.behavior_mode != "pet":
            return

        # Don't interfere with drag/drop/waving
        if self.state_machine.current_state in [State.DRAGGED, State.DROPPING, State.WAVING]:
            return

        # Update timer
        self.pet_mode_state_elapsed += 0.1

        # Switch states when duration expires
        if self.pet_mode_state_elapsed >= self.pet_mode_state_duration:
            self._choose_next_pet_state()

    def remove_instance(self):
        """Handle remove minion - close the application"""
        print("[GAME] Remove minion requested - closing application")
        # Close the window, which triggers closeEvent for proper cleanup
        self.close()
        QApplication.quit()
        sys.exit(0)

    def closeEvent(self, event):
        """Clean up resources before window closes"""
        self.timer.stop()
        if self.pet_mode_timer:
            self.pet_mode_timer.stop()
        pygame.quit()
        event.accept()
