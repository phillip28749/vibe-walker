"""Main application entry point for vibe-walker."""
import sys
import os
import json
import subprocess
import psutil
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from config import Config
from state_manager import StateManager
from activity_monitor import ActivityMonitor
from animator import Animator
from character_window import CharacterWindow

def check_setup():
    """Check if Vibe Walker is properly set up and offer to fix if not."""
    repo_dir = Path(__file__).parent.parent
    issues = []

    # Check 1: Sprites exist
    sprites_dir = repo_dir / "sprites"
    required_sprites = ["idle.png", "walk_left_1.png", "walk_left_2.png",
                       "walk_right_1.png", "walk_right_2.png"]
    missing_sprites = [s for s in required_sprites if not (sprites_dir / s).exists()]

    if missing_sprites:
        issues.append(("sprites", f"Missing sprites: {', '.join(missing_sprites)}"))

    # Check 2: Global hooks configured
    claude_settings = Path.home() / ".claude" / "settings.json"
    hooks_configured = False

    if claude_settings.exists():
        try:
            with open(claude_settings, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            hooks = settings.get("hooks", {})
            # Check if Vibe Walker hooks exist
            if "UserPromptSubmit" in hooks and "Stop" in hooks:
                # Simple check - if hooks mention vibe-walker or trace
                hook_cmd = str(hooks.get("UserPromptSubmit", [{}])[0])
                if "vibe-walker" in hook_cmd or "trace/query_events" in hook_cmd:
                    hooks_configured = True
        except:
            pass

    if not hooks_configured:
        issues.append(("hooks", "Claude Code hooks not configured"))

    # If there are issues, offer to fix them
    if issues:
        print("\n" + "!" * 50)
        print("SETUP REQUIRED")
        print("!" * 50)
        print("\nThe following issues need to be fixed:\n")

        for issue_type, message in issues:
            print(f"  - {message}")

        print("\n" + "=" * 50)
        print("AUTOMATIC FIX")
        print("=" * 50)

        # Auto-fix sprites
        if any(i[0] == "sprites" for i in issues):
            print("\n[SPRITES] Generating missing sprites...")
            try:
                generate_script = repo_dir / "generate_sprites.py"
                if generate_script.exists():
                    subprocess.run([sys.executable, str(generate_script)],
                                 cwd=str(repo_dir), check=True)
                    print("[OK] Sprites generated!")
                else:
                    print("[ERROR] generate_sprites.py not found")
                    return False
            except Exception as e:
                print(f"[ERROR] Failed to generate sprites: {e}")
                return False

        # Auto-fix hooks
        if any(i[0] == "hooks" for i in issues):
            print("\n[HOOKS] Configuring Claude Code hooks...")
            print("\nVibe Walker needs to configure global Claude Code hooks.")
            print("This will modify: ~/.claude/settings.json")
            print("(A backup will be created)")

            response = input("\nConfigure hooks now? [Y/n]: ").strip().lower()

            if response in ['', 'y', 'yes']:
                try:
                    setup_script = repo_dir / "setup.py"
                    if setup_script.exists():
                        subprocess.run([sys.executable, str(setup_script)],
                                     cwd=str(repo_dir), check=True)
                        print("\n[OK] Hooks configured!")
                    else:
                        print("[ERROR] setup.py not found")
                        print("\nManual setup required:")
                        print(f"  cd {repo_dir}")
                        print("  python setup.py")
                        return False
                except Exception as e:
                    print(f"[ERROR] Failed to configure hooks: {e}")
                    return False
            else:
                print("\n[SKIP] Hooks not configured.")
                print("The character won't appear until hooks are set up.")
                print(f"\nRun this later: python {repo_dir / 'setup.py'}")
                print()

        print("\n" + "=" * 50)
        print("Setup complete! Starting Vibe Walker...")
        print("=" * 50)
        print()

    return True

def check_already_running():
    """Check if another instance of vibe-walker is already running."""
    current_pid = os.getpid()
    current_dir = os.path.dirname(os.path.abspath(__file__))

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip the current process
            if proc.info['pid'] == current_pid:
                continue

            # Check if it's a Python process running main.py from this directory
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline', [])
                if cmdline:
                    cmdline_str = ' '.join(str(arg) for arg in cmdline)
                    # Check if it's running main.py from vibe-walker directory
                    if 'main.py' in cmdline_str and 'vibe-walker' in cmdline_str:
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return False

def main():
    """Main application entry point."""
    print("=" * 50)
    print("VIBE WALKER - Taskbar Pixel Character")
    print("=" * 50)

    # Check setup and auto-fix if needed
    if not check_setup():
        print("\n[ERROR] Setup incomplete. Please fix the issues above.")
        sys.exit(1)

    # Check for existing instances (disabled for testing)
    # if check_already_running():
    #     print("\n[ERROR] Another instance of Vibe Walker is already running!")
    #     print("Please close the existing instance before starting a new one.")
    #     print("Use 'stop_vibewalker.bat' or 'taskkill /F /IM python.exe'\n")
    #     print("=" * 50)
    #     sys.exit(1)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Don't quit when window is hidden

    # Load configuration
    config = Config("config.json")

    # Get screen dimensions
    screen = app.primaryScreen()
    screen_geometry = screen.availableGeometry()
    screen_width = screen_geometry.width()
    screen_height = screen_geometry.height()
    print(f"[MAIN] Screen size: {screen_width}x{screen_height}")

    # Initialize state manager
    state_manager = StateManager(config)
    print("[MAIN] State manager initialized")

    # Initialize animator
    animator = Animator(config, screen_width, screen_height)
    print("[MAIN] Animator initialized")

    # Initialize character window
    window = CharacterWindow(config)
    print("[MAIN] Character window initialized")

    # Initialize activity monitor
    activity_monitor = ActivityMonitor(config)
    print("[MAIN] Activity monitor initialized")

    # Connect signals and slots
    print("[MAIN] Connecting signals...")

    # Activity monitor -> State manager
    activity_monitor.activity_started.connect(state_manager.on_claude_started)
    activity_monitor.activity_stopped.connect(state_manager.on_claude_stopped)

    # State manager -> Animator and Window
    state_manager.state_changed.connect(animator.on_state_changed)
    state_manager.state_changed.connect(window.on_state_changed)

    # Animator -> Window
    animator.sprite_changed.connect(window.update_sprite)
    animator.position_changed.connect(window.update_position)

    # Animator -> State manager (edge reached)
    animator.edge_reached.connect(state_manager.reverse_direction)

    # Fade away animation signals
    state_manager.fade_away_triggered.connect(animator.start_fade_away)
    animator.animation_sequence_complete.connect(state_manager.on_fade_away_complete)

    print("[MAIN] All signals connected")

    # Start activity monitor thread
    activity_monitor.start()
    print("[MAIN] Activity monitor started")

    print()
    print("=" * 50)
    print("VIBE WALKER STARTED SUCCESSFULLY!")
    print("=" * 50)
    print()
    print("The pixel character will appear on your taskbar when")
    print("you use Claude Code in any repository!")
    print()
    print(f"Monitoring: {config.trace_file_path}")
    print(f"Idle timeout: {config.idle_timeout_sec} seconds")
    print()
    print("Press Ctrl+C to exit")
    print("=" * 50)

    # Run application
    try:
        exit_code = app.exec_()
    except KeyboardInterrupt:
        print("\n[MAIN] Keyboard interrupt received")
        exit_code = 0

    # Cleanup
    print("[MAIN] Shutting down...")
    activity_monitor.stop()
    activity_monitor.wait(2000)  # Wait up to 2 seconds for thread to finish

    print("[MAIN] Goodbye!")
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
