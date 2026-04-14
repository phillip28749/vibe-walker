# Vibe Walker - Global Setup

Run Vibe Walker **once** as a background service that works with **all your repos**.

## One-Time Setup

### 1. Start Vibe Walker (runs in background)

From this directory:
```bash
.\.venv\Scripts\pythonw.exe src\main.py
```

**Note:** Use `pythonw.exe` (not `python.exe`) to run without a console window.

The app will now monitor: `C:/Users/P1363787/.vibe-walker/trace/query_events.jsonl`

### 2. Copy hooks to any repo where you want the character

In **each other repository** where you want Vibe Walker to work:

```bash
# Create .claude directory if it doesn't exist
mkdir -p .claude

# Copy the global settings file
cp C:/Users/P1363787/Documents/GitHub/vibe-walker/.claude/settings.global.json .claude/settings.json
```

**That's it!** Now when you use Claude Code in that repo, the character will appear.

## How It Works

1. **Vibe Walker runs once** from this directory, monitoring the global trace file
2. **Each repo's hooks** write to the same global trace file (`$HOME/.vibe-walker/trace/query_events.jsonl`)
3. **Character appears** whenever you use Claude Code in ANY repo with the hooks installed

## To Add Vibe Walker to a New Repo (1 command)

```bash
cp C:/Users/P1363787/Documents/GitHub/vibe-walker/.claude/settings.global.json .claude/settings.json
```

## Run Vibe Walker on Windows Startup

Use Task Scheduler or Startup folder to run:
- **Program:** `C:\Users\P1363787\Documents\GitHub\vibe-walker\.venv\Scripts\pythonw.exe`
- **Arguments:** `src\main.py`
- **Start in:** `C:\Users\P1363787\Documents\GitHub\vibe-walker`

## Check if Vibe Walker is Running

```powershell
Get-Process python* | Where-Object {$_.CommandLine -like '*main.py*'}
```

Or just send a message to Claude Code - if the character appears, it's working!
