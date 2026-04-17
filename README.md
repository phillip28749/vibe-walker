<div align="center">

![Vibe Walker Wallpaper](wallpaper/wall%20paper.png)
</div>

A fun Windows desktop app featuring an interactive pixel assistant that responds to Claude Code activity.

> **✨ POC Release:** Interactive Desktop Pet with drag-and-drop, system tray control, and hybrid reactive/independent modes!

## POC Features (Interactive Desktop Pet)

### New in POC
- **Draggable Character**: Click and drag the minion anywhere on screen
- **Gravity Physics**: Released minion drops smoothly back to baseline height
- **System Tray Control**: Always-running app with reactive mode toggle
- **Hybrid Modes**: 
  - **Reactive Mode ON**: Minion visible, walks when Claude Code is active, idles when not
  - **Reactive Mode OFF**: Minion hidden
- **Interactive States**: HIDDEN, IDLE, WALKING, DRAGGED, DROPPING

### Controls
- **Left Click + Drag**: Pick up and move the minion
- **System Tray Right-Click**: Toggle reactive mode or exit
- **Reactive Mode ON**: Minion walks when Claude Code is active, idles when not
- **Reactive Mode OFF**: Minion disappears

### Architecture
- **Pygame**: Sprite rendering, drag-and-drop physics, 60 FPS animation
- **PyQt5**: System tray, window management, Qt-Pygame integration
- **Hybrid Design**: Leverages strengths of both frameworks

## Legacy Features

- **Responsive Character**: Pixel character appears when you send messages to Claude Code
- **Animated Walking**: Character walks back and forth across the screen while Claude processes
- **Idle Behavior**: Stops and stands still after Claude finishes
- **Interrupt Detection**: Automatically detects when you interrupt queries
- **Lightweight**: Minimal CPU and memory usage
- **Customizable**: Configure behavior via JSON file

## Requirements

- Windows 10 or 11
- Python 3.8 or higher
- PyQt5 5.15.9
- Pygame 2.5.2
- Pillow 10.0.0
- psutil
- pytest (for testing)

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/vibe-walker.git
   cd vibe-walker
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app** (automatically handles all setup):
   ```bash
   python src/main.py
   ```
   
   This automatically:
   - Generates sprites if they don't exist
   - Configures Claude Code hooks in `~/.claude/settings.json`
   - Creates a backup of your existing settings
   - Starts the desktop character monitor

That's it! The character will appear on your taskbar when you use Claude Code.

## Usage

### Running the Application

From the project root directory:

```bash
python src/main.py
```

On first run, this automatically sets up everything (hooks, sprites, config). On subsequent runs, it simply starts the character monitor.

### Using Claude Code

Simply use Claude Code normally in this project! The character will automatically:
- **Appear and walk** when you send a message to Claude Code
- **Stop and stand idle** when Claude finishes processing
- **Disappear** after 7 seconds of inactivity

The `.claude/settings.json` hooks automatically write trace events that the monitor detects.

### Important Notes

- **Only ONE instance** should run at a time - the application will prevent multiple instances
- If you see multiple characters, stop extra Python processes and run a single instance
- The application runs in the background with no visible window (except the character)

### Controls

- **Start character monitor**: `python src/main.py` (from project root)
- **Use Claude Code**: Just chat normally - the character appears automatically!
- **Stop monitor**: Press `Ctrl+C` in the terminal running main.py
- To run on startup: See the "Run on Startup" section below

## Configuration

Edit `config.json` to customize behavior:

```json
{
  "poll_interval_ms": 2000,
  "idle_timeout_sec": 30,
  "animation_fps": 7,
  "movement_speed_px": 2,
  "sprite_size": 64,
   "window_bottom_offset": 50,
   "trace_file_path": "trace/query_events.jsonl",
   "trace_poll_interval_ms": 500
}
```

### Configuration Options

- **poll_interval_ms**: Legacy setting (not currently used)
- **idle_timeout_sec**: How long character stands idle before disappearing (seconds, default: 7)
- **animation_fps**: Animation frames per second
- **movement_speed_px**: Movement speed in pixels per frame
- **sprite_size**: Size of sprite images in pixels
- **window_bottom_offset**: Distance from bottom of screen (pixels)
- **trace_file_path**: JSONL file where Claude Code hooks write lifecycle events
- **trace_poll_interval_ms**: How often to read new trace events (milliseconds, default: 500)

## How It Works

1. **Global Hooks**: Configured in `~/.claude/settings.json` (works in ALL repos)
   - `UserPromptSubmit` → writes `query_started` event (also closes interrupted queries)
   - `Stop` → writes `query_finished` when query completes
   - `StopFailure` → writes `query_finished` when query fails
   - Events are written to `<repo>/trace/query_events.jsonl`

