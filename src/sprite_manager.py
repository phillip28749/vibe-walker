import pygame
import os
from PIL import Image
from src.state_machine import State


class CharacterSprite(pygame.sprite.Sprite):
    """Pygame sprite for the desktop pet character"""

    STANDARD_COLUMNS = 4
    STANDARD_ROWS = 4
    STANDARD_FRAME_COUNT = STANDARD_COLUMNS * STANDARD_ROWS

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

        # Prefer the full 4x4 movement sprite sheet when present.
        walking_sheet_path = self._first_existing_path(
            os.path.join(sprite_dir, "movement", "walking.png"),
            os.path.join(sprite_dir, "walking.png")
        )
        if os.path.exists(walking_sheet_path):
            right_frames = self._load_standard_animation(walking_sheet_path)
            self.images[State.WALKING] = {
                "left": [pygame.transform.flip(frame, True, False) for frame in right_frames],
                "right": right_frames
            }
        else:
            left_frames = [
                self._load_sprite(os.path.join(sprite_dir, "walk_left_1.png")),
                self._load_sprite(os.path.join(sprite_dir, "walk_left_2.png"))
            ]
            right_frames = [
                self._load_sprite(os.path.join(sprite_dir, "walk_right_1.png")),
                self._load_sprite(os.path.join(sprite_dir, "walk_right_2.png"))
            ]
            self.images[State.WALKING] = {
                "left": self._repeat_to_standard_length(left_frames),
                "right": self._repeat_to_standard_length(right_frames)
            }

        # Load waving animation
        waving_sheet_path = self._first_existing_path(
            os.path.join(sprite_dir, "movement", "waving_w.png"),
            os.path.join(sprite_dir, "waving", "waving_w.png")
        )
        if os.path.exists(waving_sheet_path):
            self.images[State.WAVING] = self._load_standard_animation(waving_sheet_path)
        else:
            self.images[State.WAVING] = self._repeat_to_standard_length([self.images[State.IDLE]])

        # Load appearing/climb-out animation
        climbout_sheet_path = os.path.join(sprite_dir, "movement", "climbout.png")
        if os.path.exists(climbout_sheet_path):
            self.images[State.APPEARING] = self._load_standard_animation(climbout_sheet_path)
        else:
            appearing_frames = []
            for i in range(8):
                frame_path = os.path.join(sprite_dir, "climb_out", f"frame_{i:02d}.png")
                if os.path.exists(frame_path):
                    appearing_frames.append(self._load_sprite(frame_path))
            if appearing_frames:
                self.images[State.APPEARING] = self._repeat_to_standard_length(appearing_frames)
            else:
                self.images[State.APPEARING] = self._repeat_to_standard_length([self.images[State.IDLE]])

        # Load idle-to-walking transition animation (16 frames total: 4x4 sheet)
        idle_to_walking_path = os.path.join(sprite_dir, "transition", "idle_to_walking.png")
        if os.path.exists(idle_to_walking_path):
            self.images["IDLE_TO_WALKING"] = self._load_standard_animation(idle_to_walking_path)
        else:
            self.images["IDLE_TO_WALKING"] = self._repeat_to_standard_length([self.images[State.IDLE]])

        # Load walk-to-idle transition animation (16 frames total: 4x4 sheet)
        walk_to_idle_path = os.path.join(sprite_dir, "transition", "walk_to_idle.png")
        if os.path.exists(walk_to_idle_path):
            self.images["WALK_TO_IDLE"] = self._load_standard_animation(walk_to_idle_path)
        else:
            # Fall back to the reverse of the idle-to-walking animation if a dedicated sheet is unavailable.
            self.images["WALK_TO_IDLE"] = list(reversed(self.images["IDLE_TO_WALKING"]))

        # Load drag-to-idle transition animation (16 frames total: 4x4 sheet)
        drag_to_idle_path = os.path.join(sprite_dir, "transition", "drag_to_idle.png")
        if os.path.exists(drag_to_idle_path):
            drag_to_idle_frames = self._load_standard_animation(drag_to_idle_path)
            self.images["DRAG_TO_IDLE"] = drag_to_idle_frames
            # Reverse for idle-to-drag.
            self.images["IDLE_TO_DRAG"] = list(reversed(self.images["DRAG_TO_IDLE"]))
        else:
            self.images["DRAG_TO_IDLE"] = self._repeat_to_standard_length([self.images[State.IDLE]])
            self.images["IDLE_TO_DRAG"] = list(reversed(self.images["DRAG_TO_IDLE"]))

        # Load dragged sprite (animated or static based on config)
        if self.use_dragged_animation:
            # Load sprite sheet for animation
            dragged_sheet_path = os.path.join(sprite_dir, "dragged_sheet.png")
            if os.path.exists(dragged_sheet_path) and self._is_standard_sheet(dragged_sheet_path):
                self.images[State.DRAGGED] = self._load_standard_animation(dragged_sheet_path)
            else:
                # Fallback to single sprite
                dragged_path = os.path.join(sprite_dir, "dragged.png")
                if os.path.exists(dragged_path):
                    self.images[State.DRAGGED] = self._repeat_to_standard_length([self._load_sprite(dragged_path)])
                else:
                    self.images[State.DRAGGED] = self._repeat_to_standard_length([self.images[State.IDLE]])
        else:
            # Use single static sprite
            dragged_path = os.path.join(sprite_dir, "dragged.png")
            if os.path.exists(dragged_path):
                self.images[State.DRAGGED] = self._repeat_to_standard_length([self._load_sprite(dragged_path)])
            else:
                self.images[State.DRAGGED] = self._repeat_to_standard_length([self.images[State.IDLE]])

    def _load_sprite(self, path):
        """Load and scale a sprite image"""
        if not os.path.exists(path):
            # Create placeholder surface (fully transparent)
            surface = pygame.Surface((self.sprite_size, self.sprite_size), pygame.SRCALPHA)
            surface.fill((0, 0, 0, 0))  # Fully transparent placeholder
            return surface

        # Ensure display is set for convert_alpha to work
        if pygame.display.get_surface() is None:
            try:
                pygame.display.set_mode((1, 1), pygame.HIDDEN)
            except pygame.error:
                pass

        image = pygame.image.load(path)
        if pygame.display.get_surface() is not None:
            image = image.convert_alpha()
        # Use smoothscale for better quality when scaling
        return pygame.transform.smoothscale(image, (self.sprite_size, self.sprite_size))

    def _first_existing_path(self, *paths):
        """Return the first existing path, or the first candidate for fallback checks."""
        for path in paths:
            if os.path.exists(path):
                return path
        return paths[0]

    def _load_standard_animation(self, path):
        """Load a standardized 4x4 animation sheet as 16 frames."""
        image = Image.open(path).convert("RGBA")
        x_ranges = self._detect_grid_cell_ranges(image, self.STANDARD_COLUMNS, axis="x")
        y_ranges = self._detect_grid_cell_ranges(image, self.STANDARD_ROWS, axis="y")

        frames = []
        for top, bottom in y_ranges:
            for left, right in x_ranges:
                frame = image.crop((left, top, right + 1, bottom + 1))
                frames.append(self._pil_image_to_surface(frame))

        return self._repeat_to_standard_length(frames)

    def _is_standard_sheet(self, path):
        """Return True if an image can be interpreted as a 4x4 animation sheet."""
        image = Image.open(path)
        width, height = image.size
        return width >= self.STANDARD_COLUMNS and height >= self.STANDARD_ROWS

    def _repeat_to_standard_length(self, frames):
        """Repeat or trim frames so every animation has 16 frames."""
        if not frames:
            return []

        if len(frames) >= self.STANDARD_FRAME_COUNT:
            return frames[:self.STANDARD_FRAME_COUNT]

        repeated = []
        for index in range(self.STANDARD_FRAME_COUNT):
            source_index = int(index * len(frames) / self.STANDARD_FRAME_COUNT)
            repeated.append(frames[source_index])
        return repeated

    def _detect_grid_cell_ranges(self, image, count, axis):
        """Detect grid separators and return inclusive cell ranges."""
        width, height = image.size
        length = width if axis == "x" else height
        cross_length = height if axis == "x" else width
        separators = []
        pixels = image.load()

        for index in range(length):
            separator_pixels = 0
            for cross in range(cross_length):
                x, y = (index, cross) if axis == "x" else (cross, index)
                r, g, b, _ = pixels[x, y]
                if abs(r - g) <= 3 and abs(g - b) <= 3 and 70 <= r <= 110:
                    separator_pixels += 1
            if separator_pixels > cross_length * 0.6:
                separators.append(index)

        bands = self._group_contiguous_numbers(separators)
        if len(bands) != count + 1:
            cell_size = length // count
            return [(i * cell_size, ((i + 1) * cell_size) - 1) for i in range(count)]

        return [(bands[i][1] + 1, bands[i + 1][0] - 1) for i in range(count)]

    def _group_contiguous_numbers(self, numbers):
        """Group sorted numbers into inclusive ranges."""
        if not numbers:
            return []

        ranges = []
        start = previous = numbers[0]
        for number in numbers[1:]:
            if number == previous + 1:
                previous = number
            else:
                ranges.append((start, previous))
                start = previous = number
        ranges.append((start, previous))
        return ranges

    def _pil_image_to_surface(self, image):
        """Convert a PIL frame to a scaled pygame surface."""
        image = image.resize((self.sprite_size, self.sprite_size), Image.Resampling.LANCZOS)
        surface = pygame.image.fromstring(image.tobytes(), image.size, "RGBA")
        if pygame.display.get_surface() is not None:
            return surface.convert_alpha()
        return surface

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
            # DRAGGED/DROPPING -> IDLE: play drag-to-idle animation.
            if (self.current_state in [State.DRAGGED, State.DROPPING]) and state == State.IDLE:
                self.playing_drag_to_idle = True
                self.drag_to_idle_frame = 0
                self.current_state = state
                self.image = self.images["DRAG_TO_IDLE"][0]
                return
            # IDLE -> WALKING: play idle-to-walking animation.
            elif self.current_state == State.IDLE and state == State.WALKING:
                self.playing_idle_to_walking = True
                self.idle_to_walking_frame = 0
                self.current_state = state
                self.image = self.images["IDLE_TO_WALKING"][0]
                return
            # WALKING -> IDLE: play walk-to-idle animation.
            elif self.current_state == State.WALKING and state == State.IDLE:
                self.playing_walk_to_idle = True
                self.walk_to_idle_frame = 0
                self.current_state = state
                self.image = self.images["WALK_TO_IDLE"][0]
                return
            # IDLE -> DRAGGED: play idle-to-drag animation.
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
        direction = "right" if self.walk_direction > 0 else "left"
        self.walk_frame = (self.walk_frame + 1) % len(self.images[State.WALKING][direction])

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
