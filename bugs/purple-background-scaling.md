# Purple Background Scaling Issue

## Problem

When sprite size was changed from 246px to 69px (or any size other than 256px), a distorted purple/magenta background became visible around the character sprite instead of being transparent.

### Symptoms
- Purple background visible at 69px sprite size
- Transparency worked correctly at 256px
- Background appeared "slanted" or distorted at non-power-of-2 sizes
- The transparency mask wasn't properly removing magenta pixels

---

## Root Cause

**Byte Alignment Issue in QImage Data Transfer**

When creating a QImage from pygame surface data, Qt expects proper byte alignment for the image data. The issue occurred because:

1. **RGB Format (3 bytes per pixel):**
   ```python
   surf_data = pygame.image.tostring(self.pygame_screen, 'RGB')
   img = QImage(surf_data, width, height, QImage.Format_RGB888)
   ```

2. **Alignment Math:**
   - **256px width:** 256 × 3 = 768 bytes per line (divisible by 4) ✓
   - **69px width:** 69 × 3 = 207 bytes per line (NOT divisible by 4) ✗

3. **What Happened:**
   - Qt's QImage expects 4-byte alignment for optimal performance
   - At 69px width with RGB format, the data wasn't properly aligned
   - This caused the pixel data to be read incorrectly
   - The mask detection couldn't find the correct magenta pixels
   - Purple background showed through instead of being masked as transparent

---

## Solution

**Switch from RGB888 to RGBA8888 Format**

RGBA format uses 4 bytes per pixel, which is naturally aligned regardless of image width.

### Code Changes

**File:** `src/game_window.py`

**Before (Broken):**
```python
def _update_transparency_mask(self):
    """Update window mask to make magenta pixels transparent"""
    # Get pygame surface data as RGB
    surf_data = pygame.image.tostring(self.pygame_screen, 'RGB')
    
    # Create QImage from pygame surface
    img = QImage(surf_data, self.window_size, self.window_size, QImage.Format_RGB888)
    # ... rest of mask creation
```

**After (Fixed):**
```python
def _update_transparency_mask(self):
    """Update window mask to make magenta pixels transparent"""
    # Get pygame surface data as RGBA for proper 4-byte alignment
    surf_data = pygame.image.tostring(self.pygame_screen, 'RGBA')
    
    # Create QImage from pygame surface with explicit bytes per line
    # RGBA = 4 bytes per pixel (naturally aligned)
    bytes_per_line = self.window_size * 4
    img = QImage(surf_data, self.window_size, self.window_size, bytes_per_line, QImage.Format_RGBA8888)
    # ... rest of mask creation
```

### Why This Works

- **RGBA = 4 bytes per pixel** (R, G, B, A channels)
- Any width × 4 bytes is always 4-byte aligned
- **69px:** 69 × 4 = 276 bytes ✓
- **256px:** 256 × 4 = 1024 bytes ✓
- **Any size:** Works correctly with proper alignment

Qt can now correctly interpret the pixel data at any sprite size, allowing the mask to properly identify and hide magenta pixels.

---

## Related Issues

This fix also resolved:
- Sprite scaling artifacts from 500px → 69px
- Anti-aliasing bleed-through from `smoothscale`
- Near-magenta color threshold detection (lines 407-410)

### Additional Scaling Improvements

Changed sprite loading to use `smoothscale` for better quality:

**File:** `src/sprite_manager.py`

```python
def _load_sprite(self, path):
    # ...
    # Use smoothscale for better quality when scaling
    return pygame.transform.smoothscale(image, (self.sprite_size, self.sprite_size))
```

And added tolerance for near-magenta colors in mask detection:

**File:** `src/game_window.py` (lines 407-410)

```python
# Handle anti-aliased edges from smoothscale
r, g, b = color.red(), color.green(), color.blue()
is_magenta = (abs(r - 255) < 10 and abs(g - 0) < 10 and abs(b - 255) < 10)
```

---

## Key Learnings

1. **Byte Alignment Matters**
   - Image data formats must be properly aligned for Qt/Windows
   - RGB (3 bytes) can cause alignment issues at certain widths
   - RGBA (4 bytes) is naturally aligned and more robust

2. **Power-of-2 Sizes Aren't Required**
   - The issue wasn't about power-of-2 sizes specifically
   - It was about byte alignment (256 × 3 = 768, divisible by 4)
   - With RGBA, any size works correctly

3. **Format Selection Impact**
   - RGB888 is more memory efficient but alignment-sensitive
   - RGBA8888 uses more memory but works reliably at any size
   - For small sprites (69×69), the extra memory is negligible

4. **Cross-Platform Considerations**
   - Windows may be stricter about alignment than other platforms
   - RGBA format provides better cross-platform compatibility
   - Always specify bytes_per_line explicitly when known

---

## Testing

Verified working at multiple sizes:
- ✓ 69px (original issue size)
- ✓ 64px
- ✓ 128px
- ✓ 246px (previous working size)
- ✓ 256px (original working size)

All sizes now display with proper transparency and no purple background.

---

## Files Modified

- `src/game_window.py:387-395` - Fixed QImage format and alignment
- `src/game_window.py:407-410` - Added near-magenta threshold for anti-aliasing
- `src/sprite_manager.py:100` - Changed to smoothscale for better quality
- `src/sprite_manager.py:129` - Changed to smoothscale for sprite sheets
