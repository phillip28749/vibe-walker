"""Setup script for Vibe Walker - Configures global Claude Code hooks."""
import json
import os
from pathlib import Path

def setup_global_hooks():
    """Configure global Claude Code hooks with the correct trace file path."""

    print("=" * 60)
    print("VIBE WALKER - Setup")
    print("=" * 60)
    print()

    # Get current repo directory
    repo_dir = Path(__file__).parent.resolve()
    trace_file = repo_dir / "trace" / "query_events.jsonl"

    # Convert to forward slashes for bash compatibility
    trace_file_str = str(trace_file).replace("\\", "/")

    # Convert to bash-compatible path format
    bash_trace_path = trace_file_str.replace("C:/", "/c/")

    print(f"Repository directory: {repo_dir}")
    print(f"Trace file will be: {trace_file}")
    print()

    # Get global Claude settings path
    home = Path.home()
    claude_settings = home / ".claude" / "settings.json"

    if not claude_settings.parent.exists():
        print(f"[ERROR] Claude directory not found: {claude_settings.parent}")
        print("Please make sure Claude Code is installed.")
        return False

    # Load existing settings or create new
    if claude_settings.exists():
        print(f"[FOUND] Existing settings: {claude_settings}")
        with open(claude_settings, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    else:
        print(f"[CREATE] New settings file: {claude_settings}")
        settings = {}

    # Ensure hooks section exists
    if "hooks" not in settings:
        settings["hooks"] = {}

    # Create hook commands with the correct trace file path
    user_prompt_hook = {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": f'bash -c \'TRACE_FILE="{bash_trace_path}"; mkdir -p "$(dirname "$TRACE_FILE")"; PREV_QUERY_ID=$(cat /tmp/vibe_walker_current_query.txt 2>/dev/null); if [ -n "$PREV_QUERY_ID" ]; then TIMESTAMP=$(date +%s.%N 2>/dev/null || date +%s); echo "{{\\"query_id\\":\\"$PREV_QUERY_ID\\",\\"event_type\\":\\"query_finished\\",\\"timestamp\\":$TIMESTAMP,\\"payload\\":{{\\"reason\\":\\"interrupted\\"}}}}" >> "$TRACE_FILE"; fi; QUERY_ID="query_$(date +%s%N)"; echo "$QUERY_ID" > /tmp/vibe_walker_current_query.txt; TIMESTAMP=$(date +%s.%N 2>/dev/null || date +%s); echo "{{\\"query_id\\":\\"$QUERY_ID\\",\\"event_type\\":\\"query_started\\",\\"timestamp\\":$TIMESTAMP,\\"payload\\":{{}}}}" >> "$TRACE_FILE"\'',
                "async": True
            }
        ]
    }

    stop_hook = {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": f'bash -c \'TRACE_FILE="{bash_trace_path}"; mkdir -p "$(dirname "$TRACE_FILE")"; QUERY_ID=$(cat /tmp/vibe_walker_current_query.txt 2>/dev/null || echo "query_$(date +%s%N)"); TIMESTAMP=$(date +%s.%N 2>/dev/null || date +%s); echo "{{\\"query_id\\":\\"$QUERY_ID\\",\\"event_type\\":\\"query_finished\\",\\"timestamp\\":$TIMESTAMP,\\"payload\\":{{}}}}" >> "$TRACE_FILE"; rm -f /tmp/vibe_walker_current_query.txt\'',
                "async": True
            }
        ]
    }

    stop_failure_hook = {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": f'bash -c \'TRACE_FILE="{bash_trace_path}"; mkdir -p "$(dirname "$TRACE_FILE")"; QUERY_ID=$(cat /tmp/vibe_walker_current_query.txt 2>/dev/null || echo "query_$(date +%s%N)"); TIMESTAMP=$(date +%s.%N 2>/dev/null || date +%s); echo "{{\\"query_id\\":\\"$QUERY_ID\\",\\"event_type\\":\\"query_finished\\",\\"timestamp\\":$TIMESTAMP,\\"payload\\":{{\\"reason\\":\\"failure\\"}}}}" >> "$TRACE_FILE"; rm -f /tmp/vibe_walker_current_query.txt\'',
                "async": True
            }
        ]
    }

    # Update hooks
    settings["hooks"]["UserPromptSubmit"] = [user_prompt_hook]
    settings["hooks"]["Stop"] = [stop_hook]
    settings["hooks"]["StopFailure"] = [stop_failure_hook]

    # Backup existing settings
    if claude_settings.exists():
        backup_path = claude_settings.with_suffix('.json.backup')
        print(f"[BACKUP] Creating backup: {backup_path}")
        with open(claude_settings, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(backup_content)

    # Write updated settings
    print(f"[UPDATE] Writing hooks to: {claude_settings}")
    with open(claude_settings, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)

    print()
    print("=" * 60)
    print("[SUCCESS] Vibe Walker hooks configured!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Generate sprites: python generate_sprites.py")
    print("3. Run Vibe Walker: python src/main.py")
    print()
    print("The pixel character will appear when you use Claude Code!")
    print()

    return True

if __name__ == "__main__":
    try:
        success = setup_global_hooks()
        if not success:
            exit(1)
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
