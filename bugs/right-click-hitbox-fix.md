# Bug Fix: Right-Click Context Menu Hitbox Issue

**Date:** 2026-04-19  
**Status:** Fixed  
**Severity:** Medium  
**Component:** Game Window / User Interaction

---

## Problem Description

The right-click context menu only appeared when clicking on the **top/head** of the sprite character. Clicking on other parts of the sprite (body, legs, transparent areas) did not trigger the context menu.

**Expected Behavior:**  
Right-clicking anywhere on the sprite should show the context menu.

**Actual Behavior:**  
Only clicking on opaque pixels at the top of the sprite triggered the menu.

---

## Root Cause

The issue had two contributing factors:

1. **Pygame Event Filtering:**  
   - Right-click events were handled through Pygame's event system (`pygame.MOUSEBUTTONDOWN`)
   - Pygame only sends mouse events when clicking on **non-transparent pixels** of the sprite
   - Transparent areas of the sprite were not receiving mouse events

2. **Pixel-Perfect Transparency Mask:**  
   - The `_update_transparency_mask()` method created a mask based on individual pixel visibility
   - Only visible (non-magenta) pixels were marked as clickable in the window mask
   - This made the clickable area very small and irregular

---

## Solution

### Part 1: Expanded Transparency Mask

**File:** `src/game_window.py`  
**Method:** `_update_transparency_mask()`

Modified the transparency mask to create a **rectangular clickable area** covering the entire sprite bounds:

```python
# Track sprite bounds for creating clickable area
min_x, min_y = self.window_size, self.window_size
max_x, max_y = 0, 0
has_sprite = False

for y in range(self.window_size):
    for x in range(self.window_size):
        pixel = img.pixel(x, y)
        color = QColor(pixel)
        if not (color.red() == 255 and color.green() == 0 and color.blue() == 255):
            painter.setPen(Qt.color1)
            painter.drawPoint(x, y)
            has_sprite = True
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

# Make entire sprite bounding box clickable
if has_sprite:
    painter.setPen(Qt.color1)
    painter.setBrush(Qt.color1)
    painter.drawRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
```

**Result:** The entire sprite area becomes clickable while maintaining visual transparency.

### Part 2: Qt-Level Mouse Event Handling

**File:** `src/game_window.py`  
**Method:** `mousePressEvent()` (new)

Added Qt-level mouse event handling to **bypass Pygame's transparency filtering**:

```python
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
```

**Why this works:**
- Qt's event system respects the window mask (entire sprite bounding box)
- Pygame's event system filters based on pixel transparency
- By handling right-click at the Qt level, we bypass Pygame's filtering

---

## Testing

**Test Cases:**
1. ✅ Right-click on sprite head → Context menu appears
2. ✅ Right-click on sprite body → Context menu appears
3. ✅ Right-click on sprite legs → Context menu appears
4. ✅ Right-click on transparent areas within sprite bounds → Context menu appears
5. ✅ Left-click drag still works normally (handled by Pygame)

---

## Technical Notes

- **Event Flow:** Qt events are processed before Pygame events
- **Backward Compatibility:** Left-click dragging still works via Pygame
- **Performance:** No performance impact (mask calculation happens once per frame)

---

## Related Files

- `src/game_window.py` - Main window class
  - `_update_transparency_mask()` - Lines 387-432
  - `mousePressEvent()` - Lines 444-455

---

## Future Improvements

- Consider using Qt event handling for all mouse interactions (not just right-click)
- Optimize mask calculation if performance issues arise with large sprites
- Add visual debug mode to show clickable area boundaries
