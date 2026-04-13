# Vibe Walker 🚶

A fun Windows desktop application that displays a walking pixel character on your taskbar whenever Claude Code is running!

## Features

- **Responsive Character**: Pixel character appears when Claude Code starts
- **Animated Walking**: Character walks back and forth across the taskbar
- **Idle Behavior**: Stops and stands still for 30 seconds after Claude Code closes, then disappears
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

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate sprites** (already done if sprites/ folder exists):
   ```bash
   python generate_sprites.py
   ```

## Usage

### Running the Application

**Recommended Method (Windows):**

Double-click one of the batch files:
- **`run_vibewalker.bat`** - Start the application
- **`stop_vibewalker.bat`** - Stop the application
- **`check_status.bat`** - Check if it's running

**Manual Method:**

From the project root directory:

```bash
python -m src.main
```

Or navigate to the src directory:

```bash
cd src
python main.py
```

The application will start monitoring for Claude Code processes. When Claude Code is detected, the character will appear and start walking on your taskbar!

### Important Notes

- **Only ONE instance** should run at a time - the application will prevent multiple instances
- If you see multiple characters, stop all instances with `stop_vibewalker.bat`
- The application runs in the background with no visible window (except the character)

### Controls

- **Start**: Run `run_vibewalker.bat` or `python src/main.py`
- **Stop**: Run `stop_vibewalker.bat` or press `Ctrl+C` in terminal
- **Check Status**: Run `check_status.bat`
- To run on startup: See the "Run on Startup" section below

## Configuration

Edit `config.json` to customize behavior:

```json
{
  "process_names": ["claude.exe", "Claude.exe", "claude-code.exe", "Code.exe"],
  "poll_interval_ms": 2000,
  "idle_timeout_sec": 30,
  "animation_fps": 7,
  "movement_speed_px": 2,
  "sprite_size": 64,
  "window_bottom_offset": 50
}
```

### Configuration Options

- **process_names**: List of process names to monitor for Claude Code
- **poll_interval_ms**: How often to check for processes (milliseconds)
- **idle_timeout_sec**: How long to wait before hiding after Claude Code stops (seconds)
- **animation_fps**: Animation frames per second
- **movement_speed_px**: Movement speed in pixels per frame
- **sprite_size**: Size of sprite images in pixels
- **window_bottom_offset**: Distance from bottom of screen (pixels)

## How It Works

1. **Process Monitoring**: Continuously checks for Claude Code processes
2. **State Management**: Tracks character state (Hidden, Walking Left, Walking Right, Idle)
3. **Animation**: Cycles through sprite frames for smooth walking animation
4. **Window Overlay**: Displays character in a transparent, click-through window above taskbar

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
6. Arguments: `-m src.main`
7. Start in: `C:\path\to\vibe-walker`

### Option 2: Startup Folder

1. Press `Win+R`, type `shell:startup`, press Enter
2. Create a shortcut to run the application
3. Target: `pythonw.exe -m src.main`
4. Start in: `C:\path\to\vibe-walker`

**Note**: Use `pythonw.exe` instead of `python.exe` to run without a console window.

## Troubleshooting

### Character doesn't appear

- Check if Claude Code process name matches `config.json`
- Verify sprites loaded successfully (check console output)
- Ensure PyQt5 is installed: `pip install PyQt5`

### Character appears behind taskbar

- Adjust `window_bottom_offset` in `config.json` (increase the value)
- Check if "always on top" is working (may conflict with certain Windows settings)

### Animation is choppy

- Reduce `animation_fps` in `config.json`
- Close other resource-intensive applications

### Character doesn't disappear after 30 seconds

- Check console logs for state transitions
- Verify `idle_timeout_sec` in `config.json`

## Development

### Project Structure

```
vibe-walker/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Application entry point
│   ├── config.py             # Configuration management
│   ├── state_manager.py      # State machine
│   ├── process_monitor.py    # Process detection
│   ├── animator.py           # Sprite animation
│   └── character_window.py   # Window overlay
├── sprites/                  # Sprite images
├── config.json               # Configuration file
├── requirements.txt          # Python dependencies
├── generate_sprites.py       # Sprite generation script
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
