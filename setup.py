"""Setup script for Vibe Walker - Configures global Claude Code hooks."""
import json
import os
import sys
from pathlib import Path

# Hook version - increment this when hooks need updating
HOOK_VERSION = "2.0.0"

def setup_global_hooks(force=False):
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

    # Helper function to create per-tool PermissionRequest hooks
    def create_permission_request_hooks():
        """Create PermissionRequest hooks for each tool type with accurate tool names."""
        tools = ['Bash', 'Write', 'Edit', 'Read', 'Grep', 'Glob', 'Agent', 'Skill', 'Config']
        hooks = []

        for tool_name in tools:
            hook = {
                "matcher": tool_name,
                "hooks": [{
                    "type": "command",
                    "command": f'bash -c \'TRACE_FILE="{bash_trace_path}"; mkdir -p "$(dirname "$TRACE_FILE")"; QUERY_ID=$(cat /tmp/vibe_walker_current_query.txt 2>/dev/null || echo "query_$(date +%s%N)"); TIMESTAMP=$(date +%s.%N 2>/dev/null || date +%s); echo "{{\\"query_id\\":\\"$QUERY_ID\\",\\"event_type\\":\\"action_needed\\",\\"timestamp\\":$TIMESTAMP,\\"payload\\":{{\\"trigger\\":\\"permission_request\\",\\"tool_name\\":\\"{tool_name}\\"}}}}" >> "$TRACE_FILE"\'',
                    "async": True
                }]
            }
            hooks.append(hook)

        return hooks

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

    pre_tool_use_hook = {
        "matcher": "Bash|Write|Edit|Agent|Skill|Config",
        "hooks": [
            {
                "type": "command",
                "command": f'bash -c \'TRACE_FILE="{bash_trace_path}"; mkdir -p "$(dirname "$TRACE_FILE")"; QUERY_ID=$(cat /tmp/vibe_walker_current_query.txt 2>/dev/null || echo "query_$(date +%s%N)"); TOOL_NAME="${{TOOL_NAME:-unknown}}"; TIMESTAMP=$(date +%s.%N 2>/dev/null || date +%s); echo "{{\\"query_id\\":\\"$QUERY_ID\\",\\"event_type\\":\\"action_needed\\",\\"timestamp\\":$TIMESTAMP,\\"payload\\":{{\\"trigger\\":\\"pre_tool_use\\",\\"tool_name\\":\\"$TOOL_NAME\\"}}}}" >> "$TRACE_FILE"\'',
                "async": True
            }
        ]
    }

    notification_hook = {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": f'bash -c \'TRACE_FILE="{bash_trace_path}"; mkdir -p "$(dirname "$TRACE_FILE")"; QUERY_ID=$(cat /tmp/vibe_walker_current_query.txt 2>/dev/null || echo "query_$(date +%s%N)"); TIMESTAMP=$(date +%s.%N 2>/dev/null || date +%s); echo "{{\\"query_id\\":\\"$QUERY_ID\\",\\"event_type\\":\\"action_needed\\",\\"timestamp\\":$TIMESTAMP,\\"payload\\":{{\\"trigger\\":\\"notification\\"}}}}" >> "$TRACE_FILE"\'',
                "async": True
            }
        ]
    }

    post_tool_use_hook = {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": f'bash -c \'TRACE_FILE="{bash_trace_path}"; mkdir -p "$(dirname "$TRACE_FILE")"; QUERY_ID=$(cat /tmp/vibe_walker_current_query.txt 2>/dev/null || echo "query_$(date +%s%N)"); TOOL_NAME="${{TOOL_NAME:-unknown}}"; TIMESTAMP=$(date +%s.%N 2>/dev/null || date +%s); echo "{{\\"query_id\\":\\"$QUERY_ID\\",\\"event_type\\":\\"action_handled\\",\\"timestamp\\":$TIMESTAMP,\\"payload\\":{{\\"trigger\\":\\"post_tool_use\\",\\"tool_name\\":\\"$TOOL_NAME\\",\\"success\\":true}}}}" >> "$TRACE_FILE"\'',
                "async": True
            }
        ]
    }

    post_tool_use_failure_hook = {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": f'bash -c \'TRACE_FILE="{bash_trace_path}"; mkdir -p "$(dirname "$TRACE_FILE")"; QUERY_ID=$(cat /tmp/vibe_walker_current_query.txt 2>/dev/null || echo "query_$(date +%s%N)"); TOOL_NAME="${{TOOL_NAME:-unknown}}"; TIMESTAMP=$(date +%s.%N 2>/dev/null || date +%s); echo "{{\\"query_id\\":\\"$QUERY_ID\\",\\"event_type\\":\\"action_handled\\",\\"timestamp\\":$TIMESTAMP,\\"payload\\":{{\\"trigger\\":\\"post_tool_use_failure\\",\\"tool_name\\":\\"$TOOL_NAME\\",\\"success\\":false}}}}" >> "$TRACE_FILE"\'',
                "async": True
            }
        ]
    }

    permission_denied_hook = {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": f'bash -c \'TRACE_FILE="{bash_trace_path}"; mkdir -p "$(dirname "$TRACE_FILE")"; QUERY_ID=$(cat /tmp/vibe_walker_current_query.txt 2>/dev/null || echo "query_$(date +%s%N)"); TOOL_NAME="${{TOOL_NAME:-unknown}}"; TIMESTAMP=$(date +%s.%N 2>/dev/null || date +%s); echo "{{\\"query_id\\":\\"$QUERY_ID\\",\\"event_type\\":\\"action_denied\\",\\"timestamp\\":$TIMESTAMP,\\"payload\\":{{\\"trigger\\":\\"permission_denied\\",\\"tool_name\\":\\"$TOOL_NAME\\"}}}}" >> "$TRACE_FILE"\'',
                "async": True
            }
        ]
    }

    # Update hooks
    settings["hooks"]["UserPromptSubmit"] = [user_prompt_hook]
    settings["hooks"]["Stop"] = [stop_hook]
    settings["hooks"]["StopFailure"] = [stop_failure_hook]
    settings["hooks"]["PermissionRequest"] = create_permission_request_hooks()  # New: accurate permission dialog detection
    settings["hooks"]["PermissionDenied"] = [permission_denied_hook]  # New: detect user rejections
    settings["hooks"]["PostToolUse"] = [post_tool_use_hook]  # Updated: includes success flag
    settings["hooks"]["PostToolUseFailure"] = [post_tool_use_failure_hook]  # New: detect tool failures
    settings["hooks"]["Notification"] = [notification_hook]
    # PreToolUse removed - PermissionRequest is more accurate

    # Store version metadata
    if "vibe_walker" not in settings:
        settings["vibe_walker"] = {}
    settings["vibe_walker"]["hook_version"] = HOOK_VERSION
    from datetime import datetime
    settings["vibe_walker"]["last_updated"] = datetime.now().isoformat()

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
    print(f"[SUCCESS] Vibe Walker hooks configured! (v{HOOK_VERSION})")
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
        # Check for --force flag
        force = "--force" in sys.argv
        if force:
            print("[FORCE] Force update enabled - will overwrite existing hooks\n")

        success = setup_global_hooks(force=force)
        if not success:
            exit(1)
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
