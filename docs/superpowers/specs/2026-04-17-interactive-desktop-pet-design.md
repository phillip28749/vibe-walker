# Interactive Desktop Pet - POC Design

**Date:** 2026-04-17  
**Project:** Vibe Walker - Desktop Pet Rework  
**Approach:** Pygame + PyQt5 Hybrid Architecture

---

## Context

The current Vibe Walker is a PyQt5-based desktop character that monitors Claude Code activity via hooks and displays animated sprites on the taskbar. The character walks when Claude is active and disappears when idle.

**Problem:** The current implementation lacks user interactivity. The character is click-through (non-interactive) and tightly coupled to Claude Code activity.

**Goal:** Rework Vibe Walker into a fully interactive desktop pet with:
- Draggable character (mouse interaction)
- System tray app (always running in background)
- Hybrid mode: reactive (responds to Claude Code) or independent (hidden)
- Gravity physics (drops back to baseline when released)
- Single minion POC (remove multi-mob complexity)

**Why Pygame + PyQt5:** Pygame provides superior drag-and-drop handling and game-like physics compared to pure PyQt5. PyQt5 handles system tray, window management, and thread communication. This hybrid leverages the strengths of both frameworks.

---

## Architecture Overview

```
System Tray App (PyQt5 QSystemTrayIcon)
    ↓ controls visibility
Pygame Window Manager (PyQt5 QMainWindow + embedded Pygame surface)
    ↓ renders
Pygame Sprite System (character, animations, drag physics)
    ↓ monitored by
Activity Monitor Thread (existing hook monitoring system)
    ↓ emits Pygame events
State Machine (HIDDEN, IDLE, WALKING, DRAGGED, DROPPING)
```

### Component Responsibilities

1. **System Tray (PyQt5 QSystemTrayIcon)**
   - Always-running background app
   - Menu: "Toggle Reactive Mode", "Exit"
   - Controls minion visibility via reactive mode flag
   - Persists user preference in config.json

2. **Window Manager (PyQt5 + Pygame)**
   - PyQt5 frameless transparent window (always-on-top)
   - Embeds Pygame display surface via SDL_WINDOWID
   - Forwards mouse events to Pygame event loop
   - Positioned at baseline height (screen_height - offset)

3. **Sprite System (Pygame)**
   - Character sprite with animation state machine
   - Frame-based animation updates (60 FPS)
   - Collision detection for drag interaction
   - Gravity physics for drop animation

4. **Activity Monitor (existing, minimal changes)**
   - QThread monitoring trace/query_events.jsonl
   - Emits signals when Claude Code activity changes
   - Converted to Pygame custom events via ActivityBridge

5. **State Machine**
   - Manages character behavior across 5 states
   - Transitions triggered by: user interaction, Claude activity, animations completing

---

## State Machine

### States

| State | Behavior | Sprite | Trigger |
|-------|----------|--------|---------|
| **HIDDEN** | Not visible, reactive mode OFF | None | User toggles mode off |
| **IDLE** | Standing at baseline | idle.png | Reactive mode ON, no Claude activity |
| **WALKING** | Moving left/right at baseline | walk_left/right_1/2 | Claude Code activity detected |
| **DRAGGED** | Following mouse cursor | dragged.png (new) | Mouse press on sprite |
| **DROPPING** | Falling back to baseline | dragged.png + motion | Mouse release |

### State Transitions

```
HIDDEN
  ↓ [Reactive mode ON]
IDLE
  ↓ [Claude Code starts]
WALKING
  ↓ [Mouse press on sprite]
DRAGGED
  ↓ [Mouse release]
DROPPING
  ↓ [Reaches baseline]
IDLE or WALKING (depending on Claude Code state)

Any state → HIDDEN [Reactive mode OFF]
```

### Transition Rules

- **HIDDEN → IDLE**: User enables reactive mode in system tray
- **IDLE ↔ WALKING**: Based on Claude Code activity (trace events)
- **Any → DRAGGED**: Mouse click on sprite bounding box
- **DRAGGED → DROPPING**: Mouse release anywhere
- **DROPPING → IDLE/WALKING**: Animation complete, check Claude Code state
- **Any → HIDDEN**: User disables reactive mode (interrupts all states)

### Animation Details

