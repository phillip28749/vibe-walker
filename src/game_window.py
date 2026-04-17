import os
import sys
import pygame
import random
from PyQt5.QtWidgets import QMainWindow, QWidget
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QScreen
from src.sprite_manager import CharacterSprite
from src.state_machine import State, StateMachine
from src.drag_handler import DragHandler
from src.activity_bridge import CLAUDE_STARTED, CLAUDE_STOPPED, SHOW_MINION, HIDE_MINION


class GameWindow(QMainWindow):
    """PyQt5 window with embedded Pygame surface"""

    def __init__(self, config, state_machine):
        super().__init__()
        self.config = config
        self.state_machine = state_machine

        # Setup window
        self._setup_window()

        # Embed Pygame
        self._setup_pygame()

        # Initialize game objects
        self._init_game_objects()

        # Start game loop
        self._start_game_loop()

    def _setup_window(self):
        """Configure PyQt5 window properties"""
        # Frameless, transparent, always-on-top
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        # Set fixed size
        size = self.config.sprite_size
        self.setFixedSize(size, size)

        # Create container widget for Pygame
        self.embed = QWidget(self)
        self.embed.setGeometry(0, 0, size, size)
        self.setCentralWidget(self.embed)

        # Position at baseline
        self._position_at_baseline()

    def _position_at_baseline(self):
        """Position window at baseline with optional random X"""
        screen = self.screen().geometry()

        if self.config.random_spawn_enabled:
            x = random.randint(0, screen.width() - self.config.sprite_size)
        else:
            x = screen.width() // 2

        y = screen.height() - self.config.baseline_y_offset - self.config.sprite_size

        self.move(x, y)
        self.baseline_y = y
        self.baseline_screen_height = screen.height()

    def _setup_pygame(self):
        """Initialize Pygame surface embedded in Qt widget"""
        # Tell SDL to use our Qt widget
        os.environ['SDL_WINDOWID'] = str(int(self.embed.winId()))
        os.environ['SDL_VIDEODRIVER'] = 'windib' if sys.platform == 'win32' else 'x11'

        # Initialize Pygame
        pygame.init()
        pygame.display.init()

        # Create display surface
        size = self.config.sprite_size
        self.screen = pygame.display.set_mode((size, size), pygame.NOFRAME)
        self.clock = pygame.time.Clock()

    def _init_game_objects(self):
        """Initialize sprite, drag handler, etc."""
        # Create sprite
        self.sprite = CharacterSprite(sprite_size=self.config.sprite_size)
        self.sprite_group = pygame.sprite.Group(self.sprite)

        # Create drag handler
        self.drag_handler = DragHandler(
            sprite_size=self.config.sprite_size,
            baseline_y=0,  # Relative to window
            drop_duration_ms=self.config.drop_duration_ms
        )

        # Walking state
        self.walk_direction = 1  # 1 = right, -1 = left
        self.walk_frame_counter = 0
        self.walk_frame_update_rate = self.config.pygame_fps // self.config.animation_fps

        # Position sprite at bottom of window
        self.sprite.rect.x = 0
        self.sprite.rect.y = 0

        # Connect state machine signals
        self.state_machine.state_changed.connect(self.on_state_changed)

        # Track Claude Code activity state
        self.claude_active = False

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

        # Update drag/drop physics
        self._update_physics()

        # Render
        self.screen.fill((0, 0, 0, 0))  # Transparent
        self.sprite_group.draw(self.screen)
        pygame.display.flip()

        # Maintain framerate
        self.clock.tick(self.config.pygame_fps)

    def _handle_event(self, event):
        """Handle Pygame events"""
        if event.type == CLAUDE_STARTED:
            self.claude_active = True
            if self.state_machine.current_state in [State.IDLE, State.WALKING]:
                self.state_machine.transition_to(State.WALKING)

        elif event.type == CLAUDE_STOPPED:
            self.claude_active = False
            if self.state_machine.current_state == State.WALKING:
                self.state_machine.transition_to(State.IDLE)

        elif event.type == SHOW_MINION:
            self.state_machine.transition_to(State.IDLE)
            self.show()

        elif event.type == HIDE_MINION:
            self.state_machine.transition_to(State.HIDDEN)
            self.hide()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            result = self.drag_handler.handle_mouse_down(event.pos, self.sprite.rect)
            if result == State.DRAGGED:
                self.state_machine.transition_to(State.DRAGGED)

        elif event.type == pygame.MOUSEMOTION:
            if self.state_machine.current_state == State.DRAGGED:
                new_pos = self.drag_handler.handle_mouse_motion(event.pos)
                if new_pos:
                    # Update sprite position within window
                    self.sprite.rect.x = new_pos[0]
                    self.sprite.rect.y = new_pos[1]

                    # Update window position on screen
                    screen_x = self.x() + new_pos[0]
                    screen_y = self.y() + new_pos[1]
                    self.move(screen_x, screen_y)

        elif event.type == pygame.MOUSEBUTTONUP:
            if self.state_machine.current_state == State.DRAGGED:
                result = self.drag_handler.handle_mouse_up(self.sprite.rect.y)
                if result == State.DROPPING:
                    self.state_machine.transition_to(State.DROPPING)

    def _update_sprite(self):
        """Update sprite animation based on state"""
        state = self.state_machine.current_state

        if state == State.WALKING:
            # Update walk frame
            self.walk_frame_counter += 1
            if self.walk_frame_counter >= self.walk_frame_update_rate:
                self.walk_frame_counter = 0
                self.sprite.update_walk_frame()

            # Move sprite
            self.sprite.rect.x += self.walk_direction * self.config.movement_speed_px

            # Check screen edges
            screen = self.screen().geometry()
            if self.sprite.rect.x <= 0:
                self.walk_direction = 1
                self.sprite.set_walk_direction(1)
            elif self.sprite.rect.x >= screen.width() - self.config.sprite_size:
                self.walk_direction = -1
                self.sprite.set_walk_direction(-1)

            # Update window position
            self.move(self.sprite.rect.x, self.baseline_y)

        # Update sprite image
        self.sprite.update_state(state)

    def _update_physics(self):
        """Update drop physics if dropping"""
        if self.state_machine.current_state == State.DROPPING:
            current_time = pygame.time.get_ticks()
            y, is_complete = self.drag_handler.update_drop(current_time)

            # Update sprite Y position
            self.sprite.rect.y = y

            # Update window Y position
            self.move(self.sprite.rect.x, self.baseline_y + y)

            if is_complete:
                # Drop complete, return to baseline
                self.sprite.rect.y = 0
                self.move(self.sprite.rect.x, self.baseline_y)

                # Transition to idle or walking based on Claude state
                if self.claude_active:
                    self.state_machine.transition_to(State.WALKING)
                else:
                    self.state_machine.transition_to(State.IDLE)

    def on_state_changed(self, new_state):
        """Handle state changes"""
        if new_state == State.HIDDEN:
            self.hide()
        else:
            self.show()
