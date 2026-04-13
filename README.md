# Vibe Walker 🚶

A fun Windows desktop application that displays a walking pixel character on your taskbar whenever Claude Code is running!

## Features

- **Responsive Character**: Pixel character appears when you send messages to Claude Code
- **Animated Walking**: Character walks back and forth across the taskbar while Claude processes
- **Idle Behavior**: Stops and stands still for 7 seconds after Claude finishes, then disappears
- **Interrupt Detection**: Automatically detects when you interrupt queries by sending a new message
- **Lightweight**: Minimal CPU and memory usage
- **Customizable**: Configure behavior via JSON file

## Requirements

- Windows 10 or 11
- Python 3.8 or higher
- PyQt5
- psutil
- Pillow

## Installation

1. **Clone or download this repository**:
   ```bash
   git clone https://github.com/yourusername/vibe-walker.git
   cd vibe-walker
   ```

2. **Set up Claude Code hooks** (required for automatic detection):
   ```bash
   cp .claude/settings.example.json .claude/settings.json
   ```
   
   This configures Claude Code to write trace events when you use it in this project.

3. **Create and activate a virtual environment**:

   PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   CMD:

   ```bat
   python -m venv .venv
   .\.venv\Scripts\activate.bat
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Generate sprites** (already done if sprites/ folder exists):
   ```bash
   python generate_sprites.py
   ```

## Usage

### Running the Application

From the project root directory:

```bash
python src/main.py
```

This starts the desktop character and monitors trace lifecycle events.

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

1. **Claude Code Hooks**: When you use Claude Code, hooks write lifecycle events to `trace/query_events.jsonl`
   - `UserPromptSubmit` → writes `query_started` (also closes interrupted queries)
   - `Stop` → writes `query_finished` when query completes normally
   - `StopFailure` → writes `query_finished` when query fails
2. **Interrupt Detection**: When you send a new message while a query is running, `UserPromptSubmit` automatically closes the previous query
3. **Trace Monitoring**: ActivityMonitor continuously reads trace events
4. **State Management**: Tracks character state (Hidden, Walking Left, Walking Right, Idle)
5. **Animation**: Cycles through sprite frames for smooth walking animation
6. **Window Overlay**: Displays character in a transparent, click-through window above taskbar

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

- **Verify hooks are set up**: Make sure you copied `.claude/settings.example.json` to `.claude/settings.json`
- **Check monitor is running**: Run `python src/main.py` from the **project root** (not from `src/` directory)
- **Check console output**: Should show "[ANIMATOR] Loaded sprite: ..." messages
- **Verify trace events**: Check that `trace/query_events.jsonl` is being created when you send messages
- **Ensure PyQt5 is installed**: `pip install PyQt5`

### Character appears behind taskbar

- Adjust `window_bottom_offset` in `config.json` (increase the value)
- Check if "always on top" is working (may conflict with certain Windows settings)

### Animation is choppy

- Reduce `animation_fps` in `config.json`
- Close other resource-intensive applications

### Character doesn't disappear after finishing

- **Check console logs** for state transitions
- **Verify idle timeout**: Check `idle_timeout_sec` in `config.json` (default: 7 seconds)
- **Interrupt detection**: Send a new message to Claude Code to force cleanup of stuck queries
- **Check trace file**: Look at `trace/query_events.jsonl` - each `query_started` should have a matching `query_finished`

### Character stays visible after interruption

- **Send any message** to Claude Code - this triggers cleanup of interrupted queries
- **Restart the monitor** if the character is stuck

## Development

### Project Structure

```
vibe-walker/
├── .claude/
│   └── settings.example.json # Claude Code hooks configuration template
├── src/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Application entry point
│   ├── config.py             # Configuration management
│   ├── state_manager.py      # State machine logic
│   ├── activity_monitor.py   # Trace event monitoring
│   ├── animator.py           # Sprite animation
│   ├── character_window.py   # Transparent window overlay
│   └── claude_trace_runner.py # Optional: Manual SDK query runner (for testing)
├── sprites/                  # Sprite images (64x64 PNG)
├── config.json               # Application configuration
├── requirements.txt          # Python dependencies
├── generate_sprites.py       # Sprite generation utility
└── README.md                 # This file
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