- **IDLE**: Static `idle.png` or gentle breathing loop
- **WALKING**: Alternates walk_left/right_1/2 at 7 FPS, 2px/frame movement
- **DRAGGED**: New `dragged.png` sprite (being held/picked up)
- **DROPPING**: Smooth linear drop to baseline over ~0.5 seconds
- **Edge reversal**: When walking, reverse direction at screen edges

---

## Drag & Drop Physics

### Drag Detection (Pygame)

```python
if event.type == pygame.MOUSEBUTTONDOWN:
    if sprite.rect.collidepoint(event.pos):
        state = DRAGGED
        drag_offset = sprite.pos - mouse_pos  # Preserve grab point

if event.type == pygame.MOUSEMOTION and state == DRAGGED:
    sprite.pos = mouse_pos + drag_offset  # Follow cursor

if event.type == pygame.MOUSEBUTTONUP and state == DRAGGED:
    state = DROPPING
    drop_start_y = sprite.pos.y
    drop_start_time = pygame.time.get_ticks()
```

### Gravity Drop Animation

**Parameters:**
- Start Y: Current sprite position (wherever released)
- End Y: Baseline position = `screen_height - baseline_y_offset - sprite_size`
- Duration: 500ms (0.5 seconds)
- Easing: Smooth linear drop (constant deceleration)

**Implementation:**
```python
def update_dropping(current_time):
    elapsed = current_time - drop_start_time
    progress = min(elapsed / 500.0, 1.0)  # 0.0 to 1.0
    
    # Linear interpolation with smooth easing
    current_y = drop_start_y + (baseline_y - drop_start_y) * progress
    sprite.pos.y = current_y
    
    if progress >= 1.0:
        # Reached baseline, transition to next state
        if claude_code_active:
            state = WALKING
        else:
            state = IDLE
```

**Window Positioning:**
- Window follows sprite during drop
- Window size remains fixed (64x64)
- Final position: X = sprite.x, Y = baseline

---

## Pygame-PyQt5 Integration

### Window Setup (PyQt5)

```python
class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Frameless, transparent, always-on-top
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        # Create container widget for Pygame
        self.embed = QWidget()
        self.setCentralWidget(self.embed)
        
        # Set window size
        self.setFixedSize(64, 64)
        
        # Position at baseline
        screen = QApplication.primaryScreen().geometry()
        x = random.randint(0, screen.width() - 64) if random_spawn else 0
        y = screen.height() - baseline_offset - 64
        self.move(x, y)
```

### Pygame Initialization

```python
# Embed Pygame surface in PyQt5 widget
os.environ['SDL_WINDOWID'] = str(int(self.embed.winId()))
os.environ['SDL_VIDEODRIVER'] = 'windib'  # Windows-specific

pygame.init()
screen = pygame.display.set_mode((64, 64), pygame.NOFRAME)
clock = pygame.time.Clock()
```

### Main Loop Integration

```python
# QTimer drives Pygame update loop at 60 FPS
self.timer = QTimer()
self.timer.timeout.connect(self.pygame_update)
self.timer.start(16)  # ~60 FPS (16ms per frame)

def pygame_update(self):
    # Process Pygame events (mouse, custom events)
    for event in pygame.event.get():
        if event.type == CLAUDE_STARTED:
            state_machine.transition_to(WALKING)
        elif event.type == CLAUDE_STOPPED:
            state_machine.transition_to(IDLE)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            drag_handler.on_mouse_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            drag_handler.on_mouse_up(event)
        elif event.type == pygame.MOUSEMOTION:
            drag_handler.on_mouse_motion(event)
    
    # Update sprite animation
    sprite_group.update()
    
    # Render frame
    screen.fill((0, 0, 0, 0))  # Transparent background
    sprite_group.draw(screen)
    pygame.display.flip()
    
    # Maintain 60 FPS
    clock.tick(60)
```

### Communication Between Systems

**PyQt5 → Pygame (Activity Monitor):**
```python
class ActivityBridge(QObject):
    def __init__(self):
        self.monitor = ActivityMonitor()
        self.monitor.activity_started.connect(self.on_started)
        self.monitor.activity_stopped.connect(self.on_stopped)
    
    def on_started(self):
        pygame.event.post(pygame.event.Event(CLAUDE_STARTED))
    
    def on_stopped(self):
        pygame.event.post(pygame.event.Event(CLAUDE_STOPPED))
```

**Pygame → PyQt5 (Window Position):**
```python
# In pygame_update(), emit signal when sprite moves
if sprite.pos != last_pos:
    self.position_changed.emit(sprite.pos.x, sprite.pos.y)
    last_pos = sprite.pos

# In GameWindow, connect signal to move window
self.position_changed.connect(lambda x, y: self.move(x, y))
```

