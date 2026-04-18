import os
import sys
import pygame
import random
from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QScreen, QImage, QPixmap, QRegion, QBitmap
from src.sprite_manager import CharacterSprite
from src.state_machine import State, StateMachine
from src.drag_handler import DragHandler
from src.activity_bridge import CLAUDE_STARTED, CLAUDE_STOPPED, SHOW_MINION, HIDE_MINION, ACTION_NEEDED, ACTION_HANDLED


class GameWindow(QMainWindow):
    """PyQt5 window with embedded Pygame surface"""

    def __init__(self, config, state_machine, spawn_from=None):
        super().__init__()
        self.config = config
        self.state_machine = state_machine
        self.spawn_from = spawn_from  # Optional (x, y) position to spawn from

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

        baseline_y = screen.height() - self.config.baseline_y_offset - size

        # If spawn position provided, start there and drop straight down
        if self.spawn_from is not None:
            spawn_x, spawn_y = self.spawn_from
            # Center the window on the spawn point
            x = spawn_x - size // 2
            y = spawn_y - size // 2
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
                baseline_x = screen.width() // 2

            self.move(baseline_x, baseline_y)
            self.window_x = baseline_x
            self.baseline_y = baseline_y
            self.initial_window_x = baseline_x

        self.baseline_screen_height = screen.height()

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
        self.clock = pygame.time.Clock()

        # Set transparent color key (magenta - will be made transparent via mask)
        self.transparent_color = (255, 0, 255)

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
        self.walk_frame_update_rate = self.config.pygame_fps // self.config.animation_fps

        # Dragged animation state
        self.dragged_frame_counter = 0
        self.dragged_frame_update_rate = self.config.pygame_fps // self.config.animation_fps

        # Waving animation state
        self.waving_frame_counter = 0
        self.waving_frame_update_rate = self.config.pygame_fps // self.config.animation_fps

        # Appearing animation state
        self.appearing_frame_counter = 0
        self.appearing_frame_update_rate = self.config.pygame_fps // self.config.animation_fps

        # Track window position on screen for walking
        self.window_x = self.initial_window_x

        # Position sprite centered in window
        self.sprite.rect.x = (self.window_size - self.config.sprite_size) // 2
        self.sprite.rect.y = (self.window_size - self.config.sprite_size) // 2

        # Connect state machine signals
        self.state_machine.state_changed.connect(self.on_state_changed)

        # Track Claude Code activity state
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
        # Process events
        for event in pygame.event.get():
            self._handle_event(event)

        # Update sprite based on state
        self._update_sprite()

        # Update drag position if dragging
        self._update_drag()

        # Update drag/drop physics
        self._update_physics()

        # Render with magenta background (will be masked as transparent)
        self.pygame_screen.fill(self.transparent_color)
        self.sprite_group.draw(self.pygame_screen)

        # Create transparency mask (magenta pixels become transparent)
        self._update_transparency_mask()

        pygame.display.flip()

        # Maintain framerate
        self.clock.tick(self.config.pygame_fps)

    def _handle_event(self, event):
        """Handle Pygame events"""
        if event.type == CLAUDE_STARTED:
            print("[GAME] Received CLAUDE_STARTED event")
            self.claude_active = True
            if self.behavior_mode == "claude":  # Only respond in claude mode
                if self.state_machine.current_state in [State.IDLE, State.WALKING]:
                    self.state_machine.transition_to(State.WALKING)

        elif event.type == CLAUDE_STOPPED:
            print("[GAME] Received CLAUDE_STOPPED event")
            self.claude_active = False
            if self.behavior_mode == "claude":  # Only respond in claude mode
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
            elif event.button == 3:  # Right click - context menu
                print(f"[GAME] Right-click detected at pygame pos: {event.pos}")
                self._show_context_menu()

        elif event.type == pygame.MOUSEMOTION:
            # Mouse motion events handled in _update_drag() for smoother tracking
            pass

        elif event.type == pygame.MOUSEBUTTONUP:
            if self.state_machine.current_state == State.DRAGGED:
                # Check if we need to drop (if above baseline)
                if self.y() < self.baseline_y:
                    # Start drop animation
                    self.drag_handler.is_dropping = True
                    self.drag_handler.drop_start_y = self.y()
                    self.drag_handler.drop_start_time = pygame.time.get_ticks()
                    self.state_machine.transition_to(State.DROPPING)
                else:
                    # Already at or below baseline
                    if self.claude_active:
                        self.state_machine.transition_to(State.WALKING)
                    else:
                        self.state_machine.transition_to(State.IDLE)

    def _update_sprite(self):
        """Update sprite animation based on state"""
        state = self.state_machine.current_state

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

            # Move window position on screen (not the sprite within the window)
            self.window_x += self.walk_direction * self.config.movement_speed_px

            # Check screen edges
            screen = QApplication.primaryScreen().geometry()
            if self.window_x <= 0:
                self.walk_direction = 1
                self.sprite.set_walk_direction(1)
            elif self.window_x >= screen.width() - self.window_size:
                self.walk_direction = -1
                self.sprite.set_walk_direction(-1)

            # Update window position (sprite stays centered in window)
            self.move(self.window_x, self.baseline_y)

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

            # Update window position
            self.move(screen_x, screen_y)
            self.window_x = screen_x

    def _update_physics(self):
        """Update drop physics if dropping"""
        if self.state_machine.current_state == State.DROPPING:
            current_time = pygame.time.get_ticks()
            y, is_complete = self.drag_handler.update_drop(current_time)

            # Update window Y position (sprite stays centered in window)
            self.move(self.window_x, y)

            if is_complete:
                # Drop complete, return to baseline
                self.move(self.window_x, self.baseline_y)

                # Transition to idle or walking based on Claude state
                if self.claude_active:
                    self.state_machine.transition_to(State.WALKING)
                else:
                    self.state_machine.transition_to(State.IDLE)

    def _update_transparency_mask(self):
        """Update window mask to make magenta pixels transparent"""
        # Get pygame surface data as RGBA for proper 4-byte alignment
        surf_data = pygame.image.tostring(self.pygame_screen, 'RGBA')

        # Create QImage from pygame surface with explicit bytes per line
        # RGBA = 4 bytes per pixel (naturally aligned)
        bytes_per_line = self.window_size * 4
        img = QImage(surf_data, self.window_size, self.window_size, bytes_per_line, QImage.Format_RGBA8888)

        # Create mask: pixels matching magenta become transparent
        mask = QBitmap(self.window_size, self.window_size)
        mask.fill(Qt.color0)  # Start with all transparent

        # Paint non-magenta pixels as visible
        from PyQt5.QtGui import QPainter, QColor
        painter = QPainter(mask)

        for y in range(self.window_size):
            for x in range(self.window_size):
                pixel = img.pixel(x, y)
                color = QColor(pixel)
                # If not magenta or near-magenta (within threshold), mark as visible
                # This handles anti-aliased edges from smoothscale
                r, g, b = color.red(), color.green(), color.blue()
                is_magenta = (abs(r - 255) < 10 and abs(g - 0) < 10 and abs(b - 255) < 10)

                if not is_magenta:
                    painter.setPen(Qt.color1)
                    painter.drawPoint(x, y)

        painter.end()

        # Apply mask to window
        self.setMask(mask)

    def on_state_changed(self, new_state):
        """Handle state changes"""
        print(f"[GAME] State changed to: {new_state}")
        if new_state == State.HIDDEN:
            print("[GAME] Hiding window")
            self.hide()
        else:
            print("[GAME] Showing window")
            self.show()

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
        from PyQt5.QtGui import QCursor
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

        # Claude mode option
        claude_action = QAction("Claude mode (activity-driven)", menu)
        claude_action.setCheckable(True)
        claude_action.setChecked(self.behavior_mode == "claude")
        claude_action.triggered.connect(lambda: self.set_behavior_mode("claude"))
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
        """Switch behavior mode between pet and claude"""
        print(f"[GAME] Switching to {mode} mode")
        self.behavior_mode = mode
        self.config.behavior_mode = mode
        self.config.save()

        if mode == "pet":
            self._start_pet_mode()
        else:  # claude mode
            self._stop_pet_mode()
            # Return to appropriate state based on current Claude activity
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
        # Direct quit without confirmation to avoid hanging the pygame/Qt event loop
        QApplication.quit()

    def closeEvent(self, event):
        """Clean up resources before window closes"""
        self.timer.stop()
        if self.pet_mode_timer:
            self.pet_mode_timer.stop()
        pygame.quit()
        event.accept()