2. **Trace Monitoring**: ActivityMonitor reads the trace file and detects:
   - When queries start (character appears and walks)
   - When queries finish (character stops and goes idle)
   - Orphaned queries (stuck states)

3. **State Management**: Character has 4 states:
   - `HIDDEN` - Not visible
   - `WALKING_RIGHT/LEFT` - Active query running
   - `IDLE` - Query finished, standing still for 7 seconds

4. **Animation**: Sprite-based animation with:
   - Walk cycles (left and right)
   - Idle pose
   - Fade-away effect when disappearing

5. **Window Overlay**: Transparent, click-through PyQt5 window above taskbar

## Customizing the Character

### Creating Custom Sprites

Replace the sprites in the `sprites/` folder with your own 64x64 PNG images:

- `idle.png` - Standing still pose
- `walk_left_1.png` - Walking left, frame 1
- `walk_left_2.png` - Walking left, frame 2
- `walk_right_1.png` - Walking right, frame 1
- `walk_right_2.png` - Walking right, frame 2

All sprites should have a transparent background.

### Regenerating Default Sprites

To recreate the default sprites:

```bash
python generate_sprites.py
```

## Run on Startup (Windows)

### Option 1: Task Scheduler (Recommended)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: "When I log on"
4. Action: "Start a program"
5. Program: `pythonw.exe`
6. Arguments: `src/main.py`
7. Start in: `C:\path\to\vibe-walker`

### Option 2: Startup Folder

1. Press `Win+R`, type `shell:startup`, press Enter
2. Create a shortcut to run the application
3. Target: `pythonw.exe src/main.py`
4. Start in: `C:\path\to\vibe-walker`

**Note**: Use `pythonw.exe` instead of `python.exe` to run without a console window.

## Troubleshooting

### Character doesn't appear

- **Check monitor is running**: Run `python src/main.py` from the **project root**
- **Check console output**: Should show "[ANIMATOR] Loaded sprite: ..." messages
- **Verify trace events**: Check that `trace/query_events.jsonl` is being created when you send messages
- **Ensure PyQt5 is installed**: `pip install PyQt5`
- **Re-run setup**: If hooks aren't working, run `python src/main.py` again to reconfigure

### Character appears behind taskbar

- Adjust `window_bottom_offset` in `config.json` (increase the value)
- Check if "always on top" is working (may conflict with certain Windows settings)

### Animation is choppy

- Reduce `animation_fps` in `config.json`
- Close other resource-intensive applications

### Character doesn't disappear after finishing (Stuck Walking)

This happens when queries don't get properly closed (orphaned queries).

**Quick fix:**
```bash
# Run the cleanup script
python cleanup_orphaned_queries.py

# Or manually clear the trace file
echo "" > trace/query_events.jsonl
```

**Why this happens:**
- The Stop hook didn't fire properly
- Query was interrupted before completion
- Multiple hook configurations (check for duplicate hooks in local `.claude/settings.json`)

**Prevention:**
- Don't add hooks to local `.claude/settings.json` in the repo (only use global settings)
- Run cleanup script when character gets stuck

## Development

### Project Structure

```
vibe-walker/
├── .claude/                   # Local development settings (gitignored)
├── src/
│   ├── __init__.py            # Package initialization
│   ├── main.py                # Application entry point
│   ├── config.py              # Configuration management
│   ├── state_manager.py       # State machine logic
│   ├── activity_monitor.py    # Trace event monitoring
│   ├── animator.py            # Sprite animation
│   ├── character_window.py    # Transparent window overlay
│   └── particle_system.py     # Particle effects
├── sprites/                   # Sprite images (64x64 PNG)
├── trace/                     # Query event logs (auto-created)
│   └── query_events.jsonl     # Trace events from Claude Code
├── config.json                # Application configuration (portable)
├── setup.py                   # Automated setup script
├── cleanup_orphaned_queries.py # Manual cleanup utility
├── cleanup.bat / .sh          # Quick cleanup scripts
├── requirements.txt           # Python dependencies
├── generate_sprites.py        # Sprite generation utility
├── GLOBAL_SETUP.md            # Global setup documentation
└── README.md                  # This file
```

### Adding New Features

Some ideas for enhancements:

- System tray icon with menu
- Multiple character designs
- Different behaviors based on activity type
- Sound effects
- Customization UI

## License

MIT License - See [LICENSE](LICENSE) file for details

## Credits

Created with Claude Code

---

Enjoy your new desktop companion! If you encounter any issues, please check the troubleshooting section or open an issue on GitHub.