**System Tray → Pygame (Mode Toggle):**
```python
def on_reactive_mode_toggled(self, enabled):
    if enabled:
        pygame.event.post(pygame.event.Event(SHOW_MINION))
    else:
        pygame.event.post(pygame.event.Event(HIDE_MINION))
```

---

## System Tray & Configuration

### System Tray Menu

```
┌─────────────────────────┐
│ ✓ Reactive Mode         │  ← Checkable, persists to config
│ ─────────────────────── │
│ Exit                    │  ← Clean shutdown
└─────────────────────────┘
```

**Implementation (PyQt5 QSystemTrayIcon):**
```python
class SystemTray(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        
        # Load icon
        self.icon_active = QIcon("icons/minion_active.png")
        self.icon_inactive = QIcon("icons/minion_inactive.png")
        
        # Create menu
        menu = QMenu()
        self.reactive_action = menu.addAction("Reactive Mode")
        self.reactive_action.setCheckable(True)
        self.reactive_action.setChecked(config.reactive_mode_enabled)
        self.reactive_action.triggered.connect(self.on_toggle)
        
        menu.addSeparator()
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.on_exit)
        
        self.setContextMenu(menu)
        self.update_icon()
    
    def on_toggle(self, enabled):
        config.reactive_mode_enabled = enabled
        config.save()
        self.update_icon()
        # Emit signal to show/hide minion
        self.reactive_mode_changed.emit(enabled)
    
    def update_icon(self):
        if config.reactive_mode_enabled:
            self.setIcon(self.icon_active)
        else:
            self.setIcon(self.icon_inactive)
```

### Configuration (config.json)

**Updated Fields:**
```json
{
  "reactive_mode_enabled": true,      // NEW: Toggle reactive mode
  "random_spawn_enabled": true,       // KEEP: Random X spawn position
  "baseline_y_offset": 50,            // Fixed Y position from screen bottom
  "sprite_size": 64,
  "animation_fps": 7,
  "movement_speed_px": 2,
  "idle_timeout_sec": 7,              // (Not used in POC, kept for future)
  "trace_file_path": "trace/query_events.jsonl",
  "trace_poll_interval_ms": 500
}
```

**Removed Fields:**
- None (keep all existing fields for backwards compatibility)

**Spawn Logic:**
```python
screen = QApplication.primaryScreen().geometry()

if config.random_spawn_enabled:
    x = random.randint(0, screen.width() - config.sprite_size)
else:
    x = screen.width() // 2  # Center

y = screen.height() - config.baseline_y_offset - config.sprite_size
```

### Startup Behavior

1. Application launches, system tray icon appears
2. Load `reactive_mode_enabled` from config.json
3. If `True`: Spawn minion at baseline in IDLE state
4. If `False`: Minion stays HIDDEN
5. Activity monitor thread starts (ready for mode toggle)

---

## File Structure (Refactored)

### New Structure

```
vibe-walker/
├── src/
│   ├── main.py                    # Entry point, PyQt5 QApplication setup
│   ├── game_window.py             # PyQt5 window + Pygame surface embedding
│   ├── sprite_manager.py          # Pygame sprite system, animation logic
│   ├── state_machine.py           # State management (5 states)
│   ├── drag_handler.py            # Drag detection + gravity drop physics
│   ├── activity_monitor.py        # Keep existing (minimal changes)
│   ├── activity_bridge.py         # NEW: Converts QThread signals → Pygame events
│   ├── system_tray.py             # NEW: QSystemTrayIcon + menu
│   └── config.py                  # Keep existing (add new fields)
├── sprites/
│   ├── idle.png
│   ├── walk_left_1.png, walk_left_2.png
│   ├── walk_right_1.png, walk_right_2.png
│   ├── dragged.png                # NEW: Being held sprite
│   └── (remove climb_out, fade_away, waving for POC simplicity)
├── icons/                         # NEW: System tray icons
│   ├── minion_active.png
│   └── minion_inactive.png
├── trace/
│   └── query_events.jsonl         # NEVER cleaned up (keep all events)
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-04-17-interactive-desktop-pet-design.md
├── config.json
├── requirements.txt               # Add: pygame
├── setup.py                       # Keep existing (hook installation)
└── README.md
```

### Removed Files

