import pygame
import os
from src.state_machine import State


class CharacterSprite(pygame.sprite.Sprite):
    """Pygame sprite for the desktop pet character"""

    def __init__(self, sprite_size=64, use_dragged_animation=True):
        super().__init__()
        self.sprite_size = sprite_size
        self.use_dragged_animation = use_dragged_animation
        self.images = {}
        self.current_state = State.IDLE
        self.walk_frame = 0
        self.walk_direction = 1  # 1 = right, -1 = left
        self.dragged_frame = 0  # Frame for dragged animation
        self.waving_frame = 0  # Frame for waving animation
        self.appearing_frame = 0  # Frame for appearing animation

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

        # Load waving animation
        waving_sheet_path = os.path.join(sprite_dir, "waving", "waving_w.png")
        if os.path.exists(waving_sheet_path):
            self.images[State.WAVING] = self._load_sprite_sheet(waving_sheet_path, frames=8)
        else:
            self.images[State.WAVING] = [self.images[State.IDLE]]

        # Load appearing/climb_out animation
        appearing_frames = []
        for i in range(8):
            frame_path = os.path.join(sprite_dir, "climb_out", f"frame_{i:02d}.png")
            if os.path.exists(frame_path):
                appearing_frames.append(self._load_sprite(frame_path))
        if appearing_frames:
            self.images[State.APPEARING] = appearing_frames
        else:
            self.images[State.APPEARING] = [self.images[State.IDLE]]

        # Load dragged sprite (animated or static based on config)
        if self.use_dragged_animation:
            # Load sprite sheet for animation
            dragged_sheet_path = os.path.join(sprite_dir, "dragged_sheet.png")
            if os.path.exists(dragged_sheet_path):
                self.images[State.DRAGGED] = self._load_sprite_sheet(dragged_sheet_path, frames=8)
            else:
                # Fallback to single sprite
                dragged_path = os.path.join(sprite_dir, "dragged.png")
                if os.path.exists(dragged_path):
                    self.images[State.DRAGGED] = [self._load_sprite(dragged_path)]
                else:
                    self.images[State.DRAGGED] = [self.images[State.IDLE]]
        else:
            # Use single static sprite
            dragged_path = os.path.join(sprite_dir, "dragged.png")
            if os.path.exists(dragged_path):
                self.images[State.DRAGGED] = [self._load_sprite(dragged_path)]
            else:
                self.images[State.DRAGGED] = [self.images[State.IDLE]]

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

    def _load_sprite_sheet(self, path, frames=8):
        """Load and extract frames from a horizontal sprite sheet

        Args:
            path: Path to sprite sheet image
            frames: Number of frames in the sheet (arranged horizontally)

        Returns:
            List of pygame surfaces, one per frame
        """
        # Ensure display is set for convert_alpha to work
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1), pygame.HIDDEN)

        sheet = pygame.image.load(path).convert_alpha()
        sheet_width, sheet_height = sheet.get_size()
        frame_width = sheet_width // frames
        frame_height = sheet_height  # Assume single row

        frame_list = []
        for i in range(frames):
            # Extract frame from sheet
            frame_rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), frame_rect)

            # Scale to sprite size
            scaled_frame = pygame.transform.scale(frame, (self.sprite_size, self.sprite_size))
            frame_list.append(scaled_frame)

        return frame_list

    def update_state(self, state):
        """Update sprite based on state

        Args:
            state: State enum member
        """
        self.current_state = state

        if state == State.IDLE:
            self.image = self.images[State.IDLE]
        elif state == State.DRAGGED or state == State.DROPPING:
            # Animate dragged state
            self.image = self.images[State.DRAGGED][self.dragged_frame]
        elif state == State.WALKING:
            # Animate walking
            direction = "right" if self.walk_direction > 0 else "left"
            self.image = self.images[State.WALKING][direction][self.walk_frame]
        elif state == State.WAVING:
            # Animate waving
            self.image = self.images[State.WAVING][self.waving_frame]
        elif state == State.APPEARING:
            # Animate appearing/climb out
            self.image = self.images[State.APPEARING][self.appearing_frame]
        elif state == State.HIDDEN:
            # For HIDDEN state, use transparent surface or clear image
            # For now, keep last image (window will be hidden by game window)
            pass

    def update_walk_frame(self):
        """Advance walking animation frame"""
        self.walk_frame = (self.walk_frame + 1) % 2

    def update_dragged_frame(self):
        """Advance dragged animation frame"""
        num_frames = len(self.images[State.DRAGGED])
        self.dragged_frame = (self.dragged_frame + 1) % num_frames

    def update_waving_frame(self):
        """Advance waving animation frame"""
        num_frames = len(self.images[State.WAVING])
        self.waving_frame = (self.waving_frame + 1) % num_frames

    def update_appearing_frame(self):
        """Advance appearing animation frame"""
        num_frames = len(self.images[State.APPEARING])
        old_frame = self.appearing_frame
        self.appearing_frame = min(self.appearing_frame + 1, num_frames - 1)
        return self.appearing_frame >= num_frames - 1  # Return True when animation complete

    def reset_appearing_animation(self):
        """Reset appearing animation to first frame"""
        self.appearing_frame = 0

    def set_walk_direction(self, direction):
        """Set walk direction (1 = right, -1 = left)"""
        self.walk_direction = direction
