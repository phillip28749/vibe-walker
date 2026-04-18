# Transparency Implementation

## Overview
This document describes the challenges encountered when implementing transparent background for the desktop pet, and the final working solution.

---

## Problem 1: Character Flying to Top on Drag Release

### Symptoms
- When dragging character upward and releasing mouse
- Character would fly to the top of the screen
- Then jump back to original baseline position

### Root Cause
The `DragHandler` was initialized with `baseline_y=0` instead of the actual window baseline position:

```python
self.drag_handler = DragHandler(
    sprite_size=self.config.sprite_size,
    baseline_y=0,  # ❌ Wrong - should be actual screen position
    drop_duration_ms=self.config.drop_duration_ms
)
```

When the drop animation calculated interpolation:
```python
current_y = self.drop_start_y + (self.baseline_y - self.drop_start_y) * eased
```

It interpolated from current position → 0 (top of screen) instead of → actual baseline.

### Solution
Pass the correct `self.baseline_y` value (calculated in `_position_at_baseline()`) to the DragHandler:

```python
self.drag_handler = DragHandler(
    sprite_size=self.config.sprite_size,
    baseline_y=self.baseline_y,  # ✅ Correct screen position
    drop_duration_ms=self.config.drop_duration_ms
)
```

**File:** `src/game_window.py:111`

---

## Problem 2: Window Transparency (Multiple Failed Attempts)

### Desired Behavior
- Desktop pet should have transparent background
- Only the character sprite should be visible
- No visible window border or background color

### Attempt 1: Qt Translucent Background + Pygame Alpha

**Approach:**
```python
# Enable Qt transparency
self.setAttribute(Qt.WA_TranslucentBackground)
self.setAttribute(Qt.WA_NoSystemBackground)

# Use pygame with alpha
self.pygame_screen = pygame.display.set_mode((size, size), pygame.SRCALPHA)
self.pygame_screen.fill((0, 0, 0, 0))  # Transparent fill
```

**Root Cause of Failure:**
- Embedded pygame surfaces don't preserve alpha channel when rendered in Qt on Windows
- The embedding layer (`SDL_WINDOWID`) doesn't support per-pixel alpha transfer
- Alpha information is lost between pygame rendering and Qt window display

**Result:** Character became invisible or entire window disappeared

---

### Attempt 2: Pygame Colorkey Only

**Approach:**
```python
# No Qt transparency attributes
self.transparent_color = (255, 0, 255)  # Magenta
self.pygame_screen.set_colorkey(self.transparent_color)
self.pygame_screen.fill(self.transparent_color)
```

**Root Cause of Failure:**
- Pygame's colorkey only affects pygame's internal rendering
- Colorkey doesn't communicate transparency information to Qt
- Qt window still renders the entire surface as opaque
- Windows sees a solid window with magenta color

**Result:** Visible magenta/pink background instead of transparency

---

### Attempt 3: convert_alpha() on Display Surface

**Approach:**
```python
self.pygame_screen = pygame.display.set_mode((size, size), pygame.NOFRAME)
self.pygame_screen = self.pygame_screen.convert_alpha()  # ❌ Invalid
```

**Root Cause of Failure:**
- `convert_alpha()` is designed for regular pygame surfaces (loaded images, created surfaces)
- Cannot be called on display surface returned by `pygame.display.set_mode()`
- Display surfaces have special properties and can't be converted
- This likely caused the surface to become invalid or non-functional

**Result:** Nothing visible, application may have crashed or failed to render

---

### ✅ Working Solution: Qt Mask-Based Transparency

**Approach:**
1. Fill pygame surface with a specific transparent color (magenta: 255, 0, 255)
2. Read pygame surface pixel data each frame
3. Create a QBitmap mask marking which pixels are visible vs transparent
4. Apply mask to Qt window using `setMask()`

**Implementation:**

```python
# In _setup_pygame():
self.transparent_color = (255, 0, 255)  # Magenta as transparent marker

# In update_game():
self.pygame_screen.fill(self.transparent_color)  # Fill with magenta
self.sprite_group.draw(self.pygame_screen)
self._update_transparency_mask()  # Create and apply mask
pygame.display.flip()

# New method:
def _update_transparency_mask(self):
    """Update window mask to make transparent color invisible"""
    # Get pygame surface data
    surf_data = pygame.image.tostring(self.pygame_screen, 'RGB')
    
    # Create QImage from pygame surface
    img = QImage(surf_data, self.window_size, self.window_size, QImage.Format_RGB888)
    
    # Create mask: pixels matching transparent_color become transparent
    mask = QBitmap(self.window_size, self.window_size)
    mask.fill(Qt.color0)  # Start with all transparent
    
    # Paint non-transparent pixels
    painter = QPainter(mask)
    for y in range(self.window_size):
        for x in range(self.window_size):
            pixel = img.pixel(x, y)
            color = QColor(pixel)
            # If not magenta, mark as visible
            if not (color.red() == 255 and color.green() == 0 and color.blue() == 255):
                painter.setPen(Qt.color1)
                painter.drawPoint(x, y)
    painter.end()
    
    # Apply mask to window
    self.setMask(mask)
```

**Why This Works:**
- Uses Qt's native `setMask()` API which integrates with Windows' layered window system
- Bridges the pygame → Qt gap by reading surface data and building a bitmap mask
- Windows natively supports masked windows for transparency and click-through
- Mask tells Windows exactly which pixels to render and which to make transparent

**Tradeoffs:**
- **Performance:** Checking every pixel every frame is computationally expensive
  - 80x80 window = 6,400 pixels checked per frame
  - At 60 FPS = 384,000 pixel checks per second
- **Potential Optimization:** Only update mask when sprite state/animation changes
  - Most frames the sprite doesn't change position within window
  - Could cache mask and only regenerate when needed

**Files Modified:**
- `src/game_window.py:1-6` - Added QImage, QBitmap, QRegion imports
- `src/game_window.py:103-105` - Set transparent_color
- `src/game_window.py:153-157` - Fill with transparent color and update mask
- `src/game_window.py:267-292` - Added `_update_transparency_mask()` method

---

## Key Learnings

1. **Embedded Pygame + Qt Transparency is Problematic on Windows**
   - The embedding layer doesn't support alpha channel transfer
   - Native Qt transparency attributes don't work with embedded pygame surfaces

2. **Colorkey vs. Mask vs. Alpha**
   - **Colorkey:** Pygame-internal, doesn't affect Qt window
   - **Alpha:** Doesn't survive pygame → Qt embedding
   - **Mask:** Qt-native, works with Windows layered windows

3. **Qt's setMask() is the Reliable Approach**
   - Directly tells Windows which pixels to hide
   - Works consistently across Windows versions
   - Supports click-through for transparent areas

4. **Performance vs. Compatibility**
   - Per-pixel mask checking is slow but reliable
   - Could optimize with caching for non-moving sprites
   - Alternative would be full rewrite to pure Qt rendering (no pygame)

---

## Future Optimization Opportunities

1. **Cache mask when sprite doesn't change**
   ```python
   # Only update mask if sprite animation frame changed
   if self.sprite.current_frame != self.last_masked_frame:
       self._update_transparency_mask()
       self.last_masked_frame = self.sprite.current_frame
   ```

2. **Use faster pixel access**
   - Replace nested loops with numpy array operations
   - Use QImage.bits() for direct memory access

3. **Consider pure Qt rendering**
   - Render sprites using QPixmap instead of pygame
   - Would eliminate pygame → Qt bridging overhead
   - Native transparency support