- `animator.py` → Replaced by `sprite_manager.py` (Pygame-based animation)
- `character_window.py` → Replaced by `game_window.py` (Pygame embedded window)
- `particle_system.py` → Removed for POC simplicity (can add back later)
- `state_manager.py` → Refactored to `state_machine.py` (clearer name)
- `process_monitor.py` → Already unused, remove
- `claude_trace_runner.py` → Already unused, remove
- `cleanup_orphaned_queries.py` → Remove (no cleanup in POC)

### Key File Descriptions

**main.py**
- Creates QApplication
- Initializes SystemTray, GameWindow, ActivityBridge
- Starts activity monitor thread
- Runs Qt event loop

**game_window.py**
- PyQt5 QMainWindow with frameless, transparent window
- Embeds Pygame surface via SDL_WINDOWID
- QTimer drives Pygame update loop at 60 FPS
- Handles window positioning/visibility

**sprite_manager.py**
- Pygame sprite class with animation states
- Loads sprite images from disk
- Updates animation frame based on current state
- Manages sprite positioning and movement

**state_machine.py**
- Enum for 5 states (HIDDEN, IDLE, WALKING, DRAGGED, DROPPING)
- Transition logic with validation
- State-specific update methods
- Emits events on state changes

**drag_handler.py**
- Collision detection (mouse on sprite)
- Drag offset tracking (preserve grab point)
- Gravity drop physics (linear interpolation)
- Mouse event processing

**activity_bridge.py**
- Connects ActivityMonitor signals to Pygame events
- Thread-safe event posting
- Custom Pygame event types (CLAUDE_STARTED, CLAUDE_STOPPED)

**system_tray.py**
- QSystemTrayIcon with menu
- Reactive mode toggle (checkable menu item)
- Icon state updates (active/inactive)
- Persists preference to config.json

---

## Activity Monitor Integration

### Changes to activity_monitor.py

**Minimal Changes Required:**

The existing `ActivityMonitor` class remains mostly unchanged. It continues to:
- Poll `trace/query_events.jsonl` every 500ms
- Track open query IDs
- Emit PyQt signals on activity changes

**Signal Emission (unchanged):**
```python
# Existing signals - keep these
self.activity_started.emit()  # When query_started event detected
self.activity_stopped.emit()  # When query_finished event detected
```

### Activity Bridge (New Component)

**Purpose:** Convert PyQt signals (from QThread) to Pygame custom events (thread-safe).

```python
# activity_bridge.py
import pygame
from PyQt5.QtCore import QObject

# Define custom Pygame event types
CLAUDE_STARTED = pygame.USEREVENT + 1
CLAUDE_STOPPED = pygame.USEREVENT + 2
SHOW_MINION = pygame.USEREVENT + 3
HIDE_MINION = pygame.USEREVENT + 4

class ActivityBridge(QObject):
    def __init__(self, activity_monitor):
        super().__init__()
        self.monitor = activity_monitor
        
        # Connect Qt signals to Pygame event posters
        self.monitor.activity_started.connect(self.on_activity_started)
        self.monitor.activity_stopped.connect(self.on_activity_stopped)
    
    def on_activity_started(self):
        """Claude Code query started"""
        pygame.event.post(pygame.event.Event(CLAUDE_STARTED))
    
    def on_activity_stopped(self):
        """Claude Code query finished"""
        pygame.event.post(pygame.event.Event(CLAUDE_STOPPED))
```

### Event Handling in Pygame Loop

```python
# In game_window.py pygame_update() method
for event in pygame.event.get():
    if event.type == CLAUDE_STARTED:
        if state_machine.current_state != State.HIDDEN:
            state_machine.transition_to(State.WALKING)
    
    elif event.type == CLAUDE_STOPPED:
        if state_machine.current_state == State.WALKING:
            state_machine.transition_to(State.IDLE)
    
    elif event.type == SHOW_MINION:
        state_machine.transition_to(State.IDLE)
        game_window.show()
    
    elif event.type == HIDE_MINION:
        state_machine.transition_to(State.HIDDEN)
        game_window.hide()
    
    elif event.type == pygame.MOUSEBUTTONDOWN:
        drag_handler.on_mouse_down(event)
    
    elif event.type == pygame.MOUSEBUTTONUP:
        drag_handler.on_mouse_up(event)
    
    elif event.type == pygame.MOUSEMOTION:
        drag_handler.on_mouse_motion(event)
```

