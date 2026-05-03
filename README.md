<div align="center">

![Vibe Walker Wallpaper](sprites/wallpaper/wall%20paper.png)
</div>

A Windows desktop pet that reacts to both Claude Code and Codex activity.

> **POC Release:** Interactive desktop companion with drag-and-drop, reactive Vibe mode, and multi-mob support for overlapping sessions.

## Features

- Reacts to both Claude Code and Codex activity
- Vibe mode: walks while sessions are active, idles when they are not
- Multi-mob support for overlapping active sessions
- Companion mobs spawn with climb-out animation and despawn with fade animation
- Permission requests trigger the primary mob's waving state
- Drag-and-drop with gravity and drop-back behavior
- System tray controls for reactive mode and exit

## Current Behavior

- 1 active Claude or Codex session: primary mob is active
- 2 active sessions at the same time: primary mob plus 1 companion
- More overlapping sessions: additional companion mobs appear
- When a companion session ends, that extra mob fades out instead of disappearing instantly

Claude and Codex are detected differently:

- Claude Code: hook-based detection via `trace/query_events.jsonl`
- Codex: session-log detection via `~/.codex/sessions`

On Windows, `~/.codex/sessions` usually resolves to:

`C:\Users\<YourUser>\.codex\sessions`

## Requirements

- Windows 10 or 11
- Python 3.8+
- PyQt5
- Pygame
- Pillow
- psutil

## Quick Start

1. Clone the repo:

```bash
git clone https://github.com/yourusername/vibe-walker.git
cd vibe-walker
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure Claude hooks:

```bash
python setup.py
```

4. Start the app:

```bash
python src/main.py
```

## Setup Notes

`setup.py` configures Claude Code hooks globally through `~/.claude/settings.json`.

Codex does not currently use an installed hook in this project. Instead, Vibe Walker monitors Codex session logs from `~/.codex/sessions`.

So the current integration model is:

- Claude: hook events written into this repo's trace file
- Codex: activity inferred from Codex-generated session JSONL logs

## Usage

Run the app from the project root:

```bash
python src/main.py
```

Then use Claude Code or Codex normally.

What happens:

- active session starts -> mob appears/walks
- permission request -> primary mob waves
- overlapping sessions -> extra companion mobs appear
- extra session ends -> companion fades out

## Controls

- Left click + drag: move the primary mob
- System tray right-click: toggle reactive mode or exit

Companion mobs are visual companions only. They are not draggable and do not currently wave on permission requests.

## Configuration

Edit `config.json` to customize behavior. Important fields include:

- `behavior_mode`: use `"vibe"` for activity-driven behavior
- `reactive_mode_enabled`: show or hide the reactive mob system
- `trace_file_path`: Claude activity trace file
- `trace_poll_interval_ms`: activity polling interval
- `codex_activity_enabled`: enable Codex activity monitoring
- `codex_sessions_dir`: Codex sessions directory
- `sprite_size`
- `animation_fps`
- `movement_speed_px`

## How It Works

1. Claude hooks write lifecycle events into `trace/query_events.jsonl`.
2. Codex writes its own session logs under `~/.codex/sessions`.
3. `ActivityMonitor` combines both sources into a shared active-session count.
4. `GameWindow` drives the primary mob.
5. `MobManager` creates companion mobs for extra overlapping sessions.

## Project Structure

```text
vibe-walker/
|-- src/
|   |-- activity_bridge.py
|   |-- activity_monitor.py
|   |-- companion_window.py
|   |-- config.py
|   |-- config_dialog.py
|   |-- drag_handler.py
|   |-- game_window.py
|   |-- main.py
|   |-- mob_manager.py
|   |-- sprite_manager.py
|   |-- state_machine.py
|   `-- system_tray.py
|-- sprites/
|-- tests/
|-- trace/
|-- config.json
|-- setup.py
`-- README.md
```

## Testing

Run the test suite with:

```bash
python -m pytest -q
```

## Troubleshooting

If the app does not react:

- make sure `python src/main.py` is running
- restart the app after code changes
- re-run `python setup.py` if Claude hook events are missing
- verify Claude trace output exists in `trace/query_events.jsonl`
- verify Codex session logs exist under `~/.codex/sessions`

If a second mob does not appear:

- ensure two sessions are active at the same time
- make sure reactive mode is enabled
- confirm you restarted after updating the app

## Credits

Created with Claude Code and Codex.
