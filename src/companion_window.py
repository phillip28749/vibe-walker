"""Lightweight companion window for additional active sessions."""

import random

import pygame
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

from src.sprite_manager import CharacterSprite
from src.state_machine import State


class CompanionWindow(QWidget):
    """Simple always-on-top mob used for extra concurrent sessions."""

    window_closed = pyqtSignal(object)

    def __init__(self, config, slot_index=0):
        super().__init__()
        self.config = config
        self.slot_index = slot_index
        self.window_size = self.config.sprite_size
        self.walk_direction = random.choice([-1, 1])
        self.walk_frame_counter = 0
        self.walk_frame_update_rate = max(1, self.config.pygame_fps // self.config.animation_fps)
        self.animation_frame_update_rate = self.walk_frame_update_rate
        self.lifecycle_state = "appearing"

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedSize(self.window_size, self.window_size)

        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self.window_size, self.window_size)
        self.label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.label.setScaledContents(True)

        self.sprite = CharacterSprite(
            sprite_size=self.config.sprite_size,
            use_dragged_animation=self.config.dragged_animation_enabled,
        )
        self.sprite.set_walk_direction(self.walk_direction)
        self.sprite.reset_appearing_animation()
        self.sprite.current_state = State.APPEARING
        self.sprite.image = self.sprite._get_sprite_for_state(State.APPEARING)

        self._position_initially()
        self._render_current_frame()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(max(1, int(1000 / self.config.pygame_fps)))

    def _set_initial_walking_frame(self):
        """Switch to a direct walking frame instead of a transition frame."""
        self.sprite.walk_frame = 0
        self.sprite.current_state = State.WALKING
        self.sprite.image = self.sprite._get_sprite_for_state(State.WALKING)

    def begin_fade_out(self):
        """Play the fade animation before closing the companion."""
        if self.lifecycle_state == "fading":
            return
        self.lifecycle_state = "fading"
        self.sprite.reset_fade_animation()
        self.sprite.image = self.sprite.images["FADE"][0]

    def cancel_fade_out(self):
        """Return a fading companion to walking if activity resumes."""
        if self.lifecycle_state != "fading":
            return
        self.lifecycle_state = "walking"
        self._set_initial_walking_frame()

    def is_fading(self):
        """Return True when the companion is despawning."""
        return self.lifecycle_state == "fading"

    def _position_initially(self):
        """Spawn companions at visible, staggered taskbar positions."""
        screen = QApplication.primaryScreen().availableGeometry()
        min_x = screen.left()
        max_x = max(screen.left(), screen.right() - self.window_size + 1)
        baseline_y = screen.bottom() - self.window_size + 1

        if self.config.random_spawn_enabled:
            x = random.randint(min_x, max_x)
        else:
            center_x = screen.left() + max(0, (screen.width() - self.window_size) // 2)
            spacing = self.window_size + 12
            x = min(max_x, center_x + (self.slot_index * spacing))

        self.move(x, baseline_y)

    def _update_frame(self):
        """Advance a simple walking animation and bounce at screen edges."""
        if self.lifecycle_state == "appearing":
            self.walk_frame_counter += 1
            if self.walk_frame_counter >= self.animation_frame_update_rate:
                self.walk_frame_counter = 0
                if self.sprite.update_appearing_frame():
                    self.lifecycle_state = "walking"
                    self._set_initial_walking_frame()
                else:
                    self.sprite.image = self.sprite._get_sprite_for_state(State.APPEARING)
            self._render_current_frame()
            return

        if self.lifecycle_state == "fading":
            self.walk_frame_counter += 1
            if self.walk_frame_counter >= self.animation_frame_update_rate:
                self.walk_frame_counter = 0
                if self.sprite.update_fade_frame():
                    self.close()
                    return
                self.sprite.image = self.sprite.images["FADE"][self.sprite.fade_frame]
            self._render_current_frame()
            return

        screen = QApplication.primaryScreen().availableGeometry()
        min_x = screen.left()
        max_x = max(screen.left(), screen.right() - self.window_size + 1)

        next_x = self.x() + (self.config.movement_speed_px * self.walk_direction)
        if next_x <= min_x or next_x >= max_x:
            self.walk_direction *= -1
            self.sprite.set_walk_direction(self.walk_direction)
            next_x = max(min_x, min(max_x, next_x))

        self.move(next_x, self.y())

        self.walk_frame_counter += 1
        if self.walk_frame_counter >= self.walk_frame_update_rate:
            self.walk_frame_counter = 0
            self.sprite.update_walk_frame()

        self.sprite.update_state(State.WALKING)
        self._render_current_frame()

    def _render_current_frame(self):
        """Draw the current sprite frame into the label."""
        surface = self.sprite.image
        width, height = surface.get_size()
        image = QImage(
            pygame.image.tostring(surface, "RGBA"),
            width,
            height,
            QImage.Format_RGBA8888,
        ).copy()
        self.label.setPixmap(QPixmap.fromImage(image))

    def closeEvent(self, event):
        """Stop timers before closing the companion window."""
        self.timer.stop()
        self.window_closed.emit(self)
        super().closeEvent(event)