### Why Keep ActivityMonitor?

1. **Already Working:** Proven hook monitoring system with no bugs
2. **Thread-Safe:** QThread design handles file I/O safely
3. **No Rewrite:** Avoids introducing new bugs in trace file parsing
4. **Minimal Changes:** Just need signal-to-event bridge

---

## Verification & Testing

### Manual Testing Checklist

**System Tray:**
- [ ] App launches, system tray icon appears in notification area
- [ ] Click tray icon shows menu with "Reactive Mode" and "Exit"
- [ ] Toggle "Reactive Mode" on → minion appears at baseline
- [ ] Toggle "Reactive Mode" off → minion disappears
- [ ] Icon changes color based on mode (active vs inactive)
- [ ] Exit menu item cleanly shuts down app
- [ ] Preference persists across app restarts (check config.json)

**Dragging:**
- [ ] Click minion → cursor changes, enters DRAGGED state
- [ ] Hold and drag → sprite follows mouse cursor smoothly
- [ ] Can drag to any screen position (including off-baseline)
- [ ] Release mouse → smooth linear drop to baseline
- [ ] Minion lands at correct Y position (baseline_y_offset)
- [ ] X position preserved during drop
- [ ] Drop animation takes ~0.5 seconds

**Reactive Mode Behavior:**
- [ ] Mode ON + Claude inactive → minion idles at baseline
- [ ] Mode ON + Claude active → minion walks left/right
- [ ] Mode OFF → minion disappears completely
- [ ] Dragging while idle → switches to dragged sprite
- [ ] Dragging while walking → switches to dragged sprite
- [ ] After drop (Claude active) → resumes walking
- [ ] After drop (Claude inactive) → returns to idle

**Hook Integration:**
- [ ] Start Claude Code query → minion starts walking within 1 second
- [ ] Query completes → minion returns to idle within 1 second
- [ ] Multiple rapid queries → state transitions correctly
- [ ] trace/query_events.jsonl grows over time (no cleanup)
- [ ] Check trace file has query_started and query_finished events

**Edge Cases:**
- [ ] Drag minion at left screen edge → no crash or weird behavior
- [ ] Drag minion at right screen edge → no crash or weird behavior
- [ ] Toggle reactive mode rapidly (10x) → no race conditions
- [ ] Close Claude Code while minion walking → gracefully returns to idle
- [ ] Launch app with Claude Code already running → detects activity correctly

**Spawning:**
- [ ] random_spawn_enabled = true → X position varies each launch
- [ ] random_spawn_enabled = false → X position consistent
- [ ] Y position always fixed at baseline (never varies)
- [ ] Minion spawns fully on-screen (not clipped)

**Performance:**
- [ ] Animation runs at smooth 60 FPS (no stuttering)
- [ ] CPU usage low when idle (<5%)
- [ ] CPU usage reasonable during animation (<10%)
- [ ] No memory leaks during 1 hour runtime (check Task Manager)
- [ ] Window remains responsive to mouse events

**Visual Quality:**
- [ ] Transparency works correctly (no black background)
- [ ] Sprites render cleanly (no pixelation or artifacts)
- [ ] Walking animation loops smoothly
- [ ] Dragged sprite looks distinct from idle/walking
- [ ] Drop animation smooth (no teleporting or jitter)

### Automated Tests (Optional for POC)

**Unit Tests:**
```python
# test_state_machine.py
def test_state_transitions():
    sm = StateMachine()
    assert sm.current_state == State.HIDDEN
    
    sm.transition_to(State.IDLE)
    assert sm.current_state == State.IDLE
    
    sm.transition_to(State.WALKING)
    assert sm.current_state == State.WALKING
    
    sm.transition_to(State.DRAGGED)
    assert sm.current_state == State.DRAGGED

def test_invalid_transitions():
    sm = StateMachine()
    sm.transition_to(State.IDLE)
    
    # Cannot go from IDLE directly to DROPPING
    with pytest.raises(InvalidTransitionError):
        sm.transition_to(State.DROPPING)
```

**Integration Tests:**
```python
# test_drag_handler.py (mock Pygame events)
def test_drag_detection():
    sprite = MockSprite(pos=(100, 100), size=64)
    handler = DragHandler(sprite)
    
    # Click on sprite
    event = MockMouseButtonDown(pos=(110, 110))
    handler.on_mouse_down(event)
    assert handler.is_dragging == True
    
    # Move mouse
    event = MockMouseMotion(pos=(150, 150))
    handler.on_mouse_motion(event)
    assert sprite.pos == (150, 150)
    
    # Release
    event = MockMouseButtonUp()
    handler.on_mouse_up(event)
    assert handler.is_dragging == False
```

