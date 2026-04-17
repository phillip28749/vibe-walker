import pygame
import os
from src.state_machine import State


class CharacterSprite(pygame.sprite.Sprite):
    """Pygame sprite for the desktop pet character"""

    def __init__(self, sprite_size=64):
        super().__init__()
        self.sprite_size = sprite_size
        self.images = {}
        self.current_state = State.IDLE
        self.walk_frame = 0
        self.walk_direction = 1  # 1 = right, -1 = left

        # Load sprite images
        self._load_images()

        # Initialize rect
        self.image = self.images[State.IDLE]
        self.rect = self.image.get_rect()

    def _load_images(self):
        """Load all sprite images from disk"""
        sprite_dir = "sprites"

        # Load idle sprite
        idle_path = os.path.join(sprite_dir, "idle.png")
        self.images[State.IDLE] = self._load_sprite(idle_path)

        # Load walking sprites (2 frames per direction)
        self.images[State.WALKING] = {
            "left": [
                self._load_sprite(os.path.join(sprite_dir, "walk_left_1.png")),
                self._load_sprite(os.path.join(sprite_dir, "walk_left_2.png"))
            ],
            "right": [
                self._load_sprite(os.path.join(sprite_dir, "walk_right_1.png")),
                self._load_sprite(os.path.join(sprite_dir, "walk_right_2.png"))
            ]
        }

        # Load dragged sprite
        dragged_path = os.path.join(sprite_dir, "dragged.png")
        if os.path.exists(dragged_path):
            self.images[State.DRAGGED] = self._load_sprite(dragged_path)
        else:
            # Fallback to idle if dragged sprite doesn't exist yet
            self.images[State.DRAGGED] = self.images[State.IDLE]

    def _load_sprite(self, path):
        """Load and scale a sprite image"""
        if not os.path.exists(path):
            # Create placeholder surface
            surface = pygame.Surface((self.sprite_size, self.sprite_size), pygame.SRCALPHA)
            surface.fill((255, 0, 255, 128))  # Magenta placeholder
            return surface

        # Ensure display is set for convert_alpha to work
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1), pygame.HIDDEN)

        image = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(image, (self.sprite_size, self.sprite_size))

    def update_state(self, state):
        """Update sprite based on state

        Args:
            state: State enum member
        """
        self.current_state = state

        if state == State.IDLE:
            self.image = self.images[State.IDLE]
        elif state == State.DRAGGED or state == State.DROPPING:
            # Both dragged and dropping use the dragged sprite
            self.image = self.images[State.DRAGGED]
        elif state == State.WALKING:
            # Animate walking
            direction = "right" if self.walk_direction > 0 else "left"
            self.image = self.images[State.WALKING][direction][self.walk_frame]
        elif state == State.HIDDEN:
            # For HIDDEN state, use transparent surface or clear image
            # For now, keep last image (window will be hidden by game window)
            pass

    def update_walk_frame(self):
        """Advance walking animation frame"""
        self.walk_frame = (self.walk_frame + 1) % 2

    def set_walk_direction(self, direction):
        """Set walk direction (1 = right, -1 = left)"""
        self.walk_direction = direction
