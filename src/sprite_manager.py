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
        self.idle_to_walking_frame = 0  # Frame for idle-to-walking transition
        self.walk_to_idle_frame = 0  # Frame for walk-to-idle transition
        self.drag_to_idle_frame = 0  # Frame for drag-to-idle transition
        self.idle_to_drag_frame = 0  # Frame for idle-to-drag transition
        self.playing_idle_to_walking = False  # Flag for idle-to-walking transition animation
        self.playing_walk_to_idle = False  # Flag for walk-to-idle transition animation
        self.playing_drag_to_idle = False  # Flag for drag-to-idle transition animation
        self.playing_idle_to_drag = False  # Flag for idle-to-drag transition animation

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

        # Load idle-to-walking transition animation (16 frames total: 4x4 sheet)
        idle_to_walking_path = os.path.join(sprite_dir, "transition", "idle_to_walking2.png")
        if os.path.exists(idle_to_walking_path):
            idle_to_walking_frames = []
            for row in range(4):
                idle_to_walking_frames.extend(
                    self._load_sprite_sheet(idle_to_walking_path, frames=4, rows=4, use_row=row)
                )
            self.images["IDLE_TO_WALKING"] = idle_to_walking_frames
        else:
            legacy_idle_to_walking_path = os.path.join(sprite_dir, "transition", "idle_to_walking.png")
            if os.path.exists(legacy_idle_to_walking_path):
                top_row = self._load_sprite_sheet(legacy_idle_to_walking_path, frames=4, rows=2, use_row=0)
                bottom_row = self._load_sprite_sheet(legacy_idle_to_walking_path, frames=4, rows=2, use_row=1)
                self.images["IDLE_TO_WALKING"] = top_row + bottom_row
            else:
                self.images["IDLE_TO_WALKING"] = [self.images[State.IDLE]]

        # Load walk-to-idle transition animation (16 frames total: 4x4 sheet)
        walk_to_idle_path = os.path.join(sprite_dir, "transition", "walk_to_idle.png")
        if os.path.exists(walk_to_idle_path):
            walk_to_idle_frames = []
            for row in range(4):
                walk_to_idle_frames.extend(
                    self._load_sprite_sheet(walk_to_idle_path, frames=4, rows=4, use_row=row)
                )
            self.images["WALK_TO_IDLE"] = walk_to_idle_frames
        else:
            # Fall back to the reverse of the idle-to-walking animation if a dedicated sheet is unavailable.
            self.images["WALK_TO_IDLE"] = list(reversed(self.images["IDLE_TO_WALKING"]))

        # Load drag-to-idle transition animation (8 frames total: top row + bottom row)
        drag_to_idle_path = os.path.join(sprite_dir, "transition", "drag_to_idle.png")
        if os.path.exists(drag_to_idle_path):
            # Load top row (frames 0-3)
            top_row = self._load_sprite_sheet(drag_to_idle_path, frames=4, rows=2, use_row=0)
            # Load bottom row (frames 4-7)
            bottom_row = self._load_sprite_sheet(drag_to_idle_path, frames=4, rows=2, use_row=1)
            # Combine both rows for 8 total frames
            self.images["DRAG_TO_IDLE"] = top_row + bottom_row
            # Reverse for idle-to-drag (frames 7→6→5→4→3→2→1→0)
            self.images["IDLE_TO_DRAG"] = list(reversed(self.images["DRAG_TO_IDLE"]))
        else:
            self.images["DRAG_TO_IDLE"] = [self.images[State.IDLE]]
            self.images["IDLE_TO_DRAG"] = [self.images[State.DRAGGED][0]]

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
            # Create placeholder surface (fully transparent)
            surface = pygame.Surface((self.sprite_size, self.sprite_size), pygame.SRCALPHA)
            surface.fill((0, 0, 0, 0))  # Fully transparent placeholder
            return surface

        # Ensure display is set for convert_alpha to work
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1), pygame.HIDDEN)

        image = pygame.image.load(path).convert_alpha()
        # Use smoothscale for better quality when scaling
        return pygame.transform.smoothscale(image, (self.sprite_size, self.sprite_size))

    def _load_sprite_sheet(self, path, frames=8, rows=1, use_row=0):
        """Load and extract frames from a sprite sheet

        Args:
            path: Path to sprite sheet image
            frames: Number of frames per row (arranged horizontally)
            rows: Number of rows in the sprite sheet
            use_row: Which row to extract (0-indexed)

        Returns:
            List of pygame surfaces, one per frame
        """
        # Ensure display is set for convert_alpha to work
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1), pygame.HIDDEN)

        sheet = pygame.image.load(path).convert_alpha()
        sheet_width, sheet_height = sheet.get_size()
        frame_width = sheet_width // frames
        frame_height = sheet_height // rows

        frame_list = []
        for i in range(frames):
            # Extract frame from sheet at specified row
            frame_rect = pygame.Rect(i * frame_width, use_row * frame_height, frame_width, frame_height)
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), frame_rect)

            # Use smoothscale for better quality
            scaled_frame = pygame.transform.smoothscale(frame, (self.sprite_size, self.sprite_size))
            frame_list.append(scaled_frame)

        return frame_list

    def _get_sprite_for_state(self, state):
        """Get the sprite image for a given state

        Args:
            state: State enum member

        Returns:
            pygame.Surface: The sprite image for the state
        """
        if state == State.IDLE:
            return self.images[State.IDLE]
        elif state == State.DRAGGED or state == State.DROPPING:
            return self.images[State.DRAGGED][self.dragged_frame]
        elif state == State.WALKING:
            direction = "right" if self.walk_direction > 0 else "left"
            return self.images[State.WALKING][direction][self.walk_frame]
        elif state == State.WAVING:
            return self.images[State.WAVING][self.waving_frame]
        elif state == State.APPEARING:
            return self.images[State.APPEARING][self.appearing_frame]
        elif state == State.HIDDEN:
            # Return transparent surface
            surface = pygame.Surface((self.sprite_size, self.sprite_size), pygame.SRCALPHA)
            surface.fill((0, 0, 0, 0))
            return surface
        return self.images[State.IDLE]  # Fallback

    def update_state(self, state):
        """Update sprite based on state

        Args:
            state: State enum member
        """
        # Handle drag-to-idle transition
        if self.playing_drag_to_idle and state == State.IDLE:
            self.image = self.images["DRAG_TO_IDLE"][self.drag_to_idle_frame]
            return
        elif self.playing_drag_to_idle:
            self.playing_drag_to_idle = False
            self.drag_to_idle_frame = 0

        # Handle idle-to-walking transition
        if self.playing_idle_to_walking and state == State.WALKING:
            self.image = self.images["IDLE_TO_WALKING"][self.idle_to_walking_frame]
            return
        elif self.playing_idle_to_walking:
            self.playing_idle_to_walking = False
            self.idle_to_walking_frame = 0

        # Handle walk-to-idle transition
        if self.playing_walk_to_idle and state == State.IDLE:
            self.image = self.images["WALK_TO_IDLE"][self.walk_to_idle_frame]
            return
        elif self.playing_walk_to_idle:
            self.playing_walk_to_idle = False
            self.walk_to_idle_frame = 0

        # Handle idle-to-drag transition
        if self.playing_idle_to_drag and state == State.DRAGGED:
            self.image = self.images["IDLE_TO_DRAG"][self.idle_to_drag_frame]
            return
        elif self.playing_idle_to_drag:
            self.playing_idle_to_drag = False
            self.idle_to_drag_frame = 0

        # Check for state transitions
        if state != self.current_state:
            # DRAGGED/DROPPING -> IDLE: play drag-to-idle animation (frames 0→7)
            if (self.current_state in [State.DRAGGED, State.DROPPING]) and state == State.IDLE:
                self.playing_drag_to_idle = True
                self.drag_to_idle_frame = 0
                self.current_state = state
                self.image = self.images["DRAG_TO_IDLE"][0]
                return
            # IDLE -> WALKING: play idle-to-walking animation (frames 0→7)
            elif self.current_state == State.IDLE and state == State.WALKING:
                self.playing_idle_to_walking = True
                self.idle_to_walking_frame = 0
                self.current_state = state
                self.image = self.images["IDLE_TO_WALKING"][0]
                return
            # WALKING -> IDLE: play walk-to-idle animation (frames 0→15)
            elif self.current_state == State.WALKING and state == State.IDLE:
                self.playing_walk_to_idle = True
                self.walk_to_idle_frame = 0
                self.current_state = state
                self.image = self.images["WALK_TO_IDLE"][0]
                return
            # IDLE -> DRAGGED: play idle-to-drag animation (frames 7→0 reversed)
            elif self.current_state == State.IDLE and state == State.DRAGGED:
                self.playing_idle_to_drag = True
                self.idle_to_drag_frame = 0
                self.current_state = state
                self.image = self.images["IDLE_TO_DRAG"][0]
                return

        # Update current state and image
        self.current_state = state
        self.image = self._get_sprite_for_state(state)

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

    def update_drag_to_idle_frame(self):
        """Advance drag-to-idle transition animation frame

        Returns:
            bool: True when animation is complete
        """
        num_frames = len(self.images["DRAG_TO_IDLE"])
        self.drag_to_idle_frame = min(self.drag_to_idle_frame + 1, num_frames - 1)

        if self.drag_to_idle_frame >= num_frames - 1:
            # Animation complete
            self.playing_drag_to_idle = False
            self.drag_to_idle_frame = 0
            return True
        return False

    def update_idle_to_walking_frame(self):
        """Advance idle-to-walking transition animation frame

        Returns:
            bool: True when animation is complete
        """
        num_frames = len(self.images["IDLE_TO_WALKING"])
        self.idle_to_walking_frame = min(self.idle_to_walking_frame + 1, num_frames - 1)

        if self.idle_to_walking_frame >= num_frames - 1:
            self.playing_idle_to_walking = False
            self.idle_to_walking_frame = 0
            return True
        return False

    def update_walk_to_idle_frame(self):
        """Advance walk-to-idle transition animation frame

        Returns:
            bool: True when animation is complete
        """
        num_frames = len(self.images["WALK_TO_IDLE"])
        self.walk_to_idle_frame = min(self.walk_to_idle_frame + 1, num_frames - 1)

        if self.walk_to_idle_frame >= num_frames - 1:
            self.playing_walk_to_idle = False
            self.walk_to_idle_frame = 0
            return True
        return False

    def update_idle_to_drag_frame(self):
        """Advance idle-to-drag transition animation frame

        Returns:
            bool: True when animation is complete
        """
        num_frames = len(self.images["IDLE_TO_DRAG"])
        self.idle_to_drag_frame = min(self.idle_to_drag_frame + 1, num_frames - 1)

        if self.idle_to_drag_frame >= num_frames - 1:
            # Animation complete
            self.playing_idle_to_drag = False
            self.idle_to_drag_frame = 0
            return True
        return False

    def set_walk_direction(self, direction):
        """Set walk direction (1 = right, -1 = left)"""
        self.walk_direction = direction