### End-to-End Testing

**Scenario 1: First Launch**
1. Run `python src/main.py`
2. Verify system tray icon appears
3. Verify minion appears at baseline (reactive mode ON by default)
4. Verify minion is in IDLE state (not moving)
5. Start a Claude Code query
6. Verify minion starts walking within 1 second
7. Query completes
8. Verify minion returns to idle

**Scenario 2: Drag and Drop**
1. Minion is idle at baseline
2. Click and hold on minion
3. Drag to top-left corner of screen
4. Release mouse
5. Verify smooth drop animation back to baseline
6. Verify minion lands at correct Y position
7. Verify minion returns to IDLE state

**Scenario 3: Reactive Mode Toggle**
1. Minion is walking (Claude Code active)
2. Right-click system tray icon
3. Uncheck "Reactive Mode"
4. Verify minion disappears immediately
5. Check "Reactive Mode" again
6. Verify minion reappears in correct state (WALKING if Claude still active)

---

## Dependencies

### Python Libraries

**requirements.txt:**
```
PyQt5==5.15.9
pygame==2.5.2
Pillow==10.0.0
psutil==5.9.5
```

**Installation:**
```bash
pip install -r requirements.txt
```

### New Dependencies

- **pygame (2.5.2):** Core rendering, input handling, sprite system
  - Provides superior drag-and-drop vs pure PyQt5
  - Game-like physics and animation support
  - Cross-platform (Windows, Mac, Linux)

### Existing Dependencies (Keep)

- **PyQt5 (5.15.9):** System tray, window management, Qt event loop
- **Pillow (10.0.0):** Image loading, sprite manipulation
- **psutil (5.9.5):** Not directly used in POC, but kept for future features

---

## Implementation Notes

### Sprite Requirements

**New Sprite Needed:**
- `dragged.png` - Character being held/picked up (64x64)

**Keep Existing:**
- `idle.png` - Standing pose
- `walk_left_1.png`, `walk_left_2.png` - Walking left cycle
- `walk_right_1.png`, `walk_right_2.png` - Walking right cycle

**Remove for POC Simplicity:**
- `climb_out/` folder - Not needed (no spawn animation)
- `fade_away/` folder - Not needed (no disappear animation)
- `waving/` folder - Not needed (no permission dialogs in POC)

### Pygame Surface Transparency

**Key Settings:**
```python
# PyQt5 window transparency
self.setAttribute(Qt.WA_TranslucentBackground)

# Pygame per-pixel alpha
screen = pygame.display.set_mode((64, 64), pygame.NOFRAME)
screen.fill((0, 0, 0, 0))  # RGBA with 0 alpha = fully transparent

# Load sprites with alpha channel
sprite_image = pygame.image.load('sprites/idle.png').convert_alpha()
```

### Thread Safety

**Critical:** Pygame is not thread-safe. All Pygame operations must happen on the main thread.

**Solution:** Use `pygame.event.post()` to send events from QThread to main thread.

```python
# In QThread (ActivityMonitor)
def on_activity_started(self):
    # Thread-safe: post event to Pygame queue
    pygame.event.post(pygame.event.Event(CLAUDE_STARTED))

# In main thread (Pygame loop)
for event in pygame.event.get():
    if event.type == CLAUDE_STARTED:
        # Safe: all Pygame operations on main thread
        state_machine.transition_to(State.WALKING)
```

### Configuration Management

**Persist Reactive Mode:**
```python
# On toggle
config.reactive_mode_enabled = enabled
config.save()  # Write to config.json immediately

# On startup
config.load()  # Read from config.json
if config.reactive_mode_enabled:
    minion.show()
else:
    minion.hide()
```

### Edge Reversal Logic

**Keep from existing implementation:**
```python
if sprite.pos.x <= 0 and direction == Direction.LEFT:
    direction = Direction.RIGHT
elif sprite.pos.x >= screen_width - sprite_size and direction == Direction.RIGHT:
    direction = Direction.LEFT
```

---

## Success Criteria

**POC is complete when:**

1. ✅ System tray app launches and stays running in background
2. ✅ Minion appears/disappears based on reactive mode toggle
3. ✅ Minion can be dragged with mouse anywhere on screen
4. ✅ Minion smoothly drops back to baseline when released
5. ✅ Minion walks when Claude Code is active (reactive mode ON)
6. ✅ Minion idles when Claude Code is inactive (reactive mode ON)
7. ✅ Dragging switches sprite to "dragged" appearance
8. ✅ After drop, minion resumes correct behavior (walk or idle)
9. ✅ Random spawn on X axis, fixed on Y axis
10. ✅ No crashes, smooth 60 FPS, low CPU usage

**Out of Scope for POC:**

- Multiple minions (single minion only)
- Level system / progression
- Additional animations (climb_out, fade_away, waving)
- Particle effects
- Sound effects
- Context menu on minion itself (only system tray menu)
- Double-click or other complex interactions
- Minion customization (sprite selection, colors, etc.)
- Auto-start with Windows (manual launch only for POC)

---

## Future Enhancements (Post-POC)

Once POC is validated, consider:

1. **Multiple Minions:** Spawn multiple characters, each with independent behavior
2. **Level System:** Restore progression based on Claude Code usage
3. **More Animations:** Climb-out spawn, fade-away exit, waving for attention
4. **Particle Effects:** Dust clouds, sparkles, Thanos snap disintegration
5. **Sound Effects:** Footsteps, pickup/drop sounds, ambient noises
6. **Context Menu:** Right-click minion for quick actions (not just system tray)
7. **Customization:** User-selectable sprites, colors, animations
8. **Auto-Start:** Add to Windows startup folder or registry
9. **Minion Interactions:** Minions react to each other (following, playing)
10. **Advanced Physics:** Bounce effect on drop, throw velocity, collision with screen edges

---

## Risk Mitigation

### Potential Issues

**Issue 1: Pygame transparency on Windows**
- **Risk:** Pygame frameless windows may not support full transparency
- **Mitigation:** Test early. If fails, fall back to PyQt5-only approach (Approach 1 from design)

**Issue 2: Mouse events not registering on transparent areas**
- **Risk:** Pygame might not detect clicks on transparent pixels
- **Mitigation:** Use sprite bounding box (rect) for collision, not per-pixel alpha

**Issue 3: QThread + Pygame thread safety**
- **Risk:** Race conditions between activity monitor and Pygame loop
- **Mitigation:** Use `pygame.event.post()` exclusively (thread-safe), no direct Pygame calls from QThread

**Issue 4: Window positioning on multi-monitor setups**
- **Risk:** Minion spawns on wrong monitor or off-screen
- **Mitigation:** Use `QApplication.primaryScreen()` for baseline calculation, test on multi-monitor

**Issue 5: Performance degradation at 60 FPS**
- **Risk:** Pygame loop + Qt event loop may cause CPU spikes
- **Mitigation:** Profile early, reduce FPS to 30 if needed, optimize sprite loading

---

## Timeline Estimate

**POC Development (Single Developer):**

- **Phase 1: Core Structure** (4-6 hours)
  - Setup Pygame + PyQt5 integration
  - Create transparent window with embedded surface
  - Basic sprite rendering

- **Phase 2: State Machine** (3-4 hours)
  - Implement 5-state machine
  - State transition logic
  - Animation frame updates

- **Phase 3: Drag & Drop** (4-5 hours)
  - Mouse event handling
  - Collision detection
  - Gravity drop physics

- **Phase 4: Activity Monitor Bridge** (2-3 hours)
  - Signal-to-event conversion
  - Test with real Claude Code queries
  - Verify state transitions

- **Phase 5: System Tray** (2-3 hours)
  - Menu creation
  - Reactive mode toggle
  - Config persistence

- **Phase 6: Testing & Polish** (3-4 hours)
  - Manual testing checklist
  - Bug fixes
  - Performance optimization

**Total: 18-25 hours** (~3-4 days of focused work)

---

## Conclusion

This design reworks Vibe Walker from a passive observer into an interactive desktop pet using Pygame's game-like capabilities for drag-and-drop physics while leveraging PyQt5's system tray and threading infrastructure.

**Key Innovation:** Hybrid architecture combines strengths of both frameworks - Pygame for interaction/physics, PyQt5 for OS integration.

**Scope:** Focused POC with single draggable minion, reactive mode toggle, and Claude Code monitoring. Complex features (multiple minions, levels, effects) deferred to post-POC.

**Next Steps:** Transition to implementation planning via writing-plans skill.
